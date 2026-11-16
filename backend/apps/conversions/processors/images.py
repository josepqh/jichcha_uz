"""Image processors: format conversion, compression, images -> PDF."""

import warnings
from pathlib import Path

import img2pdf
from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from ..formats import IMAGE_FORMATS, PDF_MIME
from .base import InputFile, OutputFile, ProcessingError, stem_of

LOSSY_DEFAULT_QUALITY = 90

COMPRESS_LEVELS = {
    # level: (lossy quality, PNG palette colours or None for lossless)
    "strong": (55, 128),
    "medium": (72, 256),
    "light": (85, None),
}

PAGE_SIZES_PT = {
    "a4": (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297)),
    "letter": (img2pdf.in_to_pt(8.5), img2pdf.in_to_pt(11)),
    "fit": None,
}
MARGINS_MM = {"none": 0, "small": 10, "large": 20}


def open_image(path: Path) -> Image.Image:
    """Fully decode an image with bomb protection and apply EXIF orientation."""
    Image.MAX_IMAGE_PIXELS = settings.IMAGE_MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(path)
            img.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ProcessingError("image_too_large") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError) as exc:
        raise ProcessingError("corrupt_file") from exc
    return ImageOps.exif_transpose(img)


def has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def flatten(img: Image.Image, background=(255, 255, 255)) -> Image.Image:
    rgba = img.convert("RGBA")
    base = Image.new("RGB", rgba.size, background)
    base.paste(rgba, mask=rgba.getchannel("A"))
    return base


def prepare_for(img: Image.Image, fmt: str) -> Image.Image:
    """Convert colour mode so the target encoder accepts it."""
    alpha = has_alpha(img)
    if fmt in ("jpg", "bmp"):
        if alpha:
            return flatten(img)
        return img if img.mode in ("RGB", "L") else img.convert("RGB")
    if fmt == "gif":
        return img.convert("RGBA") if alpha else img.convert("RGB") if img.mode not in ("P", "L") else img
    # png, webp, avif, tiff
    if alpha:
        return img if img.mode == "RGBA" else img.convert("RGBA")
    if fmt == "png" and img.mode in ("L", "P", "RGB"):
        return img
    return img if img.mode == "RGB" else img.convert("RGB")


def save_image(img: Image.Image, path: Path, fmt: str, quality: int = LOSSY_DEFAULT_QUALITY) -> None:
    """Encode without EXIF/XMP metadata. ICC colour profile is kept."""
    pil_format = IMAGE_FORMATS[fmt][0]
    params: dict = {}
    icc = img.info.get("icc_profile")
    if icc and fmt in ("jpg", "png", "webp", "avif", "tiff"):
        params["icc_profile"] = icc
    if fmt == "jpg":
        params |= {"quality": quality, "optimize": True, "progressive": True}
    elif fmt == "png":
        params |= {"optimize": True}
    elif fmt == "webp":
        params |= {"quality": quality, "method": 4}
    elif fmt == "avif":
        params |= {"quality": quality, "speed": 6}
    elif fmt == "tiff":
        params |= {"compression": "tiff_deflate"}
    elif fmt == "gif":
        params |= {"optimize": True}
        if "transparency" in img.info:
            params["transparency"] = img.info["transparency"]
    img.save(path, format=pil_format, **params)


def _out_path(workdir: Path, index: int, fmt: str) -> Path:
    return workdir / f"out-{index}.{IMAGE_FORMATS[fmt][2]}"


# --- Tools ----------------------------------------------------------------


def convert_images(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    target: str = options["target"]
    quality: int = options.get("quality") or LOSSY_DEFAULT_QUALITY
    outputs = []
    for i, src in enumerate(inputs):
        with open_image(src.path) as img:
            out = _out_path(workdir, i, target)
            save_image(prepare_for(img, target), out, target, quality)
        outputs.append(
            OutputFile(path=out, name=f"{stem_of(src.name)}.{IMAGE_FORMATS[target][2]}", mime=IMAGE_FORMATS[target][1])
        )
    return outputs


def compress_target_format(src_fmt: str, alpha: bool) -> str:
    if src_fmt in ("jpg", "png", "webp", "avif", "gif"):
        return src_fmt
    return "png" if alpha else "jpg"  # heic, bmp, tiff


def _quantize(img: Image.Image, colors: int) -> Image.Image:
    if has_alpha(img):
        return img.convert("RGBA").quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
    return img.convert("RGB").quantize(colors=colors)


def compress_images(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    quality, png_colors = COMPRESS_LEVELS[options["level"]]
    if options.get("quality"):
        quality = options["quality"]
    outputs = []
    for i, src in enumerate(inputs):
        with open_image(src.path) as img:
            fmt = compress_target_format(src.fmt, has_alpha(img))
            prepared = prepare_for(img, fmt)
            lossy = _out_path(workdir, i, fmt)
            if fmt == "png" and png_colors:
                save_image(_quantize(prepared, png_colors), lossy, fmt)
            else:
                save_image(prepared, lossy, fmt, quality)
            chosen = lossy
            # A lossless, metadata-free re-encode is sometimes smaller (already optimised inputs).
            if fmt in ("png", "gif"):
                lossless = workdir / f"out-{i}-lossless.{IMAGE_FORMATS[fmt][2]}"
                save_image(prepared, lossless, fmt)
                if lossless.stat().st_size < lossy.stat().st_size:
                    chosen = lossless
        outputs.append(
            OutputFile(path=chosen, name=f"{stem_of(src.name)}.{IMAGE_FORMATS[fmt][2]}", mime=IMAGE_FORMATS[fmt][1])
        )
    return outputs


def _pdf_page_source(src: InputFile, index: int, workdir: Path) -> Path:
    """img2pdf embeds JPEG losslessly; everything else is normalised first."""
    with open_image(src.path) as img:
        if src.fmt == "jpg" and img.mode in ("RGB", "L", "CMYK") and not has_alpha(img):
            # Re-save only to bake in EXIF rotation and drop metadata; high quality keeps it visually lossless.
            out = workdir / f"page-{index}.jpg"
            save_image(img, out, "jpg", 95)
            return out
        if src.fmt in ("heic", "avif", "webp"):
            out = workdir / f"page-{index}.jpg"
            save_image(prepare_for(img, "jpg"), out, "jpg", 92)
            return out
        out = workdir / f"page-{index}.png"
        rgb = flatten(img) if has_alpha(img) else img if img.mode in ("RGB", "L") else img.convert("RGB")
        save_image(rgb, out, "png")
        return out


def images_to_pdf(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    pages = [_pdf_page_source(src, i, workdir) for i, src in enumerate(inputs)]
    margin = img2pdf.mm_to_pt(MARGINS_MM[options["margin"]])
    border = (margin, margin) if margin else None
    pagesize = PAGE_SIZES_PT[options["page_size"]]
    orientation = options["orientation"]
    if pagesize and orientation == "landscape":
        pagesize = (pagesize[1], pagesize[0])
    layout = img2pdf.get_layout_fun(
        pagesize=pagesize,
        border=border,
        fit=img2pdf.FitMode.into if pagesize else None,
        auto_orient=bool(pagesize) and orientation == "auto",
    )
    out = workdir / "out.pdf"
    try:
        with out.open("wb") as fh:
            img2pdf.convert([str(p) for p in pages], layout_fun=layout, outputstream=fh)
    except (img2pdf.ImageOpenError, ValueError) as exc:
        raise ProcessingError("corrupt_file") from exc
    return [OutputFile(path=out, name=f"{stem_of(inputs[0].name)}.pdf", mime=PDF_MIME)]


# --- Edit: crop, rotate, flip, resize (F-47 - F-49) ------------------------------------------------

ASPECTS = {"free": None, "1:1": (1, 1), "4:5": (4, 5), "16:9": (16, 9), "3:4": (3, 4)}
EDIT_FORMATS = ("keep", "jpg", "png", "webp")
MAX_EDGE = 10_000


def _crop_box(size: tuple[int, int], options: dict) -> tuple[int, int, int, int] | None:
    """Pixel box from a fractional crop (one image, chosen in the UI) or a centred aspect crop (batches)."""
    width, height = size
    if crop := options.get("crop"):
        left, top = round(crop["x"] * width), round(crop["y"] * height)
        right, bottom = round((crop["x"] + crop["w"]) * width), round((crop["y"] + crop["h"]) * height)
    elif ratio := ASPECTS.get(options.get("aspect", "free")):
        target = ratio[0] / ratio[1]
        if width / height > target:  # too wide: trim the sides
            new_w = round(height * target)
            left, top, right, bottom = (width - new_w) // 2, 0, (width - new_w) // 2 + new_w, height
        else:  # too tall: trim top and bottom
            new_h = round(width / target)
            left, top, right, bottom = 0, (height - new_h) // 2, width, (height - new_h) // 2 + new_h
    else:
        return None
    right, bottom = min(right, width), min(bottom, height)
    if right - left < 1 or bottom - top < 1:
        raise ProcessingError("invalid_crop")
    return left, top, right, bottom


def _resized_size(size: tuple[int, int], options: dict) -> tuple[int, int] | None:
    width, height = size
    mode = options.get("resize", "none")
    if mode == "percent":
        factor = options.get("percent", 100) / 100
        new = (round(width * factor), round(height * factor))
    elif mode == "pixels":
        w, h = options.get("width"), options.get("height")
        if w and h:
            new = (w, h)
        elif w:
            new = (w, round(height * w / width))
        else:
            new = (round(width * h / height), h)
    else:
        return None
    new = (max(1, new[0]), max(1, new[1]))
    if max(new) > MAX_EDGE or new[0] * new[1] > settings.IMAGE_MAX_PIXELS:
        raise ProcessingError("image_too_large")
    return new


def edit_image(img: Image.Image, options: dict) -> Image.Image:
    if box := _crop_box(img.size, options):
        img = img.crop(box)
    if rotate := options.get("rotate", 0):
        # Pillow rotates counter-clockwise; the UI and API speak clockwise.
        img = img.rotate(-rotate, expand=True)
    flip = options.get("flip", "none")
    if flip == "horizontal":
        img = ImageOps.mirror(img)
    elif flip == "vertical":
        img = ImageOps.flip(img)
    if size := _resized_size(img.size, options):
        img = img.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
    return img


def edit_images(inputs: list[InputFile], options: dict, workdir: Path) -> list[OutputFile]:
    wanted = options.get("format", "keep")
    outputs = []
    for i, src in enumerate(inputs):
        with open_image(src.path) as original:
            fmt = wanted if wanted != "keep" else compress_target_format(src.fmt, has_alpha(original))
            img = edit_image(original, options)
            out = _out_path(workdir, i, fmt)
            save_image(prepare_for(img, fmt), out, fmt)
        name = f"{stem_of(src.name)}-edited.{IMAGE_FORMATS[fmt][2]}"
        outputs.append(OutputFile(path=out, name=name, mime=IMAGE_FORMATS[fmt][1]))
    return outputs
