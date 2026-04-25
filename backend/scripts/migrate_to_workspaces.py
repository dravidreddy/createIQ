import asyncio
import os
import sys

# Add backend dir to python path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.database import init_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceTier
from app.models.project import Project
from dotenv import load_dotenv

load_dotenv()


async def migrate_users_to_workspaces():
    print("Initializing Database...")
    await init_db()

    print("Fetching users...")
    users = await User.find_all().to_list()
    
    migrated_count = 0
    projects_updated = 0

    for user in users:
        # Check if user already owns a workspace
        existing_ws = await Workspace.find_one({"owner_id": str(user.id)})
        
        if existing_ws:
            ws_id = str(existing_ws.id)
            print(f"User {user.email} already has workspace {ws_id}")
        else:
            # Create a new Personal Workspace
            ws = Workspace(
                name=f"{user.display_name}'s Workspace",
                owner_id=str(user.id),
                tier=WorkspaceTier.FREE,
                members=[
                    WorkspaceMember(
                        user_id=str(user.id),
                        role="owner"
                    )
                ]
            )
            await ws.insert()
            ws_id = str(ws.id)
            print(f"Created workspace {ws_id} for user {user.email}")
            migrated_count += 1

        # Migrate all projects belonging to this user that don't have a workspace_id yet
        projects = await Project.find({"user_id": str(user.id), "workspace_id": None}).to_list()
        for project in projects:
            project.workspace_id = ws_id
            await project.save()
            projects_updated += 1
            
    print(f"\nMigration Complete!")
    print(f"- Workspaces created: {migrated_count}")
    print(f"- Projects assigned: {projects_updated}")


if __name__ == "__main__":
    asyncio.run(migrate_users_to_workspaces())
