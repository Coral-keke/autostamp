"""
Keyword Auto-Positioning & Cross-Page Seal Engines.

Keyword positioning:
  Search for text ("乙方盖章") in PDF/Word files, return absolute coordinates.
  Used by external systems that don't provide explicit (x,y) positions.

Cross-page seal (骑缝章):
  Split a seal image into N equal horizontal slices (one per page),
  stamp each slice on the right edge of every page so the seal
  appears complete only when pages are aligned.
"""
from pathlib import Path
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image

try:
    from ..config import settings
except ImportError:
    from config import settings


# ═══════════════════════════════════════════════════════════════
#  KEYWORD POSITIONING
# ═══════════════════════════════════════════════════════════════

def find_keyword_positions_pdf(
    pdf_path: Path,
    keyword: str,
    page_num: int = None,
) -> list[dict]:
    """
    Search for a keyword in a PDF and return bounding box positions.

    Returns list of {"page": int, "x": float, "y": float, "width": float, "height": float}
    in PDF points (72 DPI).
    """
    doc = fitz.open(str(pdf_path))
    results = []

    pages = [page_num - 1] if page_num else range(doc.page_count)
    for pn in pages:
        if pn < 0 or pn >= doc.page_count:
            continue
        page = doc[pn]
        instances = page.search_for(keyword)
        for rect in instances:
            results.append({
                "page": pn + 1,
                "x": rect.x0,
                "y": rect.y0,
                "width": rect.width,
                "height": rect.height,
            })

    doc.close()
    return results


def find_keyword_positions_docx(
    docx_path: Path,
    keyword: str,
) -> list[dict]:
    """
    Search for a keyword in a .docx file.

    Note: python-docx doesn't provide exact pixel coordinates for runs.
    Returns page=1 with approximate position based on paragraph index.
    For precise positioning, convert to PDF first via LibreOffice.
    """
    from docx import Document
    doc = Document(str(docx_path))
    results = []

    for pi, para in enumerate(doc.paragraphs):
        if keyword in para.text:
            # Approximate: 10mm top-margin + ~5mm per paragraph
            y_mm = 10 + pi * 5
            results.append({
                "page": 1,
                "x_mm": 20,  # left margin
                "y_mm": y_mm,
                "width_mm": 40,
                "height_mm": 15,
                "text": para.text[:80],
            })

    return results


def suggest_stamp_position(
    file_path: Path,
    keyword: str,
    file_type: str = "pdf",
    offset_x_mm: float = 60,
    offset_y_mm: float = 15,
) -> list[dict]:
    """
    Given a keyword, return suggested stamp positions (offset to the right of the keyword).

    This provides the coordinates that can be passed directly to stamp_xxx() functions.
    """
    if file_type == "pdf":
        hits = find_keyword_positions_pdf(file_path, keyword)
        positions = []
        for h in hits:
            positions.append({
                "page": h["page"],
                "x": h["x"] + offset_x_mm * settings.MM_TO_PT,
                "y": h["y"] + h["height"] + offset_y_mm * settings.MM_TO_PT,
                "width": 40 * settings.MM_TO_PT,
                "height": 40 * settings.MM_TO_PT,
            })
        return positions

    elif file_type == "docx":
        hits = find_keyword_positions_docx(file_path, keyword)
        positions = []
        for h in hits:
            positions.append({
                "page": h.get("page", 1),
                "x_mm": h["x_mm"] + offset_x_mm,
                "y_mm": h["y_mm"] + offset_y_mm,
                "width_mm": 40,
                "height_mm": 40,
            })
        return positions

    return []


# ═══════════════════════════════════════════════════════════════
#  CROSS-PAGE SEAL (骑缝章)
# ═══════════════════════════════════════════════════════════════

def generate_cross_page_positions(
    pdf_path: Path,
    seal_path: Path,
    edge: str = "right",
    margin_mm: float = 5,
) -> list[dict]:
    """
    Generate stamp positions for a cross-page (骑缝) seal.

    The seal image is split vertically into one slice per page.
    Each slice is stamped on the specified edge of its corresponding page.

    Args:
        pdf_path: The PDF to stamp.
        seal_path: Seal image (PNG).
        edge: "left" or "right" — which edge to place the slices.
        margin_mm: Distance from the edge.

    Returns:
        List of position dicts ready for stamp_pdf().
    """
    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count
    doc.close()

    if total_pages == 0:
        return []

    seal_img = Image.open(str(seal_path))
    seal_w, seal_h = seal_img.size  # pixels

    # Each slice height (pixels) = total seal height / pages
    slice_h_px = max(1, seal_h // total_pages)

    positions = []
    for i in range(total_pages):
        y0 = i * slice_h_px
        y1 = min((i + 1) * slice_h_px, seal_h)

        # Crop slice
        slice_img = seal_img.crop((0, y0, seal_w, y1))

        # Save slice to temp
        slice_path = seal_path.parent / f"_seal_slice_{i}.png"
        slice_img.save(str(slice_path), "PNG")

        # Position on page
        if edge == "right":
            # Right edge, full height
            x_mm = 210 - margin_mm - 15  # A4 width = 210mm, seal≈15mm
        else:
            x_mm = margin_mm

        # Y position: stretch slice to fit page proportionally
        page_h_mm = 297  # A4 height
        slice_h_on_page = page_h_mm * (slice_h_px / seal_h)

        positions.append({
            "page": i + 1,
            "x_mm": x_mm,
            "y_mm": i * slice_h_on_page,  # Stacked vertically
            "width_mm": 15,
            "height_mm": slice_h_on_page,
            "rotation": 0,
            "seal_slice_path": str(slice_path),  # Hint for engine
        })

    return positions
