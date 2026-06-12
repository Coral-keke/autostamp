"""
Seal CRUD API — integration tests via TestClient.
"""
import io
from PIL import Image


def _make_seal_png():
    """Return (bytes, filename) for a valid seal PNG."""
    buf = io.BytesIO()
    img = Image.new("RGBA", (200, 200), (255, 0, 0, 100))
    img.save(buf, "PNG")
    buf.seek(0)
    return buf.read(), "test_seal.png"


class TestSealUpload:
    """POST /api/v1/seals"""

    def test_upload_success(self, app):
        data, fname = _make_seal_png()
        resp = app.post("/api/v1/seals", data={
            "name": "测试公章",
            "seal_code": "TEST_UPLOAD_001",
            "seal_type": "OFFICIAL",
        }, files={"file": (fname, data, "image/png")})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["seal"]["seal_code"] == "TEST_UPLOAD_001"

    def test_upload_duplicate_code_rejected(self, app):
        data, fname = _make_seal_png()
        # First upload
        app.post("/api/v1/seals", data={
            "name": "First", "seal_code": "DUP_001",
        }, files={"file": (fname, data, "image/png")})
        # Second upload with same code
        resp = app.post("/api/v1/seals", data={
            "name": "Second", "seal_code": "DUP_001",
        }, files={"file": (fname, data, "image/png")})
        assert resp.status_code == 409

    def test_upload_missing_seal_code(self, app):
        data, fname = _make_seal_png()
        resp = app.post("/api/v1/seals", data={
            "name": "No Code",
        }, files={"file": (fname, data, "image/png")})
        assert resp.status_code == 422


class TestSealList:
    """GET /api/v1/seals"""

    def test_list_empty(self, app):
        resp = app.get("/api/v1/seals")
        assert resp.status_code == 200
        body = resp.json()
        assert "seals" in body
        assert isinstance(body["count"], int)

    def test_list_with_seals(self, app):
        data, fname = _make_seal_png()
        app.post("/api/v1/seals", data={
            "name": "S1", "seal_code": "LIST_001",
        }, files={"file": (fname, data, "image/png")})
        resp = app.get("/api/v1/seals")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] >= 1


class TestSealGetByCode:
    """GET /api/v1/seals/code/{seal_code}"""

    def test_found(self, app):
        data, fname = _make_seal_png()
        app.post("/api/v1/seals", data={
            "name": "ByCode", "seal_code": "CODE_LOOKUP",
        }, files={"file": (fname, data, "image/png")})
        resp = app.get("/api/v1/seals/code/CODE_LOOKUP")
        assert resp.status_code == 200
        assert resp.json()["seal"]["seal_code"] == "CODE_LOOKUP"

    def test_not_found(self, app):
        resp = app.get("/api/v1/seals/code/NONEXISTENT")
        assert resp.status_code == 404


class TestSealUpdate:
    """PATCH /api/v1/seals/{id}"""

    def test_update_seal_code(self, app):
        data, fname = _make_seal_png()
        r = app.post("/api/v1/seals", data={
            "name": "Before", "seal_code": "UPDATE_001",
        }, files={"file": (fname, data, "image/png")})
        seal_id = r.json()["seal"]["id"]

        resp = app.patch(f"/api/v1/seals/{seal_id}", data={
            "seal_code": "UPDATE_001_NEW",
            "name": "After",
        })
        assert resp.status_code == 200
        assert resp.json()["seal"]["seal_code"] == "UPDATE_001_NEW"
        assert resp.json()["seal"]["name"] == "After"

    def test_update_nonexistent(self, app):
        resp = app.patch("/api/v1/seals/nonexistent-id", data={"name": "X"})
        assert resp.status_code == 404


class TestSealDelete:
    """DELETE /api/v1/seals/{id}"""

    def test_delete_success(self, app):
        data, fname = _make_seal_png()
        r = app.post("/api/v1/seals", data={
            "name": "ToDelete", "seal_code": "DEL_001",
        }, files={"file": (fname, data, "image/png")})
        seal_id = r.json()["seal"]["id"]

        resp = app.delete(f"/api/v1/seals/{seal_id}")
        assert resp.status_code == 200

        # Verify gone
        r2 = app.get(f"/api/v1/seals/{seal_id}")
        assert r2.status_code == 404

    def test_delete_nonexistent(self, app):
        resp = app.delete("/api/v1/seals/fake-id")
        assert resp.status_code == 404


class TestSealImage:
    """GET /api/v1/seals/{id}/image"""

    def test_get_image(self, app):
        data, fname = _make_seal_png()
        r = app.post("/api/v1/seals", data={
            "name": "Img", "seal_code": "IMG_001",
        }, files={"file": (fname, data, "image/png")})
        seal_id = r.json()["seal"]["id"]

        resp = app.get(f"/api/v1/seals/{seal_id}/image")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
