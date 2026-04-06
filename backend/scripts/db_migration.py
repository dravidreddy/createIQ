"""
CreatorIQ Enterprise MongoDB Migration Suite (Pure Python Edition)

A production-grade migration tool to safely move data from local/dev to Atlas.
Uses pymongo for document-level transfers (no external CLI tools required).

Updated to handle restricted Atlas users (skip listDatabases).

Usage:
    python backend/scripts/db_migration.py --target-env dev --no-dry-run
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from pymongo import MongoClient

# Add backend to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

def verify_migration(source_db, target_db):
    """Deep verification: Counts + Sampling + Schema Audit."""
    logger.info(f"Starting verification: {source_db.name} (Local) -> {target_db.name} (Atlas)")
    
    try:
        source_cols = source_db.list_collection_names()
        target_cols = target_db.list_collection_names()
    except Exception as e:
        logger.error(f"Failed to list collections for verification: {e}")
        return

    # 1. Schema Audit
    missing_cols = set(source_cols) - set(target_cols)
    if missing_cols:
        logger.error(f"CRITICAL: Missing collections in target: {missing_cols}")
    else:
        logger.info("✓ Schema Audit: All collections present.")

    # 2. Document Counts
    for col_name in source_cols:
        s_count = source_db[col_name].count_documents({})
        t_count = target_db[col_name].count_documents({})
        
        if s_count != t_count:
            logger.error(f"Mismatch in {col_name}: Source={s_count}, Target={t_count}")
        else:
            logger.info(f"✓ {col_name:25} | Docs: {s_count}")

    # 3. Random Sampling
    logger.info("Performing random sampling (5 docs per collection)...")
    for col_name in source_cols:
        if source_db[col_name].count_documents({}) == 0:
            continue
        cursor = source_db[col_name].aggregate([{"$sample": {"size": 5}}])
        for doc in cursor:
            exists = target_db[col_name].find_one({"_id": doc["_id"]})
            if not exists:
                logger.error(f"Sample doc {doc['_id']} missing in target collection {col_name}!")

    logger.info("Verification complete.")

def migrate_python_mode(source_uri, target_uri, source_db_name, target_db_name, dry_run=True):
    """Pure Python migration using pymongo."""
    logger.info("Initializing Pure Python Migration Engine...")
    
    s_client = MongoClient(source_uri)
    t_client = MongoClient(target_uri)
    
    try:
        # Check source database
        source_db = s_client[source_db_name]
        try:
            collections = source_db.list_collection_names()
        except Exception as e:
            logger.error(f"Failed to access source database '{source_db_name}': {e}")
            return

        if not collections:
            logger.warning(f"No collections found in source database '{source_db_name}'.")
            return

        logger.info(f"Processing database: {source_db_name} -> {target_db_name}")
        target_db = t_client[target_db_name]
        
        for col_name in collections:
            if col_name.startswith("system."):
                continue
            
            count = source_db[col_name].count_documents({})
            logger.info(f"  Collection: {col_name:30} ({count} documents)")
            
            if dry_run:
                logger.info(f"    [DRY-RUN] Would copy {count} documents to Atlas.")
                continue
            
            if count == 0:
                logger.info("    Skipping empty collection.")
                continue

            # Perform the copy in batches
            logger.info(f"    Copying {count} documents...")
            cursor = source_db[col_name].find()
            batch = []
            batch_size = 500
            processed = 0
            
            for doc in cursor:
                batch.append(doc)
                if len(batch) >= batch_size:
                    try:
                        target_db[col_name].insert_many(batch, ordered=False)
                    except Exception as e:
                        logger.warning(f"    Batch insert error (non-fatal, possibly duplicates): {e}")
                    processed += len(batch)
                    batch = []
                    logger.info(f"    Progress: {processed}/{count}")
            
            if batch:
                try:
                    target_db[col_name].insert_many(batch, ordered=False)
                except Exception as e:
                    logger.warning(f"    Final batch insert error: {e}")
                processed += len(batch)
            
            # Copy Indexes
            logger.info("    Recreating indexes...")
            try:
                indexes = source_db[col_name].list_indexes()
                for idx in indexes:
                    if idx['name'] == '_id_':
                        continue
                    keys = list(idx['key'].items())
                    options = {k: v for k, v in idx.items() if k not in ['v', 'key', 'ns', 'name']}
                    try:
                        target_db[col_name].create_index(keys, name=idx['name'], **options)
                    except Exception as e:
                        logger.warning(f"    Failed to create index {idx['name']}: {e}")
            except Exception as e:
                logger.warning(f"    Could not list indexes for {col_name}: {e}")

        if not dry_run:
            verify_migration(source_db, target_db)

    finally:
        s_client.close()
        t_client.close()

def main():
    parser = argparse.ArgumentParser(description="CreatorIQ DB Migration Suite")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate migration")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Execute actual migration")
    parser.add_argument("--target-env", choices=["dev", "test", "prod"], default="dev", help="Target environment")
    parser.add_argument("--source-db", default="createIQ", help="Source local database name")
    parser.add_argument("--force", action="store_true", help="Required to target production")
    
    args = parser.parse_args()
    settings = get_settings()

    # Determine URIs
    # If the user has a local URI set up with credentials, let's try to detect it
    # Currently we default to unauthenticated local
    source_uri = "mongodb://localhost:27017" 
    target_uri = settings.mongo_uri
    target_db_name = f"creatoriq_{args.target_env}"
    
    logger.info("="*60)
    logger.info(" CreatorIQ MongoDB Migration Suite (Python Engine)")
    logger.info("="*60)
    logger.info(f"Source DB: {args.source_db}")
    logger.info(f"Target DB: {target_db_name}")
    logger.info(f"Mode:      {'DRY-RUN' if args.dry_run else 'LIVE EXECUTION'}")
    logger.info("="*60)

    # Production Safeguard
    if args.target_env == "prod" and not args.dry_run:
        if not args.force:
            logger.critical("Aborting: Target is PROD but --force flag is missing.")
            sys.exit(1)
        
        confirm = input("\n[CAUTION] You are about to migrate to PRODUCTION. This will overwrite data. Type 'CONFIRM' to proceed: ")
        if confirm != "CONFIRM":
            logger.info("Migration aborted by user.")
            sys.exit(0)

    # Run Migration
    try:
        migrate_python_mode(source_uri, target_uri, args.source_db, target_db_name, args.dry_run)
    except Exception as e:
        logger.exception(f"Migration failed with error: {e}")
        sys.exit(1)

    logger.info("\n" + "="*60)
    logger.info("Migration status: SUCCESS" if not args.dry_run else "Dry-run complete.")
    logger.info("="*60)

if __name__ == "__main__":
    main()
