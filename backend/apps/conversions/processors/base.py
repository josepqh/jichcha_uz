"""Shared types for processors. Processors are pure: local paths in, local paths out."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePath


class ProcessingError(Exception):
    """A failure the user can understand. `code` is shown (translated) in the UI."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class InputFile:
    path: Path
    name: str  # sanitized original name, for naming outputs only
    fmt: str  # detected format key


@dataclass(frozen=True)
class OutputFile:
    path: Path
    name: str
    mime: str


_UNSAFE = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]+')


def safe_name(name: str, max_len: int = 120) -> str:
    """Strip directories, control and reserved characters; keep Unicode letters (o', g', кирилл)."""
    name = unicodedata.normalize("NFC", PurePath(name.replace("\\", "/")).name)
    name = _UNSAFE.sub("_", name).strip(" .")
    if not name:
        return "file"
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return name[:max_len]
    ext = ext[:10]
    return f"{stem[: max_len - len(ext) - 1]}.{ext}"


def stem_of(name: str) -> str:
    stem = PurePath(name).stem
    return stem or "file"


MAX_PATH_DEPTH = 16


def safe_relpath(name: str, max_len: int = 240) -> str:
    """Like safe_name, but keeps folders: "a/../b\\c.txt" -> "a/b/c.txt". Never absolute, never "..".

    Used for display names and paths inside zips we build; storage paths never use it.
    """
    parts = [safe_name(part) for part in name.replace("\\", "/").split("/") if part.strip(" .") not in ("", "..", ".")][
        -MAX_PATH_DEPTH:
    ]
    if not parts:
        return "file"
    path = "/".join(parts)
    while len(path) > max_len and len(parts) > 1:
        parts = parts[1:]
        path = "/".join(parts)
    return path if len(path) <= max_len else safe_name(parts[-1], max_len)
