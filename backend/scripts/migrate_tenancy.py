# FILE: backend/scripts/migrate_tenancy.py
# PHOENIX PROTOCOL - MIGRATION SCRIPT V1.1 (URI PARSING FIX)
# 1. FIX: Removed reliance on non-existent 'settings.DATABASE_NAME'.
# 2. LOGIC: Parses DB name directly from 'settings.DATABASE_URI'.
# 3. RUN: python -m scripts.migrate_tenancy

import asyncio
import os
import sys
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime

# Ensure the script can find the app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings

async def migrate():
    print("--- 🚀 STARTING TENANCY MIGRATION ---")
    
    # 1. Connect directly (bypassing app logic for safety)
    uri = settings.DATABASE_URI
    client = AsyncIOMotorClient(uri)
    
    # Parse Database Name from URI
    try:
        db_name = urlparse(uri).path.lstrip('/')
        if not db_name:
            print("⚠️  Warning: No database name in URI, defaulting to 'juristi_ai_db'")
            db_name = 'juristi_ai_db'
    except Exception as e:
        print(f"⚠️  Error parsing URI: {e}, defaulting to 'juristi_ai_db'")
        db_name = 'juristi_ai_db'
        
    db = client[db_name]
    print(f"--- Connected to DB: {db_name} ---")

    # 2. Find Orphan Users (No org_id)
    users_cursor = db.users.find({
        "$or": [
            {"org_id": {"$exists": False}},
            {"org_id": None}
        ]
    })
    
    users = await users_cursor.to_list(length=1000)
    
    if not users:
        print("--- ✅ No orphan users found. Migration not needed. ---")
        return

    print(f"--- Found {len(users)} orphan users to migrate ---")

    for user in users:
        user_id = user["_id"]
        username = user.get("username", "Unknown")
        print(f"Processing User: {username} ({user_id})...")

        # 3. Create Organization
        org_doc = {
            "name": f"{username}'s Firm",
            "owner_id": user_id,
            "tier": "TIER_1",
            "max_seats": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        org_result = await db.organizations.insert_one(org_doc)
        org_id = org_result.inserted_id
        print(f"   -> Created Org: {org_doc['name']} ({org_id})")

        # 4. Update User (Link to Org + Set Role)
        await db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "org_id": org_id,
                    "org_role": "OWNER"
                }
            }
        )
        print(f"   -> Updated User Role to OWNER")

        # 5. Update Cases (Transfer Ownership to Org)
        case_result = await db.cases.update_many(
            {"user_id": user_id},
            {"$set": {"org_id": org_id}}
        )
        print(f"   -> Linked {case_result.modified_count} cases to Organization")

    print("--- ✅ MIGRATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(migrate())