# FILE: backend/scripts/ingest_statutes.py
# PHOENIX PROTOCOL - STATUTORY LAW INGESTOR V8.0 (STRICT ARTICLE COUNT SKIP GUARD)

import os
import sys
import time
import uuid
import logging
import hashlib
import unicodedata
import re
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

for p in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
    if p.exists(): 
        load_dotenv(p, override=True)

sys.path.insert(0, str(BACKEND_DIR))

from pymongo import MongoClient
from app.services.embedding_service import generate_embedding
from app.services.text_extraction_service import extract_text
from app.services.albanian_language_detector import detect_document_language

print("--- [PHOENIX] Starting Statutory Law Ingester (Fast Skip) ---")


def calculate_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def clean_law_title(filename: str) -> str:
    clean = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
    return " ".join(word.capitalize() for word in unicodedata.normalize('NFC', clean).split())


def split_articles_strictly(raw_text: str) -> list[tuple[str, str, int]]:
    page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', raw_text)
    content_by_page = {}
    if len(page_splits) > 1:
        for i in range(1, len(page_splits), 2):
            content_by_page[int(page_splits[i])] = page_splits[i+1]
    else:
        content_by_page[1] = raw_text

    articles = []
    current_art_num = "0"
    current_art_lines = []
    current_page = 1

    header_regex = re.compile(r'^\s*(?:Neni|NENI|Artikulli)\s+(\d+[a-zA-Z]*)\b[^\n]*$', re.MULTILINE)

    for p_num in sorted(content_by_page.keys()):
        p_text = content_by_page[p_num]
        lines = p_text.split('\n')

        for line in lines:
            header_match = header_regex.match(line)
            if header_match and not line.strip().startswith('(') and not line.strip().endswith(')'):
                if current_art_lines:
                    full_art_text = "\n".join(current_art_lines).strip()
                    if len(full_art_text) > 15:
                        articles.append((current_art_num, full_art_text, current_page))
                
                current_art_num = header_match.group(1)
                current_art_lines = [line]
                current_page = p_num
            else:
                current_art_lines.append(line)

    if current_art_lines:
        full_art_text = "\n".join(current_art_lines).strip()
        if len(full_art_text) > 15:
            articles.append((current_art_num, full_art_text, current_page))

    if len(articles) <= 1 and len(raw_text) > 4000:
        articles = []
        chunks = [raw_text[i:i+2500] for i in range(0, len(raw_text), 2200)]
        for idx, ch in enumerate(chunks, 1):
            articles.append((str(idx), ch, 1))

    return articles


def ingest_statutes():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    if not uri:
        print("❌ DATABASE_URI is missing from environment variables.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    coll = db["legal_knowledge_base"]

    laws_dirs = [ROOT_DIR / "data" / "laws", BACKEND_DIR / "data" / "laws"]
    
    all_files = []
    for ldir in laws_dirs:
        if ldir.exists():
            all_files.extend(list(ldir.rglob("*.pdf")))

    seen = set()
    files = []
    for f in all_files:
        if f.name not in seen and not any(kw in f.name.upper() for kw in ["AKADEMIA", "KOMMENTAR", "DORACAK"]):
            seen.add(f.name)
            files.append(f)

    if not files:
        print(f"⚠️ No Statutory Law PDFs found.")
        return

    print(f"🚀 Scanning {len(files)} files...")
    stats = {"skipped": 0, "added": 0, "failed": 0}

    for file_path in files:
        fname = file_path.name
        law_title = clean_law_title(fname)
        current_hash = calculate_file_hash(str(file_path))
        
        # 🛡️ PURE ARTICLE COUNT SKIP: If law has more than 5 articles in DB, skip in 0.001s
        existing_articles_count = coll.count_documents({"source": fname})
        
        if existing_articles_count > 5:
            print(f"⏭️  Skipped (Already Synced - {existing_articles_count} articles): {fname}")
            stats["skipped"] += 1
            continue

        print(f"\n⚖️ Ingesting Only Incomplete/New Law: {fname}")
        coll.delete_many({"source": fname})
        
        raw_text = extract_text(str(file_path), "application/pdf")
        if not raw_text or len(raw_text.strip()) < 50:
            print(f"   ⚠️ Extraction empty or too short. Skipping.")
            stats["failed"] += 1
            continue

        lang = detect_document_language(raw_text)
        parsed_articles = split_articles_strictly(raw_text)

        docs_to_insert = []
        for idx, (art_num, art_text, p_num) in enumerate(parsed_articles):
            clamped_text = art_text[:4000].strip()
            vector = generate_embedding(clamped_text)
            chunk_id = str(uuid.uuid4())
            docs_to_insert.append({
                "chunk_id": chunk_id,
                "embedding": vector if vector else [],
                "text": clamped_text,
                "source": fname,
                "law_title": law_title,
                "article_number": art_num,
                "chunk_index": idx,
                "page": p_num,
                "language": lang,
                "jurisdiction": "ks",
                "is_article": True,
                "file_hash": current_hash,
                "processor_version": "V8.0-STATUTE"
            })

        if docs_to_insert:
            coll.insert_many(docs_to_insert)
            print(f"✅ Finished Law: {law_title} ({len(docs_to_insert)} articles indexed)")
            stats["added"] += 1

    print("\n" + "="*40)
    print(f"🏁 Statutes Ingestion Report:")
    print(f"   Added/Updated: {stats['added']}")
    print(f"   Skipped:       {stats['skipped']}")
    print(f"   Failed:        {stats['failed']}")
    print("="*40)


if __name__ == "__main__":
    ingest_statutes()