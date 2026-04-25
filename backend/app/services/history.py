"""
History Service — Script Version Management

Provides version history, comparison, and restoration for project content blocks.
Rules:
  - NEVER overwrite an existing version (append-only).
  - Restore creates a NEW version from old content.
  - Diff uses difflib for structured comparison.
"""

import difflib
import logging
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from app.models.content_block import ContentBlock, BlockType
from app.models.content_version import ContentVersion
from app.services.project import ProjectService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class HistoryService:
    """Manages version history for project content blocks."""

    def __init__(self):
        self.project_service = ProjectService()

    # ── List ─────────────────────────────────────────────────────

    async def get_project_history(
        self, project_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all content versions for a project, grouped by block type.

        Returns:
            List of block groups, each containing:
              - block_id, block_type, versions: [...]
        """
        # Access check
        project = await self.project_service.get_project(project_id, user_id)
        if not project:
            return []

        blocks = await ContentBlock.find(
            ContentBlock.project_id == project_id
        ).to_list()

        result = []
        for block in blocks:
            versions = await ContentVersion.find(
                ContentVersion.block_id == str(block.id)
            ).sort(-ContentVersion.version_number).to_list()

            result.append({
                "block_id": str(block.id),
                "block_type": block.type.value,
                "current_version_id": block.current_version_id,
                "versions": [
                    {
                        "id": str(v.id),
                        "version_number": v.version_number,
                        "is_active": v.is_active,
                        "created_by": v.created_by,
                        "created_at": v.created_at.isoformat(),
                        "parent_version_id": v.parent_version_id,
                    }
                    for v in versions
                ],
            })

        return result

    # ── Get Single Version ───────────────────────────────────────

    async def get_version(
        self, project_id: str, version_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific version's full content."""
        project = await self.project_service.get_project(project_id, user_id)
        if not project:
            return None

        try:
            version = await ContentVersion.get(PydanticObjectId(version_id))
        except Exception:
            return None

        if not version:
            return None

        # Verify the version belongs to this project
        block = await ContentBlock.find_one(
            ContentBlock.id == PydanticObjectId(version.block_id),
            ContentBlock.project_id == project_id,
        )
        if not block:
            return None

        return {
            "id": str(version.id),
            "block_id": version.block_id,
            "block_type": block.type.value,
            "version_number": version.version_number,
            "content": version.content,
            "is_active": version.is_active,
            "created_by": version.created_by,
            "created_at": version.created_at.isoformat(),
            "parent_version_id": version.parent_version_id,
        }

    # ── Compare ──────────────────────────────────────────────────

    async def compare_versions(
        self, project_id: str, v1_id: str, v2_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Compare two versions and return a structured diff."""
        v1_data = await self.get_version(project_id, v1_id, user_id)
        v2_data = await self.get_version(project_id, v2_id, user_id)

        if not v1_data or not v2_data:
            return None

        # Extract script text for diffing
        v1_text = self._extract_text(v1_data["content"])
        v2_text = self._extract_text(v2_data["content"])

        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            v1_text.splitlines(keepends=True),
            v2_text.splitlines(keepends=True),
            fromfile=f"V{v1_data['version_number']}",
            tofile=f"V{v2_data['version_number']}",
            lineterm="",
        ))

        # Generate HTML-friendly diff for frontend
        differ = difflib.HtmlDiff(tabsize=2)
        html_diff = differ.make_table(
            v1_text.splitlines(),
            v2_text.splitlines(),
            fromdesc=f"V{v1_data['version_number']}",
            todesc=f"V{v2_data['version_number']}",
            context=True,
            numlines=3,
        )

        return {
            "v1": {
                "id": v1_data["id"],
                "version_number": v1_data["version_number"],
                "created_at": v1_data["created_at"],
            },
            "v2": {
                "id": v2_data["id"],
                "version_number": v2_data["version_number"],
                "created_at": v2_data["created_at"],
            },
            "diff_lines": diff_lines,
            "html_diff": html_diff,
            "stats": {
                "additions": sum(1 for l in diff_lines if l.startswith("+")),
                "deletions": sum(1 for l in diff_lines if l.startswith("-")),
            },
        }

    # ── Restore ──────────────────────────────────────────────────

    async def restore_version(
        self, project_id: str, version_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Restore an old version by creating a new version with its content.

        This follows the append-only rule: we NEVER overwrite. We create a new
        version that copies the old content, then mark it as active.
        """
        project = await self.project_service.get_project(project_id, user_id)
        if not project:
            return None

        try:
            old_version = await ContentVersion.get(PydanticObjectId(version_id))
        except Exception:
            return None

        if not old_version:
            return None

        # Verify it belongs to this project
        block = await ContentBlock.find_one(
            ContentBlock.id == PydanticObjectId(old_version.block_id),
            ContentBlock.project_id == project_id,
        )
        if not block:
            return None

        # Deactivate all current active versions for this block
        await ContentVersion.find(
            ContentVersion.block_id == old_version.block_id,
            ContentVersion.is_active == True,
        ).update({"$set": {"is_active": False}})

        # Get next version number
        latest = await ContentVersion.find(
            ContentVersion.block_id == old_version.block_id
        ).sort(-ContentVersion.version_number).first_or_none()

        next_num = (latest.version_number + 1) if latest else 1

        # Create new version with old content (append-only)
        new_version = ContentVersion(
            block_id=old_version.block_id,
            version_number=next_num,
            content=old_version.content,
            created_by=user_id,
            is_active=True,
            parent_version_id=str(old_version.id),
        )
        await new_version.insert()

        # Update block pointer
        block.current_version_id = str(new_version.id)
        block.updated_at = utc_now()
        await block.save()

        logger.info(
            "history: restored V%d → V%d for block %s",
            old_version.version_number,
            next_num,
            old_version.block_id,
        )

        return {
            "id": str(new_version.id),
            "block_id": new_version.block_id,
            "version_number": new_version.version_number,
            "content": new_version.content,
            "is_active": True,
            "created_by": user_id,
            "created_at": new_version.created_at.isoformat(),
            "parent_version_id": str(old_version.id),
            "restored_from": old_version.version_number,
        }

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_text(content: dict) -> str:
        """Extract readable text from a version content dict for diffing."""
        if not content:
            return ""

        # Try common content shapes
        if isinstance(content.get("script"), dict):
            return content["script"].get("full_script", str(content["script"]))
        if isinstance(content.get("script"), str):
            return content["script"]

        # Fallback: serialize the whole dict
        import json
        return json.dumps(content, indent=2, default=str)
