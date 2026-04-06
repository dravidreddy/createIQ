"""
Final MongoDB Database Audit — Post-Migration
DEVTOOLS - DO NOT import in production code.
"""
from pymongo import MongoClient
import json
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        return super().default(o)

from app.config import get_settings
settings = get_settings()

client = MongoClient(settings.mongo_uri)
db = client[settings.mongodb_db_name]

collections = sorted(db.list_collection_names())
print(f"Total Collections: {len(collections)}")
print()

# Target collections check
target = [
    "users", "workspaces", "user_profiles", "projects",
    "content_blocks", "content_versions", "ai_generations",
    "strategies", "conversations", "messages", "memory_embeddings",
    "project_agent_states", "budget_allocations", "job_metrics",
    "ranking_profiles", "variant_logs", "content_templates",
    "agent_sessions", "project_artifacts", "project_versions",
]

print("=== TARGET COLLECTION CHECK ===")
for t in sorted(target):
    status = "OK" if t in collections else "MISSING"
    print(f"  [{status}] {t}")

extra = [c for c in collections if c not in target]
if extra:
    print(f"\n  Extra collections (from legacy): {extra}")

print(f"\n=== COLLECTION DETAILS ===")
for col_name in collections:
    col = db[col_name]
    count = col.count_documents({})
    indexes = list(col.list_indexes())
    idx_names = [i['name'] for i in indexes if i['name'] != '_id_']
    unique_idxs = [i['name'] for i in indexes if i.get('unique') and i['name'] != '_id_']
    print(f"\n{col_name} (docs={count}, indexes={len(indexes)})")
    if idx_names:
        print(f"  Indexes: {', '.join(idx_names)}")
    if unique_idxs:
        print(f"  Unique:  {', '.join(unique_idxs)}")

    if count > 0:
        sample = col.find_one()
        if sample:
            keys = list(sample.keys())
            print(f"  Schema:  {keys}")

print(f"\n=== SUMMARY ===")
print(f"Total collections: {len(collections)}")
print(f"Total documents:   {sum(db[c].count_documents({}) for c in collections)}")
total_indexes = sum(len(list(db[c].list_indexes())) for c in collections)
print(f"Total indexes:     {total_indexes}")

client.close()
