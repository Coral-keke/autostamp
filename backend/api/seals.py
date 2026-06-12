"""
Seal Management API — CRUD for stamps/seals.

Each seal has a `sealCode` (business code like "VP_GZ_001") used by
external systems to reference it.
"""
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

try:
    from ..config import settings
    from ..models.seal import (
        Seal, SealInDB,
        get_seal, get_seal_by_code, list_seals, save_seal, delete_seal,
    )
except ImportError:
    from config import settings
    from models.seal import (
        Seal, SealInDB,
        get_seal, get_seal_by_code, list_seals, save_seal, delete_seal,
    )

router = APIRouter(prefix="/api/v1/seals", tags=["seals"])


# ── Upload ──────────────────────────────────────────────────────

@router.post("", summary="上传新印章")
async def upload_seal(
    name: str = Form(...),
    seal_code: str = Form(..., description="业务编码，如 VP_GZ_001"),
    file: UploadFile = File(...),
    seal_type: str = Form("OFFICIAL"),
    description: str = Form(""),
    default_width_mm: float = Form(40.0),
    default_height_mm: float = Form(40.0),
    category: str = Form("general"),
):
    """Upload a seal image (PNG recommended, transparent background)."""
    # Validate format
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in settings.ALLOWED_SEAL_FORMATS:
        raise HTTPException(400, f"格式不支持: .{ext}")

    # Check seal_code uniqueness
    if get_seal_by_code(seal_code):
        raise HTTPException(409, f"印章编码 '{seal_code}' 已存在")

    # Validate size
    contents = await file.read()
    if len(contents) > settings.MAX_SEAL_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"文件超过 {settings.MAX_SEAL_SIZE_MB}MB")

    # Convert to PNG with transparency
    seal_id = uuid.uuid4().hex[:12]
    safe_name = f"{seal_id}.png"
    img = Image.open(BytesIO(contents))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.save(settings.SEAL_STORAGE / safe_name, "PNG")

    seal = SealInDB(
        id=seal_id,
        name=name,
        seal_code=seal_code,
        seal_type=seal_type,
        description=description,
        default_width_mm=default_width_mm,
        default_height_mm=default_height_mm,
        category=category,
        filename=safe_name,
        file_size_bytes=len(contents),
        original_filename=file.filename or "unknown",
    )
    save_seal(seal)
    return {"status": "ok", "seal": seal.model_dump()}


# ── List ────────────────────────────────────────────────────────

@router.get("", summary="获取印章列表")
def get_seals(category: str | None = None, seal_type: str | None = None):
    seals = list_seals(category=category, seal_type=seal_type)
    return {"count": len(seals), "seals": [s.model_dump() for s in seals]}


# ── Lookup by sealCode ─────────────────────────────────────────

@router.get("/code/{seal_code}", summary="按编码查询印章")
def get_seal_by_code_api(seal_code: str):
    """Look up a seal by its business code (sealCode)."""
    seal = get_seal_by_code(seal_code)
    if not seal:
        raise HTTPException(404, f"印章编码 '{seal_code}' 不存在")
    return {"seal": seal.model_dump()}


# ── Get One ─────────────────────────────────────────────────────

@router.get("/{seal_id}", summary="获取印章详情")
def get_seal_detail(seal_id: str):
    seal = get_seal(seal_id)
    if not seal:
        raise HTTPException(404, "印章不存在")
    return {"seal": seal.model_dump()}


# ── Update ─────────────────────────────────────────────────────

@router.patch("/{seal_id}", summary="修改印章信息")
def update_seal_api(
    seal_id: str,
    seal_code: str = Form(None, description="新业务编码"),
    name: str = Form(None, description="新名称"),
    seal_type: str = Form(None, description="新类型"),
    description: str = Form(None, description="新描述"),
    default_width_mm: float = Form(None, description="新默认宽度(mm)"),
    default_height_mm: float = Form(None, description="新默认高度(mm)"),
    category: str = Form(None, description="新分类"),
):
    """Update seal metadata. All fields optional — only changed fields need to be sent."""
    seal = get_seal(seal_id)
    if not seal:
        raise HTTPException(404, "印章不存在")

    # Check seal_code uniqueness if changing
    if seal_code and seal_code != seal.seal_code:
        if get_seal_by_code(seal_code):
            raise HTTPException(409, f"印章编码 '{seal_code}' 已被占用")

    # Apply changes
    if seal_code is not None:
        seal.seal_code = seal_code
    if name is not None:
        seal.name = name
    if seal_type is not None:
        seal.seal_type = seal_type
    if description is not None:
        seal.description = description
    if default_width_mm is not None:
        seal.default_width_mm = default_width_mm
    if default_height_mm is not None:
        seal.default_height_mm = default_height_mm
    if category is not None:
        seal.category = category

    from datetime import datetime
    seal.updated_at = datetime.now().isoformat()
    save_seal(seal)

    return {"status": "updated", "seal": seal.model_dump()}


# ── Delete ──────────────────────────────────────────────────────

@router.delete("/{seal_id}", summary="删除印章")
def remove_seal(seal_id: str):
    seal = get_seal(seal_id)
    if not seal:
        raise HTTPException(404, "印章不存在")
    file_path = settings.SEAL_STORAGE / seal.filename
    if file_path.exists():
        file_path.unlink()
    delete_seal(seal_id)
    return {"status": "deleted", "seal_id": seal_id}


# ── Preview Image ───────────────────────────────────────────────

@router.get("/{seal_id}/image", summary="获取印章图片")
def get_seal_image(seal_id: str):
    from fastapi.responses import FileResponse
    seal = get_seal(seal_id)
    if not seal:
        raise HTTPException(404, "印章不存在")
    file_path = settings.SEAL_STORAGE / seal.filename
    if not file_path.exists():
        raise HTTPException(404, "印章文件缺失")
    return FileResponse(file_path, media_type="image/png")
