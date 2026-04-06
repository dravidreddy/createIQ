import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add the backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import get_settings

STATIC_USER_ID = "60f0f1f2f3f4f5f6f7f8f9fa"
STATIC_PROJECT_ID = "60f0f1f2f3f4f5f6f7f8f9fb"

async def seed():
    settings = get_settings()
    print(f"Connecting to {settings.mongodb_url}")
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    
    users_col = db["User"] # Beanie usually uses class name
    projects_col = db["projects"] # Project model says name = "projects"
    
    print("Clearing existing test data...")
    await users_col.delete_many({"email": "test@creatoriq.com"})
    await projects_col.delete_many({"_id": ObjectId(STATIC_PROJECT_ID)})
    
    print("Inserting fresh test data...")
    
    # Insert User
    user_doc = {
        "_id": ObjectId(STATIC_USER_ID),
        "email": "test@creatoriq.com",
        "full_name": "Test User",
        "is_active": True,
        "hashed_password": "fake",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    await users_col.insert_one(user_doc)
    print(f"User {STATIC_USER_ID} inserted.")
    
    # Insert Project
    project_doc = {
        "_id": ObjectId(STATIC_PROJECT_ID),
        "user_id": STATIC_USER_ID,
        "title": "Test Production Project",
        "topic": "Technology Review",
        "status": "draft",
        "is_deleted": False,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "completed_stages": []
    }
    await projects_col.insert_one(project_doc)
    print(f"Project {STATIC_PROJECT_ID} inserted.")
    
    # Verification
    p = await projects_col.find_one({"_id": ObjectId(STATIC_PROJECT_ID)})
    u = await users_col.find_one({"_id": ObjectId(STATIC_USER_ID)})
    if p and u:
        print("✅ RAW VERIFICATION SUCCESS: User and Project found in DB via Motor.")
    else:
        print(f"❌ RAW VERIFICATION FAILED. Project: {p is not None}, User: {u is not None}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
