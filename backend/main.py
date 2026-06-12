"""
Auto-Stamp System — FastAPI Application Entry Point

Run:
  cd /home/udg/automaticstamping && python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
  OR
  cd /home/udg/automaticstamping/backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
"""
import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

try:
    from .api import seals_router, stamp_router, auth_router
except ImportError:
    from api import seals_router, stamp_router, auth_router
try:
    from .config import settings
    from .models.database import cleanup_expired_files
except ImportError:
    from config import settings
    from models.database import cleanup_expired_files

app = FastAPI(
    title="Auto-Stamp System",
    description="自动盖章系统",
    version="0.3.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_PREFIXES = (
    "/docs", "/redoc", "/openapi.json",
    "/api/v1/health", "/api/v1/auth/", "/favicon.ico",
    "/assets/",  # Frontend static assets (no auth)
)


def _is_public(path: str) -> bool:
    """Check if path is public (no auth required)."""
    if path == "/":
        return True
    if path.startswith(PUBLIC_PREFIXES):
        return True
    if "/image" in path or "/download/" in path:
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths
        if _is_public(path):
            return await call_next(request)

        # External API: X-API-Key
        api_key = request.headers.get(settings.API_KEY_HEADER)
        if api_key:
            if not settings.API_KEY or api_key != settings.API_KEY:
                return JSONResponse({"detail": "Invalid API Key"}, 401)
            return await call_next(request)

        # Web UI: Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from .api.auth import verify_token
            except ImportError:
                from api.auth import verify_token
            if not verify_token(token):
                return JSONResponse({"detail": "登录已过期，请重新登录"}, 401)
            return await call_next(request)

        # No credentials
        if settings.API_KEY or settings.WEB_PASSWORD:
            return JSONResponse({"detail": "请先登录或提供 API Key"}, 401)

        return await call_next(request)


app.add_middleware(AuthMiddleware)

app.include_router(auth_router)
app.include_router(seals_router)
app.include_router(stamp_router)

# ── Production: serve frontend static files ─────────
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    # Mount assets with no auth (handled via PUBLIC_PREFIXES)
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        """Serve frontend SPA, falling back to index.html for client-side routing."""
        # Skip API paths — they're handled by routers above
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, 404)
        
        file_path = os.path.join(FRONTEND_DIST, full_path) if full_path else os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(file_path) and not full_path.startswith("api"):
            return FileResponse(file_path)
        # SPA fallback
        index = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"detail": "Not Found"}, 404)
    
    print(f"Frontend static files: {FRONTEND_DIST}")


async def periodic_cleanup(interval: int = 3600):
    while True:
        await asyncio.sleep(interval)
        try:
            cleaned = cleanup_expired_files()
            if cleaned:
                print(f"Cleaned up {cleaned} expired files")
        except Exception as e:
            print(f"Cleanup error: {e}")


@app.on_event("startup")
async def startup():
    print("Auto-Stamp System v0.3.1 starting...")
    print(f"  Auth: API_KEY={'set' if settings.API_KEY else 'none'}, WEB_PASSWORD={'set' if settings.WEB_PASSWORD else 'none'}")
    asyncio.create_task(periodic_cleanup())
