"""
CreatorIQ Database Migration Script
DEVTOOLS - DO NOT import in production code.
"""

import asyncio
import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def migrate():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]

    logger.info("=" * 60)
    logger.info("CreatorIQ Database Migration")
    logger.info("=" * 60)

    # ─── Step 1: Initialise Beanie (creates collections + indexes) ──
    logger.info("\n[Step 1] Initialising Beanie — creating collections and indexes...")
    from app.models.database import init_db
    await init_db()
    logger.info("✓ All 21 document models registered and indexed")

    # ─── Step 2: Create default workspace for existing users ────────
    logger.info("\n[Step 2] Creating default workspaces for existing users...")
    from app.models.user import User
    from app.models.workspace import Workspace, WorkspaceMember

    users = await User.find_all().to_list()
    for user in users:
        user_id = str(user.id)
        existing_ws = await Workspace.find_one(Workspace.owner_id == user_id)
        if existing_ws:
            logger.info(f"  ⊘ User {user.email} already has workspace: {existing_ws.name}")
            continue

        ws = Workspace(
            name=f"{user.display_name}'s Workspace",
            owner_id=user_id,
            members=[WorkspaceMember(user_id=user_id, role="owner")],
        )
        await ws.insert()
        logger.info(f"  ✓ Created default workspace for {user.email}: {ws.name}")

    # ─── Step 3: Migrate embedded profiles to user_profiles ─────────
    logger.info("\n[Step 3] Migrating embedded profiles to user_profiles collection...")
    from app.models.profile import UserProfile

    for user in users:
        user_id = str(user.id)
        existing_profile = await UserProfile.find_one(UserProfile.user_id == user_id)
        if existing_profile:
            logger.info(f"  ⊘ User {user.email} already has profile in user_profiles")
            continue

        if user.profile and isinstance(user.profile, dict) and user.profile.get("content_niche"):
            profile = UserProfile(
                user_id=user_id,
                content_niche=user.profile.get("content_niche", ""),
                custom_niche=user.profile.get("custom_niche"),
                primary_platforms=user.profile.get("primary_platforms", []),
                content_style=user.profile.get("content_style", ""),
                target_audience=user.profile.get("target_audience"),
                typical_video_length=user.profile.get("typical_video_length", ""),
                preferred_language=user.profile.get("preferred_language", "English"),
                additional_context=user.profile.get("additional_context"),
            )
            await profile.insert()
            logger.info(f"  ✓ Migrated embedded profile for {user.email}")
        else:
            logger.info(f"  ⊘ User {user.email} has no embedded profile to migrate")

    # ─── Step 4: Audit final state ──────────────────────────────────
    logger.info("\n[Step 4] Final collection audit...")
    collections = sorted(await db.list_collection_names())
    logger.info(f"Total collections: {len(collections)}")
    for col_name in collections:
        col = db[col_name]
        count = await col.count_documents({})
        indexes = [idx["name"] async for idx in col.list_indexes()]
        logger.info(f"  {col_name:30s}  docs={count:5d}  indexes={len(indexes)}")

    logger.info("\n" + "=" * 60)
    logger.info("Migration complete!")
    logger.info("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
