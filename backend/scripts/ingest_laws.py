# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - SAAS LAW INGESTOR V8.1 (FORCE RE-INGESTION MODE)

import os, sys, time, uuid, logging, hashlib, unicodedata
from pathlib import Path
from dotenv import load_dotenv

# --- BOOTSTRAP PHASE ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

env_paths = [ROOT_DIR / ".env", BACKEND_DIR / ".env"]
for p in env_paths:
    if p.exists(): load_dotenv(p, override=True)

sys.path.append(str(BACKEND_DIR))

from pymongo import MongoClient
from app.services.embedding_service import generate_embedding
from app.services.text_extraction_service import extract_text
from app.services.albanian_document_processor import EnhancedDocumentProcessor
from app.services.albanian_language_detector import detect_document_language

print("--- [PHOENIX] Starting Force Re-Ingestion Sequence V8.1 ---")

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

def clean_law_title(filename: str) -> str:
    clean_name = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
    clean_name = unicodedata.normalize('NFC', clean_name)
    words = clean_name.split()
    capitalized_words = [word.capitalize() for word in words]
    return " ".join(capitalized_words)

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

    print(f"🚀 Found {len(files)} files. Forcing complete re-indexing...")

    stats = {"skipped": 0, "added": 0, "failed": 0}

    for file_path in files:
        fname = file_path.name
        
        try:
            current_hash = calculate_file_hash(str(file_path))
            print(f"\n📄 Force Processing: {fname}")
            
            # FORCE WIPE: Delete all old chunks for this file
            deleted_count = mongo_coll.delete_many({"source": fname}).deleted_count
            print(f"   -> Wiped {deleted_count} old chunks from Atlas.")
            
            raw_text = extract_text(str(file_path), "application/pdf")
            if not raw_text or len(raw_text.strip()) < 50:
                print(f"   ⚠️  Extraction empty or too short. Skipping.")
                stats["failed"] += 1
                continue
            
            detected_lang = detect_document_language(raw_text)
            law_title = clean_law_title(fname)
            print(f"   -> Title: {law_title} | Language: {detected_lang.upper()}")

            document_metadata = {
                "source": fname,
                "law_title": law_title,
                "jurisdiction": "ks",
                "file_hash": current_hash
            }

            chunks = EnhancedDocumentProcessor.process_document(
                text_content=raw_text,
                document_metadata=document_metadata,
                language=detected_lang
            )

            if not chunks:
                print(f"   ⚠️  No chunks generated. Skipping.")
                stats["failed"] += 1
                continue

            print(f"   -> Generated {len(chunks)} processed chunks. Generating embeddings...")

            chunks_processed = 0
            for i, chunk in enumerate(chunks):
                time.sleep(1.2) # Polite pacing for embeddings API
                
                vector = generate_embedding(chunk.content)
                if not vector or all(v == 0.0 for v in vector):
                    print(f"❌ Embedding Blocked at chunk {i}. Waiting 5 seconds...")
                    time.sleep(5.0) 
                    continue
                
                chunk_id = str(uuid.uuid4())
                
                mongo_coll.update_one(
                    {"chunk_id": chunk_id}, 
                    {
                        "$set": {
                            "chunk_id": chunk_id,
                            "embedding": vector, 
                            "text": chunk.content, 
                            **chunk.metadata
                        }
                    }, 
                    upsert=True
                )
                chunks_processed += 1
                print(f"   [Synced Chunks: {chunks_processed}/{len(chunks)}]", end="\r")
                
            print(f"\n✅ Completed: {law_title} ({chunks_processed} chunks indexed)")
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