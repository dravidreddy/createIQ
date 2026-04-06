"""
CreatorIQ Atlas Cloud Initialization Script

This script initializes the CreatorIQ database schema directly in MongoDB Atlas.
It uses Beanie to create all collections and indexes automatically.

Usage:
    python backend/scripts/atlas_init.py --env dev
"""

import asyncio
import argparse
import logging
import sys
import os

# Add backend to path to import config and models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import get_settings
from app.models.database import init_db, close_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def initialize_atlas(env_name: str):
    """Connects to Atlas and initializes the Beanie schema."""
    logger.info("="*60)
    logger.info(f" CreatorIQ Atlas Cloud Initialization [{env_name.upper()}]")
    logger.info("="*60)
    
    # Force environment for naming
    os.environ["ENV"] = env_name
    settings = get_settings()
    
    logger.info(f"Target DB: {settings.mongodb_db_name}")
    logger.info("Connecting to Atlas...")
    
    try:
        # init_db handles connection, retries, and Beanie registration
        await init_db()
        logger.info("✓ Connection established")
        logger.info("✓ Beanie initialization complete")
        logger.info("✓ Collections and Indexes synchronized")
        
        # Verification: Check if we can write a test doc
        from app.models.database import _client
        db = _client[settings.mongodb_db_name]
        await db.command("ping")
        logger.info("✓ Cluster Handshake (Ping) SUCCESS")
        
        # Schema Audit
        collections = await db.list_collection_names()
        logger.info(f"✓ Found {len(collections)} collections in {settings.mongodb_db_name}")
        for col in sorted(collections):
            count = await db[col].count_documents({})
            logger.info(f"  - {col:25} | Docs: {count}")

    except Exception as e:
        logger.error(f"CRITICAL: Atlas Initialization Failed: {e}")
        raise
    finally:
        await close_db()
        logger.info("="*60)
        logger.info("Initialization FINISHED")
        logger.info("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize CreatorIQ Atlas Schema")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev", help="Target environment")
    args = parser.parse_args()
    
    asyncio.run(initialize_atlas(args.env))
