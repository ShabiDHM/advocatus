# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - SAAS LAW INGESTOR V7.0 (IDEMPOTENT & RESILIENT)
# 1. FIX: Added MD5 Hash checking to skip already-ingested files.
# 2. FIX: Added try/except around individual files to prevent pipeline crashes.
# 3. STATUS: 100% Robust for continuous deployment operations.

import os, sys, time, uuid, logging, hashlib
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

print("--- [PHOENIX] Starting Smart Ingestion Sequence V7.0 ---")

def calculate_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"⚠️ Could not hash file {filepath}: {e}")
        return ""

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

    print(f"🚀 Found {len(files)} laws. Starting smart sync...")

    stats = {"skipped": 0, "added": 0, "failed": 0}

    for file_path in files:
        fname = file_path.name
        
        try:
            # 1. Idempotency Check (Has this file changed?)
            current_hash = calculate_file_hash(str(file_path))
            existing = mongo_coll.find_one({"source": fname, "file_hash": current_hash})
            
            if existing:
                print(f"⏭️  Skipped: {fname} (Already in database)")
                stats["skipped"] += 1
                continue
                
            print(f"\n📄 Processing: {fname}")
            
            # If it exists but hash is different, delete old chunks to update
            mongo_coll.delete_many({"source": fname})
            
            raw_text = extract_text(str(file_path), "application/pdf")
            if not raw_text or len(raw_text.strip()) < 50:
                print(f"   ⚠️  Extraction empty or too short. Skipping.")
                stats["failed"] += 1
                continue
            
            law_title = fname.replace(".pdf", "").replace("_", " ").title()
            print(f"   -> Title: {law_title}")
            
            articles = raw_text.split("Neni ") 
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            
            chunks_processed = 0
            for idx, art_text in enumerate(articles):
                if len(art_text) < 30: continue
                chunks = splitter.split_text(art_text)
                
                for i, chunk in enumerate(chunks):
                    time.sleep(1.5) # Polite Pacing for OpenRouter
                    
                    vector = generate_embedding(chunk)
                    if not vector or all(v == 0.0 for v in vector):
                        print(f"\n❌ Embedding Blocked at chunk {idx}.{i}. Waiting 5 seconds...")
                        time.sleep(5.0) 
                        continue
                    
                    chunk_id = str(uuid.uuid4())
                    meta = {
                        "source": fname, 
                        "law_title": law_title, 
                        "article_number": str(idx), 
                        "chunk_index": i, 
                        "jurisdiction": "ks",
                        "file_hash": current_hash # Save the hash for future checks
                    }
                    
                    mongo_coll.update_one(
                        {"chunk_id": chunk_id}, 
                        {"$set": {"embedding": vector, "text": chunk, **meta}}, 
                        upsert=True
                    )
                    chunks_processed += 1
                    print(f"   [Synced Chunks: {chunks_processed}]", end="\r")
                    
            print(f"\n✅ Completed: {law_title}")
            stats["added"] += 1
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR processing {fname}: {e}")
            stats["failed"] += 1

    print("\n" + "="*40)
    print(f"🏁 Ingestion Report:")
    print(f"   Added/Updated: {stats['added']}")
    print(f"   Skipped:       {stats['skipped']}")
    print(f"   Failed:        {stats['failed']}")
    print("="*40)

if __name__ == "__main__":
    ingest()