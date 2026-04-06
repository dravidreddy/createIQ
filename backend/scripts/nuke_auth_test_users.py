import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Add current directory to path so 'app' module can be found
sys.path.append(os.getcwd())

async def nuke_test_users():
    """
    Remove all users with 'test' or 'qa' in their email to allow fresh testing.
    """
    from app.config import get_settings
    
    settings = get_settings()
    
    print(f"--- 🧨 Nuking Test Users from {settings.mongodb_db_name} ---")
    
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client.get_database(settings.mongodb_db_name)
    users_coll = db.get_collection("User") # Beanie uses class name as collection name by default
    
    # Remove ALL users to ensure zero collision and fresh start
    query = {} 
    
    # Count first
    count = await users_coll.count_documents(query)
    print(f"🔍 Found {count} total users to remove.")
    
    if count > 0:
        result = await users_coll.delete_many(query)
        print(f"✅ Successfully deleted {result.deleted_count} users.")
    else:
        print("ℹ️ No users found to delete.")

if __name__ == "__main__":
    asyncio.run(nuke_test_users())
