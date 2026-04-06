"""
Project Service (V4)

Handles hierarchical content projects and collaborator management.
"""

from datetime import datetime
from typing import Optional, List, Tuple
from app.models.project import Project, ProjectStatus, Collaborator, CollaboratorRole
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.repositories.project_repo import ProjectRepository
from app.utils.determinism import get_now
import logging

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self):
        self.repo = ProjectRepository()
    async def create_project(self, user_id: str, project_data: ProjectCreate) -> Project:
        project = Project(
            user_id=user_id,
            title=project_data.title,
            topic=project_data.topic,
            niche=project_data.niche,
            parent_project_id=project_data.parent_project_id,
            strategy_plan_id=project_data.strategy_plan_id,
            platform=project_data.platform,
            goal=project_data.goal,
            status=ProjectStatus.DRAFT,
            collaborators=[Collaborator(user_id=user_id, role=CollaboratorRole.OWNER)]
        )
        return await self.repo.create(project)

    async def get_project(self, project_id: str, user_id: str = None) -> Optional[Project]:
        project = await self.repo.get_by_id(project_id)
        if not project:
            return None

        if user_id:
            # Check if owner or collaborator
            is_collab = any(c.user_id == user_id for c in project.collaborators)
            if project.user_id != user_id and not is_collab:
                return None
        return project

    async def get_projects(self, user_id: str, page: int = 1, per_page: int = 10, status: ProjectStatus = None) -> Tuple[List[Project], int]:
        return await self.repo.list_by_user(user_id, page, per_page, status)

    async def update_project(self, project_id: str, user_id: str, project_data: ProjectUpdate) -> Optional[Project]:
        project = await self.get_project(project_id, user_id)
        if not project:
            return None
            
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        project.updated_at = get_now()
        return await self.repo.update(project)

    async def update_project_status(self, project_id: str, status: ProjectStatus, current_agent: str = None, error_message: str = None) -> Optional[Project]:
        project = await self.get_project(project_id) # Internal system update
        if not project:
            return None

        project.status = status
        project.current_agent = current_agent
        project.updated_at = get_now()

        if error_message:
            project.error_message = error_message

        if status == ProjectStatus.COMPLETED:
            project.completed_at = get_now()

        return await self.repo.update(project)

    async def add_collaborator(self, project_id: str, owner_id: str, target_user_id: str, role: CollaboratorRole) -> Optional[Project]:
        project = await self.get_project(project_id, owner_id)
        if not project: return None
        
        # Only owner can add collab
        if project.user_id != owner_id: return None
        
        # Check if already exists
        if any(c.user_id == target_user_id for c in project.collaborators):
            return project
            
        project.collaborators.append(Collaborator(user_id=target_user_id, role=role))
        project.updated_at = get_now()
        return await self.repo.update(project)

    async def save_agent_output(self, project_id: str, agent_name: str, output_data) -> None:
        """Persist an agent's output as a content block + version.

        Called by the worker after pipeline execution.  Maps legacy agent
        names to BlockType values and creates an append-only version.
        """
        from app.models.content_block import ContentBlock, BlockType
        from app.models.content_version import ContentVersion

        type_map = {
            "idea_discovery": BlockType.IDEA,
            "research_script": BlockType.SCRIPT,
            "screenplay_structure": BlockType.OUTLINE,
            "editing_improvement": BlockType.SCRIPT,
            "hook_creation": BlockType.HOOK,
        }
        block_type = type_map.get(agent_name, BlockType.SCRIPT)

        # Find or create the block
        block = await ContentBlock.find_one(
            ContentBlock.project_id == project_id,
            ContentBlock.type == block_type,
        )
        if not block:
            block = ContentBlock(
                project_id=project_id,
                type=block_type,
                created_by="system",
            )
            await block.insert()

        # Handle deactivation and version increment with collision avoidance
        import pymongo.errors
        from beanie import UpdateResponse
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 1. Determine next version number
                latest = await ContentVersion.find(
                    ContentVersion.block_id == str(block.id)
                ).sort(-ContentVersion.version_number).first_or_none()
                next_num = (latest.version_number + 1) if latest else 1

                # 2. Deactivate ALL previous active versions for this block atomically
                await ContentVersion.find(
                    ContentVersion.block_id == str(block.id),
                    ContentVersion.is_active == True,
                ).update_many({"$set": {"is_active": False}})

                # 3. Create new version
                content_payload = output_data if isinstance(output_data, dict) else {"text": str(output_data)}
                version = ContentVersion(
                    block_id=str(block.id),
                    version_number=next_num,
                    content=content_payload,
                    created_by="system",
                    is_active=True,
                )
                await version.insert()
                
                # Success - update block pointer and break
                block.current_version_id = str(version.id)
                block.updated_at = get_now()
                await block.save()
                break
                
            except pymongo.errors.DuplicateKeyError:
                if attempt == max_retries - 1:
                    logger.error("Failed to save ContentVersion after %s retries", max_retries)
                    raise
                logger.warning("Version collision for block %s, retrying...", block.id)
                continue

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        project = await self.get_project(project_id, user_id)
        if not project: return False
        if project.user_id != user_id: return False # Only owner can delete
        return await self.repo.delete(project)
