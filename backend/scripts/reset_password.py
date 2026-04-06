import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Add current directory to path so 'app' module can be found
sys.path.append(os.getcwd())

async def reset_password(email: str, new_password: str = "password123"):
    """
    Manually reset a user's password in MongoDB.
    Useful for overcoming hashing mismatches during development.
    """
    from app.config import get_settings
    from app.utils.security import hash_password
    
    settings = get_settings()
    
    print(f"--- 🔑 Resetting Password for {email} ---")
    
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client.get_database(settings.mongodb_db_name)
    users_coll = db.get_collection("User") # Beanie uses class name as collection name by default
    
    # Try both "User" and "users" just in case
    user = await users_coll.find_one({"email": email})
    if not user:
        users_coll = db.get_collection("users")
        user = await users_coll.find_one({"email": email})
        
    if not user:
        print(f"❌ User with email {email} not found in database {settings.mongodb_db_name}")
        return

    new_hash = hash_password(new_password)
    result = await users_coll.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": new_hash}}
    )
    
    if result.modified_count > 0:
        print(f"✅ SUCCESS: Password for {email} reset to '{new_password}'")
        print(f"   New Hash: {new_hash[:20]}...")
    else:
        print(f"⚠️ No changes made (password might already be '{new_password}')")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_password.py <email> [new_password]")
        sys.exit(1)
        
    email_to_reset = sys.argv[1]
    pwd = sys.argv[2] if len(sys.argv) > 2 else "password123"
    
    asyncio.run(reset_password(email_to_reset, pwd))
