"""Office documents -> PDF through headless LibreOffice.

Each task gets a throwaway LibreOffice profile inside its work directory, so settings or macro trust
never carry over between users. Input files are renamed to ids we choose, so nothing user-supplied
reaches the command line.
"""

import os
import shutil
import subprocess  # noqa: S404 - fixed argv, no shell
from pathlib import Path

from django.conf import settings

from ..formats import DOC_FORMATS, PDF_MIME
from .base import InputFile, OutputFile, ProcessingError, stem_of

# Written into each throwaway profile before LibreOffice starts. Keys and values are from
# officecfg/registry/schema (Writer: Link 2 = Never; Calc: Link 1 = Never). Together they stop
# documents from pulling in local files or URLs (INCLUDETEXT, linked sections/images, external
# cell references, DDE/OLE) and from running macros.
_HARDENED_SETTINGS = [
    ("/org.openoffice.Office.Writer/Content/Update", "Link", "2"),
    ("/org.openoffice.Office.Writer/Content/Update", "Field", "false"),
    ("/org.openoffice.Office.Calc/Content/Update", "Link", "1"),
    ("/org.openoffice.Office.Common/Security/Scripting", "DisableActiveContent", "true"),
    ("/org.openoffice.Office.Common/Security/Scripting", "DisableMacrosExecution", "true"),
    ("/org.openoffice.Office.Common/Security/Scripting", "BlockUntrustedRefererLinks", "true"),
    ("/org.openoffice.Office.Common/Security/Scripting", "DisableOLEAutomation", "true"),
    ("/org.openoffice.Office.Common/Security/Scripting", "DisablePythonRuntime", "true"),
]
_HARDENED_PROFILE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
    + "".join(
        f'<item oor:path="{path}"><prop oor:name="{name}" oor:op="fuse"><value>{value}</value></prop></item>\n'
        for path, name, value in _HARDENED_SETTINGS
    )
    + "</oor:items>\n"
)


def _prepare_profile(profile: Path) -> None:
    user = profile / "user"
    user.mkdir(parents=True, exist_ok=True)
    (user / "registrymodifications.xcu").write_text(_HARDENED_PROFILE, encoding="utf-8")


def _soffice() -> str:
    binary = shutil.which(settings.SOFFICE_BINARY) or settings.SOFFICE_BINARY
    if not Path(binary).exists():
        raise ProcessingError("tool_unavailable")
    return binary


def office_to_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    soffice = _soffice()
    profile = workdir / "lo-profile"
    outdir = workdir / "lo-out"
    outdir.mkdir()
    _prepare_profile(profile)
    env = {
        "HOME": str(workdir),  # keep LibreOffice away from the service user's real home
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
    }
    outputs = []
    for i, src in enumerate(inputs):
        # LibreOffice picks the import filter from the extension, so give it the detected one.
        typed = workdir / f"doc-{i}.{DOC_FORMATS[src.fmt][1]}"
        shutil.copyfile(src.path, typed)
        argv = [
            soffice,
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--invisible",
            "--norestore",
            "--nolockcheck",
            "--nodefault",
            "--nologo",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(typed),
        ]
        try:
            subprocess.run(  # noqa: S603 - argv is fully controlled
                argv, env=env, cwd=workdir, capture_output=True, timeout=settings.OFFICE_TIMEOUT, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise ProcessingError("timeout") from exc
        result = outdir / f"doc-{i}.pdf"
        if not result.exists() or result.stat().st_size == 0:
            raise ProcessingError("corrupt_file")
        outputs.append(OutputFile(path=result, name=f"{stem_of(src.name)}.pdf", mime=PDF_MIME))
    return outputs
