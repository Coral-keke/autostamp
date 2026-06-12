"""
Server-side PDF/DWG preview — renders pages as PNG images using PyMuPDF.

This provides reliable previews without browser dependency on pdf.js CDN.
For DWG files, requires ODA CLI to convert to PDF first.
"""
import io
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

try:
    from ..config import settings
except ImportError:
    from config import settings


def render_pdf_page_to_png(
    pdf_path: Path,
    page_num: int = 1,
    scale: float = 1.5,
    max_dimension: int = 1200,
) -> bytes:
    """
    Render a single PDF page to PNG bytes.

    Args:
        pdf_path: Path to the PDF file.
        page_num: 1-indexed page number.
        scale: Render scale (higher = sharper, larger file).
        max_dimension: Maximum width/height in pixels (clamps scale).

    Returns:
        PNG image bytes.
    """
    doc = fitz.open(str(pdf_path))
    if page_num < 1 or page_num > doc.page_count:
        doc.close()
        raise ValueError(f"页码 {page_num} 超出范围 (1-{doc.page_count})")

    page = doc[page_num - 1]

    # Auto-adjust scale to fit within max_dimension
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix)

    # If too large, rescale
    if pix.width > max_dimension or pix.height > max_dimension:
        ratio = min(max_dimension / pix.width, max_dimension / pix.height)
        matrix = fitz.Matrix(ratio, ratio)
        pix = page.get_pixmap(matrix=matrix)

    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def render_pdf_to_png(
    pdf_bytes: bytes,
    page_num: int = 1,
    scale: float = 1.5,
) -> bytes:
    """
    Render PDF bytes to PNG. Convenience wrapper.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)

    try:
        return render_pdf_page_to_png(tmp_path, page_num, scale)
    finally:
        tmp_path.unlink(missing_ok=True)
