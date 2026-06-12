"""
SQLite persistent storage — replaces in-memory dicts.

Tables:
  - seals:     Seal metadata (id, seal_code, name, type, filename, etc.)
  - jobs:      Async stamp jobs (requestNo, status, result, timestamps)
  - cleanup:   File lifecycle tracking for auto-cleanup
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from ..config import settings
except ImportError:
    from config import settings


DB_PATH = settings.BACKEND_DIR / "data" / "autostamp.db"


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local connection."""
    thread_id = threading.get_ident()
    if not hasattr(_get_conn, "_conns"):
        _get_conn._conns = {}
    if thread_id not in _get_conn._conns:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _get_conn._conns[thread_id] = conn
    return _get_conn._conns[thread_id]


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seals (
            id TEXT PRIMARY KEY,
            seal_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            seal_type TEXT DEFAULT 'OFFICIAL',
            description TEXT DEFAULT '',
            default_width_mm REAL DEFAULT 40.0,
            default_height_mm REAL DEFAULT 40.0,
            category TEXT DEFAULT 'general',
            filename TEXT NOT NULL,
            file_size_bytes INTEGER DEFAULT 0,
            original_filename TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            request_no TEXT PRIMARY KEY,
            business_id TEXT DEFAULT '',
            system_code TEXT DEFAULT '',
            system_name TEXT DEFAULT '',
            file_type TEXT DEFAULT 'pdf',
            seal_code TEXT DEFAULT '',
            callback_url TEXT DEFAULT '',
            status TEXT DEFAULT 'ACCEPTED',
            message TEXT DEFAULT '',
            error TEXT DEFAULT '',
            request_json TEXT DEFAULT '{}',
            result_file TEXT DEFAULT '',
            result_filename TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            completed_at TEXT DEFAULT '',
            callback_failed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS file_tracker (
            file_path TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            ttl_hours INTEGER DEFAULT 24,
            job_request_no TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_seals_code ON seals(seal_code);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_file_created ON file_tracker(created_at);
    """)
    conn.commit()


# ── Seal CRUD ──────────────────────────────────────────────

def db_save_seal(seal_dict: dict):
    conn = _get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO seals
        (id, seal_code, name, seal_type, description,
         default_width_mm, default_height_mm, category,
         filename, file_size_bytes, original_filename,
         created_at, updated_at)
        VALUES (?,?,?,?,?, ?,?,?, ?,?,?, ?,?)
    """, (
        seal_dict["id"], seal_dict["seal_code"], seal_dict["name"],
        seal_dict["seal_type"], seal_dict["description"],
        seal_dict["default_width_mm"], seal_dict["default_height_mm"],
        seal_dict["category"], seal_dict["filename"],
        seal_dict["file_size_bytes"], seal_dict["original_filename"],
        seal_dict["created_at"], seal_dict["updated_at"],
    ))
    conn.commit()


def db_get_seal(seal_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM seals WHERE id = ?", (seal_id,)).fetchone()
    return dict(row) if row else None


def db_get_seal_by_code(code: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM seals WHERE seal_code = ?", (code,)).fetchone()
    return dict(row) if row else None


def db_list_seals(category: str = None, seal_type: str = None) -> list[dict]:
    conn = _get_conn()
    query = "SELECT * FROM seals WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if seal_type:
        query += " AND seal_type = ?"
        params.append(seal_type)
    query += " ORDER BY created_at DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def db_delete_seal(seal_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM seals WHERE id = ?", (seal_id,))
    conn.commit()


# ── Job CRUD ───────────────────────────────────────────────

def db_save_job(job_dict: dict):
    conn = _get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO jobs
        (request_no, business_id, system_code, system_name,
         file_type, seal_code, callback_url,
         status, message, error, request_json,
         result_file, result_filename,
         created_at, completed_at, callback_failed)
        VALUES (?,?,?,?, ?,?,?, ?,?,?, ?, ?,?, ?,?,?)
    """, (
        job_dict["request_no"], job_dict.get("business_id", ""),
        job_dict.get("system_code", ""), job_dict.get("system_name", ""),
        job_dict.get("file_type", ""), job_dict.get("seal_code", ""),
        job_dict.get("callback_url", ""),
        job_dict["status"], job_dict.get("message", ""),
        job_dict.get("error", ""), json.dumps(job_dict.get("request", {})),
        job_dict.get("result_file", ""), job_dict.get("result_filename", ""),
        job_dict["created_at"], job_dict.get("completed_at", ""),
        int(job_dict.get("callback_failed", False)),
    ))
    conn.commit()


def db_get_job(request_no: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE request_no = ?", (request_no,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["request"] = json.loads(d.pop("request_json", "{}"))
    d["callback_failed"] = bool(d.get("callback_failed", False))
    return d


# ── File Tracker ───────────────────────────────────────────

def db_track_file(file_path: str, ttl_hours: int = 24, job_request_no: str = ""):
    conn = _get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO file_tracker (file_path, created_at, ttl_hours, job_request_no)
        VALUES (?, ?, ?, ?)
    """, (str(file_path), datetime.now().isoformat(), ttl_hours, job_request_no))
    conn.commit()


def db_get_expired_files() -> list[str]:
    """Return files past their TTL for cleanup."""
    conn = _get_conn()
    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    rows = conn.execute("""
        SELECT file_path FROM file_tracker
        WHERE created_at < ?
    """, (cutoff,)).fetchall()
    return [r["file_path"] for r in rows]


def db_delete_file_tracker(file_path: str):
    conn = _get_conn()
    conn.execute("DELETE FROM file_tracker WHERE file_path = ?", (str(file_path),))
    conn.commit()


# ── Cleanup ────────────────────────────────────────────────

def cleanup_expired_files():
    """Remove expired files from disk and DB. Call periodically."""
    expired = db_get_expired_files()
    cleaned = 0
    for fp in expired:
        p = Path(fp)
        if p.exists():
            try:
                p.unlink()
                cleaned += 1
            except OSError:
                pass
        db_delete_file_tracker(fp)
    return cleaned


# Initialize on import
init_db()
