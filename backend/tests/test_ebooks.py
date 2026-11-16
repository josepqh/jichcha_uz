import os
import shutil
import zipfile
from pathlib import Path

import pytest

from apps.conversions.processors import ebooks
from apps.conversions.processors.base import InputFile, ProcessingError
from tests.docs import docx_bytes, epub_bytes, fb2_bytes

MAC_CALIBRE = "/Applications/calibre.app/Contents/MacOS/ebook-convert"
calibre_missing = shutil.which("ebook-convert") is None and not Path(MAC_CALIBRE).exists()
needs_calibre = pytest.mark.skipif(calibre_missing, reason="Calibre is not installed")

SECRET = "SECRET_KEY=canary-7f3a9c"


@pytest.fixture
def calibre(settings):
    if shutil.which("ebook-convert") is None:
        settings.EBOOK_CONVERT_BINARY = MAC_CALIBRE


def convert(tmp_path, name: str, data: bytes, fmt: str, target: str) -> Path:
    src = tmp_path / f"src-{name}"
    src.write_bytes(data)
    [out] = ebooks.ebook_convert([InputFile(path=src, name=name, fmt=fmt)], {"target": target}, tmp_path)
    assert out.name == f"{Path(name).stem}.{target}"
    return out.path


def text_of(path: Path) -> str:
    if path.suffix == ".pdf":
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(path)
        try:
            return " ".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
        finally:
            doc.close()
    with zipfile.ZipFile(path) as zf:
        return " ".join(zf.read(n).decode("utf-8", "replace") for n in zf.namelist())


def test_tool_unavailable(tmp_path, settings):
    settings.EBOOK_CONVERT_BINARY = "/nonexistent/ebook-convert"
    with pytest.raises(ProcessingError) as exc:
        convert(tmp_path, "a.epub", epub_bytes([("Bob", "x")]), "epub", "pdf")
    assert exc.value.code == "tool_unavailable"


@needs_calibre
class TestConvert:
    def test_epub_to_pdf_keeps_uzbek_text(self, tmp_path, calibre):
        out = convert(tmp_path, "kitob.epub", epub_bytes([("Birinchi bob", "Gʻoʻza dalasi")]), "epub", "pdf")
        assert out.read_bytes().startswith(b"%PDF-")
        assert "Gʻoʻza dalasi" in text_of(out)

    @pytest.mark.parametrize(
        ("name", "data", "fmt"),
        [("ertak.fb2", fb2_bytes("Bir bor ekan"), "fb2"), ("hujjat.docx", docx_bytes("Bir bor ekan"), "docx")],
    )
    def test_to_epub(self, tmp_path, calibre, name, data, fmt):
        out = convert(tmp_path, name, data, fmt, "epub")
        assert "Bir bor ekan" in text_of(out)

    @pytest.mark.parametrize("target", ["mobi", "azw3"])
    def test_epub_to_kindle(self, tmp_path, calibre, target):
        out = convert(tmp_path, "kitob.epub", epub_bytes([("Bob", "Matn")]), "epub", target)
        assert out.read_bytes()[60:68] == b"BOOKMOBI"

    def test_broken_book(self, tmp_path, calibre):
        with pytest.raises(ProcessingError) as exc:
            convert(tmp_path, "a.epub", b"PK\x03\x04 not really a zip", "epub", "pdf")
        assert exc.value.code == "corrupt_file"


def _attacks(base: Path) -> dict[str, tuple[str, bytes]]:
    secret = base / "secret.txt"
    secret.write_text(SECRET)
    page = base / "secret.xhtml"
    page.write_text(f'<html xmlns="http://www.w3.org/1999/xhtml"><body><p>{SECRET}</p></body></html>')
    uri = secret.as_uri()
    escape = "../" * 12 + os.path.relpath(page, "/")
    return {
        # A manifest item that climbs out of the book to a server file.
        "manifest": (
            "epub",
            epub_bytes(
                [("Bob", "x")], extra_manifest=f'<item id="leak" href="{escape}" media-type="application/xhtml+xml"/>'
            ),
        ),
        # Embedded local URLs, which a browser engine rendering the PDF might load.
        "embed": (
            "epub",
            epub_bytes([("Bob", "x")], extra_body=f'<iframe src="{uri}"></iframe><object data="{uri}"></object>'),
        ),
        # XML external entity in FictionBook.
        "xxe": ("fb2", fb2_bytes("&e;", f'<!DOCTYPE FictionBook [<!ENTITY e SYSTEM "{uri}">]>')),
        # Script in the book: Calibre's PDF renderer runs it, so it must not be able to read local files.
        "script": (
            "epub",
            epub_bytes(
                [("Bob", "x")],
                extra_body=(
                    "<script>try{var r=new XMLHttpRequest();"
                    f"r.open('GET','{uri}',false);r.send();"
                    "document.body.appendChild(document.createTextNode(r.responseText));}catch(e){}</script>"
                ),
            ),
        ),
    }


@needs_calibre
@pytest.mark.parametrize("target", ["epub", "pdf"])
@pytest.mark.parametrize("attack", ["manifest", "embed", "xxe", "script"])
def test_books_cannot_pull_in_server_files(tmp_path, calibre, attack, target):
    fmt, data = _attacks(tmp_path)[attack]
    out = convert(tmp_path, f"evil.{fmt}", data, fmt, target)
    assert "canary-7f3a9c" not in text_of(out)


@needs_calibre
class TestText:
    def test_markdown_to_pdf(self, tmp_path, calibre):
        md = "# Hisobot\n\nBu **muhim** matn: gʻoʻza.\n\n- birinchi\n- ikkinchi\n".encode()
        src = tmp_path / "src-hisobot.md"
        src.write_bytes(md)
        [out] = ebooks.text_convert([InputFile(src, "hisobot.md", "md")], {"target": "pdf"}, tmp_path)
        assert out.name == "hisobot.pdf"
        assert "Bu muhim matn: gʻoʻza." in text_of(out.path)

    def test_text_to_docx(self, tmp_path, calibre):
        src = tmp_path / "src-eslatma.txt"
        src.write_text("Salom, dunyo!\n\nIkkinchi xatboshi.", encoding="utf-8")
        [out] = ebooks.text_convert([InputFile(src, "eslatma.txt", "txt")], {"target": "docx"}, tmp_path)
        assert out.name == "eslatma.docx"
        assert "Salom, dunyo!" in text_of(out.path)

    @pytest.mark.parametrize("target", ["pdf", "docx", "epub"])
    def test_markdown_cannot_pull_in_server_files(self, tmp_path, calibre, target):
        secret = tmp_path / "secret.txt"
        secret.write_text(SECRET)
        escape = "../" * 12 + os.path.relpath(secret, "/")
        md = (
            f"# Doc\n\n![x]({secret.as_uri()})\n\n![y]({escape})\n\n"
            f'<iframe src="{secret.as_uri()}"></iframe>\n<object data="{secret.as_uri()}"></object>\n'
            f"<script>var r=new XMLHttpRequest();r.open('GET','{secret.as_uri()}',false);r.send();"
            "document.body.appendChild(document.createTextNode(r.responseText));</script>\n"
        )
        src = tmp_path / "src-evil.md"
        src.write_text(md, encoding="utf-8")
        [out] = ebooks.text_convert([InputFile(src, "evil.md", "md")], {"target": target}, tmp_path)
        assert "canary-7f3a9c" not in text_of(out.path)
