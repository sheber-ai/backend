import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

# Decompression bombs: a tiny file that expands to gigabytes of pixels
Image.MAX_IMAGE_PIXELS = 50_000_000
MAX_IMAGE_SIDE = 4096

IMAGE_TYPES = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}
PDF_TYPE = ("application/pdf", "pdf")


class UnsupportedFileError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InspectedFile:
    data: bytes
    content_type: str
    extension: str
    width: int | None = None
    height: int | None = None

    @property
    def is_image(self) -> bool:
        return self.content_type.startswith("image/")


def inspect_file(data: bytes, *, allow_pdf: bool) -> InspectedFile:
    """Detects the type by content, never by name or client headers.

    Images are re-encoded: that drops EXIF (GPS of the client's flat), fixes rotation
    and strips anything appended to the image bytes.
    """
    if data.startswith(b"%PDF-"):
        if not allow_pdf:
            raise UnsupportedFileError("PDF is not allowed here")
        return InspectedFile(data=data, content_type=PDF_TYPE[0], extension=PDF_TYPE[1])
    try:
        with Image.open(io.BytesIO(data)) as probe:
            image_format = probe.format
            probe.verify()
        if image_format not in IMAGE_TYPES:
            raise UnsupportedFileError(f"Image format {image_format} is not allowed")
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            return _encode(image, image_format)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as error:
        raise UnsupportedFileError("Not a supported image or PDF") from error


def _encode(image: Image.Image, image_format: str) -> InspectedFile:
    out = io.BytesIO()
    if image_format == "JPEG":
        image.convert("RGB").save(out, "JPEG", quality=88, optimize=True)
    elif image_format == "PNG":
        image.save(out, "PNG", optimize=True)
    else:
        image.save(out, "WEBP", quality=88)
    content_type, extension = IMAGE_TYPES[image_format]
    return InspectedFile(
        data=out.getvalue(),
        content_type=content_type,
        extension=extension,
        width=image.width,
        height=image.height,
    )
