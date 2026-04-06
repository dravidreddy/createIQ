"""
DEVTOOLS - Drop DB Temp
DO NOT import in production code.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

async def drop():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    await client.drop_database(settings.mongodb_db_name)
    print(f"Dropped DB: {settings.mongodb_db_name}")
    client.close()

if __name__ == "__main__":
    asyncio.run(drop())
