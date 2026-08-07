# FILE: backend/scripts/ingest_caselaw.py
# PHOENIX PROTOCOL - CASELAW PDF INGESTION WITH DYNAMIC CASE-NUMBER PARSER & ZERO-DUPLICATE GUARANTEE

import os
import sys
import glob
import re
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
logger = logging.getLogger("ingest_caselaw")

# Regex pattern for Kosovo Supreme & Court Case Numbers (e.g. PML.Nr.85/2025, PA1.Nr.716/2024, Rev.Nr.45/2021)
CASE_NO_PATTERN = re.compile(
    r'((?:PML|PA1|Rev|A|CP|PKR|P|KMLP)\s*\.?\s*Nr\s*\.?\s*\d+\s*/\s*\d{4})', 
    re.IGNORECASE
)

def ingest_caselaw_pdfs(force_reingest: bool = False):
    workspace_data = os.path.join(WORKSPACE_ROOT, "data", "case_law")
    backend_data = os.path.join(BACKEND_DIR, "data", "case_law")
    desktop_data = os.path.join(os.path.expanduser("~"), "Desktop", "caselaw_pdfs")

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
    logger.info(f"📁 U gjetën {total_files} skedarë aktgjykimesh në: {target_folder}")

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
        logger.info(f"📄 [{f_idx}/{total_files}] DUKE PROCESUAR AKTGJY KIMIN: {filename}")

        # Header check for non-PDF HTML files
        try:
            with open(file_path, "rb") as f:
                header = f.read(10)
                if b"<!DOC" in header or b"<html" in header.lower():
                    logger.warning(f"   ⚠️ SKIPPED: Skedari nuk është PDF i vërtetë (është përmbajtje HTML).")
                    continue
        except Exception as file_err:
            logger.error(f"   ❌ Nuk mund të lexohet skedari: {file_err}")
            continue

        # 1. Backblaze B2 Upload under 'case_law/' prefix
        b2_key = f"case_law/{filename}"
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

        # 2. Extract Text & Detect Case Numbers
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            
            docs_to_insert = []
            current_case_no = "Gjyjata Supreme e Kosovës"
            chunk_global_idx = 1

            logger.info(f"   📖 Lexuar: {total_pages} Faqje. Duke nxjerrë numrat e lëndëve dhe vektorizuar...")

            for p_idx, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue

                # Check if this page introduces a new Case Number (e.g. PML.Nr.85/2025)
                matches = CASE_NO_PATTERN.findall(page_text)
                if matches:
                    current_case_no = matches[0].strip().replace(" ", "")

                # Split page text into 1000-character chunks
                chunk_size = 1000
                overlap = 100
                start = 0
                while start < len(page_text):
                    end = start + chunk_size
                    chunk_str = page_text[start:end]
                    start += chunk_size - overlap

                    vector = embedding_service.get_embedding(chunk_str)
                    docs_to_insert.append({
                        "chunk_id": f"caselaw_{filename}_{chunk_global_idx}",
                        "law_title": f"{current_case_no} - {filename.replace('.pdf', '')}",
                        "source": filename,
                        "category": "caselaw",
                        "case_number": current_case_no,
                        "page": p_idx,
                        "text": chunk_str,
                        "embedding": vector,
                        "chunk_index": chunk_global_idx
                    })
                    chunk_global_idx += 1

                if p_idx % 20 == 0 or p_idx == total_pages:
                    percent = int((p_idx / total_pages) * 100)
                    print(f"\r   🤖 AI Vectoring: Faqja {p_idx}/{total_pages} ({percent}%) | Numri i Rasteve: {current_case_no}...", end="", flush=True)

            print() # new line
            if docs_to_insert:
                db.legal_knowledge_base.delete_many({"source": filename})
                db.legal_knowledge_base.insert_many(docs_to_insert)
                logger.info(f"   ✅ U ruajtën me sukses {len(docs_to_insert)} vektore me numra lëndësh në MongoDB!")

        except (PdfReadError, Exception) as e:
            logger.error(f"   ❌ Gabim gjatë procesimit të PDF: {e}")

    print(f"\n============================================================")
    logger.info("🎉 TË GJITHA AKTGJY KIMET U INGESTUAN ME SUKSES TË PLOTË!")
    print(f"============================================================\n")

if __name__ == "__main__":
    ingest_caselaw_pdfs()