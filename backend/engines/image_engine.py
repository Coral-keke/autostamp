"""
Image Stamping Engine — PNG / JPG / BMP / TIFF.

Uses PIL/Pillow to overlay a seal onto an image at specified coordinates.
"""
from pathlib import Path

from PIL import Image


def stamp_image(
    input_path: Path,
    output_path: Path,
    seal_path: Path,
    positions: list[dict],
    input_unit: str = "mm",
):
    """
    Stamp a seal onto an image file.

    Args:
        input_path: Source image (PNG, JPG, BMP, TIFF).
        output_path: Output image (keeps original format).
        seal_path: PNG seal (with transparency).
        positions: List of {page:1, x_mm, y_mm, width_mm?, height_mm?, rotation?}.
                   'page' is ignored for images (always page 1).
        input_unit: "mm" or "pt" — converted to pixel via DPI assumption.
    """
    base = Image.open(str(input_path)).convert("RGBA")
    seal = Image.open(str(seal_path)).convert("RGBA")

    # Assume 96 DPI for images unless a different mapping is needed
    dpi = 96
    px_per_mm = dpi / 25.4

    for pos in positions:
        if input_unit == "pt":
            x_px = pos.get("x", 0) / 72.0 * dpi
            y_px = pos.get("y", 0) / 72.0 * dpi
            w_px = pos.get("width", 40 * 2.8346) / 72.0 * dpi
            h_px = pos.get("height", 40 * 2.8346) / 72.0 * dpi
        else:
            x_px = int(pos.get("x_mm", 0) * px_per_mm)
            y_px = int(pos.get("y_mm", 0) * px_per_mm)
            w_px = int(pos.get("width_mm", 40) * px_per_mm)
            h_px = int(pos.get("height_mm", 40) * px_per_mm)

        rotation = pos.get("rotation", 0)

        # Scale seal to target size
        seal_resized = seal.resize((max(1, w_px), max(1, h_px)), Image.LANCZOS)

        if rotation != 0:
            seal_resized = seal_resized.rotate(rotation, expand=True, resample=Image.BICUBIC)

        # Paste with alpha mask
        base.paste(seal_resized, (x_px, y_px), seal_resized)

    # Save — preserve format
    fmt = input_path.suffix.upper().lstrip(".")
    save_fmt = "JPEG" if fmt in ("JPG", "JPEG") else fmt
    base = base.convert("RGB") if save_fmt == "JPEG" else base
    base.save(str(output_path), format=save_fmt)
