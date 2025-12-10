# FILE: backend/scripts/sync_findings.py
import os
import sys
import logging
from pymongo import MongoClient

# Add backend to path so we can import services
sys.path.append(os.getcwd())

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "advocatus")

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncTool")

def sync_memory():
    # 1. Connect to DB
    print(f"🔌 Connecting to MongoDB at {MONGO_URL}...")
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # 2. Get Findings
        findings = list(db.findings.find({}))
        if not findings:
            print("⚠️ No findings found in MongoDB.")
            return

        print(f"📊 Found {len(findings)} findings. Sending to AI Memory...")

        # 3. Import Service here to avoid startup issues
        from app.services.vector_store_service import store_structured_findings
        
        # 4. Clean Data
        clean_findings = []
        for f in findings:
            if f.get("finding_text"):
                clean_findings.append({
                    "finding_text": f.get("finding_text"),
                    "case_id": str(f.get("case_id")),
                    "document_id": str(f.get("document_id")),
                    "category": f.get("category", "FAKT"),
                    "document_name": f.get("document_name", "N/A")
                })

        # 5. Push to Vector DB
        success = store_structured_findings(clean_findings)
        
        if success:
            print("✅ SUCCESS: Findings synced to Vector Store.")
        else:
            print("❌ FAILURE: Embedding Service failed. Check AI Core connection.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    sync_memory()