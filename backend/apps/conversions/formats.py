"""Content-based format detection. File extensions are never trusted."""

from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

# Format key -> (Pillow save format, MIME type, file extension)
IMAGE_FORMATS: dict[str, tuple[str, str, str]] = {
    "png": ("PNG", "image/png", "png"),
    "jpg": ("JPEG", "image/jpeg", "jpg"),
    "webp": ("WEBP", "image/webp", "webp"),
    "gif": ("GIF", "image/gif", "gif"),
    "bmp": ("BMP", "image/bmp", "bmp"),
    "tiff": ("TIFF", "image/tiff", "tiff"),
    "avif": ("AVIF", "image/avif", "avif"),
    "heic": ("HEIF", "image/heic", "heic"),
}

# Formats we can read as input.
IMAGE_INPUTS = frozenset(IMAGE_FORMATS)
# Formats we write. HEIC output is intentionally not offered.
IMAGE_OUTPUTS = ("png", "jpg", "webp", "avif", "gif", "bmp", "tiff")

# Pillow's detected format name -> our key. MPO is how many phone JPEGs are detected.
_PILLOW_TO_KEY = {
    "PNG": "png",
    "JPEG": "jpg",
    "MPO": "jpg",
    "WEBP": "webp",
    "GIF": "gif",
    "BMP": "bmp",
    "TIFF": "tiff",
    "AVIF": "avif",
    "HEIF": "heic",
}

PDF_MIME = "application/pdf"
ZIP_MIME = "application/zip"


@dataclass(frozen=True)
class DetectedImage:
    fmt: str
    width: int
    height: int

    @property
    def pixels(self) -> int:
        return self.width * self.height


class ImageTooLargeError(Exception):
    """Decoded pixel count exceeds the configured ceiling."""


def detect_image(fileobj: BinaryIO) -> DetectedImage | None:
    """Read only the header to identify the image. Returns None if not a supported image.

    Raises ImageTooLargeError for decompression-bomb sized images.
    """
    pos = fileobj.tell()
    try:
        with Image.open(fileobj) as img:
            key = _PILLOW_TO_KEY.get(img.format or "")
            if key is None:
                return None
            width, height = img.size
            return DetectedImage(fmt=key, width=width, height=height)
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError from exc
    except UnidentifiedImageError, OSError, ValueError, SyntaxError:
        return None
    finally:
        fileobj.seek(pos)


def mime_for(fmt: str) -> str:
    return IMAGE_FORMATS[fmt][1]


# --- Documents -------------------------------------------------------------------------------------

# Format key -> (MIME type, file extension)
DOC_FORMATS: dict[str, tuple[str, str]] = {
    "pdf": (PDF_MIME, "pdf"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "doc": ("application/msword", "doc"),
    "odt": ("application/vnd.oasis.opendocument.text", "odt"),
    "rtf": ("application/rtf", "rtf"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "xls": ("application/vnd.ms-excel", "xls"),
    "ods": ("application/vnd.oasis.opendocument.spreadsheet", "ods"),
    "csv": ("text/csv", "csv"),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
    "ppt": ("application/vnd.ms-powerpoint", "ppt"),
    "odp": ("application/vnd.oasis.opendocument.presentation", "odp"),
}
OFFICE_INPUTS = frozenset({"docx", "doc", "odt", "rtf", "xlsx", "xls", "ods", "csv", "pptx", "ppt", "odp"})
PDF_INPUTS = frozenset({"pdf"})

ARCHIVE_FORMATS: dict[str, tuple[str, str]] = {
    "zip": (ZIP_MIME, "zip"),
    "rar": ("application/vnd.rar", "rar"),
    "7z": ("application/x-7z-compressed", "7z"),
    "tar": ("application/x-tar", "tar"),
    "gz": ("application/gzip", "gz"),
    "bz2": ("application/x-bzip2", "bz2"),
    "xz": ("application/x-xz", "xz"),
}
# Any other file, accepted only by tools that never parse content (packing into an archive).
DOC_FORMATS["bin"] = ("application/octet-stream", "bin")
DOC_FORMATS.update(ARCHIVE_FORMATS)
ARCHIVE_INPUTS = frozenset(ARCHIVE_FORMATS)

_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_OOXML_PARTS = {"word/document.xml": "docx", "xl/workbook.xml": "xlsx", "ppt/presentation.xml": "pptx"}
_ZIP_MIMETYPES = {
    b"application/vnd.oasis.opendocument.text": "odt",
    b"application/vnd.oasis.opendocument.spreadsheet": "ods",
    b"application/vnd.oasis.opendocument.presentation": "odp",
}
_OLE_STREAMS = {"WordDocument": "doc", "Workbook": "xls", "Book": "xls", "PowerPoint Document": "ppt"}
# Zip documents with absurd directories are never handed to LibreOffice; they count as plain zips.
_MAX_ZIP_ENTRIES = 10_000
_RAR_MAGIC = (b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")
_7Z_MAGIC = b"7z\xbc\xaf\x27\x1c"
_XZ_MAGIC = b"\xfd7zXZ\x00"


@dataclass(frozen=True)
class DetectedFile:
    fmt: str
    width: int = 0
    height: int = 0

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def mime(self) -> str:
        return IMAGE_FORMATS[self.fmt][1] if self.fmt in IMAGE_FORMATS else DOC_FORMATS[self.fmt][0]

    @property
    def ext(self) -> str:
        return IMAGE_FORMATS[self.fmt][2] if self.fmt in IMAGE_FORMATS else DOC_FORMATS[self.fmt][1]


def _detect_zip(fileobj: BinaryIO) -> str | None:
    """OOXML / ODF by their marker entries; any other readable zip (an EPUB too) is a plain "zip"."""
    import zipfile

    try:
        with zipfile.ZipFile(fileobj) as zf:
            infos = zf.infolist()
            if len(infos) > _MAX_ZIP_ENTRIES:
                return "zip"
            names = {info.filename for info in infos}
            if "mimetype" in names:
                # Read a bounded prefix: a crafted "mimetype" entry could expand to gigabytes.
                with zf.open("mimetype") as entry:
                    fmt = _ZIP_MIMETYPES.get(entry.read(100).strip())
                if fmt:
                    return fmt
            if "[Content_Types].xml" in names:
                for part, fmt in _OOXML_PARTS.items():
                    if part in names:
                        return fmt
            return "zip"
    except zipfile.BadZipFile, OSError, ValueError, KeyError, NotImplementedError:
        return None


def _detect_ole_document(fileobj: BinaryIO) -> str | None:
    import olefile

    try:
        with olefile.OleFileIO(fileobj) as ole:
            for stream, fmt in _OLE_STREAMS.items():
                if ole.exists(stream):
                    return fmt
    except OSError, ValueError, IndexError:
        return None
    return None


def _looks_like_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as exc:
        # A multi-byte character may be cut at the end of the sample.
        return exc.start >= len(head) - 3
    return True


def _detect_archive(head: bytes) -> str | None:
    if head.startswith(_RAR_MAGIC):
        return "rar"
    if head.startswith(_7Z_MAGIC):
        return "7z"
    if head.startswith(b"\x1f\x8b"):
        return "gz"
    if head.startswith(b"BZh") and head[3:4].isdigit() and head[4:10] == b"1AY&SY":
        return "bz2"
    if head.startswith(_XZ_MAGIC):
        return "xz"
    if head[257:262] == b"ustar":
        return "tar"
    return None


def detect_document(fileobj: BinaryIO, filename: str = "") -> str | None:
    """Identify documents and archives by content. CSV is plain text, so it also needs the .csv name."""
    pos = fileobj.tell()
    try:
        head = fileobj.read(8192)
        fileobj.seek(pos)
        # Containers first: a zip or tar that stores a PDF uncompressed has "%PDF-" near its start too.
        if head.startswith(_ZIP_MAGIC):
            return _detect_zip(fileobj)
        if head.startswith(_OLE_MAGIC):
            return _detect_ole_document(fileobj)
        archive = _detect_archive(head)
        if archive:
            return archive
        if b"%PDF-" in head[:1024]:
            return "pdf"
        if head.lstrip(b"\xef\xbb\xbf").startswith(b"{\\rtf"):
            return "rtf"
        if filename.lower().endswith(".csv") and head and _looks_like_text(head):
            return "csv"
        return None
    finally:
        fileobj.seek(pos)


def detect_file(fileobj: BinaryIO, filename: str = "") -> DetectedFile | None:
    """Images first (Pillow), then documents. Raises ImageTooLargeError for decompression bombs."""
    image = detect_image(fileobj)
    if image is not None:
        return DetectedFile(fmt=image.fmt, width=image.width, height=image.height)
    fmt = detect_document(fileobj, filename)
    return DetectedFile(fmt=fmt) if fmt else None
