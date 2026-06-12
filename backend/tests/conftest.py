"""
Shared fixtures for auto-stamp tests.

Isolates: temp directory, test DB, fresh FastAPI TestClient.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# ── Must happen BEFORE any backend imports ──────────────────────
# The database module caches connections per-thread. We swap the
# DB path and clear the cache so every test gets a fresh SQLite.
TMP = Path(tempfile.mkdtemp(prefix="autostamp_test_"))
import backend.models.database as db_mod
db_mod.DB_PATH = TMP / "test_autostamp.db"
# Reset cached connections so init_db() creates tables in the new file
if hasattr(db_mod._get_conn, "_conns"):
    db_mod._get_conn._conns.clear()
db_mod.init_db()
# ────────────────────────────────────────────────────────────────

import backend.config as cfg
cfg.settings.SEAL_STORAGE = TMP / "seals"
cfg.settings.UPLOAD_DIR    = TMP / "uploads"
cfg.settings.OUTPUT_DIR    = TMP / "output"
cfg.settings.TEMP_DIR      = TMP / "temp"
cfg.settings.HMAC_SECRET   = "test-secret-key-for-hmac"
cfg.settings.API_KEY        = ""

for d in [cfg.settings.SEAL_STORAGE, cfg.settings.UPLOAD_DIR,
          cfg.settings.OUTPUT_DIR, cfg.settings.TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

from backend.main import app as _app
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """FastAPI TestClient with isolated settings and fresh DB."""
    client = TestClient(_app)
    yield client


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp():
    """Clean up the temp directory after all tests."""
    yield
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)


# ── Data fixtures ──────────────────────────────────────────────

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_pdf(temp_dir):
    """Create a minimal 3-page PDF."""
    import fitz
    path = temp_dir / "sample.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)  # A4 pt
        page.insert_text((50, 50), f"Page {i+1} — Test", fontsize=14)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def sample_seal_image(temp_dir):
    """A transparent PNG seal."""
    from PIL import Image, ImageDraw
    path = temp_dir / "seal.png"
    img = Image.new("RGBA", (200, 200), (255, 0, 0, 128))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, 190, 190), fill=(200, 0, 0, 180))
    draw.text((60, 90), "TEST", fill=(255, 255, 255, 255))
    img.save(str(path), "PNG")
    return path
