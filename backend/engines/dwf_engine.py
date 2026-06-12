"""
DWF Direct Stamping Engine.

Current implementation: DWF is an Autodesk ZIP+XML format.
For the initial version, we stamp via the PDF intermediate pipeline
(dwg → pdf → stamp → dwf) in converter.py.

Future: direct DWF manipulation via ODA SDK for vector-level stamping
without the PDF round-trip quality loss.
"""
from pathlib import Path


def stamp_dwf_direct(
    input_dwf: Path,
    output_dwf: Path,
    seal_path: Path,
    positions: list[dict],
):
    """
    NOT YET IMPLEMENTED — placeholder for ODA SDK direct DWF stamping.

    This will be implemented when ODA Drawings SDK is integrated.
    For now, use the PDF intermediate pipeline in converter.py.
    """
    raise NotImplementedError(
        "DWF 直接盖章暂未实现。当前使用 DWG→PDF→盖章→DWF 管线。"
    )
