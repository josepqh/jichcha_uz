"""PDF page tools: rotate, remove and extract pages, page numbers, watermark, crop, protect, repair.

pikepdf (qpdf) does the page work; reportlab draws page numbers and watermarks on a transparent
overlay that is laid over each page, so the original content is never re-rendered.
"""

import io
import math
from functools import cache
from pathlib import Path

import pikepdf
from django.conf import settings
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ..formats import PDF_MIME
from .base import InputFile, OutputFile, ProcessingError, stem_of
from .pdf import open_pdf, parse_ranges, save_pdf

MM = 72 / 25.4
# Unicode fonts, first found wins: Uzbek (oʻ gʻ), Cyrillic and the rest need more than Helvetica.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)
WATERMARK_OPACITY = {"light": 0.12, "medium": 0.22, "strong": 0.35}
NUMBER_POSITIONS = ("bottom-center", "bottom-right", "bottom-left", "top-center", "top-right", "top-left")


@cache
def _font() -> str:
    for path in (getattr(settings, "PDF_FONT_PATH", ""), *FONT_CANDIDATES):
        if path and Path(path).is_file():
            pdfmetrics.registerFont(TTFont("jichcha-sans", path))
            return "jichcha-sans"
    return "Helvetica"  # Latin only; non-Latin text would show as boxes


def _one(inputs: list[InputFile]) -> InputFile:
    [src] = inputs
    return src


def _save(doc: pikepdf.Pdf, workdir: Path, src: InputFile, suffix: str) -> list[OutputFile]:
    out = workdir / f"{suffix}.pdf"
    save_pdf(doc, out)
    return [OutputFile(path=out, name=f"{stem_of(src.name)}-{suffix}.pdf", mime=PDF_MIME)]


def _page_set(spec: str, count: int) -> list[int]:
    """0-based page indexes named by '1-3, 5', in document order, each once."""
    wanted = {i for start, end in parse_ranges(spec, count) for i in range(start - 1, end)}
    return sorted(wanted)


def rotate_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    src = _one(inputs)
    with open_pdf(src.path) as doc:
        for page in doc.pages:
            page.rotate(int(options["angle"]), relative=True)
        return _save(doc, workdir, src, "rotated")


def remove_pages(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    src = _one(inputs)
    with open_pdf(src.path) as doc:
        gone = set(_page_set(options["pages"], len(doc.pages)))
        if len(gone) >= len(doc.pages):
            raise ProcessingError("all_pages_removed")
        for index in sorted(gone, reverse=True):
            del doc.pages[index]
        return _save(doc, workdir, src, "edited")


def extract_pages(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    src = _one(inputs)
    with open_pdf(src.path) as doc, pikepdf.new() as out_doc:
        for index in _page_set(options["pages"], len(doc.pages)):
            out_doc.pages.append(doc.pages[index])
        return _save(out_doc, workdir, src, "extract")


def _overlay(doc: pikepdf.Pdf, draw) -> pikepdf.Pdf:
    """One overlay page per document page, same size, drawn by draw(canvas, width, height, index)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    total = len(doc.pages)
    for index, page in enumerate(doc.pages):
        box = [float(v) for v in page.mediabox]
        width, height = box[2] - box[0], box[3] - box[1]
        c.setPageSize((width, height))
        draw(c, width, height, index, total)
        c.showPage()
    c.save()
    buf.seek(0)
    return pikepdf.open(buf)


def _apply_overlay(doc: pikepdf.Pdf, overlay: pikepdf.Pdf) -> None:
    for page, layer in zip(doc.pages, overlay.pages, strict=True):
        box = [float(v) for v in page.mediabox]
        page.add_overlay(layer, pikepdf.Rectangle(*box))


def add_page_numbers(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    src = _one(inputs)
    position, start, style = options["position"], int(options["start"]), options["style"]
    font = _font()

    def draw(c, width, height, index, total):
        number = start + index
        label = f"{number} / {start + total - 1}" if style == "n-of-total" else str(number)
        size = 10
        margin = 12 * MM
        y = margin - size / 2 if position.startswith("bottom") else height - margin
        c.setFont(font, size)
        c.setFillColor(Color(0.2, 0.2, 0.2))
        if position.endswith("center"):
            c.drawCentredString(width / 2, y, label)
        elif position.endswith("right"):
            c.drawRightString(width - margin, y, label)
        else:
            c.drawString(margin, y, label)

    with open_pdf(src.path) as doc, _overlay(doc, draw) as overlay:
        _apply_overlay(doc, overlay)
        return _save(doc, workdir, src, "numbered")


def add_watermark(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    src = _one(inputs)
    text, opacity = options["text"].strip(), WATERMARK_OPACITY[options["opacity"]]
    font = _font()

    def draw(c, width, height, index, total):
        # Across the page's diagonal, sized so the text spans about 70% of it.
        diagonal = math.hypot(width, height)
        size = max(12.0, min(160.0, 0.7 * diagonal / max(pdfmetrics.stringWidth(text, font, 1), 1)))
        c.saveState()
        c.translate(width / 2, height / 2)
        c.rotate(math.degrees(math.atan2(height, width)))
        c.setFont(font, size)
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
        c.drawCentredString(0, -size / 3, text)
        c.restoreState()

    with open_pdf(src.path) as doc, _overlay(doc, draw) as overlay:
        _apply_overlay(doc, overlay)
        return _save(doc, workdir, src, "watermarked")


def crop_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    """Trim the same margin (mm) from every side of every page, via the crop box."""
    src = _one(inputs)
    margin = int(options["margin"]) * MM
    with open_pdf(src.path) as doc:
        for page in doc.pages:
            x0, y0, x1, y1 = (float(v) for v in page.mediabox)
            if x1 - x0 <= 2 * margin + 36 or y1 - y0 <= 2 * margin + 36:  # keep at least half an inch
                raise ProcessingError("crop_too_large")
            page.obj.CropBox = pikepdf.Array([x0 + margin, y0 + margin, x1 - margin, y1 - margin])
        return _save(doc, workdir, src, "cropped")


def protect_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    """AES-256 encryption with the given open password. The password is never stored."""
    src = _one(inputs)
    password = options["password"]
    with open_pdf(src.path) as doc:
        out = workdir / "protected.pdf"
        doc.save(out, encryption=pikepdf.Encryption(user=password, owner=password, R=6), compress_streams=True)
    return [OutputFile(path=out, name=f"{stem_of(src.name)}-protected.pdf", mime=PDF_MIME)]


def repair_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    """qpdf rebuilds broken cross-reference tables and streams while opening; save a clean copy."""
    src = _one(inputs)
    with open_pdf(src.path) as doc:
        if len(doc.pages) == 0:
            raise ProcessingError("corrupt_file")
        return _save(doc, workdir, src, "repaired")
