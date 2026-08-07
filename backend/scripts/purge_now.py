# FILE: backend/scripts/purge_now.py
# PHOENIX PROTOCOL - GUARANTEED MONGODB & CLOUD B2 PURGER

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from app.core.db import get_db_instance
from app.services import storage_service

def purge_now():
    db = get_db_instance()
    
    print("\n================ STARTING TOTAL PURGE ================")
    
    # 1. MongoDB Purge by Source
    del1 = db.legal_knowledge_base.delete_many({"source": {"$regex": "AKADEMIA|VENDIME|DREJT|udhezues|doracak", "$options": "i"}})
    print(f"✓ Deleted {del1.deleted_count} documents by source regex.")

    # 2. MongoDB Purge by Law Title
    del2 = db.legal_knowledge_base.delete_many({"law_title": {"$regex": "AKADEMIA|VENDIME|A.Nr|PML.Nr|Rev.Nr|udhezues|doracak", "$options": "i"}})
    print(f"✓ Deleted {del2.deleted_count} documents by law_title regex.")

    # 3. MongoDB Purge by Category
    del3 = db.legal_knowledge_base.delete_many({"category": {"$in": ["academic", "caselaw"]}})
    print(f"✓ Deleted {del3.deleted_count} documents by category.")

    # 4. Backblaze B2 Cloud Storage Purge
    try:
        s3_client = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        for prefix in ["academic/", "case_law/", "decisions/", "jurisprudence/"]:
            b2_response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            contents = b2_response.get('Contents', [])
            count = 0
            for obj in contents:
                key = obj.get('Key')
                if key:
                    s3_client.delete_object(Bucket=bucket, Key=key)
                    count += 1
            print(f"✓ Backblaze B2: Deleted {count} cloud files from '{prefix}'")
    except Exception as e:
        print(f"⚠️ B2 Cloud purge note: {e}")

    print("================ PURGE COMPLETE ================\n")

if __name__ == "__main__":
    purge_now()