import codecs
import math
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote, urlsplit

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import AppError, ImportRateLimitedError, SourceImportError
from common.imports.extract import extract_product
from common.imports.safe_fetch import FetchError, SafeFetcher
from enums.attachments_enum import AttachmentPurposeEnum
from enums.imports_enum import ImportKindEnum
from managers.imports.mng_import_requests import ImportRequestManager
from models.imports.mdl_import_request import ImportRequest
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.imports.sch_import import (
    ImportImagesRequestSchema,
    ImportImagesResultSchema,
    ImportPreviewRequestSchema,
    ImportPreviewSchema,
    ImportSizeSchema,
)
from services.attachments.svc_attachments import MB, AttachmentService
from services.users.svc_users import UserService
from settings.imports_settings import ImportsSettings

PAGE_LIMIT = 3 * MB
IMAGE_LIMIT = 10 * MB
HTML_TYPES = ("text/html", "application/xhtml+xml")
_CHARSET = re.compile(rb"charset=[\"']?([A-Za-z0-9_-]+)", re.IGNORECASE)


class ImportService:
    """Reads public product pages (Open Graph, schema.org JSON-LD) into a reference for a design.

    Only what the page publishes for sharing is read; no scripts run, robots.txt is respected,
    nothing is crawled beyond the one page and the images the client picked.
    """

    def __init__(
        self,
        session: AsyncSession,
        fetcher: SafeFetcher,
        svc_attachments: AttachmentService,
        svc_users: UserService,
        mng_import_requests: ImportRequestManager,
        settings: ImportsSettings,
    ) -> None:
        self._session = session
        self._fetcher = fetcher
        self._svc_attachments = svc_attachments
        self._svc_users = svc_users
        self._mng_import_requests = mng_import_requests
        self._settings = settings

    async def _take_slot(self, current: CurrentUserSchema, kind: ImportKindEnum) -> None:
        """Counts the attempt against the user's limit before any outbound request; failed reads count too."""
        await self._svc_users.sync_user(current)
        # The lock makes parallel requests of one user wait for each other, so none slips past the count
        await self._mng_import_requests.lock_user(current.id)
        now = datetime.now(UTC)
        window = timedelta(seconds=self._settings.rate_window_seconds)
        await self._mng_import_requests.purge_before(current.id, now - window)
        used, oldest = await self._mng_import_requests.window(current.id, now - window)
        if used >= self._settings.rate_limit:
            await self._session.rollback()
            free_at = (oldest or now) + window
            raise ImportRateLimitedError(max(1, math.ceil((free_at - now).total_seconds())))
        await self._mng_import_requests.add(ImportRequest(user_id=current.id, kind=kind, created_at=now))
        # Commit releases the lock before the slow network part
        await self._session.commit()

    async def preview_import(self, current: CurrentUserSchema, data: ImportPreviewRequestSchema) -> ImportPreviewSchema:
        await self._take_slot(current, ImportKindEnum.PREVIEW)
        try:
            if not await self._fetcher.allowed_by_robots(data.url):
                raise FetchError("import_not_allowed", "The site does not allow automated reading of this page")
            page = await self._fetcher.fetch(data.url, accept=HTML_TYPES, max_bytes=PAGE_LIMIT)
        except FetchError as error:
            raise SourceImportError(error.code, error.detail) from error
        product = extract_product(page.body.decode(_charset(page.body), errors="replace"), page.url)
        if product.empty:
            raise SourceImportError("import_no_data", "The page publishes no product data")
        has_size = any((product.width_mm, product.height_mm, product.depth_mm))
        return ImportPreviewSchema(
            url=page.url,
            source=urlsplit(page.url).hostname or "",
            site_name=product.site_name,
            title=product.title,
            description=product.description,
            images=product.images,
            price=product.price,
            currency=product.currency,
            brand=product.brand,
            size=ImportSizeSchema(width=product.width_mm, height=product.height_mm, depth=product.depth_mm)
            if has_size
            else None,
            structured=product.structured,
        )

    async def import_images(
        self, current: CurrentUserSchema, data: ImportImagesRequestSchema
    ) -> ImportImagesResultSchema:
        await self._take_slot(current, ImportKindEnum.IMAGES)
        attached = []
        failed = 0
        for url in data.image_urls:
            try:
                image = await self._fetcher.fetch(url, accept=("image/",), max_bytes=IMAGE_LIMIT)
            except FetchError:
                failed += 1
                continue
            name = unquote(urlsplit(image.url).path.rsplit("/", 1)[-1]) or "reference"
            try:
                attached.append(
                    await self._svc_attachments.attach_bytes(
                        current,
                        AttachmentPurposeEnum.REFERENCE,
                        image.body,
                        name,
                        design_id=data.design_id,
                        order_id=None,
                        caption=data.source,
                    )
                )
            except AppError as error:
                # Permission and limit problems concern every image: report them, do not count as failures
                if error.code in ("permission_denied", "too_many_files", "attachment_target"):
                    raise
                failed += 1
        return ImportImagesResultSchema(attached=attached, failed=failed)


def _charset(body: bytes) -> str:
    """Encoding declared in the page head, utf-8 when missing or unknown."""
    match = _CHARSET.search(body[:4096])
    if match:
        name = match.group(1).decode("ascii")
        try:
            codecs.lookup(name)
            return name
        except LookupError:
            pass
    return "utf-8"
