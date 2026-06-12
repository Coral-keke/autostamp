"""
Seal data model — backed by SQLite.

Provides the same interface as before, but persists across restarts.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .database import (
    db_save_seal, db_get_seal, db_get_seal_by_code,
    db_list_seals, db_delete_seal,
)


class Seal(BaseModel):
    """Seal creation/update request."""
    name: str = Field(..., min_length=1, max_length=100, description="印章名称")
    seal_code: str = Field(..., min_length=1, max_length=50, description="业务编码")
    seal_type: str = Field("OFFICIAL", description="类型: OFFICIAL/CONTRACT/FINANCE/SIGNATURE")
    description: str = Field("", max_length=500)
    default_width_mm: float = Field(40.0, gt=0)
    default_height_mm: float = Field(40.0, gt=0)
    category: str = Field("general")


class SealInDB(Seal):
    """Seal as stored, with system fields."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    filename: str = ""
    file_size_bytes: int = 0
    original_filename: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_db_row(cls, row: dict) -> "SealInDB":
        return cls(**row)

    def to_db_dict(self) -> dict:
        return self.model_dump()


# ── Public API (delegates to database) ────────────────────

def get_seal(seal_id: str) -> Optional[SealInDB]:
    row = db_get_seal(seal_id)
    return SealInDB.from_db_row(row) if row else None


def get_seal_by_code(seal_code: str) -> Optional[SealInDB]:
    row = db_get_seal_by_code(seal_code)
    return SealInDB.from_db_row(row) if row else None


def list_seals(category: str = None, seal_type: str = None) -> list[SealInDB]:
    rows = db_list_seals(category=category, seal_type=seal_type)
    return [SealInDB.from_db_row(r) for r in rows]


def save_seal(seal: SealInDB) -> None:
    db_save_seal(seal.to_db_dict())


def delete_seal(seal_id: str) -> bool:
    if db_get_seal(seal_id):
        db_delete_seal(seal_id)
        return True
    return False
