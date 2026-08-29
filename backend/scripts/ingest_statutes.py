# FILE: backend/scripts/ingest_statutes.py
# PHOENIX PROTOCOL - STATUTORY INGESTOR V10.1 (CLEAN SYNTAX & ZERO-DUPLICATE DEDUPLICATION)

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

print("--- [PHOENIX] Starting Clean Deduplicated Statutory Law Ingestor V10.1 ---")


def clean_canonical_law_title(filename: str) -> str:
    """Standardizon emrin e ligjit duke hequr prapashtesat si (konsoliduar), .pdf, etj."""
    clean = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
    clean = re.sub(r'\(konsoliduar\)', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return " ".join(word.capitalize() for word in unicodedata.normalize('NFC', clean).split())


def get_law_canonical_id(filename: str) -> str:
    """Nxjerr numrin e ligjit (p.sh. 06/L-074) për të parandaluar ngarkimin e dyfishtë."""
    match = re.search(r'(\d+[\/_]L[\-_]\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace("_", "-").replace("/", "-")
    clean = re.sub(r'[^a-zA-Z0-9]', '', filename.lower())
    return clean[:20]


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


def ingest_statutes_clean():
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

    # Deduplikimi: Mbajmë vetëm 1 skedar për çdo ligj kanonik
    canonical_files_map = {}
    for f in all_files:
        if any(kw in f.name.upper() for kw in ["AKADEMIA", "KOMMENTAR", "DORACAK"]):
            continue
        
        cid = get_law_canonical_id(f.name)
        if cid not in canonical_files_map:
            canonical_files_map[cid] = f
        else:
            if "konsoliduar" in f.name.lower() and "konsoliduar" not in canonical_files_map[cid].name.lower():
                canonical_files_map[cid] = f

    unique_files = list(canonical_files_map.values())

    if not unique_files:
        print("⚠️ No Statutory Law PDFs found in data/laws.")
        return

    print("🧹 PASTRIMI I MBETURINAVE: Duke fshirë nenet e dyfishuara nga MongoDB...")
    deleted_old = coll.delete_many({
        "$or": [
            {"is_article": True},
            {"category": "statute"}
        ]
    })
    print(f"   🗑️ U fshinë {deleted_old.deleted_count} rekorde të vjetra me sukses.")

    print(f"\n🚀 Duke procesuar {len(unique_files)} Ligje Kanonike pa asnjë duplikatë...")
    stats = {"processed": 0, "articles_total": 0, "failed": 0}

    for file_path in unique_files:
        fname = file_path.name
        law_title = clean_canonical_law_title(fname)

        print(f"\n⚖️ Parsing Law: {law_title} (Skedari: {fname})...")
        
        parsed_articles = extract_all_articles_from_pdf(str(file_path))
        if not parsed_articles:
            print(f"   ⚠️ Could not extract articles from {fname}. Skipping.")
            stats["failed"] += 1
            continue

        print(f"   📄 Extracted {len(parsed_articles)} articles. Generating embeddings in batches...")

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
                "processor_version": "V10.1-DEDUPLICATED"
            })

        if docs_to_insert:
            coll.insert_many(docs_to_insert)
            print(f"   ✅ Indexed ALL {len(docs_to_insert)} unique articles for: {law_title}")
            stats["processed"] += 1
            stats["articles_total"] += len(docs_to_insert)

    print("\n" + "="*50)
    print("🏁 Clean Ingestion Finished (Zero Duplicates):")
    print(f"   Canonical Laws Ingested: {stats['processed']}")
    print(f"   Unique Articles Stored:  {stats['articles_total']}")
    print(f"   Failed Files:            {stats['failed']}")
    print("="*50)


if __name__ == "__main__":
    ingest_statutes_clean()