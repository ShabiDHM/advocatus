# FILE: backend/scripts/ingest_statutes.py
# PHOENIX PROTOCOL - STATUTORY LAW INGESTOR V9.0 (COMPLETE 435-ARTICLE EXHAUSTIVE INGESTION)

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

import fitz  # PyMuPDF për lexim të garantuar faqe për faqe
from pymongo import MongoClient
from app.services.embedding_service import generate_embeddings_batch

print("--- [PHOENIX] Starting Exhaustive Statutory Law Ingestor V9.0 ---")


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


def extract_all_articles_from_pdf(filepath: str) -> list[dict]:
    """
    Lexon të gjithë PDF-në faqe për faqe dhe nxjerr çdo nen nga Neni 1 deri te neni i fundit.
    """
    doc = fitz.open(filepath)
    full_text_pages = []
    
    for page_idx in range(len(doc)):
        page_text = doc[page_idx].get_text("text")
        full_text_pages.append((page_idx + 1, page_text))
    doc.close()

    # Bashkojmë tekstin duke ruajtur shënuesit e faqeve
    combined_lines = []
    for page_num, text in full_text_pages:
        for line in text.split("\n"):
            combined_lines.append((page_num, line))

    articles = []
    current_art_num = "0"
    current_art_title = ""
    current_lines = []
    current_page = 1

    # Regex i fuqishëm për të kapur çdo variant të "Neni 1", "Neni 390.", "NENI 424"
    article_header_regex = re.compile(r'^\s*(?:Neni|NENI|Artikulli|ARTIKULLI)\s+(\d+[a-zA-Z]?)\.?\s*(.*)$')

    for page_num, line in combined_lines:
        stripped = line.strip()
        match = article_header_regex.match(stripped)

        # Kontrollojmë që nuk është thjesht një referencë në mes të fjalisë
        if match and not stripped.startswith("(") and not stripped.endswith(")"):
            if current_lines:
                full_content = "\n".join(current_lines).strip()
                if len(full_content) > 15:
                    articles.append({
                        "article_number": current_art_num,
                        "title": current_art_title or f"Neni {current_art_num}",
                        "text": full_content,
                        "page": current_page
                    })

            current_art_num = match.group(1)
            current_art_title = match.group(2).strip()
            current_lines = [stripped]
            current_page = page_num
        else:
            current_lines.append(line)

    if current_lines:
        full_content = "\n".join(current_lines).strip()
        if len(full_content) > 15:
            articles.append({
                "article_number": current_art_num,
                "title": current_art_title or f"Neni {current_art_num}",
                "text": full_content,
                "page": current_page
            })

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
        print(f"⚠️ No Statutory Law PDFs found in data/laws.")
        return

    print(f"🚀 Found {len(files)} Statutory Law files. Starting complete ingestion...")
    stats = {"processed": 0, "articles_total": 0, "failed": 0}

    for file_path in files:
        fname = file_path.name
        law_title = clean_law_title(fname)
        current_hash = calculate_file_hash(str(file_path))

        print(f"\n⚖️ Parsing Law: {fname} ({law_title})...")
        
        parsed_articles = extract_all_articles_from_pdf(str(file_path))
        if not parsed_articles:
            print(f"   ⚠️ Could not extract articles from {fname}. Skipping.")
            stats["failed"] += 1
            continue

        print(f"   📄 Extracted {len(parsed_articles)} articles. Generating embeddings in batches...")

        # Pastrojmë versionet e vjetra jo të plota të këtij ligji
        coll.delete_many({"source": fname})

        # Gjenerimi i vektorëve me batch
        texts_to_embed = [art["text"][:3500] for art in parsed_articles]
        
        batch_size = 50
        all_embeddings = []
        for b_idx in range(0, len(texts_to_embed), batch_size):
            batch_texts = texts_to_embed[b_idx:b_idx+batch_size]
            batch_vectors = generate_embeddings_batch(batch_texts)
            all_embeddings.extend(batch_vectors)

        docs_to_insert = []
        for idx, art in enumerate(parsed_articles):
            vector = all_embeddings[idx] if idx < len(all_embeddings) else []
            chunk_id = str(uuid.uuid4())
            
            docs_to_insert.append({
                "chunk_id": chunk_id,
                "embedding": vector if vector else [],
                "text": art["text"],
                "source": fname,
                "law_title": law_title,
                "title": art["title"],
                "article_number": str(art["article_number"]),
                "chunk_index": idx,
                "page": art["page"],
                "jurisdiction": "ks",
                "is_article": True,
                "file_hash": current_hash,
                "processor_version": "V9.0-EXHAUSTIVE"
            })

        if docs_to_insert:
            coll.insert_many(docs_to_insert)
            print(f"   ✅ Successfully indexed ALL {len(docs_to_insert)} articles for: {law_title}")
            stats["processed"] += 1
            stats["articles_total"] += len(docs_to_insert)

    print("\n" + "="*50)
    print(f"🏁 Complete Statutory Ingestion Finished:")
    print(f"   Laws Fully Ingested:   {stats['processed']}")
    print(f"   Total Articles Stored: {stats['articles_total']}")
    print(f"   Failed Files:          {stats['failed']}")
    print("="*50)


if __name__ == "__main__":
    ingest_statutes()