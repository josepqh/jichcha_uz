"""PDF tools on permissively licensed engines: pikepdf (qpdf, MPL) and pypdfium2 (PDFium, BSD/Apache)."""

import io
import re
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium
from django.conf import settings
from PIL import Image

from ..formats import IMAGE_FORMATS, PDF_MIME
from .base import InputFile, OutputFile, ProcessingError, stem_of

MAX_PAGES = 500
MAX_RENDER_PAGES = 200

# level: (longest image side in px, JPEG quality)
PDF_COMPRESS_LEVELS = {"strong": (1200, 50), "medium": (1800, 65), "light": (2600, 80)}
RENDER_DPI = {"low": 72, "medium": 150, "high": 300}

_RANGE = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d*)\s*)?$")


def open_pdf(path: Path) -> pikepdf.Pdf:
    try:
        pdf = pikepdf.open(path)
    except pikepdf.PasswordError as exc:
        raise ProcessingError("pdf_encrypted") from exc
    except (pikepdf.PdfError, OSError, ValueError) as exc:
        raise ProcessingError("corrupt_file") from exc
    if len(pdf.pages) > MAX_PAGES:
        pdf.close()
        raise ProcessingError("too_many_pages")
    return pdf


def save_pdf(pdf: pikepdf.Pdf, path: Path) -> None:
    pdf.remove_unreferenced_resources()
    pdf.save(
        path,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
        recompress_flate=True,
    )


def parse_ranges(spec: str, page_count: int) -> list[tuple[int, int]]:
    """'1-3, 5, 8-' -> [(1, 3), (5, 5), (8, page_count)] (1-based, inclusive)."""
    ranges = []
    for part in spec.split(","):
        if not part.strip():
            continue
        match = _RANGE.match(part)
        if not match:
            raise ProcessingError("invalid_page_range")
        start = int(match.group(1))
        end_raw = match.group(2)
        end = start if end_raw is None else (int(end_raw) if end_raw else page_count)
        if not 1 <= start <= end <= page_count:
            raise ProcessingError("invalid_page_range")
        ranges.append((start, end))
    if not ranges:
        raise ProcessingError("invalid_page_range")
    return ranges


# --- Tools ------------------------------------------------------------------------------------------


def merge_pdfs(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    merged = pikepdf.new()
    for src in inputs:
        with open_pdf(src.path) as pdf:
            if len(merged.pages) + len(pdf.pages) > MAX_PAGES:
                raise ProcessingError("too_many_pages")
            merged.pages.extend(pdf.pages)
    out = workdir / "merged.pdf"
    save_pdf(merged, out)
    return [OutputFile(path=out, name=f"{stem_of(inputs[0].name)}-merged.pdf", mime=PDF_MIME)]


def split_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    src = inputs[0]
    stem = stem_of(src.name)
    outputs = []
    with open_pdf(src.path) as pdf:
        count = len(pdf.pages)
        if options["mode"] == "each":
            ranges = [(n, n) for n in range(1, count + 1)]
        else:
            ranges = parse_ranges(options.get("ranges", ""), count)
        for i, (start, end) in enumerate(ranges):
            part = pikepdf.new()
            part.pages.extend(pdf.pages[start - 1 : end])
            out = workdir / f"part-{i}.pdf"
            save_pdf(part, out)
            label = f"{start}" if start == end else f"{start}-{end}"
            outputs.append(OutputFile(path=out, name=f"{stem}-p{label}.pdf", mime=PDF_MIME))
    return outputs


def organize_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    """Rebuild the document from an ordered list of {page, rotate}; pages left out are deleted."""
    src = inputs[0]
    with open_pdf(src.path) as pdf:
        count = len(pdf.pages)
        result = pikepdf.new()
        for item in options["pages"]:
            if not 1 <= item["page"] <= count:
                raise ProcessingError("invalid_page_range")
            result.pages.append(pdf.pages[item["page"] - 1])
            if item.get("rotate"):
                result.pages[-1].rotate(item["rotate"], relative=True)
        out = workdir / "organized.pdf"
        save_pdf(result, out)
    return [OutputFile(path=out, name=f"{stem_of(src.name)}.pdf", mime=PDF_MIME)]


def _recompress_image(obj: pikepdf.Object, max_side: int, quality: int) -> None:
    """Downscale and re-encode one image XObject as JPEG when that makes it smaller."""
    if obj.get("/ImageMask") or "/Decode" in obj or "/SMaskInData" in obj:
        return
    image = pikepdf.PdfImage(obj)
    if image.bits_per_component != 8 or image.colorspace not in ("/DeviceRGB", "/DeviceGray") or image.indexed:
        return
    if image.width * image.height > settings.IMAGE_MAX_PIXELS or max(image.width, image.height) < 64:
        return
    try:
        pil = image.as_pil_image()
    except pikepdf.PdfError, NotImplementedError, OSError, ValueError:
        return  # unusual encoding: leave it untouched
    if pil.mode not in ("RGB", "L"):
        return
    if max(pil.size) > max_side:
        pil.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    pil.save(buffer, format="JPEG", quality=quality, optimize=True)
    data = buffer.getvalue()
    if len(data) >= len(obj.read_raw_bytes()):
        return
    obj.write(data, filter=pikepdf.Name.DCTDecode)
    obj.Width, obj.Height = pil.size
    obj.ColorSpace = pikepdf.Name.DeviceRGB if pil.mode == "RGB" else pikepdf.Name.DeviceGray
    obj.BitsPerComponent = 8
    if "/DecodeParms" in obj:
        del obj.DecodeParms


def compress_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    max_side, quality = PDF_COMPRESS_LEVELS[options["level"]]
    outputs = []
    for i, src in enumerate(inputs):
        with open_pdf(src.path) as pdf:
            seen: set[tuple[int, int]] = set()
            for page in pdf.pages:
                for raw in page.get_images().values():
                    if raw.objgen in seen:
                        continue
                    seen.add(raw.objgen)
                    _recompress_image(raw, max_side, quality)
            out = workdir / f"compressed-{i}.pdf"
            save_pdf(pdf, out)
        if out.stat().st_size >= src.path.stat().st_size:
            out.write_bytes(src.path.read_bytes())  # already optimal: never hand back a bigger file
        outputs.append(OutputFile(path=out, name=f"{stem_of(src.name)}.pdf", mime=PDF_MIME))
    return outputs


def pdf_to_images(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    fmt = options["format"]
    dpi = RENDER_DPI[options["quality"]]
    src = inputs[0]
    stem = stem_of(src.name)
    outputs = []
    try:
        document = pdfium.PdfDocument(src.path)
    except pdfium.PdfiumError as exc:
        code = "pdf_encrypted" if "password" in str(exc).lower() else "corrupt_file"
        raise ProcessingError(code) from exc
    try:
        count = len(document)
        if count > MAX_RENDER_PAGES:
            raise ProcessingError("too_many_pages")
        for index in range(count):
            page = document[index]
            try:
                width_pt, height_pt = page.get_size()
                scale = dpi / 72
                # Keep each rendered page under the decompression-bomb ceiling.
                limit = settings.IMAGE_MAX_PIXELS / max(width_pt * height_pt, 1)
                scale = min(scale, limit**0.5)
                bitmap = page.render(scale=scale)
                image = bitmap.to_pil()
                if fmt == "jpg" and image.mode != "RGB":
                    image = image.convert("RGB")
                out = workdir / f"page-{index + 1}.{IMAGE_FORMATS[fmt][2]}"
                save_kwargs = {"quality": 88, "optimize": True} if fmt == "jpg" else {"optimize": True}
                image.save(out, format=IMAGE_FORMATS[fmt][0], **save_kwargs)
            finally:
                page.close()
            outputs.append(
                OutputFile(path=out, name=f"{stem}-{index + 1:03d}.{IMAGE_FORMATS[fmt][2]}", mime=IMAGE_FORMATS[fmt][1])
            )
    finally:
        document.close()
    return outputs
