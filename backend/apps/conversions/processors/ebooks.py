"""E-books through Calibre's `ebook-convert` (GPL), run as a separate process.

Like LibreOffice, it gets a throwaway home/config/temp directory per task and a minimal
environment, so nothing from the worker's environment (database URL, secret key) is visible to it.
In Docker it runs on a worker with no network access.
"""

import os
import shutil
import subprocess  # noqa: S404 - fixed argv, no shell
from pathlib import Path

from django.conf import settings

from ..formats import DOC_FORMATS
from .base import InputFile, OutputFile, ProcessingError, stem_of


def _binary() -> str:
    binary = shutil.which(settings.EBOOK_CONVERT_BINARY) or settings.EBOOK_CONVERT_BINARY
    if not Path(binary).exists():
        raise ProcessingError("tool_unavailable")
    return binary


def _env(workdir: Path) -> dict[str, str]:
    home = workdir / "calibre"
    for sub in ("config", "tmp", "cache"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "QT_QPA_PLATFORM": "offscreen",
        "CALIBRE_CONFIG_DIRECTORY": str(home / "config"),
        "CALIBRE_TEMP_DIR": str(home / "tmp"),
        "CALIBRE_CACHE_DIRECTORY": str(home / "cache"),
    }


def _convert(src: InputFile, index: int, target: str, extra: list[str], workdir: Path, env: dict) -> OutputFile:
    binary = _binary()
    # Calibre picks its reader from the extension, so give it the detected one.
    typed = workdir / f"book-{index}.{DOC_FORMATS[src.fmt][1]}"
    shutil.copyfile(src.path, typed)
    result = workdir / f"book-{index}-out.{target}"
    argv = [binary, str(typed), str(result), *extra]
    if target == "pdf":
        argv += ["--paper-size", "a4", "--pdf-page-numbers"]
    try:
        proc = subprocess.run(  # noqa: S603 - argv is fully controlled
            argv, env=env, cwd=workdir, capture_output=True, timeout=settings.EBOOK_TIMEOUT, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError("timeout") from exc
    if b"DRMError" in proc.stderr or b"DRMError" in proc.stdout:
        raise ProcessingError("ebook_drm")
    if proc.returncode != 0 or not result.exists() or result.stat().st_size == 0:
        raise ProcessingError("corrupt_file")
    return OutputFile(path=result, name=f"{stem_of(src.name)}.{target}", mime=DOC_FORMATS[target][0])


def ebook_convert(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    target = options.get("target", "epub")
    env = _env(workdir)
    return [_convert(src, i, target, [], workdir, env) for i, src in enumerate(inputs)]


def text_convert(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    """TXT / Markdown -> PDF, DOCX or EPUB (the text editor's server-side exports)."""
    target = options.get("target", "pdf")
    env = _env(workdir)
    outputs = []
    for i, src in enumerate(inputs):
        formatting = "markdown" if src.fmt == "md" else "plain"
        extra = ["--formatting-type", formatting, "--input-encoding", "utf-8"]
        outputs.append(_convert(src, i, target, extra, workdir, env))
    return outputs
