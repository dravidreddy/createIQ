from typing import Optional, List, Tuple
from beanie import PydanticObjectId
from app.models.project import Project, ProjectStatus

class ProjectRepository:
    """
    Data Access Layer for Projects.
    Separates MongoDB Beanie queries from pure business logic.
    """
    
    async def create(self, project: Project) -> Project:
        await project.insert()
        return project

    async def get_by_id(self, project_id: str) -> Optional[Project]:
        try:
            # Explicitly ignore soft-deleted documents
            return await Project.find_one({"_id": PydanticObjectId(project_id), "is_deleted": {"$ne": True}})
        except Exception:
            return None

    async def list_by_user(self, user_id: str, page: int = 1, per_page: int = 10, status: ProjectStatus = None) -> Tuple[List[Project], int]:
        query = Project.find({"$or": [{"user_id": user_id}, {"collaborators.user_id": user_id}]})
        
        # Filter active only
        query = query.find({"is_deleted": {"$ne": True}})
        
        if status:
            query = query.find(Project.status == status)

        total = await query.count()
        offset = (page - 1) * per_page
        projects = await query.sort(-Project.created_at).skip(offset).limit(per_page).to_list()
        return projects, total

    async def update(self, project: Project) -> Project:
        await project.save()
        return project

    async def delete(self, project: Project) -> bool:
        project.is_deleted = True
        await project.save()
        return True
