# FILE: backend/scripts/ingest_academy.py
# PHOENIX PROTOCOL - ACADEMY INGESTOR V2.0 (SMART SKIP IDEMPOTENCY)

import os, sys, time, uuid, logging, hashlib, unicodedata, re
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

for p in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
    if p.exists(): load_dotenv(p, override=True)

sys.path.append(str(BACKEND_DIR))

from pymongo import MongoClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.embedding_service import generate_embedding
from app.services.text_extraction_service import extract_text
from app.services.albanian_language_detector import detect_document_language

print("--- [PHOENIX] Starting Academy Commentary Ingester (Smart Skip) ---")

def calculate_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return ""

def clean_title(filename: str) -> str:
    clean = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
    return " ".join(word.capitalize() for word in unicodedata.normalize('NFC', clean).split())

def ingest_academy():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    coll = db["legal_knowledge_base"]

    laws_dir = ROOT_DIR / "data" / "laws"
    all_files = list(laws_dir.rglob("*.pdf"))
    
    # INCLUDE ONLY ACADEMY / COMMENTARY FILES
    files = [
        f for f in all_files 
        if any(keyword in f.name.upper() for keyword in ["AKADEMIA", "KOMMENTAR", "DORACAK"])
    ]

    if not files:
        print(f"⚠️ No Academy PDFs found.")
        return

    print(f"🚀 Scanning {len(files)} Academy/Commentary files...")

    stats = {"skipped": 0, "added": 0, "failed": 0}
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200, separators=["\n\n", "\n", ". ", " "])

    for file_path in files:
        fname = file_path.name
        current_hash = calculate_file_hash(str(file_path))
        
        # IDEMPOTENCY CHECK
        existing = coll.find_one({"source": fname, "file_hash": current_hash})
        if existing:
            print(f"⏭️  Skipped (Already Synced): {fname}")
            stats["skipped"] += 1
            continue

        print(f"\n📚 Processing New/Modified Academy Manual: {fname}")
        
        # Wipe old chunks
        coll.delete_many({"source": fname})
        
        raw_text = extract_text(str(file_path), "application/pdf")
        if not raw_text or len(raw_text.strip()) < 50: continue

        title = clean_title(fname)
        lang = detect_document_language(raw_text)

        page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', raw_text)
        content_by_page = {int(page_splits[i]): page_splits[i+1] for i in range(1, len(page_splits), 2)}
        if not content_by_page: content_by_page[1] = raw_text

        global_idx = 0
        for page_num, page_text in content_by_page.items():
            if not page_text.strip(): continue
            chunks = splitter.split_text(page_text)

            for chunk_content in chunks:
                if not chunk_content.strip(): continue

                time.sleep(0.3)
                vector = generate_embedding(chunk_content)
                if not vector: continue

                chunk_id = str(uuid.uuid4())
                coll.update_one(
                    {"chunk_id": chunk_id},
                    {"$set": {
                        "chunk_id": chunk_id, "embedding": vector, "text": chunk_content,
                        "source": fname, "law_title": title, "article_number": f"Pjesa {global_idx + 1}",
                        "chunk_index": global_idx, "page": page_num, "language": lang,
                        "jurisdiction": "ks", "is_article": False, "file_hash": current_hash,
                        "processor_version": "V2.0-ACADEMY"
                    }},
                    upsert=True
                )
                global_idx += 1
                print(f"   [Indexed Section Pjesa {global_idx}]", end="\r")

        print(f"\n✅ Finished Academy Manual: {title} ({global_idx} sections)")
        stats["added"] += 1

    print("\n" + "="*40)
    print(f"🏁 Academy Ingestion Report:")
    print(f"   Added/Updated: {stats['added']}")
    print(f"   Skipped:       {stats['skipped']}")
    print(f"   Failed:        {stats['failed']}")
    print("="*40)

if __name__ == "__main__":
    ingest_academy()