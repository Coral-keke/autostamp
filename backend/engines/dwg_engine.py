"""
DWG Stamping Engine — DXF bridge approach.

Flow:  DWG ──ODA CLI──→ DXF ──ezdxf stamp──→ DXF ──ODA CLI──→ DWG

This preserves CAD data (layers, blocks, dimensions, xrefs).
Output is a valid DWG file — not DWF, not PDF.
"""
import subprocess
import tempfile
from pathlib import Path

import ezdxf
try:
    from ..config import settings
except ImportError:
    from config import settings


def _oda_convert(input_path: Path, output_path: Path, out_format: str, timeout: int = 120):
    """Run ODA File Converter. Accepted formats: DXF, DWG, PDF."""
    odabin = Path(settings.ODA_CONVERTER_PATH)
    if not odabin.exists():
        raise RuntimeError(f"ODA File Converter not found at {odabin}")

    result = subprocess.run(
        [str(odabin), str(input_path), str(output_path), out_format, "0", "1"],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ODA conversion failed: {result.stderr.strip()}")
    if not output_path.exists():
        raise RuntimeError(f"ODA output not created: {output_path}")


def stamp_dwg(
    input_path: Path,
    output_path: Path,
    seal_path: Path,
    positions: list[dict],
    input_unit: str = "mm",
):
    """
    Stamp a DWG file via DXF bridge, outputting DWG.

    Args:
        input_path:  Source DWG file.
        output_path: Destination DWG file.
        seal_path:   PNG seal image (with transparency).
        positions:   List of dicts with {page, x_mm, y_mm, width_mm?, height_mm?, rotation?}.
        input_unit:  "mm" (Web UI) or "pt" (API).
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="dwg_stamp_"))
    dxf_in  = tmp_dir / "input.dxf"
    dxf_out = tmp_dir / "stamped.dxf"

    try:
        # 1. DWG → DXF
        _oda_convert(input_path, dxf_in, "DXF")

        # 2. Stamp in DXF via ezdxf
        _stamp_dxf(dxf_in, dxf_out, seal_path, positions, input_unit)

        # 3. DXF → DWG
        _oda_convert(dxf_out, output_path, "DWG")
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _stamp_dxf(
    dxf_path: Path,
    output_path: Path,
    seal_path: Path,
    positions: list[dict],
    input_unit: str,
):
    """Insert raster image references into a DXF file at given positions."""
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # PNG size is known — we embed a reference to the seal image
    for pos in positions:
        # Convert coordinates
        if input_unit == "pt":
            x_mm = pos.get("x", 0) / settings.MM_TO_PT
            y_mm = pos.get("y", 0) / settings.MM_TO_PT
            w_mm = pos.get("width", 40 * settings.MM_TO_PT) / settings.MM_TO_PT
            h_mm = pos.get("height", 40 * settings.MM_TO_PT) / settings.MM_TO_PT
        else:
            x_mm = pos.get("x_mm", 0)
            y_mm = pos.get("y_mm", 0)
            w_mm = pos.get("width_mm", 40)
            h_mm = pos.get("height_mm", 40)

        rotation = pos.get("rotation", 0)

        # DXF uses Y-up, so flip the Y coordinate if needed
        insert_point = (x_mm, y_mm)

        # Insert as IMAGE entity (raster reference)
        img_def_name = f"SEAL_{seal_path.stem}"
        try:
            doc.images.add(str(seal_path), name=img_def_name)
        except Exception:
            pass  # Already defined

        image = msp.add_image(
            image_def=doc.image_defs.get(img_def_name),
            insert=insert_point,
            size_in_units=(w_mm, h_mm),
            rotation=rotation,
        )

    doc.saveas(str(output_path))
