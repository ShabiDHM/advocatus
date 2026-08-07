# FILE: backend/scripts/purge_academy_mongo.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

for p in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)

sys.path.append(str(BACKEND_DIR))

from app.core.db import get_db_instance

def purge_mongo_academy():
    print("--- [PHOENIX] Purging Academic Chunks from MongoDB Atlas ---")
    try:
        db = get_db_instance()
        result = db.legal_knowledge_base.delete_many({
            "$or": [
                {"source": {"$regex": "AKADEMIA|KOMMENTAR|DORACAK", "$options": "i"}},
                {"law_title": {"$regex": "AKADEMIA|KOMMENTAR|DORACAK", "$options": "i"}},
                {"processor_version": {"$regex": "ACADEMY", "$options": "i"}}
            ]
        })
        
        remaining_statutes = db.legal_knowledge_base.count_documents({})
        print(f"🗑️ Purged {result.deleted_count} academic chunks from MongoDB Atlas!")
        print(f"📊 Remaining Statutory Chunks in DB: {remaining_statutes}")
    except Exception as e:
        print(f"❌ Error purging MongoDB Atlas: {e}")

if __name__ == "__main__":
    purge_mongo_academy()