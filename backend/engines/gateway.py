"""
Multi-Format Stamping Gateway — Strategy Pattern.

Routes stamp requests to the correct engine based on file extension.
All engines share the same position format (mm or pt).
"""
from pathlib import Path

from .pdf_engine import stamp_pdf
from .dwg_engine import stamp_dwg
from .image_engine import stamp_image
from .office_engine import stamp_docx, stamp_xlsx
try:
    from ..config import settings
except ImportError:
    from config import settings


# ── Strategy registry ──────────────────────────────────────────
ENGINES = {
    "pdf":  stamp_pdf,
    "dwg":  stamp_dwg,
    "png":  stamp_image,
    "jpg":  stamp_image,
    "jpeg": stamp_image,
    "bmp":  stamp_image,
    "tiff": stamp_image,
    "tif":  stamp_image,
    "docx": stamp_docx,
    "xlsx": stamp_xlsx,
}

SUPPORTED_EXTENSIONS = list(ENGINES.keys())


def stamp_file(
    input_path: Path,
    output_path: Path,
    seal_path: Path,
    positions: list[dict],
    input_unit: str = "mm",
    file_type: str = None,
):
    """
    Route to the correct engine based on file extension.

    Args:
        input_path: Source file.
        output_path: Destination file.
        seal_path: PNG seal image.
        positions: List of position dicts — all engines accept the same format.
        input_unit: "mm" or "pt".
        file_type: Override auto-detection (e.g., force "dwf" as "dwg").

    Raises:
        ValueError if the file type is unsupported.
    """
    ext = (file_type or input_path.suffix.lstrip(".")).lower()

    engine = ENGINES.get(ext)
    if not engine:
        raise ValueError(
            f"Unsupported file type: .{ext}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    return engine(
        input_path=input_path,
        output_path=output_path,
        seal_path=seal_path,
        positions=positions,
        input_unit=input_unit,
    )
