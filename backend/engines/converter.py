"""
DWG ↔ PDF ↔ DWF Converter — wraps ODA File Converter CLI.

ODA File Converter is a free command-line tool from the Open Design Alliance
that converts between DWG, DXF, PDF, and DWF formats.

Download: https://www.opendesign.com/guestfiles/oda_file_converter

Installation (Linux):
  tar -xzf ODAFileConverter_*.tgz
  sudo cp ODAFileConverter_*/usr/bin/ODAFileConverter /usr/local/bin/

Usage:
  ODAFileConverter <input_dir> <output_dir> <version> <out_type> <recurse> <audit>
"""
import subprocess
from pathlib import Path

try:
    from ..config import settings
except ImportError:
    from config import settings


def _run_oda(input_path: Path, output_dir: Path, output_format: str) -> Path:
    """
    Run ODAFileConverter to convert a file.

    Args:
        input_path: Source file (.dwg or .pdf).
        output_dir: Directory for output (must exist).
        output_format: Target format extension: 'pdf' or 'dwf'.

    Returns:
        Path to the output file.

    Raises:
        RuntimeError: If conversion fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # ODAFileConverter CLI:
    #   ODAFileConverter <input_dir> <output_dir> <version> <out_type> <recurse> <audit>
    #   version: "Acad2018" or similar
    #   out_type: "PDF" or "DWF" or "DXF"
    #   recurse: 0 or 1
    #   audit: 0 or 1
    cmd = [
        settings.ODA_CONVERTER_PATH,
        str(input_path.parent),    # Input directory
        str(output_dir),           # Output directory
        "Acad2018",                # Target version
        output_format.upper(),     # "PDF" or "DWF"
        "0",                       # No recursion
        "0",                       # No audit
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,  # 2 min timeout for large files
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ODA File Converter 转换失败 (exit={result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # ODA names output as <basename>.<out_format>
    basename = input_path.stem
    output_path = output_dir / f"{basename}.{output_format.lower()}"

    if not output_path.exists():
        raise RuntimeError(f"ODA 转换后输出文件未找到: {output_path}")

    return output_path


def dwg_to_pdf(input_path: Path, output_path: Path) -> Path:
    """
    Convert DWG → PDF using ODA File Converter.

    The output_path is the desired destination; ODA generates in a temp dir
    and we move it.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_out = Path(tmpdir) / "out"
        tmp_out.mkdir()
        result = _run_oda(input_path, tmp_out, "pdf")
        result.rename(output_path)
    return output_path


def pdf_to_dwf(input_path: Path, output_path: Path) -> Path:
    """
    Convert PDF → DWF using ODA File Converter.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_out = Path(tmpdir) / "out"
        tmp_out.mkdir()
        result = _run_oda(input_path, tmp_out, "dwf")
        result.rename(output_path)
    return output_path
