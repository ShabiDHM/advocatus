# FILE: backend/scripts/sync_findings.py
# PHOENIX PROTOCOL - MEMORY SYNC UTILITY V1.1 (AUTH FIX)
# 1. FIX: Added MongoDB Authentication support using environment variables.
# 2. LOGIC: Constructs a secure connection string (mongodb://user:pass@host...).

import os
import sys
import logging
from pymongo import MongoClient
import urllib.parse

# Add backend to path so we can import services
sys.path.append(os.getcwd())

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncTool")

# --- AUTHENTICATION CONFIGURATION ---
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
DB_NAME = os.getenv("MONGO_DB_NAME", "advocatus")

# Construct Secure URL
if MONGO_USER and MONGO_PASSWORD:
    # URL encode credentials to handle special characters
    username = urllib.parse.quote_plus(MONGO_USER)
    password = urllib.parse.quote_plus(MONGO_PASSWORD)
    MONGO_URL = f"mongodb://{username}:{password}@{MONGO_HOST}:{MONGO_PORT}/"
else:
    # Fallback to direct URL if provided, or unauthenticated default
    MONGO_URL = os.getenv("MONGO_URL", f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")

def sync_memory():
    # 1. Connect to DB
    print(f"🔌 Connecting to MongoDB at {MONGO_HOST}...")
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Test Connection & Auth
        try:
            db.command('ping')
            print("✅ MongoDB Connection & Auth Successful.")
        except Exception as auth_err:
            print(f"❌ Connection Failed: {auth_err}")
            return
        
        # 2. Get Findings
        print(f"🔍 Scanning 'findings' collection in database: {DB_NAME}")
        findings = list(db.findings.find({}))
        
        if not findings:
            print("⚠️ No findings found in MongoDB. Upload a document first.")
            return

        print(f"📊 Found {len(findings)} findings. Initiating Transfer to Vector Store...")

        # 3. Import Service (Lazy load to avoid startup conflicts)
        try:
            from app.services.vector_store_service import store_structured_findings
        except ImportError as ie:
            print(f"❌ Import Error: {ie}")
            print("Ensure you are running this inside the docker container.")
            return
        
        # 4. Clean & Normalize Data
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
        print("🧠 Generating Embeddings & Storing...")
        success = store_structured_findings(clean_findings)
        
        if success:
            print("✅ SUCCESS: Findings successfully injected into AI Memory.")
            print("👉 The Chat should now be able to answer specific questions.")
        else:
            print("❌ FAILURE: Embedding Service failed. Check 'ai-core-service' logs.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    sync_memory()