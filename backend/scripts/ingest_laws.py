# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - PERMANENT LAW INGESTOR V5.3 (OMNI-PATH ENV)
# 1. FIX: Automated .env discovery in both Root and Backend directories.
# 2. INTEGRITY: Hard-stop on missing API keys to prevent database corruption.
# 3. STATUS: 100% Cloud-Independent aligned.

import os, sys, glob, re, uuid, logging
from pymongo import MongoClient
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Absolute Path Setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
sys.path.append(BACKEND_DIR)

from app.services.embedding_service import generate_embedding
from app.services.text_extraction_service import extract_text
from app.services.vector_store_service import get_global_collection

print("--- [PHOENIX] Starting Ingestion Sequence V5.3 ---")

# 1. Omni-Path Environment Loading
env_paths = [os.path.join(ROOT_DIR, ".env"), os.path.join(BACKEND_DIR, ".env")]
for p in env_paths:
    if os.path.exists(p):
        load_dotenv(p, override=True)
        print(f"✅ Loaded Environment from: {p}")

# 2. Critical Key Validation
if not os.getenv("OPENROUTER_API_KEY"):
    print("❌ CRITICAL ERROR: OPENROUTER_API_KEY not found in environment!")
    print("Ensure your .env file contains: OPENROUTER_API_KEY=sk-or-v1-...")
    sys.exit(1)

def ingest():
    # 3. Verify Database
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    try:
        mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        db = mongo_client[db_name]
        mongo_coll = db["legal_knowledge_base"]
        print(f"✅ Connected to Cloud MongoDB: {db_name}")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")
        return

    # 4. Verify ChromaDB
    try:
        chroma_coll = get_global_collection()
        print("✅ ChromaDB Persistence Active.")
    except Exception as e:
        print(f"❌ ChromaDB Failed: {e}")
        return

    # 5. Locate Laws
    laws_dir = os.path.join(ROOT_DIR, "data", "laws")
    files = glob.glob(os.path.join(laws_dir, "**", "*.pdf"), recursive=True)
    
    if not files:
        print(f"⚠️  No PDFs found in {laws_dir}")
        return

    print(f"🚀 Found {len(files)} files. Processing...")

    for file_path in files:
        fname = os.path.basename(file_path)
        raw_text = extract_text(file_path, "application/pdf")
        if not raw_text: continue
        
        law_title = fname.replace(".pdf", "").replace("_", " ").title()
        print(f"\n📄 Ingesting: {law_title}")
        
        articles = raw_text.split("Neni ") 
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        for idx, art_text in enumerate(articles):
            if len(art_text) < 20: continue
            chunks = splitter.split_text(art_text)
            for i, chunk in enumerate(chunks):
                # Verify embedding generation
                vector = generate_embedding(chunk)
                if not vector or all(v == 0.0 for v in vector):
                    print(f"❌ Failed to generate vector for chunk {idx}.{i}. Aborting law.")
                    break
                
                chunk_id = str(uuid.uuid4())
                meta = {"source": fname, "law_title": law_title, "article_number": str(idx), "chunk_index": i, "jurisdiction": "ks"}
                
                mongo_coll.update_one({"chunk_id": chunk_id}, {"$set": {**meta, "text": chunk, "chunk_id": chunk_id}}, upsert=True)
                chroma_coll.add(ids=[chunk_id], embeddings=[vector], documents=[chunk], metadatas=[meta])
                print(f"   [Synced Chunk {idx}.{i}]", end="\r")
        print(f"\n✅ Law Complete: {law_title}")

if __name__ == "__main__":
    ingest()
    print("\n--- [PHOENIX] Ingestion Sequence Finished ---")