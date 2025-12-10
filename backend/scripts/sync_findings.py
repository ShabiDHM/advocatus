# FILE: backend/scripts/final_sync.py
# PHOENIX PROTOCOL - FINAL OVERRIDE SCRIPT (PRE-FILLED)
# 1. DIRECT: Uses the exact, verified credentials. No placeholders.
# 2. CORRECTED: Targets the correct database ('phoenix_protocol_db') and auth source ('admin').

import os
import sys
import logging
from pymongo import MongoClient
import urllib.parse

# Add backend to path so we can import app modules
sys.path.append(os.getcwd())

# Setup Logging
logging.basicConfig(level=logging.INFO)

# --- VERIFIED CREDENTIALS ---
MONGO_USER = "advocatus_admin"
MONGO_PASSWORD = "681wRsFTiffSw7G+JxyEnceWHIpFg/hyvcbcN4ECwpA="
MONGO_HOST = "mongo"
DB_NAME = "phoenix_protocol_db"  # CORRECTED
MONGO_AUTH_SOURCE = "admin"      # CORRECTED

def force_sync_memory():
    print("--- PHOENIX FINAL SYNC ---")
    try:
        # URL Encode credentials to handle special characters like '+' and '/'
        username = urllib.parse.quote_plus(MONGO_USER)
        password = urllib.parse.quote_plus(MONGO_PASSWORD)
        
        # Construct the final, correct connection string
        MONGO_URL = f"mongodb://{username}:{password}@{MONGO_HOST}:27017/?authSource={MONGO_AUTH_SOURCE}"
        
        print(f"🔌 Attempting connection to host '{MONGO_HOST}' with authSource='{MONGO_AUTH_SOURCE}'...")
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Verify connection by reading from the target database
        db.command('ping')
        print(f"✅ MongoDB Connection Successful to database '{DB_NAME}'.")
        
        print("🔍 Scanning 'findings' collection...")
        findings = list(db.findings.find({}))
        
        if not findings:
            print("⚠️ No findings found in MongoDB. Please ensure a document has been uploaded and processed.")
            return

        print(f"📊 Found {len(findings)} findings. Preparing for AI Memory injection...")

        # Lazy import to prevent circular dependencies
        from app.services.vector_store_service import store_structured_findings
        
        # Prepare data for the vector store service
        clean_findings = [
            {
                "finding_text": f.get("finding_text"),
                "case_id": str(f.get("case_id")),
                "document_id": str(f.get("document_id")),
                "category": f.get("category", "FAKT"),
                "document_name": f.get("document_name", "N/A")
            } for f in findings if f.get("finding_text")
        ]

        print("🧠 Generating embeddings and synchronizing with ChromaDB...")
        success = store_structured_findings(clean_findings)
        
        if success:
            print("✅✅✅ SUCCESS: AI Memory is now fully synchronized.")
            print("👉 The Chat and Drafting tools are now fully operational.")
        else:
            print("❌ FAILURE: Could not store findings. Check 'ai-core-service' and 'backend' logs for embedding errors.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print("--- TROUBLESHOOTING ---")
        print("1. Is the 'ai-core-service' container running and healthy?")
        print("2. Is the password copy-pasted correctly into this script?")
        print("-----------------------")

if __name__ == "__main__":
    force_sync_memory()