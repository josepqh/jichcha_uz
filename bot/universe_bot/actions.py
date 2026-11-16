"""What the bot offers for a file: the same families and tools as the website's catalog.

The family is guessed from the file name / MIME type only to pick buttons. The backend detects
the real format from content and refuses a mismatch, so a renamed file cannot slip through.
"""

from dataclasses import dataclass, field
from pathlib import PurePath

FAMILY_FORMATS: dict[str, tuple[str, ...]] = {
    "pdf": ("pdf",),
    "word": ("docx", "doc", "odt", "rtf"),
    "excel": ("xlsx", "xls", "ods", "csv"),
    "powerpoint": ("pptx", "ppt", "odp"),
    "image": ("png", "jpg", "jpeg", "webp", "heic", "heif", "avif", "gif", "bmp", "tif", "tiff"),
    "ebook": ("epub", "mobi", "azw3", "fb2"),
    "archive": ("zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "tbz2", "xz", "txz"),
}
_MIME_FAMILY = {"application/pdf": "pdf", "application/epub+zip": "ebook", "application/zip": "archive"}

# Web pages for files too large for the bot (Telegram lets bots download only up to 20 MB).
WEB_TOOL = {
    "pdf": "tools/pdf-compress",
    "word": "convert/docx-to-pdf",
    "excel": "convert/xlsx-to-pdf",
    "powerpoint": "convert/pptx-to-pdf",
    "image": "tools/image-compress",
    "ebook": "tools/ebook-convert",
    "archive": "tools/archive-extract",
}


@dataclass(frozen=True)
class Action:
    key: str  # short id used in callback data
    tool: str
    options: dict = field(default_factory=dict)


ACTIONS: dict[str, tuple[Action, ...]] = {
    "image": (
        Action("pdf", "images-to-pdf", {"page_size": "a4", "orientation": "auto", "margin": "small"}),
        Action("jpg", "image-convert", {"target": "jpg"}),
        Action("png", "image-convert", {"target": "png"}),
        Action("webp", "image-convert", {"target": "webp"}),
        Action("shrink", "image-compress", {"level": "medium"}),
    ),
    "pdf": (
        Action("shrink", "pdf-compress", {"level": "medium"}),
        Action("jpg", "pdf-to-images", {"format": "jpg", "quality": "medium"}),
        Action("split", "pdf-split", {"mode": "each"}),
        Action("epub", "ebook-convert", {"target": "epub"}),
    ),
    "word": (
        Action("pdf", "office-to-pdf"),
        Action("epub", "ebook-convert", {"target": "epub"}),
    ),
    "excel": (Action("pdf", "office-to-pdf"),),
    "powerpoint": (Action("pdf", "office-to-pdf"),),
    "ebook": (
        Action("epub", "ebook-convert", {"target": "epub"}),
        Action("pdf", "ebook-convert", {"target": "pdf"}),
        Action("mobi", "ebook-convert", {"target": "mobi"}),
        Action("azw3", "ebook-convert", {"target": "azw3"}),
    ),
    "archive": (
        Action("extract", "archive-extract"),
        Action("zip", "archive-convert", {"target": "zip"}),
    ),
}


def extension(name: str) -> str:
    return PurePath(name.lower()).suffix.lstrip(".")


def family_of(name: str, mime: str = "") -> str | None:
    ext = extension(name)
    for family, formats in FAMILY_FORMATS.items():
        if ext in formats:
            return family
    if mime.startswith("image/"):
        return "image"
    return _MIME_FAMILY.get(mime)


def actions_for(family: str, name: str = "") -> tuple[Action, ...]:
    """Actions for one file. Converting a format to itself is not offered (EPUB -> EPUB)."""
    ext = extension(name)
    same = {"jpeg": "jpg"}.get(ext, ext)
    return tuple(a for a in ACTIONS.get(family, ()) if a.key != same)


def find_action(family: str, key: str) -> Action | None:
    return next((a for a in ACTIONS.get(family, ()) if a.key == key), None)


# Several files sent as one album. Only tools that take a batch; a PDF album can also be merged.
ALBUM_ACTIONS: dict[str, tuple[Action, ...]] = {
    "image": (
        Action("pdf", "images-to-pdf", {"page_size": "a4", "orientation": "auto", "margin": "small"}),
        Action("shrink", "image-compress", {"level": "medium"}),
    ),
    "pdf": (
        Action("merge", "pdf-merge"),
        Action("shrink", "pdf-compress", {"level": "medium"}),
    ),
    "word": (Action("pdf", "office-to-pdf"),),
    "excel": (Action("pdf", "office-to-pdf"),),
    "powerpoint": (Action("pdf", "office-to-pdf"),),
    "ebook": (
        Action("epub", "ebook-convert", {"target": "epub"}),
        Action("pdf", "ebook-convert", {"target": "pdf"}),
    ),
    "archive": (Action("zip", "archive-convert", {"target": "zip"}),),
}


def album_actions_for(family: str) -> tuple[Action, ...]:
    return ALBUM_ACTIONS.get(family, ())


def find_album_action(family: str, key: str) -> Action | None:
    return next((a for a in ALBUM_ACTIONS.get(family, ()) if a.key == key), None)
