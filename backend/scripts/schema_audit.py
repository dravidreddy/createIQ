import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models.database import init_db, close_db

async def audit_schema():
    await init_db()
    from app.models.database import _client
    from app.config import get_settings
    settings = get_settings()
    
    db = _client[settings.mongodb_db_name]
    collections = await db.list_collection_names()
    
    print("="*60)
    print(f" CreatorIQ Atlas Schema Audit: [{settings.mongodb_db_name}]")
    print("="*60)
    
    expected_count = 21
    print(f"Found {len(collections)} collections (Expected: {expected_count})")
    
    for col in sorted(collections):
        indexes = await db[col].list_indexes().to_list(length=100)
        print(f"✓ {col:25} | Indexes: {len(indexes)}")
        
    await close_db()
    print("="*60)

if __name__ == "__main__":
    asyncio.run(audit_schema())
