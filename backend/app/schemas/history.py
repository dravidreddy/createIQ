"""
History Schemas — Pydantic response models for version history API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VersionSummary(BaseModel):
    """Compact version info for listing."""
    id: str
    version_number: int
    is_active: bool
    created_by: str
    created_at: str
    parent_version_id: Optional[str] = None


class BlockHistory(BaseModel):
    """All versions for a single content block."""
    block_id: str
    block_type: str
    current_version_id: Optional[str] = None
    versions: List[VersionSummary] = []


class VersionDetail(BaseModel):
    """Full version content."""
    id: str
    block_id: str
    block_type: str
    version_number: int
    content: Dict[str, Any] = {}
    is_active: bool
    created_by: str
    created_at: str
    parent_version_id: Optional[str] = None
    restored_from: Optional[int] = None  # Present when this was a restore


class DiffStats(BaseModel):
    additions: int = 0
    deletions: int = 0


class VersionRef(BaseModel):
    id: str
    version_number: int
    created_at: str


class VersionDiff(BaseModel):
    """Diff between two versions."""
    v1: VersionRef
    v2: VersionRef
    diff_lines: List[str] = []
    html_diff: str = ""
    stats: DiffStats = Field(default_factory=DiffStats)
