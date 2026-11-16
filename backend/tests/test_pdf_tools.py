import io
import shutil

import pikepdf
import pytest
from PIL import Image

from apps.conversions.formats import detect_file
from apps.conversions.processors import office, pdf
from apps.conversions.processors.base import InputFile, ProcessingError
from tests.docs import docx_bytes, encrypted_pdf_bytes, pdf_bytes


def write(tmp_path, name: str, data: bytes, fmt: str = "pdf") -> InputFile:
    path = tmp_path / f"src-{name}"
    path.write_bytes(data)
    return InputFile(path=path, name=name, fmt=fmt)


def page_count(path) -> int:
    with pikepdf.open(path) as doc:
        return len(doc.pages)


class TestDetection:
    @pytest.mark.parametrize(
        ("data", "name", "fmt"),
        [
            (pdf_bytes(1), "x.bin", "pdf"),
            (docx_bytes(), "report.pdf", "docx"),  # extension lies; content wins
            ("Ism;Familiya\nAli;Valiyev\nGʻulom;Oʻrinov\n".encode(), "royxat.csv", "csv"),
            (b"{\\rtf1\\ansi Salom}", "a.rtf", "rtf"),
        ],
    )
    def test_documents(self, data, name, fmt):
        assert detect_file(io.BytesIO(data), name).fmt == fmt

    @pytest.mark.parametrize(
        ("data", "name"),
        [
            (b"PK\x03\x04garbage", "a.docx"),
            (b"MZ\x90\x00", "setup.pdf"),
            (b"a,b\n", "notes.log"),
            (b"\x00\x01", "a.csv"),
        ],
    )
    def test_rejects_unknown(self, data, name):
        assert detect_file(io.BytesIO(data), name) is None


def test_odf_mimetype_bomb_is_read_lazily(monkeypatch):
    """A huge 'mimetype' entry must never be fully decompressed during detection."""
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", b"application/vnd.oasis.opendocument.text" + b" " * 20_000_000)
    assert len(buf.getvalue()) < 100_000  # tiny on disk, 20 MB expanded
    monkeypatch.setattr(zipfile.ZipFile, "read", lambda *a, **k: pytest.fail("full read of an entry"))
    assert detect_file(io.BytesIO(buf.getvalue()), "x.odt").fmt == "odt"


class TestMergeSplitOrganize:
    def test_merge_keeps_order(self, tmp_path):
        a = write(tmp_path, "birinchi.pdf", pdf_bytes(2))
        b = write(tmp_path, "ikkinchi.pdf", pdf_bytes(3))
        [out] = pdf.merge_pdfs([a, b], {}, tmp_path)
        assert out.name == "birinchi-merged.pdf"
        assert page_count(out.path) == 5

    def test_split_each_page(self, tmp_path):
        outs = pdf.split_pdf([write(tmp_path, "doc.pdf", pdf_bytes(3))], {"mode": "each"}, tmp_path)
        assert [o.name for o in outs] == ["doc-p1.pdf", "doc-p2.pdf", "doc-p3.pdf"]
        assert all(page_count(o.path) == 1 for o in outs)

    def test_split_ranges(self, tmp_path):
        src = write(tmp_path, "doc.pdf", pdf_bytes(6))
        outs = pdf.split_pdf([src], {"mode": "ranges", "ranges": "1-2, 4, 5-"}, tmp_path)
        assert [o.name for o in outs] == ["doc-p1-2.pdf", "doc-p4.pdf", "doc-p5-6.pdf"]
        assert [page_count(o.path) for o in outs] == [2, 1, 2]

    @pytest.mark.parametrize("spec", ["0-2", "3-1", "9", "abc", ""])
    def test_bad_ranges(self, spec):
        with pytest.raises(ProcessingError) as exc:
            pdf.parse_ranges(spec, 5)
        assert exc.value.code == "invalid_page_range"

    def test_organize_reorders_rotates_and_deletes(self, tmp_path):
        src = write(tmp_path, "doc.pdf", pdf_bytes(3))
        spec = {"pages": [{"page": 3, "rotate": 90}, {"page": 1, "rotate": 0}]}
        [out] = pdf.organize_pdf([src], spec, tmp_path)
        with pikepdf.open(out.path) as doc:
            assert len(doc.pages) == 2
            assert int(doc.pages[0].obj.get("/Rotate", 0)) == 90
            assert int(doc.pages[1].obj.get("/Rotate", 0)) == 0

    def test_organize_page_out_of_range(self, tmp_path):
        with pytest.raises(ProcessingError):
            pdf.organize_pdf([write(tmp_path, "d.pdf", pdf_bytes(2))], {"pages": [{"page": 5}]}, tmp_path)

    def test_encrypted_pdf(self, tmp_path):
        with pytest.raises(ProcessingError) as exc:
            pdf.merge_pdfs([write(tmp_path, "s.pdf", encrypted_pdf_bytes())] * 2, {}, tmp_path)
        assert exc.value.code == "pdf_encrypted"

    def test_corrupt_pdf(self, tmp_path):
        with pytest.raises(ProcessingError) as exc:
            pdf.split_pdf([write(tmp_path, "b.pdf", b"%PDF-1.7\nnot really")], {"mode": "each"}, tmp_path)
        assert exc.value.code == "corrupt_file"

    def test_page_limit(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pdf, "MAX_PAGES", 2)
        with pytest.raises(ProcessingError) as exc:
            pdf.split_pdf([write(tmp_path, "d.pdf", pdf_bytes(3))], {"mode": "each"}, tmp_path)
        assert exc.value.code == "too_many_pages"


class TestCompressAndRender:
    def test_compress_shrinks_photo_heavy_pdf(self, tmp_path):
        src = write(tmp_path, "skan.pdf", pdf_bytes(2, size=(2400, 1800), quality=95, noise=True))
        [out] = pdf.compress_pdf([src], {"level": "strong"}, tmp_path)
        assert out.path.stat().st_size < src.path.stat().st_size * 0.6
        assert page_count(out.path) == 2

    def test_compress_never_grows_file(self, tmp_path):
        src = write(tmp_path, "tiny.pdf", pdf_bytes(1, size=(50, 50)))
        [out] = pdf.compress_pdf([src], {"level": "light"}, tmp_path)
        assert out.path.stat().st_size <= src.path.stat().st_size

    @pytest.mark.parametrize(("fmt", "magic"), [("jpg", b"\xff\xd8"), ("png", b"\x89PNG")])
    def test_pdf_to_images(self, tmp_path, fmt, magic):
        src = write(tmp_path, "slayd.pdf", pdf_bytes(2, size=(400, 300)))
        outs = pdf.pdf_to_images([src], {"format": fmt, "quality": "low"}, tmp_path)
        assert [o.name for o in outs] == [f"slayd-001.{fmt}", f"slayd-002.{fmt}"]
        assert outs[0].path.read_bytes()[:4].startswith(magic)
        with Image.open(outs[0].path) as img:
            assert img.size[0] > 0

    def test_render_respects_pixel_ceiling(self, tmp_path, settings):
        settings.IMAGE_MAX_PIXELS = 10_000
        src = write(tmp_path, "big.pdf", pdf_bytes(1, size=(800, 600)))
        [out] = pdf.pdf_to_images([src], {"format": "png", "quality": "high"}, tmp_path)
        with Image.open(out.path) as img:
            assert img.size[0] * img.size[1] <= 10_500


soffice_missing = shutil.which("soffice") is None and not shutil.os.path.exists(
    "/Applications/LibreOffice.app/Contents/MacOS/soffice"
)


class TestOffice:
    def test_missing_libreoffice_is_reported(self, tmp_path, settings):
        settings.SOFFICE_BINARY = "/nonexistent/soffice"
        with pytest.raises(ProcessingError) as exc:
            office.office_to_pdf([write(tmp_path, "a.docx", docx_bytes(), "docx")], {}, tmp_path)
        assert exc.value.code == "tool_unavailable"

    @pytest.mark.skipif(soffice_missing, reason="LibreOffice is not installed")
    def test_docx_to_pdf_with_uzbek_text(self, tmp_path, settings):
        if shutil.which("soffice") is None:
            settings.SOFFICE_BINARY = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        [out] = office.office_to_pdf([write(tmp_path, "Referat.docx", docx_bytes(), "docx")], {}, tmp_path)
        assert out.name == "Referat.pdf"
        assert out.path.read_bytes().startswith(b"%PDF-")
        assert page_count(out.path) == 1


def pdf_text(path) -> str:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(path)
    try:
        return "".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    finally:
        doc.close()


@pytest.mark.skipif(soffice_missing, reason="LibreOffice is not installed")
@pytest.mark.parametrize("fmt", ["docx", "odt"])
def test_office_does_not_pull_in_server_files(tmp_path, settings, fmt):
    """A document must not copy a local file (think /proc/1/environ) into the PDF.

    Vectors: a Word INCLUDETEXT field and an ODT linked section. LibreOffice 26.8 already skips
    these during --convert-to, even with a profile that forces link updates, so this guards
    against regressions in LibreOffice; the hardened profile in office.py is a second layer.
    """
    from tests.docs import docx_including_file, odt_linking_file

    if shutil.which("soffice") is None:
        settings.SOFFICE_BINARY = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    canary = tmp_path / "secret.txt"
    canary.write_text("SECRET_KEY=canary-7f3a9c")
    build = docx_including_file if fmt == "docx" else odt_linking_file
    src = write(tmp_path, f"evil.{fmt}", build(str(canary)), fmt)

    [out] = office.office_to_pdf([src], {}, tmp_path)

    text = pdf_text(out.path)
    assert "Before" in text and "After" in text
    assert "canary-7f3a9c" not in text
