# FILE: backend/scripts/ingest_academic.py
# PHOENIX PROTOCOL - ACADEMIC PDF INGESTION WITH CORRUPTED/HTML FILE FILTER

import os
import sys
import glob
import logging

# Ensure parent paths are in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
WORKSPACE_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from app.services import storage_service, embedding_service
from app.core.db import get_db_instance

# Mute noisy HTTP request logs from httpx/urllib3
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ingest_academic")

def ingest_academic_pdfs(force_reingest: bool = False):
    workspace_data = os.path.join(WORKSPACE_ROOT, "data", "academic")
    backend_data = os.path.join(BACKEND_DIR, "data", "academic")
    desktop_data = os.path.join(os.path.expanduser("~"), "Desktop", "academic_pdfs")

    target_folder = None
    for path in [workspace_data, backend_data, desktop_data]:
        if os.path.exists(path) and glob.glob(os.path.join(path, "*.pdf")):
            target_folder = path
            break

    if not target_folder:
        logger.error(f"Nuk u gjet asnjë skedar PDF! Kontrolluar në:\n - {workspace_data}\n - {backend_data}\n - {desktop_data}")
        return

    pdf_files = glob.glob(os.path.join(target_folder, "*.pdf"))
    total_files = len(pdf_files)
    logger.info(f"📁 U gjetën {total_files} skedarë në: {target_folder}")

    db = get_db_instance()
    s3_client = storage_service.get_s3_client()
    b2_bucket = storage_service.B2_BUCKET_NAME

    for f_idx, file_path in enumerate(pdf_files, 1):
        filename = os.path.basename(file_path)

        # --- SMART SKIP CHECK ---
        existing_count = db.legal_knowledge_base.count_documents({"source": filename})
        if existing_count > 0 and not force_reingest:
            logger.info(f"⏭️  [{f_idx}/{total_files}] SKIPPED (Tashmë i ingestuar me {existing_count} vektore): {filename}")
            continue

        print(f"\n------------------------------------------------------------")
        logger.info(f"📄 [{f_idx}/{total_files}] DUKE PROCESUAR: {filename}")

        # Check for HTML / invalid PDF headers
        try:
            with open(file_path, "rb") as f:
                header = f.read(10)
                if b"<!DOC" in header or b"<html" in header.lower():
                    logger.warning(f"   ⚠️ SKIPPED: Skedari nuk është PDF i vërtetë (është përmbajtje HTML/Ueb).")
                    continue
        except Exception as file_err:
            logger.error(f"   ❌ Nuk mund të lexohet skedari: {file_err}")
            continue

        # 1. Backblaze B2 Upload under 'academic/' prefix
        b2_key = f"academic/{filename}"
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            s3_client.put_object(
                Bucket=b2_bucket,
                Key=b2_key,
                Body=file_bytes,
                ContentType="application/pdf"
            )
            logger.info(f"   ☁️  U ngarkua në B2 Cloud: Key = '{b2_key}'")
        except Exception as e:
            logger.error(f"   ❌ Gabim në B2 Upload: {e}")

        # 2. Extract Text & Create AI Vector Embeddings
        try:
            reader = PdfReader(file_path)
            full_text = ""
            total_pages = len(reader.pages)
            
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                full_text += f"\n--- Faqja {idx + 1} ---\n" + page_text

            if not full_text.strip():
                logger.warning(f"   ⚠️ Skedari nuk ka tekst të lexueshëm.")
                continue

            chunk_size = 1000
            overlap = 100
            chunks = []
            start = 0
            while start < len(full_text):
                end = start + chunk_size
                chunks.append(full_text[start:end])
                start += chunk_size - overlap

            total_chunks = len(chunks)
            logger.info(f"   📖 Lexuar: {total_pages} Faqje | Ndarë në: {total_chunks} Chunks për AI Vectoring")

            docs_to_insert = []
            title_display = filename.replace(".pdf", "").replace("_", " ")

            for c_idx, chunk_text in enumerate(chunks, 1):
                vector = embedding_service.get_embedding(chunk_text)
                docs_to_insert.append({
                    "chunk_id": f"academic_{filename}_{c_idx}",
                    "law_title": title_display,
                    "source": filename,
                    "category": "academic",
                    "text": chunk_text,
                    "embedding": vector,
                    "chunk_index": c_idx
                })

                if c_idx % 10 == 0 or c_idx == total_chunks:
                    percent = int((c_idx / total_chunks) * 100)
                    print(f"\r   🤖 AI Vectoring: Chunk {c_idx}/{total_chunks} ({percent}%) të kompletuara...", end="", flush=True)

            print() # new line
            if docs_to_insert:
                db.legal_knowledge_base.delete_many({"source": filename})
                db.legal_knowledge_base.insert_many(docs_to_insert)
                logger.info(f"   ✅ U ruajtën me sukses {len(docs_to_insert)} vektore në MongoDB!")

        except (PdfReadError, Exception) as e:
            logger.error(f"   ❌ Gabim gjatë procesimit të PDF: {e}")

    print(f"\n============================================================")
    logger.info("🎉 PROCESI U COMPLETOU! TË GJITHA SKEDARËT E REJA U INGESTUAN ME SUKSES.")
    print(f"============================================================\n")

if __name__ == "__main__":
    ingest_academic_pdfs()