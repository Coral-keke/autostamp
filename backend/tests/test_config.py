"""
Application configuration — unit tests.
"""
import os
import math
import pytest
from pathlib import Path


class TestDefaultSettings:
    """Verify default values are sane."""

    def test_mm_to_pt_conversion_factor(self):
        """1 mm = 72/25.4 ≈ 2.8346 points."""
        from backend.config import settings
        expected = 72.0 / 25.4
        assert math.isclose(settings.MM_TO_PT, expected, rel_tol=1e-6)

    def test_default_dpi(self):
        from backend.config import settings
        assert settings.DEFAULT_DPI == 72

    def test_allowed_formats(self):
        from backend.config import settings
        assert "pdf" in settings.ALLOWED_INPUT_FORMATS
        assert "dwg" in settings.ALLOWED_INPUT_FORMATS
        assert "pdf" in settings.ALLOWED_OUTPUT_FORMATS
        assert "dwf" in settings.ALLOWED_OUTPUT_FORMATS

    def test_seal_formats(self):
        from backend.config import settings
        assert "png" in settings.ALLOWED_SEAL_FORMATS

    def test_size_limits(self):
        from backend.config import settings
        assert settings.MAX_SEAL_SIZE_MB > 0
        assert settings.MAX_FILE_SIZE_MB > 0
        assert settings.MAX_FILE_SIZE_MB >= 10  # Must be reasonable

    def test_default_url(self):
        from backend.config import settings
        assert "localhost" in settings.BASE_URL or "8000" in settings.BASE_URL

    def test_paths_are_path(self):
        from backend.config import settings
        assert isinstance(settings.SEAL_STORAGE, Path)
        assert isinstance(settings.OUTPUT_DIR, Path)


class TestEnvOverrides:
    """Settings should respect environment variables."""

    def test_env_prefix(self):
        from backend.config import Settings
        os.environ["STAMP_API_KEY"] = "override-key-123"
        s = Settings()
        assert s.API_KEY == "override-key-123"
        del os.environ["STAMP_API_KEY"]

    def test_missing_env_uses_default(self):
        from backend.config import Settings
        s = Settings()
        assert s.CALLBACK_RETRY_COUNT == 3  # default


class TestCoordinateConversion:
    """mm ↔ pt round-trip."""

    def test_10mm_to_pt(self):
        from backend.config import settings
        pt = 10 * settings.MM_TO_PT
        assert math.isclose(pt, 720 / 25.4, rel_tol=1e-6)

    def test_pt_to_mm_roundtrip(self):
        from backend.config import settings
        pt = 100.0
        mm = pt / settings.MM_TO_PT
        pt2 = mm * settings.MM_TO_PT
        assert math.isclose(pt, pt2, rel_tol=1e-10)
