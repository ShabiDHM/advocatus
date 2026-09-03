# FILE: backend/scripts/master_clean_and_sync.py
# PHOENIX PROTOCOL - ROBUST 1,425-PAGE SUPREME COURT INGESTOR V20.0

import os
import sys
import uuid
import logging
import hashlib
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
    r'((?:ARJ|PML|Pml|Rev|REV|PA1|Pa1|A|CP|PKR|P|KMLP|Kmlp|KA|CN)\s*\.?\s*Nr\s*\.?\s*\d+\s*/\s*(?:20\d{2}|\d{2})|'
    r'(?:Mendim\s+Juridik|Qëndrim\s+Parimor|Qendrim\s+Parimor|Mendimi\s+Juridik)\s*(?:-\s*)?(?:Nr\.?\s*)?\d+\s*/\s*(?:20\d{2}|\d{2}))', 
    re.IGNORECASE
)

CASE_HEADER_START_REGEX = re.compile(
    r'(?:Aktgjykim(?:i)?|Aktvendim(?:i)?|Kolegj(?:i)?|Mendim\s+Juridik|Qëndrim\s+Parimor|Qendrim\s+Parimor)\s+'
    r'(?:i\s+kolegjit\s+)?(?:penal|civil|administrativ|tregtar|të\s+përgjithshëm)?\s*(?:të\s+Gjykatës\s+Supreme)?',
    re.IGNORECASE
)

def calculate_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

def clean_law_title_from_filename(filename: str) -> str:
    clean = filename.replace(".pdf.pdf", "").replace(".pd.pdf", "").replace("..pdf", "").replace(".pdf", "").replace(".PDF", "").replace("_", " ").replace("-", " ")
    clean = re.sub(r'^\d+_\d*\.?\s*', '', clean)
    clean = re.sub(r'\s+pdf$', '', clean, flags=re.IGNORECASE)
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

def run_master_sync():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    if not uri:
        logger.error("❌ DATABASE_URI is missing.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    coll = db["legal_knowledge_base"]

    args = sys.argv[1:]
    force_clean_all = "--clean" in args
    sync_only_caselaw = "--caselaw" in args
    sync_only_statutes = "--statutes" in args
    sync_only_academic = "--academic" in args

    sync_all = not (sync_only_caselaw or sync_only_statutes or sync_only_academic)

    if force_clean_all:
        print("\n" + "="*60)
        print("🧹 PASTRIMI TOTAL I DITURISË GLOBALE NGA MONGODB")
        print("="*60)
        coll.delete_many({})
        logger.info("✅ Koleksioni 'legal_knowledge_base' u pastrua në 0 mbeturina.")

    stats = {"laws_new": 0, "laws_skipped": 0, "caselaw_new": 0, "caselaw_skipped": 0, "acad_new": 0, "acad_skipped": 0}

    # 1. LIGJET STATUTORE
    if sync_all or sync_only_statutes:
        print("\n" + "="*60)
        print("⚖️ KONTROLLI I LIGJEVE STATUTORE (data/laws/ks)")
        print("="*60)
        if sync_only_statutes:
            coll.delete_many({"category": "statute"})

        laws_dir = ROOT_DIR / "data" / "laws" / "ks"
        if not laws_dir.exists(): laws_dir = BACKEND_DIR / "data" / "laws" / "ks"

        law_files = []
        if laws_dir.exists():
            for p in sorted(list(laws_dir.iterdir())):
                if p.is_file():
                    law_files.append(p)

        for file_path in law_files:
            fname = file_path.name
            fhash = calculate_file_hash(str(file_path))
            law_title = clean_law_title_from_filename(fname)

            existing_count = coll.count_documents({"source": fname, "file_hash": fhash})
            if existing_count > 5 and not (force_clean_all or sync_only_statutes):
                logger.info(f"⏭️  [Synced - {existing_count} nene]: {fname}")
                stats["laws_skipped"] += 1
                continue

            logger.info(f"🔄 Duke procesuar ligjin: {fname}...")
            coll.delete_many({"source": fname})

            parsed_articles = extract_articles_from_pdf(str(file_path))
            if not parsed_articles: continue

            texts_to_embed = [art["text"][:3500] for art in parsed_articles]
            all_embeddings = []
            for b_idx in range(0, len(texts_to_embed), 50):
                all_embeddings.extend(generate_embeddings_batch(texts_to_embed[b_idx:b_idx+50]))

            docs_to_insert = []
            for idx, art in enumerate(parsed_articles):
                vector = all_embeddings[idx] if idx < len(all_embeddings) else []
                docs_to_insert.append({
                    "chunk_id": str(uuid.uuid4()),
                    "embedding": vector if vector else [],
                    "text": art["text"],
                    "source": fname,
                    "file_hash": fhash,
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
                coll.insert_many(docs_to_insert)
                logger.info(f"   ✅ [U ruajtën {len(docs_to_insert)} nene]: {law_title}")
                stats["laws_new"] += 1

    # 2. VENDIMET DHE MENDIMET PARIMORE TË GJYKATËS SUPREME (1,425 FAQE)
    if sync_all or sync_only_caselaw:
        print("\n" + "="*60)
        print("🏛️ KONTROLLI I GJYKATËS SUPREME (data/case_law)")
        print("="*60)
        if sync_only_caselaw:
            coll.delete_many({"category": "caselaw"})

        caselaw_dir = ROOT_DIR / "data" / "case_law"
        if not caselaw_dir.exists(): caselaw_dir = BACKEND_DIR / "data" / "case_law"

        caselaw_files = []
        if caselaw_dir.exists():
            for p in sorted(list(caselaw_dir.iterdir())):
                if p.is_file():
                    caselaw_files.append(p)

        print(f"📂 Duke përpunuar {len(caselaw_files)} skedarë të Gjykatës Supreme:")
        for cf in caselaw_files:
            print(f"   👉 {cf.name}")

        for file_path in caselaw_files:
            fname = file_path.name
            fhash = calculate_file_hash(str(file_path))
            default_doc_title = clean_law_title_from_filename(fname)

            logger.info(f"🔄 Duke procesuar: {fname}...")
            coll.delete_many({"source": fname})

            try:
                doc = fitz.open(str(file_path))
            except Exception as e:
                logger.warning(f"❌ Dështoi hapja e {fname}: {e}")
                continue

            raw_chunks = []
            current_case_no = default_doc_title
            case_start_page = 1
            chunk_idx = 1

            for page_num in range(len(doc)):
                page_text = doc[page_num].get_text("text") or ""
                if not page_text.strip(): continue

                is_new_header = bool(CASE_HEADER_START_REGEX.search(page_text))
                matches = CASE_NO_PATTERN.findall(page_text)
                
                if is_new_header or matches:
                    if matches:
                        current_case_no = matches[0].strip().replace("  ", " ")
                    case_start_page = page_num + 1

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
                            "law_title": f"Gjykata Supreme - {current_case_no}",
                            "title": current_case_no,
                            "source": fname,
                            "file_hash": fhash,
                            "case_number": current_case_no,
                            "page": case_start_page,
                            "actual_page": page_num + 1,
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

                coll.insert_many(raw_chunks)
                logger.info(f"   ✅ [U ruajtën {len(raw_chunks)} pjesëza me embeddings]: {fname}")
                stats["caselaw_new"] += 1

    # 3. AKADEMIA E DREJTËSISË
    if sync_all or sync_only_academic:
        print("\n" + "="*60)
        print("📚 KONTROLLI I AKADEMISË SË DREJTËSISË (data/academic)")
        print("="*60)
        if sync_only_academic:
            coll.delete_many({"category": "academic"})

        academic_dir = ROOT_DIR / "data" / "academic"
        if not academic_dir.exists(): academic_dir = BACKEND_DIR / "data" / "academic"

        academic_files = []
        if academic_dir.exists():
            for p in sorted(list(academic_dir.iterdir())):
                if p.is_file():
                    academic_files.append(p)

        for file_path in academic_files:
            fname = file_path.name
            fhash = calculate_file_hash(str(file_path))
            doc_title = clean_law_title_from_filename(fname)

            logger.info(f"🔄 Duke procesuar materialin e Akademisë: {fname}...")
            coll.delete_many({"source": fname})

            try:
                doc = fitz.open(str(file_path))
            except Exception as e:
                logger.warning(f"❌ Dështoi hapja e {fname}: {e}")
                continue

            raw_chunks = []
            chunk_idx = 1

            for page_num in range(len(doc)):
                page_text = doc[page_num].get_text("text") or ""
                if not page_text.strip(): continue

                chunk_size = 1400
                overlap = 150
                start = 0
                while start < len(page_text):
                    end = start + chunk_size
                    chunk_str = page_text[start:end].strip()
                    start += chunk_size - overlap
                    if len(chunk_str) > 20:
                        raw_chunks.append({
                            "chunk_id": str(uuid.uuid4()),
                            "law_title": f"Akademia e Drejtësisë - {doc_title}",
                            "title": doc_title,
                            "source": fname,
                            "file_hash": fhash,
                            "page": page_num + 1,
                            "text": chunk_str,
                            "chunk_index": chunk_idx,
                            "is_academic": True,
                            "is_case_law": False,
                            "is_article": False,
                            "category": "academic",
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

                coll.insert_many(raw_chunks)
                logger.info(f"   ✅ [U ruajtën {len(raw_chunks)} pjesëza]: {fname}")
                stats["acad_new"] += 1

    print("\n" + "="*60)
    print("🏁 SINKRONIZIMI PËRFUNDOI ME SUKSES:")
    print(f"   • Ligje:      {stats['laws_new']} të reja")
    print(f"   • Gj.Supreme: {stats['caselaw_new']} skedarë të përpunuar ({len(caselaw_files)} total)")
    print(f"   • Akademia:   {stats['acad_new']} të reja")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_master_sync()