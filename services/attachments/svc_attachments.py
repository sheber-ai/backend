import asyncio
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePath
from typing import Literal
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import (
    AttachmentLimitError,
    AttachmentTargetError,
    InvalidStatusError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    UnsupportedFileTypeError,
)
from common.files.inspect import UnsupportedFileError, inspect_file
from common.files.signing import UrlSigner
from common.files.storage import FileStorage
from enums.attachments_enum import AttachmentPurposeEnum
from enums.auth_enum import UserRoleEnum
from enums.orders_enum import OrderStatusEnum
from enums.workshops_enum import WorkshopStatusEnum
from managers.attachments.mng_attachments import AttachmentManager
from managers.designs.mng_designs import DesignManager
from managers.offers.mng_offers import OfferManager
from managers.orders.mng_orders import OrderManager
from managers.workshops.mng_workshops import WorkshopManager
from models.attachments.mdl_attachment import Attachment
from models.orders.mdl_order import Order
from schemas.attachments.sch_attachment import (
    AttachmentFilterSchema,
    AttachmentLimitSchema,
    AttachmentReorderSchema,
    AttachmentSchema,
    AttachmentUpdateSchema,
)
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.sch_base import PageSchema
from settings.files_settings import FilesSettings

MB = 1024 * 1024
_CHUNK = 256 * 1024


@dataclass(frozen=True, slots=True)
class PurposeRule:
    max_files: int
    max_bytes: int
    allow_pdf: bool
    # Public files of an approved workshop are visible to anyone, the rest only to the people involved
    public: bool
    target: Literal["workshop", "item"]


RULES: dict[AttachmentPurposeEnum, PurposeRule] = {
    AttachmentPurposeEnum.WORKSHOP_LOGO: PurposeRule(1, 5 * MB, allow_pdf=False, public=True, target="workshop"),
    AttachmentPurposeEnum.WORKSHOP_PORTFOLIO: PurposeRule(30, 10 * MB, allow_pdf=False, public=True, target="workshop"),
    AttachmentPurposeEnum.REFERENCE: PurposeRule(10, 10 * MB, allow_pdf=False, public=False, target="item"),
    AttachmentPurposeEnum.ROOM: PurposeRule(10, 10 * MB, allow_pdf=False, public=False, target="item"),
    AttachmentPurposeEnum.DOCUMENT: PurposeRule(5, 20 * MB, allow_pdf=True, public=False, target="item"),
}

_CLOSED_ORDER = (OrderStatusEnum.COMPLETED, OrderStatusEnum.CANCELLED)


def display_name(raw: str | None, extension: str) -> str:
    """A readable name for people; the stored key never comes from it."""
    stem = PurePath((raw or "").replace("\\", "/")).stem
    stem = re.sub(r"[\x00-\x1f\x7f<>:\"/\\|?*]+", " ", stem).strip(" .")[:180]
    return f"{stem or 'file'}.{extension}"


@dataclass(frozen=True, slots=True)
class _Target:
    workshop_id: UUID | None = None
    design_id: UUID | None = None
    order_id: UUID | None = None


class AttachmentService:
    def __init__(
        self,
        session: AsyncSession,
        mng_attachments: AttachmentManager,
        mng_workshops: WorkshopManager,
        mng_designs: DesignManager,
        mng_orders: OrderManager,
        mng_offers: OfferManager,
        storage: FileStorage,
        settings: FilesSettings,
    ) -> None:
        self._session = session
        self._mng_attachments = mng_attachments
        self._mng_workshops = mng_workshops
        self._mng_designs = mng_designs
        self._mng_orders = mng_orders
        self._mng_offers = mng_offers
        self._storage = storage
        self._settings = settings
        self._signer = UrlSigner(settings.signing_key, settings.url_ttl_seconds)

    @staticmethod
    def list_attachment_limits() -> list[AttachmentLimitSchema]:
        return [
            AttachmentLimitSchema(
                purpose=purpose,
                max_files=rule.max_files,
                max_bytes=rule.max_bytes,
                allow_pdf=rule.allow_pdf,
                public=rule.public,
            )
            for purpose, rule in RULES.items()
        ]

    async def upload_attachment(
        self,
        current: CurrentUserSchema,
        purpose: AttachmentPurposeEnum,
        upload: UploadFile,
        design_id: UUID | None,
        order_id: UUID | None,
    ) -> AttachmentSchema:
        data = await self._read_limited(upload, RULES[purpose].max_bytes)
        return await self.attach_bytes(current, purpose, data, upload.filename, design_id, order_id)

    async def attach_bytes(
        self,
        current: CurrentUserSchema,
        purpose: AttachmentPurposeEnum,
        data: bytes,
        name: str | None,
        design_id: UUID | None,
        order_id: UUID | None,
        caption: str = "",
    ) -> AttachmentSchema:
        """Stores already received bytes (an upload or a file fetched by the server) with all the usual checks."""
        rule = RULES[purpose]
        if len(data) > rule.max_bytes:
            raise PayloadTooLargeError(f"File is larger than {rule.max_bytes // MB} MB")
        target = await self._upload_target(current, rule, design_id, order_id)
        existing = await self._mng_attachments.list_for(
            workshop_id=target.workshop_id, design_id=target.design_id, order_id=target.order_id, purpose=purpose
        )
        # A logo is replaced, the other purposes collect up to the limit
        replaced = list(existing) if rule.max_files == 1 else []
        if not replaced and len(existing) >= rule.max_files:
            raise AttachmentLimitError(f"At most {rule.max_files} files for {purpose}")
        if not data:
            raise UnsupportedFileTypeError("The file is empty")
        try:
            inspected = await asyncio.to_thread(inspect_file, data, allow_pdf=rule.allow_pdf)
        except UnsupportedFileError as error:
            raise UnsupportedFileTypeError(str(error)) from error

        key = f"{uuid.uuid4().hex}.{inspected.extension}"
        await self._storage.save(key, inspected.data)
        try:
            attachment = await self._mng_attachments.add(
                Attachment(
                    owner_id=current.id,
                    purpose=purpose,
                    workshop_id=target.workshop_id,
                    design_id=target.design_id,
                    order_id=target.order_id,
                    storage_key=key,
                    content_type=inspected.content_type,
                    size=len(inspected.data),
                    name=display_name(name, inspected.extension),
                    caption=caption[:500],
                    width=inspected.width,
                    height=inspected.height,
                    position=max((item.position for item in existing), default=-1) + 1,
                )
            )
            for old in replaced:
                await self._mng_attachments.delete(old)
            await self._session.commit()
        except Exception:
            await self._storage.delete(key)
            raise
        await self.purge_blobs(old.storage_key for old in replaced)
        return self._to_schema(attachment)

    async def list_attachments(
        self, current: CurrentUserSchema | None, filters: AttachmentFilterSchema
    ) -> PageSchema[AttachmentSchema]:
        target = _Target(filters.workshop_id, filters.design_id, filters.order_id)
        if sum(value is not None for value in (target.workshop_id, target.design_id, target.order_id)) != 1:
            raise AttachmentTargetError("Pass exactly one of workshopId, designId, orderId")
        await self._require_view(current, target)
        items = await self._mng_attachments.list_for(
            workshop_id=target.workshop_id, design_id=target.design_id, order_id=target.order_id
        )
        return PageSchema(items=[self._to_schema(item) for item in items], total=len(items))

    async def update_attachment(
        self, current: CurrentUserSchema, attachment_id: UUID, data: AttachmentUpdateSchema
    ) -> AttachmentSchema:
        attachment = await self._get_managed(current, attachment_id)
        attachment.caption = data.caption.strip()
        await self._session.commit()
        return self._to_schema(attachment)

    async def reorder_attachments(
        self, current: CurrentUserSchema, data: AttachmentReorderSchema
    ) -> PageSchema[AttachmentSchema]:
        """The first id becomes the cover. All ids must belong to one target."""
        attachments = [await self._get_managed(current, attachment_id) for attachment_id in data.ids]
        targets = {(item.workshop_id, item.design_id, item.order_id) for item in attachments}
        if len(targets) != 1 or len(set(data.ids)) != len(data.ids):
            raise AttachmentTargetError("Reorder files of one gallery at a time")
        for position, attachment in enumerate(attachments):
            attachment.position = position
        await self._session.commit()
        workshop_id, design_id, order_id = targets.pop()
        items = await self._mng_attachments.list_for(workshop_id=workshop_id, design_id=design_id, order_id=order_id)
        return PageSchema(items=[self._to_schema(item) for item in items], total=len(items))

    async def delete_attachment(self, current: CurrentUserSchema, attachment_id: UUID) -> None:
        attachment = await self._get_managed(current, attachment_id)
        key = attachment.storage_key
        await self._mng_attachments.delete(attachment)
        await self._session.commit()
        await self.purge_blobs([key])

    async def read_attachment_content(
        self, attachment_id: UUID, expires: int, signature: str
    ) -> tuple[Attachment, bytes]:
        if not self._signer.verify(attachment_id, expires, signature):
            raise PermissionDeniedError("The link is invalid or expired")
        attachment = await self._mng_attachments.get_by_id(attachment_id)
        if attachment is None:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        try:
            return attachment, await self._storage.read(attachment.storage_key)
        except FileNotFoundError as error:
            raise NotFoundError("File content is missing") from error

    async def copy_to_order(self, design_id: UUID, order: Order) -> None:
        """Snapshot of the design files for a new order. Does not commit."""
        for source in await self._mng_attachments.list_for(design_id=design_id):
            await self._mng_attachments.add(
                Attachment(
                    owner_id=source.owner_id,
                    purpose=source.purpose,
                    order_id=order.id,
                    storage_key=source.storage_key,
                    content_type=source.content_type,
                    size=source.size,
                    name=source.name,
                    width=source.width,
                    height=source.height,
                    caption=source.caption,
                    position=source.position,
                )
            )

    async def storage_keys(self, *, design_id: UUID) -> list[str]:
        return [item.storage_key for item in await self._mng_attachments.list_for(design_id=design_id)]

    async def purge_blobs(self, keys: Iterable[str]) -> None:
        """Removes blobs no row points at. Call after the commit that dropped the rows."""
        for key in set(keys):
            if not await self._mng_attachments.key_in_use(key):
                await self._storage.delete(key)

    def _to_schema(self, attachment: Attachment) -> AttachmentSchema:
        expires = self._signer.expires_at()
        signature = self._signer.sign(attachment.id, expires)
        url = (
            f"{self._settings.public_base_url}/api/v1/attachments/{attachment.id}/content"
            f"?expires={expires}&signature={signature}"
        )
        return AttachmentSchema(
            id=attachment.id,
            purpose=AttachmentPurposeEnum(attachment.purpose),
            name=attachment.name,
            content_type=attachment.content_type,
            is_image=attachment.content_type.startswith("image/"),
            size=attachment.size,
            width=attachment.width,
            height=attachment.height,
            caption=attachment.caption,
            position=attachment.position,
            url=url,
            created_at=attachment.created_at,
        )

    @staticmethod
    async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while chunk := await upload.read(_CHUNK):
            total += len(chunk)
            if total > max_bytes:
                raise PayloadTooLargeError(f"File is larger than {max_bytes // MB} MB")
            chunks.append(chunk)
        return b"".join(chunks)

    async def _upload_target(
        self, current: CurrentUserSchema, rule: PurposeRule, design_id: UUID | None, order_id: UUID | None
    ) -> _Target:
        if rule.target == "workshop":
            if design_id or order_id:
                raise AttachmentTargetError("Workshop files belong to your workshop only")
            workshop = await self._mng_workshops.get_by_owner(current.id)
            if workshop is None:
                raise AttachmentTargetError("Fill in the workshop application first")
            return _Target(workshop_id=workshop.id)
        if (design_id is None) == (order_id is None):
            raise AttachmentTargetError("Pass either designId or orderId")
        target = _Target(design_id=design_id, order_id=order_id)
        await self._require_manage(current, target)
        return target

    async def _get_managed(self, current: CurrentUserSchema, attachment_id: UUID) -> Attachment:
        attachment = await self._mng_attachments.get_by_id(attachment_id)
        if attachment is None:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        await self._require_manage(current, _Target(attachment.workshop_id, attachment.design_id, attachment.order_id))
        return attachment

    async def _require_manage(self, current: CurrentUserSchema, target: _Target) -> None:
        if target.workshop_id is not None:
            workshop = await self._mng_workshops.get_by_id(target.workshop_id)
            if workshop is None or workshop.owner_id != current.id:
                raise PermissionDeniedError("Not your workshop")
        elif target.design_id is not None:
            design = await self._mng_designs.get_by_id(target.design_id)
            if design is None or design.owner_id != current.id:
                raise PermissionDeniedError("Not your design")
        elif target.order_id is not None:
            order = await self._mng_orders.get_by_id(target.order_id)
            if order is None or order.client_id != current.id:
                raise PermissionDeniedError("Not your order")
            if order.status in _CLOSED_ORDER:
                raise InvalidStatusError("The order is closed")

    async def _require_view(self, current: CurrentUserSchema | None, target: _Target) -> None:
        is_admin = current is not None and current.has_role(UserRoleEnum.ADMIN)
        if target.workshop_id is not None:
            workshop = await self._mng_workshops.get_by_id(target.workshop_id)
            if workshop is None:
                raise NotFoundError("Workshop not found")
            approved = workshop.status == WorkshopStatusEnum.APPROVED
            if not (approved or is_admin or (current is not None and workshop.owner_id == current.id)):
                raise NotFoundError("Workshop not found")
            return
        if current is None:
            raise PermissionDeniedError("Sign in to see these files")
        if target.design_id is not None:
            design = await self._mng_designs.get_by_id(target.design_id)
            if design is None or design.owner_id != current.id:
                raise PermissionDeniedError("Not your design")
            return
        if target.order_id is not None:
            order = await self._mng_orders.get_by_id(target.order_id)
            if order is None:
                raise PermissionDeniedError("Order is not available")
            if is_admin or order.client_id == current.id or await self._workshop_sees(order, current.id):
                return
            raise PermissionDeniedError("Order is not available")

    async def _workshop_sees(self, order: Order, user_id: UUID) -> bool:
        workshop = await self._mng_workshops.get_by_owner(user_id)
        if workshop is None or workshop.status != WorkshopStatusEnum.APPROVED:
            return False
        if order.status == OrderStatusEnum.PUBLISHED or order.workshop_id == workshop.id:
            return True
        return await self._mng_offers.get_for_workshop(order.id, workshop.id) is not None
