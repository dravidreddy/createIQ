"""
Version Service (V4)

Manages pipeline outputs and temporary/saved versions of a project.
"""
from app.utils.datetime_utils import utc_now
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId
from app.models.project_version import ProjectVersion
from app.services.project import ProjectService
import logging
import asyncio
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

class VersionService:
    def __init__(self):
        self.project_service = ProjectService()
        
    async def create_version(self, project_id: str, user_id: str, is_saved: bool = False, pipeline_data: Dict[str, Any] = None) -> Optional[ProjectVersion]:
        # Validate access
        project = await self.project_service.get_project(project_id, user_id)
        if not project:
            return None
            
        # Get next version number
        latest = await ProjectVersion.find(ProjectVersion.project_id == project_id).sort(-ProjectVersion.version_number).first_or_none()
        v_num = (latest.version_number + 1) if latest else 1
        
        pipeline_data = pipeline_data or {}
        
        expires_at = None
        if not is_saved:
            expires_at = utc_now() + timedelta(hours=48)
            
        for attempt in range(3):
            try:
                version = ProjectVersion(
                    project_id=project_id,
                    version_number=v_num,
                    is_saved=is_saved,
                    ideas=pipeline_data.get("ideas"),
                    selected_idea=pipeline_data.get("selected_idea"),
                    hook=pipeline_data.get("hook"),
                    script=pipeline_data.get("script"),
                    screenplay_guidance=pipeline_data.get("screenplay_guidance"),
                    expires_at=expires_at
                )
                await version.insert()
                return version
            except DuplicateKeyError:
                if attempt == 2:
                    logger.error("Failed to sequence ProjectVersion after 3 attempts due to massive concurrency.")
                    raise
                await asyncio.sleep(0.1)
                latest = await ProjectVersion.find(ProjectVersion.project_id == project_id).sort(-ProjectVersion.version_number).first_or_none()
                v_num = (latest.version_number + 1) if latest else 1

    async def get_versions(self, project_id: str, user_id: str) -> List[ProjectVersion]:
        project = await self.project_service.get_project(project_id, user_id)
        if not project: return []
        
        return await ProjectVersion.find(ProjectVersion.project_id == project_id).sort(-ProjectVersion.created_at).to_list()

    async def save_version(self, version_id: str, user_id: str) -> Optional[ProjectVersion]:
        """Convert a temporary version to a saved persistent version."""
        try:
            version = await ProjectVersion.get(PydanticObjectId(version_id))
        except Exception:
            return None
            
        if not version: return None
        
        # Access check
        project = await self.project_service.get_project(version.project_id, user_id)
        if not project: return None
        
        version.is_saved = True
        version.expires_at = None # Remove TTL
        version.updated_at = utc_now()
        await version.save()
        return version
