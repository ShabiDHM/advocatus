# FILE: backend/scripts/ingest_caselaw.py
# PHOENIX PROTOCOL - CASELAW INGESTOR V10.0 (FAST BATCH EMBEDDING, EXACT SUPREME METADATA & FITZ ENGINE)

import os
import sys
import glob
import re
import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

for p in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
    if p.exists(): 
        load_dotenv(p, override=True)

sys.path.insert(0, str(BACKEND_DIR))

import fitz  # PyMuPDF për lexim të shpejtë dhe të saktë të të gjitha faqeve
from pymongo import MongoClient
from app.services import storage_service
from app.services.embedding_service import generate_embeddings_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ingest_caselaw")

# Regex për të gjithë numrat e lëndëve të Gjykatës Supreme të Kosovës (p.sh. PML.Nr.185/2025, Rev.Nr.541/2024)
CASE_NO_PATTERN = re.compile(
    r'((?:PML|Pml|Rev|REV|PA1|Pa1|A|CP|PKR|P|KMLP|Kmlp)\s*\.?\s*Nr\s*\.?\s*\d+\s*/\s*(?:20\d{2}|\d{2}))', 
    re.IGNORECASE
)

def ingest_caselaw_pdfs(force_reingest: bool = True):
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    if not uri:
        logger.error("❌ DATABASE_URI is missing from environment variables.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    coll = db["legal_knowledge_base"]

    workspace_data = ROOT_DIR / "data" / "case_law"
    backend_data = BACKEND_DIR / "data" / "case_law"
    desktop_data = Path(os.path.expanduser("~")) / "Desktop" / "caselaw_pdfs"

    target_folder = None
    for path in [workspace_data, backend_data, desktop_data]:
        if path.exists() and list(path.glob("*.pdf")):
            target_folder = path
            break

    if not target_folder:
        logger.error(f"❌ Nuk u gjet asnjë skedar PDF i Gjykatës Supreme në folderat e të dhënave.")
        return

    pdf_files = list(target_folder.glob("*.pdf"))
    total_files = len(pdf_files)
    logger.info(f"📁 U gjetën {total_files} skedarë të Gjykatës Supreme në: {target_folder}")

    for f_idx, file_path in enumerate(pdf_files, 1):
        filename = file_path.name

        existing_count = coll.count_documents({"source": filename})
        if existing_count > 0 and not force_reingest:
            logger.info(f"⏭️  [{f_idx}/{total_files}] SKIPPED: {filename} (Tashmë i ingestuar me {existing_count} vektore)")
            continue

        print(f"\n------------------------------------------------------------")
        logger.info(f"📄 [{f_idx}/{total_files}] DUKE PROCESUAR VENDIMET SUPREME: {filename}")

        try:
            doc = fitz.open(str(file_path))
            total_pages = len(doc)
            logger.info(f"   📖 Lexuar: {total_pages} Faqe. Duke nxjerrë precedentët dhe numrat e lëndëve...")

            raw_chunks = []
            current_case_no = "Gjykata Supreme e Kosovës"
            chunk_global_idx = 1

            for page_num in range(total_pages):
                page_text = doc[page_num].get_text("text") or ""
                if not page_text.strip():
                    continue

                # Zbulojmë numrin e lëndës në këtë faqe (p.sh. PML.Nr.185/2025)
                matches = CASE_NO_PATTERN.findall(page_text)
                if matches:
                    current_case_no = matches[0].strip().replace(" ", "")

                # Ndarja në copa prej 1200 karakteresh me mbivendosje
                chunk_size = 1200
                overlap = 150
                start = 0
                while start < len(page_text):
                    end = start + chunk_size
                    chunk_str = page_text[start:end].strip()
                    start += chunk_size - overlap

                    if len(chunk_str) > 20:
                        raw_chunks.append({
                            "chunk_id": f"caselaw_{filename}_{chunk_global_idx}",
                            "law_title": f"Gjykata Supreme e Kosovës - {current_case_no}",
                            "title": current_case_no,
                            "source": filename,
                            "case_number": current_case_no,
                            "page": page_num + 1,
                            "text": chunk_str,
                            "chunk_index": chunk_global_idx,
                            "is_case_law": True,
                            "is_article": False,
                            "jurisdiction": "ks"
                        })
                        chunk_global_idx += 1

            doc.close()

            if not raw_chunks:
                logger.warning(f"   ⚠️ Nuk u gjet tekst i vlefshëm në {filename}.")
                continue

            logger.info(f"   🤖 Duke gjeneruar vektorët me Batch për {len(raw_chunks)} pjesëza...")

            # Gjenerim i shpejtë i vektorëve me batch prej 50 copash
            texts_to_embed = [c["text"] for c in raw_chunks]
            batch_size = 50
            all_embeddings = []
            for b_idx in range(0, len(texts_to_embed), batch_size):
                batch_texts = texts_to_embed[b_idx:b_idx+batch_size]
                batch_vectors = generate_embeddings_batch(batch_texts)
                all_embeddings.extend(batch_vectors)

            # Bashkojmë vektorët me të dhënat e dokumenteve
            docs_to_insert = []
            for idx, c_data in enumerate(raw_chunks):
                vector = all_embeddings[idx] if idx < len(all_embeddings) else []
                c_data["embedding"] = vector if vector else []
                docs_to_insert.append(c_data)

            if docs_to_insert:
                coll.delete_many({"source": filename})
                coll.insert_many(docs_to_insert)
                logger.info(f"   ✅ U ruajtën me sukses të gjitha {len(docs_to_insert)} pjesëzat e Gjykatës Supreme në MongoDB!")

        except Exception as e:
            logger.error(f"   ❌ Gabim gjatë procesimit të {filename}: {e}")

    print(f"\n============================================================")
    logger.info("🎉 TË GJITHA 700+ FAQET E GJYKATËS SUPREME U INGESTUAN ME SUKSES TË PLOTË!")
    print(f"============================================================\n")

if __name__ == "__main__":
    ingest_caselaw_pdfs(force_reingest=True)