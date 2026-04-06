"""
ProjectMemoryStore — Per-project context and artifact management.

Stores project configuration, pipeline artifacts (ideas, hooks, scripts),
and edit history in MongoDB via the existing Project model.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.project import Project
from app.models.memory_entry import MemoryEntry

logger = logging.getLogger(__name__)


class ProjectMemoryStore:
    """Manages per-project context in MongoDB."""

    async def load(self, project_id: str) -> Dict:
        """Load project context needed for pipeline execution."""
        project = await Project.get(project_id)
        if project is None:
            return {
                "topic": "",
                "niche": "general",
                "platforms": ["YouTube"],
                "video_length": "Medium (1-10 min)",
                "target_audience": "general audience",
                "language": "English",
                "style_overrides": {},
            }

        return {
            "topic": project.topic or (project.selected_idea.get("title", "") if project.selected_idea else ""),
            "niche": getattr(project, "niche", "general"),
            "platforms": getattr(project, "platforms", ["YouTube"]),
            "video_length": getattr(project, "video_length", "Medium (1-10 min)"),
            "target_audience": getattr(project, "target_audience", "general audience"),
            "language": getattr(project, "language", "English"),
            "style_overrides": {},
        }

    async def save_artifact(
        self,
        project_id: str,
        artifact_type: str,
        content: Any,
    ) -> None:
        """Save a pipeline artifact to project memory for future retrieval."""
        import json
        if isinstance(content, (dict, list)):
            serialized = json.dumps(content, default=str)[:10000]
        else:
            serialized = str(content)[:10000]
        entry = MemoryEntry(
            user_id="pipeline",
            project_id=project_id,
            entry_type=f"artifact_{artifact_type}",
            content=serialized,
        )
        await entry.insert()
        logger.info(
            "ProjectMemoryStore: saved %s artifact for project %s",
            artifact_type, project_id
        )

    async def get_edit_history(self, project_id: str) -> List[Dict]:
        """Get all edit records for a project."""
        entries = await MemoryEntry.find(
            MemoryEntry.project_id == project_id,
            MemoryEntry.entry_type == "user_edit",
        ).sort("-created_at").to_list()

        return [
            {
                "stage": e.metadata.get("stage", "") if hasattr(e, "metadata") else "",
                "content": e.content,
                "created_at": e.created_at.isoformat() if hasattr(e, "created_at") and e.created_at else "",
            }
            for e in entries
        ]

    async def append_edit(self, project_id: str, edit: Dict) -> None:
        """Append a user edit record to project memory."""
        import json
        entry = MemoryEntry(
            user_id="pipeline",
            project_id=project_id,
            entry_type="user_edit",
            content=json.dumps(edit, default=str)[:10000],
        )
        await entry.insert()
