# FILE: backend/scripts/ingest_statutes.py
# PHOENIX PROTOCOL - EXACT DIRECTORY INGESTOR V11.0 (DATA/LAWS/KS CANONICAL INGESTION)

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

import fitz  # PyMuPDF
from pymongo import MongoClient
from app.services.embedding_service import generate_embeddings_batch

print("--- [PHOENIX] Starting 19-Law Canonical Ingestor from data/laws/ks ---")


def clean_law_title_from_filename(filename: str) -> str:
    """Konverton emrin e skedarit në Titull Zyrtar të Pastër."""
    clean = filename.replace(".pdf", "").replace(".PDF", "").replace("_", " ").replace("-", " ")
    clean = re.sub(r'\(konsoliduar\)', '(Konsoliduar)', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.upper()


def extract_all_articles_from_pdf(filepath: str) -> list[dict]:
    doc = fitz.open(filepath)
    full_text_pages = []
    
    for page_idx in range(len(doc)):
        page_text = doc[page_idx].get_text("text")
        full_text_pages.append((page_idx + 1, page_text))
    doc.close()

    combined_lines = []
    for page_num, text in full_text_pages:
        for line in text.split("\n"):
            combined_lines.append((page_num, line))

    articles = []
    current_art_num = "0"
    current_art_title = ""
    current_lines = []
    current_page = 1

    article_header_regex = re.compile(r'^\s*(?:Neni|NENI|Artikulli|ARTIKULLI)\s+(\d+[a-zA-Z]?)\.?\s*(.*)$')

    for page_num, line in combined_lines:
        stripped = line.strip()
        match = article_header_regex.match(stripped)

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


def ingest_19_laws():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    if not uri:
        print("❌ DATABASE_URI is missing from environment variables.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    coll = db["legal_knowledge_base"]

    # Targetojmë EKZAKTSISHT folderin data/laws/ks
    target_dir = ROOT_DIR / "data" / "laws" / "ks"
    if not target_dir.exists():
        target_dir = BACKEND_DIR / "data" / "laws" / "ks"

    if not target_dir.exists():
        print(f"❌ Folderi data/laws/ks nuk u gjet në {target_dir}")
        return

    files = sorted(list(target_dir.glob("*.pdf")) + list(target_dir.glob("*.PDF")))
    if not files:
        print(f"⚠️ Nuk u gjet asnjë skedar PDF në {target_dir}")
        return

    print(f"📁 U gjetën ekzaktësisht {len(files)} skedarë ligjesh në: {target_dir}")

    # 1. PASTRIMI TOTAL I NENEVE TË VJETRA STATUTORE NGA MONGODB
    print("🧹 Duke fshirë të gjitha nenet e vjetra statutore nga MongoDB...")
    deleted_old = coll.delete_many({
        "$or": [
            {"is_article": True},
            {"category": "statute"}
        ]
    })
    print(f"   🗑️ U fshinë {deleted_old.deleted_count} rekorde të vjetra me sukses.\n")

    stats = {"processed": 0, "articles_total": 0, "failed": 0}

    for file_path in files:
        fname = file_path.name
        law_title = clean_law_title_from_filename(fname)

        print(f"⚖️ Duke procesuar [{stats['processed']+1}/{len(files)}]: {law_title}")

        parsed_articles = extract_all_articles_from_pdf(str(file_path))
        if not parsed_articles:
            print(f"   ⚠️ Nuk u nxorën nene nga {fname}. Skipping.")
            stats["failed"] += 1
            continue

        print(f"   📄 U nxorën {len(parsed_articles)} nene. Duke gjeneruar vektorët me batch...")

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
                "is_case_law": False,
                "category": "statute",
                "processor_version": "V11.0-CANONICAL-KS"
            })

        if docs_to_insert:
            coll.insert_many(docs_to_insert)
            print(f"   ✅ U indeksuan të gjitha {len(docs_to_insert)} nenet për: {law_title}\n")
            stats["processed"] += 1
            stats["articles_total"] += len(docs_to_insert)

    print("="*50)
    print(f"🏁 Përfundoi Ingestion-i i Pastër i 19 Ligjeve të Kosovës:")
    print(f"   Ligje të Plotësuara: {stats['processed']}/{len(files)}")
    print(f"   Nene Gjithsej:       {stats['articles_total']}")
    print("="*50)


if __name__ == "__main__":
    ingest_19_laws()