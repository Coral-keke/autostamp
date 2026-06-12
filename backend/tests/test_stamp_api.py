"""
Stamp API — integration tests via TestClient.

Tests async submit, status query, download, health check,
and admin cleanup endpoints.
"""
import io
import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from PIL import Image

import pytest


# ── Helpers ──────────────────────────────────────────────────────

def _make_seal_png():
    buf = io.BytesIO()
    img = Image.new("RGBA", (200, 200), (255, 0, 0, 100))
    img.save(buf, "PNG"); buf.seek(0)
    return buf.read(), "seal.png"


def _make_test_pdf(tmpdir: Path) -> Path:
    import fitz
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.new_page(width=595, height=842)
    doc.save(str(tmpdir / "test.pdf"))
    doc.close()
    return tmpdir / "test.pdf"


@pytest.fixture
def file_server(tmp_path):
    """Start a temporary HTTP server serving tmp_path files."""
    pdf = _make_test_pdf(tmp_path)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(tmp_path), **kwargs)

    server = HTTPServer(("127.0.0.1", 18976), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    url = f"http://127.0.0.1:18976/test.pdf"
    yield url

    server.shutdown()
    t.join(timeout=1)


@pytest.fixture
def seal(app):
    """Upload a test seal with unique code per test."""
    import uuid
    code = f"STAMP_{uuid.uuid4().hex[:8].upper()}"
    data, fname = _make_seal_png()
    r = app.post("/api/v1/seals", data={
        "name": "测试印章", "seal_code": code,
    }, files={"file": (fname, data, "image/png")})
    assert r.status_code == 200
    return code


# ── Tests ────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, app):
        resp = app.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "jobs" in body


class TestAsyncSubmit:
    """POST /api/v1/stamp/submit"""

    def test_submit_success(self, app, seal, file_server):
        resp = app.post("/api/v1/stamp/submit", json={
            "requestNo": "TEST-ASYNC-001",
            "businessId": "BIZ-001",
            "systemCode": "VP",
            "systemName": "测试系统",
            "fileType": "pdf",
            "sealCode": seal,
            "fileUrl": file_server,
            "callbackUrl": "http://localhost:9999/callback",
            "position": {"x": 420, "y": 680, "width": 120, "height": 120},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ACCEPTED"
        assert body["requestNo"] == "TEST-ASYNC-001"

    def test_submit_missing_seal_code(self, app, file_server):
        resp = app.post("/api/v1/stamp/submit", json={
            "requestNo": "TEST-ASYNC-002",
            "fileType": "pdf",
            "sealCode": "NONEXISTENT",
            "fileUrl": file_server,
            "position": {"x": 0, "y": 0, "width": 10, "height": 10},
        })
        assert resp.status_code == 404

    def test_duplicate_submit_returns_existing(self, app, seal, file_server):
        payload = {
            "requestNo": "TEST-DUP-001",
            "fileType": "pdf",
            "sealCode": seal,
            "fileUrl": file_server,
            "position": {"x": 0, "y": 0, "width": 10, "height": 10},
        }
        r1 = app.post("/api/v1/stamp/submit", json=payload)
        assert r1.status_code == 200

        # Resubmit — should not crash, returns existing status
        r2 = app.post("/api/v1/stamp/submit", json=payload)
        assert r2.status_code == 200
        assert r2.json()["requestNo"] == "TEST-DUP-001"


class TestStampStatus:
    """GET /api/v1/stamp/status/{requestNo}"""

    def test_status_nonexistent(self, app):
        resp = app.get("/api/v1/stamp/status/NONEXISTENT")
        assert resp.status_code == 404

    def test_status_after_submit(self, app, seal, file_server):
        r = app.post("/api/v1/stamp/submit", json={
            "requestNo": "TEST-STATUS-001",
            "fileType": "pdf",
            "sealCode": seal,
            "fileUrl": file_server,
            "position": {"x": 0, "y": 0, "width": 10, "height": 10},
        })
        assert r.status_code == 200

        resp = app.get("/api/v1/stamp/status/TEST-STATUS-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["requestNo"] == "TEST-STATUS-001"
        assert body["status"] in ("ACCEPTED", "PROCESSING", "SUCCESS", "FAILED")


class TestStampDownload:
    """GET /api/v1/stamp/download/{requestNo}"""

    def test_download_nonexistent(self, app):
        resp = app.get("/api/v1/stamp/download/NONEXISTENT")
        assert resp.status_code == 404


class TestAdminCleanup:
    """POST /api/v1/admin/cleanup"""

    def test_cleanup(self, app):
        resp = app.post("/api/v1/admin/cleanup")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "cleaned_files" in body
