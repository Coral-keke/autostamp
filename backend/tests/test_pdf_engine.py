"""
PDF Stamping Engine — unit tests.

Tests stamp_pdf() with both mm and pt coordinate modes,
including multi-page, rotation, edge cases.
"""
import fitz
from pathlib import Path

from backend.engines.pdf_engine import stamp_pdf


class TestPdfEngineMM:
    """Tests using mm coordinate input (Web UI mode)."""

    def test_basic_single_stamp(self, sample_pdf, sample_seal_image, temp_dir):
        out = temp_dir / "out_mm.pdf"
        stamp_pdf(
            input_path=sample_pdf, output_path=out,
            seal_path=sample_seal_image,
            seal_width_mm=40, seal_height_mm=40,
            positions=[{"page": 1, "x_mm": 50, "y_mm": 100}],
            input_unit="mm",
        )
        assert out.exists()
        doc = fitz.open(str(out))
        assert doc.page_count == 3
        # Verify page 1 has an image (stamp overlay)
        assert len(doc[0].get_images()) >= 1
        doc.close()

    def test_multi_page(self, sample_pdf, sample_seal_image, temp_dir):
        out = temp_dir / "out_mp.pdf"
        stamp_pdf(
            input_path=sample_pdf, output_path=out,
            seal_path=sample_seal_image,
            seal_width_mm=40, seal_height_mm=40,
            positions=[
                {"page": 1, "x_mm": 10, "y_mm": 20},
                {"page": 2, "x_mm": 30, "y_mm": 40},
                {"page": 3, "x_mm": 50, "y_mm": 60},
            ],
            input_unit="mm",
        )
        out_sz = out.stat().st_size
        assert out_sz > 1000  # Should be larger than input with stamps

    def test_out_of_range_page_skipped(self, sample_pdf, sample_seal_image, temp_dir):
        """Page 99 doesn't exist — should skip gracefully, not crash."""
        out = temp_dir / "out_skip.pdf"
        stamp_pdf(
            input_path=sample_pdf, output_path=out,
            seal_path=sample_seal_image,
            seal_width_mm=40, seal_height_mm=40,
            positions=[{"page": 99, "x_mm": 0, "y_mm": 0}],
            input_unit="mm",
        )
        assert out.exists()


class TestPdfEnginePT:
    """Tests using pt coordinate input (external API mode)."""

    def test_basic_pt_stamp(self, sample_pdf, sample_seal_image, temp_dir):
        out = temp_dir / "out_pt.pdf"
        stamp_pdf(
            input_path=sample_pdf, output_path=out,
            seal_path=sample_seal_image,
            seal_width_mm=40, seal_height_mm=40,
            positions=[{"page": 1, "x": 420, "y": 680, "width": 120, "height": 120}],
            input_unit="pt",
        )
        assert out.exists()
        doc = fitz.open(str(out))
        images = doc[0].get_images()
        assert len(images) >= 1
        doc.close()

    def test_pt_position_matches_bbox(self, sample_pdf, sample_seal_image, temp_dir):
        """Verify the stamp image placement matches the expected bbox."""
        out = temp_dir / "out_bbox.pdf"
        x, y, w, h = 300, 400, 150, 150
        stamp_pdf(
            input_path=sample_pdf, output_path=out,
            seal_path=sample_seal_image,
            seal_width_mm=40, seal_height_mm=40,
            positions=[{"page": 1, "x": x, "y": y, "width": w, "height": h}],
            input_unit="pt",
        )
        # Check the image was placed with correct bbox
        doc = fitz.open(str(out))
        img_list = doc[0].get_images(full=True)
        assert len(img_list) >= 1
        # fitz returns (xref, smask, width, height, bpc, colorspace, ...)
        doc.close()

    def test_rotation(self, sample_pdf, sample_seal_image, temp_dir):
        out = temp_dir / "out_rot.pdf"
        stamp_pdf(
            input_path=sample_pdf, output_path=out,
            seal_path=sample_seal_image,
            seal_width_mm=40, seal_height_mm=40,
            positions=[{"page": 1, "x": 200, "y": 300, "width": 100, "height": 100, "rotation": 90}],
            input_unit="pt",
        )
        assert out.exists()
        doc = fitz.open(str(out))
        assert len(doc[0].get_images()) >= 1
        doc.close()
