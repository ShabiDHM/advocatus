# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - SAAS LAW INGESTOR V6.0 (RATE-LIMIT OPTIMIZED)
# 1. FIX: Integrated time.sleep() to prevent OpenRouter/OpenAI 429 errors.
# 2. ALIGNMENT: Writes directly to MongoDB Atlas for Vector Search.
# 3. STATUS: Robust for large PDF ingestion.

import os, sys, time, uuid, logging
from pathlib import Path
from dotenv import load_dotenv

# --- BOOTSTRAP PHASE ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

# Load variables
env_paths = [ROOT_DIR / ".env", BACKEND_DIR / ".env"]
for p in env_paths:
    if p.exists(): load_dotenv(p, override=True)

sys.path.append(str(BACKEND_DIR))

# --- IMPORT PHASE ---
from pymongo import MongoClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.embedding_service import generate_embedding
from app.services.text_extraction_service import extract_text

print("--- [PHOENIX] Starting Rate-Limited Ingestion Sequence V6.0 ---")

def ingest():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    try:
        mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = mongo_client[db_name]
        mongo_coll = db["legal_knowledge_base"]
        print(f"✅ Connected to Atlas: {db_name}")
    except Exception as e:
        print(f"❌ Database Failure: {e}")
        return

    laws_dir = ROOT_DIR / "data" / "laws"
    files = list(laws_dir.rglob("*.pdf"))
    if not files:
        print(f"⚠️  No PDFs found in {laws_dir}")
        return

    print(f"🚀 Found {len(files)} laws. Starting rate-limited cloud sync...")

    for file_path in files:
        fname = file_path.name
        raw_text = extract_text(str(file_path), "application/pdf")
        if not raw_text: continue
        
        law_title = fname.replace(".pdf", "").replace("_", " ").title()
        print(f"\n📄 Processing: {law_title}")
        
        articles = raw_text.split("Neni ") 
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        for idx, art_text in enumerate(articles):
            if len(art_text) < 30: continue
            chunks = splitter.split_text(art_text)
            
            for i, chunk in enumerate(chunks):
                # PHOENIX FIX: Polite Pacing
                # Wait 1.5 seconds between each request to prevent quota bans
                time.sleep(1.5)
                
                vector = generate_embedding(chunk)
                if not vector or all(v == 0.0 for v in vector):
                    print(f"\n❌ Embedding Blocked at chunk {idx}.{i}. Waiting 5 seconds before resuming...")
                    time.sleep(5.0) # Backoff if blocked
                    continue
                
                chunk_id = str(uuid.uuid4())
                meta = {"source": fname, "law_title": law_title, "article_number": str(idx), "chunk_index": i, "jurisdiction": "ks"}
                
                # Permanent SaaS Storage
                mongo_coll.update_one(
                    {"chunk_id": chunk_id}, 
                    {"$set": {"embedding": vector, "text": chunk, **meta}}, 
                    upsert=True
                )
                print(f"   [Synced: {idx}.{i}]", end="\r")
                
        print(f"\n✅ Completed: {law_title}")

if __name__ == "__main__":
    ingest()
    print("\n--- [PHOENIX] All Ingestion Tasks Complete ---")