# FILE: backend/scripts/master_clean_and_sync.py
# PHOENIX PROTOCOL - MASTER VECTOR SANITIZER V12.0 (WINDOWS CASE-INSENSITIVE 19-LAW DEDUPLICATION)

import os
import sys
import uuid
import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("master_sync")

CASE_NO_PATTERN = re.compile(
    r'((?:PML|Pml|Rev|REV|PA1|Pa1|A|CP|PKR|P|KMLP|Kmlp)\s*\.?\s*Nr\s*\.?\s*\d+\s*/\s*(?:20\d{2}|\d{2}))', 
    re.IGNORECASE
)

def clean_law_title_from_filename(filename: str) -> str:
    clean = filename.replace(".pdf", "").replace(".PDF", "").replace("_", " ").replace("-", " ")
    clean = re.sub(r'\(konsoliduar\)', '(Konsoliduar)', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.upper()

def extract_articles_from_pdf(filepath: str) -> list[dict]:
    doc = fitz.open(filepath)
    full_text_pages = [(page_idx + 1, doc[page_idx].get_text("text") or "") for page_idx in range(len(doc))]
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

def run_master_sanitization_and_sync():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    if not uri:
        logger.error("❌ DATABASE_URI is missing.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]

    print("\n" + "="*60)
    print("🧹 FAZA 1: PASTRIMI TOTAL I DITURISË GLOBALE")
    print("="*60)

    db.legal_knowledge_base.delete_many({})
    logger.info("✅ Koleksioni 'legal_knowledge_base' u pastrua 100% (0 mbeturina).")

    # =========================================================================
    # ⚖️ FAZA 2: INGESTIMI I 19 LIGJEVE UNIKË TË KOSOVËS
    # =========================================================================
    print("\n" + "="*60)
    print("⚖️ FAZA 2: INGESTIMI I 19 LIGJEVE UNIKË NGA data/laws/ks")
    print("="*60)

    laws_dir = ROOT_DIR / "data" / "laws" / "ks"
    if not laws_dir.exists():
        laws_dir = BACKEND_DIR / "data" / "laws" / "ks"

    # DEDUPLIKIM I PLOTË I SKEDARËVE NË WINDOWS
    seen_law_names = set()
    law_files = []
    for p in sorted(list(laws_dir.iterdir())):
        if p.is_file() and p.suffix.lower() == '.pdf':
            clean_name = p.name.lower().strip()
            if clean_name not in seen_law_names:
                seen_law_names.add(clean_name)
                law_files.append(p)

    logger.info(f"📁 U gjetën ekzaktësisht {len(law_files)} ligje zyrtare unike në {laws_dir}")

    total_articles = 0
    for idx_f, file_path in enumerate(law_files, 1):
        fname = file_path.name
        law_title = clean_law_title_from_filename(fname)
        
        parsed_articles = extract_articles_from_pdf(str(file_path))
        if not parsed_articles:
            continue

        texts_to_embed = [art["text"][:3500] for art in parsed_articles]
        batch_size = 50
        all_embeddings = []
        for b_idx in range(0, len(texts_to_embed), batch_size):
            batch_texts = texts_to_embed[b_idx:b_idx+batch_size]
            all_embeddings.extend(generate_embeddings_batch(batch_texts))

        docs_to_insert = []
        for idx, art in enumerate(parsed_articles):
            vector = all_embeddings[idx] if idx < len(all_embeddings) else []
            docs_to_insert.append({
                "chunk_id": str(uuid.uuid4()),
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
                "category": "statute"
            })

        if docs_to_insert:
            db.legal_knowledge_base.insert_many(docs_to_insert)
            total_articles += len(docs_to_insert)
            logger.info(f"   ✅ [{idx_f}/{len(law_files)}] {law_title}: {len(docs_to_insert)} nene.")

    # =========================================================================
    # 🏛️ FAZA 3: INGESTIMI I 700+ FAQEVE TË GJYKATËS SUPREME
    # =========================================================================
    print("\n" + "="*60)
    print("🏛️ FAZA 3: INGESTIMI I VENDIMEVE SUPREME NGA data/case_law")
    print("="*60)

    caselaw_dir = ROOT_DIR / "data" / "case_law"
    if not caselaw_dir.exists():
        caselaw_dir = BACKEND_DIR / "data" / "case_law"

    seen_case_names = set()
    caselaw_files = []
    for p in sorted(list(caselaw_dir.iterdir())):
        if p.is_file() and p.suffix.lower() == '.pdf':
            clean_name = p.name.lower().strip()
            if clean_name not in seen_case_names:
                seen_case_names.add(clean_name)
                caselaw_files.append(p)

    logger.info(f"📁 U gjetën ekzaktësisht {len(caselaw_files)} skedarë të Gjykatës Supreme")

    total_caselaw_chunks = 0
    for idx_c, file_path in enumerate(caselaw_files, 1):
        fname = file_path.name
        doc = fitz.open(str(file_path))
        raw_chunks = []
        current_case_no = "Gjykata Supreme e Kosovës"
        chunk_idx = 1

        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text("text") or ""
            if not page_text.strip(): continue

            matches = CASE_NO_PATTERN.findall(page_text)
            if matches:
                current_case_no = matches[0].strip().replace(" ", "")

            chunk_size = 1200
            overlap = 150
            start = 0
            while start < len(page_text):
                end = start + chunk_size
                chunk_str = page_text[start:end].strip()
                start += chunk_size - overlap
                if len(chunk_str) > 20:
                    raw_chunks.append({
                        "chunk_id": str(uuid.uuid4()),
                        "law_title": f"Gjykata Supreme e Kosovës - {current_case_no}",
                        "title": current_case_no,
                        "source": fname,
                        "case_number": current_case_no,
                        "page": page_num + 1,
                        "text": chunk_str,
                        "chunk_index": chunk_idx,
                        "is_case_law": True,
                        "is_article": False,
                        "category": "caselaw",
                        "jurisdiction": "ks"
                    })
                    chunk_idx += 1
        doc.close()

        if raw_chunks:
            texts_to_embed = [c["text"] for c in raw_chunks]
            all_embeddings = []
            for b_idx in range(0, len(texts_to_embed), 50):
                all_embeddings.extend(generate_embeddings_batch(texts_to_embed[b_idx:b_idx+50]))

            for idx, c_data in enumerate(raw_chunks):
                c_data["embedding"] = all_embeddings[idx] if idx < len(all_embeddings) else []

            db.legal_knowledge_base.insert_many(raw_chunks)
            total_caselaw_chunks += len(raw_chunks)
            logger.info(f"   ✅ [{idx_c}/{len(caselaw_files)}] {fname}: {len(raw_chunks)} pjesëza.")

    print("\n" + "="*60)
    print("🏁 RAPORTI PËRFUNDIMTAR I PASTRIMIT MASTER:")
    print(f"   • Ligje Zyrtare Unike: {len(law_files)} ligje ({total_articles} nene totale)")
    print(f"   • Vendime Supreme Unike: {len(caselaw_files)} skedarë ({total_caselaw_chunks} pjesëza)")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_master_sanitization_and_sync()