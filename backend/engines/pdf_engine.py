"""
PDF Stamping Engine — uses PyMuPDF (fitz) for seal overlay.

Supports two coordinate input modes:
  - input_unit="mm": x_mm, y_mm, width_mm, height_mm → auto-convert to pt (72 DPI)
  - input_unit="pt": x, y, width, height already in pt → direct placement

External API (async submit) uses "pt" mode — position values are raw PDF points.
Web UI (drag mode) uses "mm" mode — human-oriented millimeters.
"""
from pathlib import Path
import fitz  # PyMuPDF
try:
    from ..config import settings
except ImportError:
    from config import settings


def stamp_pdf(
    input_path: Path,
    output_path: Path,
    seal_path: Path,
    seal_width_mm: float,
    seal_height_mm: float,
    positions: list[dict],
    input_unit: str = "mm",
):
    """
    Overlay a seal image onto a PDF at the given positions.

    Args:
        input_path: Source PDF file.
        output_path: Destination PDF file.
        seal_path: Seal image (PNG with transparency).
        seal_width_mm: Default seal width in mm (fallback when width not in position).
        seal_height_mm: Default seal height in mm (fallback when height not in position).
        positions: List of dicts. Fields depend on input_unit:
            input_unit="mm":
                - page (int, 1-indexed)
                - x_mm (float): X from left, mm
                - y_mm (float): Y from bottom, mm
                - width_mm (float, optional): seal width, mm
                - height_mm (float, optional): seal height, mm
                - rotation (float, optional): degrees clockwise, default 0
            input_unit="pt":
                - page (int, 1-indexed)
                - x (float): X from left, pt (PDF native)
                - y (float): Y from bottom, pt (PDF native)
                - width (float, optional): seal width, pt
                - height (float, optional): seal height, pt
                - rotation (float, optional): degrees clockwise, default 0
    """
    doc = fitz.open(str(input_path))
    total_pages = doc.page_count

    try:
        for pos in positions:
            page_num = pos.get("page", 1)
            rotation = pos.get("rotation", 0)

            if input_unit == "pt":
                # Direct PDF coordinates — no conversion needed
                x_pt = pos.get("x", 0)
                y_pt = pos.get("y", 0)
                w_pt = pos.get("width", seal_width_mm * settings.MM_TO_PT)
                h_pt = pos.get("height", seal_height_mm * settings.MM_TO_PT)
            else:
                # mm → pt conversion
                x_mm = pos.get("x_mm", 0)
                y_mm = pos.get("y_mm", 0)
                w_mm = pos.get("width_mm", seal_width_mm)
                h_mm = pos.get("height_mm", seal_height_mm)

                x_pt = x_mm * settings.MM_TO_PT
                y_pt = y_mm * settings.MM_TO_PT
                w_pt = w_mm * settings.MM_TO_PT
                h_pt = h_mm * settings.MM_TO_PT

            # Validate page number
            if page_num < 1 or page_num > total_pages:
                continue

            page = doc[page_num - 1]  # 0-indexed

            # fitz.Rect: (x0, y0, x1, y1) — bottom-left origin
            rect = fitz.Rect(x_pt, y_pt, x_pt + w_pt, y_pt + h_pt)

            seal_bytes = seal_path.read_bytes()

            if rotation != 0:
                page.insert_image(
                    rect, stream=seal_bytes,
                    rotate=rotation, overlay=True,
                )
            else:
                page.insert_image(
                    rect, stream=seal_bytes, overlay=True,
                )

        doc.save(str(output_path))
    finally:
        doc.close()
