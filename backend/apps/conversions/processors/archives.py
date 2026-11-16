"""Archives: extract, create and repack, through libarchive (BSD licence).

Bomb and traversal defences:
- entries are streamed and counted; extraction stops as soon as the unpacked size or the entry
  count passes the limit, so a 42.zip never reaches the disk in full;
- entries are written to numbered files we name ourselves; the name from the archive is only
  cleaned and kept for display and for zips we build, so "../../etc/passwd" cannot escape;
- links, devices and other special entries are skipped;
- nested archives are returned as files and never opened (depth 1).
"""

import zipfile
from dataclasses import dataclass
from pathlib import Path

import libarchive
from django.conf import settings

from ..formats import ARCHIVE_FORMATS
from .base import InputFile, OutputFile, ProcessingError, safe_relpath, stem_of

MB = 1024 * 1024
OCTET = "application/octet-stream"
# Single-stream compressors: "report.txt.gz" holds one file, not an archive.
_STREAMS = {"gz", "bz2", "xz"}
_TAR_SUFFIXES = (".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")
# Names in zips made on Windows without the UTF-8 flag: Russian/Uzbek Windows uses CP866 for zip.
_LEGACY_CODECS = ("utf-8", "cp866", "cp1251")


@dataclass(frozen=True)
class Extracted:
    path: Path
    name: str  # cleaned relative path, e.g. "photos/2024/img.jpg"


def _decode(name: str | bytes | None) -> str:
    if isinstance(name, str):
        return name
    if not name:
        return ""
    for codec in _LEGACY_CODECS:
        try:
            return name.decode(codec)
        except UnicodeDecodeError:
            continue
    return name.decode("utf-8", "replace")


def _map_error(exc: Exception, password: str = "") -> ProcessingError:
    text = str(exc).lower()
    if "encrypt" in text or "passphrase" in text or "password" in text:
        return ProcessingError("wrong_password" if password else "archive_encrypted")
    return ProcessingError("corrupt_file")


def _stream_name(src: InputFile) -> str:
    """Name of the single file inside "x.txt.gz" -> "x.txt"."""
    stem = stem_of(src.name)
    return stem if stem and stem != src.name else "file"


def extract_archive(
    src: InputFile, outdir: Path, max_unpacked_mb: int | None = None, password: str = ""
) -> list[Extracted]:
    max_entries = settings.ARCHIVE_MAX_ENTRIES
    max_bytes = min(max_unpacked_mb or settings.ARCHIVE_MAX_UNPACKED_MB, settings.ARCHIVE_MAX_UNPACKED_MB) * MB
    outdir.mkdir(parents=True, exist_ok=True)
    files: list[Extracted] = []
    total = 0
    seen = 0

    def read(format_name: str) -> None:
        nonlocal total, seen
        with libarchive.file_reader(str(src.path), format_name=format_name, passphrase=password or None) as archive:
            for entry in archive:
                # Folders and links count too: millions of empty entries would keep a worker busy.
                seen += 1
                if seen > max_entries * 4:
                    raise ProcessingError("archive_too_many_files")
                if not entry.isreg or entry.islnk or entry.issym:
                    continue
                if len(files) >= max_entries:
                    raise ProcessingError("archive_too_many_files")
                name = _decode(entry.pathname)
                if format_name == "raw":
                    name = _stream_name(src)
                dest = outdir / f"{len(files):05d}"
                with dest.open("wb") as fh:
                    for block in entry.get_blocks():
                        total += len(block)
                        if total > max_bytes:
                            raise ProcessingError("archive_too_large")
                        fh.write(block)
                files.append(Extracted(path=dest, name=safe_relpath(name)))

    try:
        try:
            read("all")
        except libarchive.ArchiveError:
            # "x.txt.gz" is a compressed stream, not an archive: libarchive reads it as "raw".
            if src.fmt not in _STREAMS or files:
                raise
            read("raw")
    except libarchive.ArchiveError as exc:
        raise _map_error(exc, password) from exc
    if not files:
        raise ProcessingError("archive_empty")
    return files


def _archive_stem(name: str) -> str:
    lower = name.lower()
    for suffix in _TAR_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)] or "archive"
    return stem_of(name)


def _write_archive(files: list[Extracted], dest: Path, fmt: str) -> None:
    if fmt == "zip":
        # Python's zipfile always marks non-ASCII names as UTF-8, so they open correctly everywhere.
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for f in files:
                zf.write(f.path, arcname=f.name)
        return
    with libarchive.file_writer(str(dest), "7zip") as archive:
        for f in files:
            archive.add_files(str(f.path), pathname=f.name)


def _dedupe(files: list[Extracted]) -> list[Extracted]:
    seen: dict[str, int] = {}
    out = []
    for f in files:
        key = f.name.lower()
        count = seen.get(key, 0)
        seen[key] = count + 1
        if count:
            stem, dot, ext = f.name.rpartition(".")
            name = f"{stem} ({count + 1}).{ext}" if dot and "/" not in ext else f"{f.name} ({count + 1})"
            f = Extracted(path=f.path, name=name)
        out.append(f)
    return out


def _mime(fmt: str) -> str:
    return ARCHIVE_FORMATS[fmt][0]


# --- Tools ---------------------------------------------------------------------------------------


def extract(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    [src] = inputs
    files = extract_archive(src, workdir / "x", options.get("_max_unpacked_mb"), options.get("password", ""))
    # Extracted files are served as downloads only, so they never get a type the browser would render.
    return [OutputFile(path=f.path, name=f.name, mime=OCTET) for f in files]


def create(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    fmt = options.get("format", "zip")
    files = _dedupe([Extracted(path=i.path, name=safe_relpath(i.name)) for i in inputs])
    stem = stem_of(inputs[0].name) if len(inputs) == 1 else "archive"
    dest = workdir / f"out.{fmt}"
    _write_archive(files, dest, fmt)
    return [OutputFile(path=dest, name=f"{stem}.{fmt}", mime=_mime(fmt))]


def repack(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    fmt = options.get("target", "zip")
    outputs = []
    for i, src in enumerate(inputs):
        files = _dedupe(
            extract_archive(src, workdir / f"x{i}", options.get("_max_unpacked_mb"), options.get("password", ""))
        )
        dest = workdir / f"out-{i}.{fmt}"
        _write_archive(files, dest, fmt)
        outputs.append(OutputFile(path=dest, name=f"{_archive_stem(src.name)}.{fmt}", mime=_mime(fmt)))
    return outputs
