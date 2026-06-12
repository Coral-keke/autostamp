"""
Stamping API — accepts external system requests and processes asynchronously.

Flow:
  1. POST /api/v1/stamp/submit  →  JSON, validate, return ACCEPTED
  2. Background: download → stamp → callback (HMAC signed)
  3. GET  /api/v1/stamp/status/{no} → query
  4. GET  /api/v1/stamp/download/{no} → download
  5. GET  /api/v1/preview/{no}?page=1 → PNG preview

Also: POST /api/v1/stamp (legacy multipart for Web UI)
"""
import json
import tempfile
import uuid
import hashlib
import hmac
import asyncio
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

try:
    from ..config import settings
    from ..engines.converter import dwg_to_pdf, pdf_to_dwf
    from ..engines.pdf_engine import stamp_pdf
    from ..engines.preview import render_pdf_page_to_png, render_pdf_to_png
    from ..models.seal import get_seal_by_code, get_seal
    from ..models.request import StampRequest, StampResponse, CallbackPayload
    from ..models.database import db_get_job, db_save_job, db_track_file, cleanup_expired_files
except ImportError:
    from config import settings
    from engines.converter import dwg_to_pdf, pdf_to_dwf
    from engines.pdf_engine import stamp_pdf
    from engines.preview import render_pdf_page_to_png, render_pdf_to_png
    from models.seal import get_seal_by_code, get_seal
    from models.request import StampRequest, StampResponse, CallbackPayload
    from models.database import db_get_job, db_save_job, db_track_file, cleanup_expired_files

router = APIRouter(prefix="/api/v1", tags=["stamp"])

_stamp_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)


# ═══════════════════════════════════════════════════════════════
#  ASYNC SUBMIT — External system API
# ═══════════════════════════════════════════════════════════════

@router.post("/stamp/submit", response_model=StampResponse, summary="提交盖章请求（异步）")
async def stamp_submit(req: StampRequest):
    """Accept a stamp request. Returns ACCEPTED immediately, processes in background."""
    seal = get_seal_by_code(req.sealCode)
    if not seal:
        raise HTTPException(404, f"印章编码 '{req.sealCode}' 不存在")

    existing = db_get_job(req.requestNo)
    if existing:
        if existing["status"] in ("SUCCESS", "FAILED"):
            return StampResponse(
                requestNo=req.requestNo, status=existing["status"],
                message=f"请求已处理完成: {existing['status']}",
            )
        return StampResponse(requestNo=req.requestNo, status="PROCESSING", message="请求正在处理中")

    job = {
        "request_no": req.requestNo, "business_id": req.businessId,
        "system_code": req.systemCode, "system_name": req.systemName,
        "file_type": req.fileType.value, "seal_code": req.sealCode,
        "callback_url": req.callbackUrl or "",
        "status": "ACCEPTED", "message": "请求已接收，排队处理中",
        "created_at": datetime.now().isoformat(), "completed_at": "",
        "result_file": "", "result_filename": "", "error": "",
        "callback_failed": False, "request": req.model_dump(),
    }
    db_save_job(job)
    asyncio.create_task(_process_stamp_job(req.requestNo))
    return StampResponse(requestNo=req.requestNo, status="ACCEPTED")


@router.get("/stamp/status/{request_no}", summary="查询盖章状态")
async def stamp_status(request_no: str):
    job = db_get_job(request_no)
    if not job:
        raise HTTPException(404, "请求不存在")
    resp = {
        "requestNo": request_no, "status": job["status"],
        "message": job.get("message", ""),
        "createdAt": job.get("created_at"), "completedAt": job.get("completed_at"),
    }
    if job["status"] == "SUCCESS":
        resp["downloadUrl"] = f"{settings.BASE_URL}/api/v1/stamp/download/{request_no}"
    if job["status"] == "FAILED":
        resp["errorDetail"] = job.get("error", "")
    return resp


@router.get("/stamp/download/{request_no}", summary="下载盖章文件")
async def stamp_download(request_no: str):
    job = db_get_job(request_no)
    if not job: raise HTTPException(404, "请求不存在")
    if job["status"] != "SUCCESS": raise HTTPException(400, f"状态: {job['status']}")
    result_path = Path(job.get("result_file", ""))
    if not result_path.exists(): raise HTTPException(404, "结果文件不存在")
    return FileResponse(str(result_path), filename=job.get("result_filename", "stamped_output"))


# ═══════════════════════════════════════════════════════════════
#  PREVIEW
# ═══════════════════════════════════════════════════════════════

@router.get("/preview/{request_no}", summary="预览盖章结果")
async def preview_result(request_no: str, page: int = 1):
    job = db_get_job(request_no)
    if not job: raise HTTPException(404, "请求不存在")
    if job["status"] != "SUCCESS": raise HTTPException(400, f"状态: {job['status']}")
    result_path = Path(job.get("result_file", ""))
    if not result_path.exists(): raise HTTPException(404, "结果文件不存在")
    try:
        png_bytes = render_pdf_page_to_png(result_path, page_num=page)
        return Response(content=png_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/preview", summary="上传文件预览")
async def preview_upload(file: UploadFile = File(...), page: int = 1):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext != "pdf": raise HTTPException(400, "预览仅支持 PDF")
    contents = await file.read()
    try:
        png_bytes = render_pdf_to_png(contents, page_num=page)
        return Response(content=png_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(400, str(e))


# ═══════════════════════════════════════════════════════════════
#  BACKGROUND PROCESSING
# ═══════════════════════════════════════════════════════════════

async def _process_stamp_job(request_no: str):
    async with _stamp_semaphore:
        await _process_stamp_job_impl(request_no)


async def _process_stamp_job_impl(request_no: str):
    job = db_get_job(request_no)
    if not job: return

    req_data = job["request"]
    job["status"] = "PROCESSING"
    db_save_job(job)

    try:
        file_bytes, _ = await _download_file(req_data["fileUrl"])
        ext = req_data["fileType"]
        seal = get_seal_by_code(req_data["sealCode"])
        seal_path = settings.SEAL_STORAGE / seal.filename

        pos = req_data["position"]
        positions = [{
            "page": req_data["pageNo"], "x": pos["x"], "y": pos["y"],
            "width": pos["width"], "height": pos["height"], "rotation": 0,
        }]

        output_id = uuid.uuid4().hex[:12]

        if ext == "pdf":
            output_path = settings.OUTPUT_DIR / f"{output_id}_stamped.pdf"
            output_ext = "pdf"
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                input_path = Path(tmp.name)
            try:
                stamp_pdf_direct(input_path, output_path, seal_path, positions, "pt")
            finally:
                input_path.unlink(missing_ok=True)

        elif ext == "dwg":
            output_path = settings.OUTPUT_DIR / f"{output_id}_stamped.dwf"
            output_ext = "dwf"
            with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as tmp:
                tmp.write(file_bytes)
                dwg_path = Path(tmp.name)
            pi = settings.OUTPUT_DIR / f"{output_id}_intermediate.pdf"
            sp = settings.OUTPUT_DIR / f"{output_id}_stamped_intermediate.pdf"
            try:
                dwg_to_pdf(dwg_path, pi)
                stamp_pdf_direct(pi, sp, seal_path, positions, "pt")
                pdf_to_dwf(sp, output_path)
            finally:
                dwg_path.unlink(missing_ok=True)
                pi.unlink(missing_ok=True)
                sp.unlink(missing_ok=True)
        else:
            raise ValueError(f"不支持: {ext}")

        result_filename = f"stamped_{req_data.get('contractName', 'output')}"
        if output_ext not in result_filename:
            result_filename = f"{result_filename}.{output_ext}"

        job["status"] = "SUCCESS"
        job["message"] = "盖章完成"
        job["result_file"] = str(output_path)
        job["result_filename"] = result_filename
        job["completed_at"] = datetime.now().isoformat()
        db_save_job(job)
        db_track_file(str(output_path), ttl_hours=168, job_request_no=request_no)
        await _send_callback(request_no, success=True)

    except Exception as e:
        job["status"] = "FAILED"
        job["message"] = f"处理失败: {str(e)}"
        job["error"] = str(e)
        job["completed_at"] = datetime.now().isoformat()
        db_save_job(job)
        await _send_callback(request_no, success=False, error=str(e))


async def _download_file(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=settings.DOWNLOAD_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content
        if len(content) > settings.DOWNLOAD_MAX_SIZE_MB * 1024 * 1024:
            raise ValueError(f"文件超过 {settings.DOWNLOAD_MAX_SIZE_MB}MB")
        filename = url.rsplit("/", 1)[-1].split("?")[0] or "downloaded_file"
        return content, filename


async def _send_callback(request_no: str, success: bool, error: str = ""):
    job = db_get_job(request_no)
    if not job: return
    req_data = job["request"]
    callback_url = req_data.get("callbackUrl")
    if not callback_url: return

    status = "SUCCESS" if success else "FAILED"
    download_url = f"{settings.BASE_URL}/api/v1/stamp/download/{request_no}" if success else None

    payload = CallbackPayload(
        requestNo=request_no, businessId=req_data.get("businessId", ""),
        status=status, message=job.get("message", ""),
        fileUrl=download_url, fileType=req_data.get("fileType"),
        stampedFileName=job.get("result_filename"),
        errorDetail=error if error else None,
    )

    for attempt in range(1, settings.CALLBACK_RETRY_COUNT + 1):
        try:
            headers = {"Content-Type": "application/json"}
            body_json = json.dumps(payload.model_dump())
            if settings.HMAC_SECRET:
                signature = hmac.new(
                    settings.HMAC_SECRET.encode(), body_json.encode(), hashlib.sha256,
                ).hexdigest()
                headers["X-Stamp-Signature"] = f"sha256={signature}"
                headers["X-Stamp-RequestNo"] = request_no
            async with httpx.AsyncClient(timeout=settings.CALLBACK_TIMEOUT) as client:
                resp = await client.post(callback_url, content=body_json, headers=headers)
                if resp.status_code < 500:
                    return
        except Exception:
            pass
        if attempt < settings.CALLBACK_RETRY_COUNT:
            await asyncio.sleep(settings.CALLBACK_RETRY_DELAY)

    job["callback_failed"] = True
    db_save_job(job)


# ═══════════════════════════════════════════════════════════════
#  SYNC: Multi-format stamping (Web UI + direct API)
# ═══════════════════════════════════════════════════════════════

try:
    from ..engines.gateway import stamp_file as gateway_stamp, SUPPORTED_EXTENSIONS
except ImportError:
    from engines.gateway import stamp_file as gateway_stamp, SUPPORTED_EXTENSIONS

# MIME types for response
MIME_MAP = {
    "pdf": "application/pdf",
    "dwf": "application/octet-stream",
    "dwg": "application/acad",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/stamp", summary="盖章（同步/多格式）")
async def stamp_file(
    file: UploadFile = File(...), seal_id: str = Form(...),
    positions_json: str = Form(...), output_format: str = Form("pdf"),
):
    """Multi-format stamping: PDF, DWG, PNG, JPG, DOCX, XLSX."""
    seal = get_seal(seal_id)
    if not seal: raise HTTPException(404, "印章不存在")
    seal_path = settings.SEAL_STORAGE / seal.filename
    if not seal_path.exists(): raise HTTPException(500, "印章文件缺失")

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in settings.ALLOWED_INPUT_FORMATS:
        raise HTTPException(400, f"不支持: .{ext} (支持: {', '.join(settings.ALLOWED_INPUT_FORMATS)})")

    try: positions = json.loads(positions_json)
    except json.JSONDecodeError: raise HTTPException(400, "坐标 JSON 解析失败")
    if not positions: raise HTTPException(400, "至少需要一个坐标")

    for pos in positions:
        pos.setdefault("width_mm", seal.default_width_mm)
        pos.setdefault("height_mm", seal.default_height_mm)

    contents = await file.read()
    output_id = uuid.uuid4().hex[:12]
    out_ext = output_format if output_format in settings.ALLOWED_OUTPUT_FORMATS else ext
    output_path = settings.OUTPUT_DIR / f"{output_id}_stamped.{out_ext}"

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(contents); input_path = Path(tmp.name)

    try:
        gateway_stamp(
            input_path=input_path, output_path=output_path,
            seal_path=seal_path, positions=positions,
            input_unit="mm",
        )
    finally:
        input_path.unlink(missing_ok=True)

    media_type = MIME_MAP.get(out_ext, "application/octet-stream")
    return FileResponse(output_path, media_type=media_type,
                        filename=f"stamped_{file.filename or 'output'}.{out_ext}")


# ═══════════════════════════════════════════════════════════════
#  KEYWORD AUTO-POSITIONING
# ═══════════════════════════════════════════════════════════════

try:
    from ..engines.auto_position import suggest_stamp_position, generate_cross_page_positions
except ImportError:
    from engines.auto_position import suggest_stamp_position, generate_cross_page_positions


@router.post("/stamp/keyword-positions", summary="关键字定位")
def keyword_positions(
    file: UploadFile = File(...),
    keyword: str = Form(...),
    file_type: str = Form("pdf"),
    offset_x_mm: float = Form(60),
    offset_y_mm: float = Form(15),
):
    """Search a file for a keyword (e.g. '乙方盖章') and return suggested stamp coordinates."""
    with tempfile.NamedTemporaryFile(suffix=f".{file_type}", delete=False) as tmp:
        tmp.write(file.file.read()); file_path = Path(tmp.name)

    try:
        positions = suggest_stamp_position(file_path, keyword, file_type, offset_x_mm, offset_y_mm)
    finally:
        file_path.unlink(missing_ok=True)

    return {"keyword": keyword, "file_type": file_type, "count": len(positions), "positions": positions}


@router.post("/stamp/cross-page-positions", summary="骑缝章定位")
def cross_page_positions(
    file: UploadFile = File(...),
    seal_id: str = Form(...),
    edge: str = Form("right"),
    margin_mm: float = Form(5),
):
    """Generate cross-page (骑缝) stamp positions for a PDF."""
    seal = get_seal(seal_id)
    if not seal: raise HTTPException(404, "印章不存在")
    seal_path = settings.SEAL_STORAGE / seal.filename

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file.file.read()); file_path = Path(tmp.name)

    try:
        positions = generate_cross_page_positions(file_path, seal_path, edge, margin_mm)
    finally:
        file_path.unlink(missing_ok=True)

    return {"edge": edge, "page_count": len(positions), "positions": positions}


# ═══════════════════════════════════════════════════════════════
#  HEALTH & ADMIN
# ═══════════════════════════════════════════════════════════════

@router.get("/health", summary="健康检查")
def health():
    import sqlite3
    try:
        conn = sqlite3.connect(str(settings.BACKEND_DIR / "data" / "autostamp.db"))
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
        success = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='SUCCESS'").fetchone()["c"]
        failed = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='FAILED'").fetchone()["c"]
        processing = total - success - failed
        conn.close()
    except Exception:
        total = success = failed = processing = 0
    return {"status": "ok", "service": "auto-stamp",
            "jobs": {"total": total, "processing": processing, "success": success, "failed": failed}}


@router.post("/admin/cleanup", summary="手动清理过期文件")
def manual_cleanup():
    cleaned = cleanup_expired_files()
    return {"status": "ok", "cleaned_files": cleaned}


# ── Helper ────────────────────────────────────────────────────

def stamp_pdf_direct(input_path, output_path, seal_path, positions, input_unit="mm"):
    if input_unit == "pt":
        for pos in positions:
            pos.setdefault("width", 40 * settings.MM_TO_PT)
            pos.setdefault("height", 40 * settings.MM_TO_PT)
    else:
        for pos in positions:
            pos.setdefault("width_mm", 40)
            pos.setdefault("height_mm", 40)

    stamp_pdf(
        input_path=input_path, output_path=output_path, seal_path=seal_path,
        seal_width_mm=40, seal_height_mm=40,
        positions=positions, input_unit=input_unit,
    )
