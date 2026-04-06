import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check_users():
    mongo_uri = "mongodb://localhost:27017" # Default or check .env
    # Check .env for real URI
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("MONGO_URI="):
                    mongo_uri = line.split("=", 1)[1].strip()

    client = AsyncIOMotorClient(mongo_uri)
    db = client.get_database("creatoriq_dev")
    users_coll = db.get_collection("users")
    
    count = await users_coll.count_documents({})
    print(f"Total users: {count}")
    
    async for user in users_coll.find().limit(5):
        print(f"User: {user.get('email')} | Hashed PW: {user.get('hashed_password')[:20]}...")

if __name__ == "__main__":
    asyncio.run(check_users())
