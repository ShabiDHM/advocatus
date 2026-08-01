# FILE: backend/scripts/ingest_statutes.py
# PHOENIX PROTOCOL - STRICT STATUTORY LAW INGESTOR V2.0 (SMART SKIP IDEMPOTENCY)

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
from app.services.embedding_service import generate_embedding
from app.services.text_extraction_service import extract_text
from app.services.albanian_language_detector import detect_document_language

print("--- [PHOENIX] Starting Statutory Law Ingester (Smart Skip) ---")

def calculate_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return ""

def clean_law_title(filename: str) -> str:
    clean = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
    return " ".join(word.capitalize() for word in unicodedata.normalize('NFC', clean).split())

def ingest_statutes():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    coll = db["legal_knowledge_base"]

    laws_dir = ROOT_DIR / "data" / "laws"
    all_files = list(laws_dir.rglob("*.pdf"))
    
    # EXCLUDE ACADEMY FILES FROM STATUTES
    files = [
        f for f in all_files 
        if not any(keyword in f.name.upper() for keyword in ["AKADEMIA", "KOMMENTAR", "DORACAK"])
    ]

    if not files:
        print(f"⚠️ No Statutory Law PDFs found.")
        return

    print(f"🚀 Scanning {len(files)} Statutory Law files...")

    stats = {"skipped": 0, "added": 0, "failed": 0}

    for file_path in files:
        fname = file_path.name
        current_hash = calculate_file_hash(str(file_path))
        
        # IDEMPOTENCY CHECK: Skip if file & hash already exist in database
        existing = coll.find_one({"source": fname, "file_hash": current_hash})
        if existing:
            print(f"⏭️  Skipped (Already Synced): {fname}")
            stats["skipped"] += 1
            continue

        print(f"\n⚖️ Processing New/Modified Law: {fname}")
        
        # Wipe old chunks for this file
        coll.delete_many({"source": fname})
        
        raw_text = extract_text(str(file_path), "application/pdf")
        if not raw_text or len(raw_text.strip()) < 50:
            print(f"   ⚠️ Extraction empty or too short. Skipping.")
            stats["failed"] += 1
            continue

        law_title = clean_law_title(fname)
        lang = detect_document_language(raw_text)

        article_pattern = re.compile(r'(?m)^(?=Neni\s+\d+|NENI\s+\d+|Artikulli\s+\d+)', re.IGNORECASE)
        page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', raw_text)
        content_by_page = {int(page_splits[i]): page_splits[i+1] for i in range(1, len(page_splits), 2)}
        if not content_by_page: content_by_page[1] = raw_text

        global_idx = 0
        for page_num, page_text in content_by_page.items():
            if not page_text.strip(): continue
            raw_articles = article_pattern.split(page_text)

            for art_content in raw_articles:
                cleaned_art = art_content.strip()
                if len(cleaned_art) < 15: continue

                match = re.search(r'^(?:Neni|NENI|Artikulli)\s+(\d+[a-zA-Z]*)', cleaned_art, re.IGNORECASE)
                art_num = match.group(1) if match else ('0' if global_idx == 0 and ('Kuvendi' in cleaned_art or 'Miraton' in cleaned_art) else None)
                
                if not art_num: continue

                time.sleep(0.4)
                vector = generate_embedding(cleaned_art)
                if not vector: continue

                chunk_id = str(uuid.uuid4())
                coll.update_one(
                    {"chunk_id": chunk_id},
                    {"$set": {
                        "chunk_id": chunk_id, "embedding": vector, "text": cleaned_art,
                        "source": fname, "law_title": law_title, "article_number": art_num,
                        "chunk_index": global_idx, "page": page_num, "language": lang,
                        "jurisdiction": "ks", "is_article": True, "file_hash": current_hash,
                        "processor_version": "V2.0-STATUTE"
                    }},
                    upsert=True
                )
                global_idx += 1
                print(f"   [Indexed Article {art_num}]", end="\r")

        print(f"\n✅ Finished Law: {law_title} ({global_idx} articles)")
        stats["added"] += 1

    print("\n" + "="*40)
    print(f"🏁 Statutes Ingestion Report:")
    print(f"   Added/Updated: {stats['added']}")
    print(f"   Skipped:       {stats['skipped']}")
    print(f"   Failed:        {stats['failed']}")
    print("="*40)

if __name__ == "__main__":
    ingest_statutes()