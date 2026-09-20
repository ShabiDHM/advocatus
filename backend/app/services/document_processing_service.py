# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V38.1 (BATCH INGESTION + STATUS PROPAGATION)
# V38.1: Summary timeout 40s -> 120s — ne perputhje me llm_service V5.2 qe
#        paralelizon chunks (4 chunks ~13s paralel + final call ~5s = ~18s).
# V38.0: task_embeddings kontrollon rezultatin e ingestion (dict, jo bool).
#        Log i detajuar + warning nëse success=False.
# V37.0: Accurate DOCX/PDF multi-page chunker.

import os
import tempfile
import logging
import shutil
import json
import asyncio
import gc
import time
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from bson import ObjectId
import redis.asyncio as aioredis
import fitz  # PyMuPDF për skedarët PDF

from app.services import storage_service, llm_service, text_extraction_service, conversion_service
from app.services.albanian_document_processor import EnhancedDocumentProcessor
from app.models.document import DocumentStatus
from app.services.vector_store_service import create_and_store_embeddings_from_chunks
from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_remove_temp_file(file_path: str):
    if not file_path or not os.path.exists(file_path):
        return
    gc.collect()
    for _ in range(3):
        try:
            os.remove(file_path)
            return
        except Exception:
            time.sleep(0.1)
    try:
        os.remove(file_path)
    except Exception:
        pass


async def _update_db_and_broadcast(db: Any, collection: str, doc_id: ObjectId, user_id: str, document_id_str: str, percent: int, message: str, doc_status: str = "PROCESSING"):
    try:
        await asyncio.to_thread(
            db[collection].update_one,
            {"_id": doc_id},
            {"$set": {
                "progress_percent": percent,
                "progress_message": message,
                "status": doc_status,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    except Exception as db_err:
        logger.warning(f"MongoDB progress update error: {db_err}")

    try:
        payload = {
            "type": "DOCUMENT_PROGRESS",
            "document_id": document_id_str,
            "percent": percent,
            "message": message,
            "status": doc_status
        }
        channel = f"user:{user_id}:updates"
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0
        )
        await redis_client.publish(channel, json.dumps(payload))
        await redis_client.close()
    except Exception as sse_err:
        logger.warning(f"SSE progress broadcast skipped: {sse_err}")


def _detect_page_number_for_chunk(chunk_text: str, default_page: int = 1) -> int:
    """Zbulon numrin e faqes përkatëse për një copëz teksti bazuar në shënimet [FAQJA X]."""
    match = re.search(r'---\s*\[FAQJA\s*(\d+)\]\s*---', chunk_text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return default_page
    return default_page


async def orchestrate_document_processing_mongo(
    document_id_str: str,
    *args,
    db: Any = None,
    collection: str = "documents",
    redis_client: Any = None,
    **kwargs
):
    logger.info(f"⚡ [Orchestrator V38.1] Processing booted for doc: {document_id_str} in collection '{collection}'")
    
    if db is None:
        from app.core.db import get_db_instance
        db = get_db_instance()

    try:
        doc_id = ObjectId(document_id_str)
    except Exception:
        logger.error(f"Invalid Document ID: {document_id_str}")
        return

    document = await asyncio.to_thread(db[collection].find_one, {"_id": doc_id})
    if not document:
        logger.error(f"Document {document_id_str} not found in {collection} collection.")
        return

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))

    # Faza 1: 30% Përgatitja
    await _update_db_and_broadcast(db, collection, doc_id, user_id, document_id_str, 30, "Duke përgatitur skedarin...")

    temp_original_file_path = ""
    raw_text = f"Dokument i ngarkuar: {doc_name}."
    final_summary = "Përmbledhje e dokumentit."
    preview_storage_key = ""
    text_key = ""
    real_page_count = 1
    ingestion_result: Dict[str, Any] = {}

    try:
        suffix = os.path.splitext(doc_name)[1] or ".pdf"
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            await asyncio.to_thread(shutil.copyfileobj, file_stream, temp_file)
        if hasattr(file_stream, 'close'): 
            file_stream.close()

        # Numërimi fillestar për skedarët PDF (nëse është PDF)
        if suffix.lower() == ".pdf":
            try:
                pdf_doc = fitz.open(temp_original_file_path)
                real_page_count = max(len(pdf_doc), 1)
                pdf_doc.close()
            except Exception as page_err:
                logger.warning(f"Could not calculate PDF page count for {doc_name}: {page_err}")
                real_page_count = 1

        # Faza 2: 60% Leximi me AI Vision & Sequential DOCX OCR
        await _update_db_and_broadcast(db, collection, doc_id, user_id, document_id_str, 60, "Duke lexuar tekstin...")
        
        ocr_timeout = max(90.0, real_page_count * 20.0)
        try:
            extracted = await asyncio.wait_for(
                asyncio.to_thread(text_extraction_service.extract_text, temp_original_file_path, document.get("mime_type", "")),
                timeout=ocr_timeout
            )
            if extracted and len(extracted.strip()) > 10:
                raw_text = extracted

                # Përcaktimi ekzakt i faqeve nga shënimet reale në tekst
                page_markers = re.findall(r'---\s*\[FAQJA\s*(\d+)\]\s*---', raw_text, re.IGNORECASE)
                if page_markers:
                    try:
                        max_marker_page = max(int(p) for p in page_markers)
                        real_page_count = max(real_page_count, max_marker_page)
                    except Exception:
                        real_page_count = max(real_page_count, len(page_markers))
                elif real_page_count <= 1 and len(raw_text) > 2200:
                    real_page_count = max(1, round(len(raw_text) / 2200))

                logger.info(f"✅ [Orchestrator V38.1] U nxorën {len(raw_text)} karaktere nga {real_page_count} faqe reale.")
        except Exception as extract_err:
            logger.warning(f"OCR warning for {doc_name} (using fallback): {extract_err}")

        # Faza 3: 80% Vektorizimi në RAG
        await _update_db_and_broadcast(db, collection, doc_id, user_id, document_id_str, 80, "Duke indeksuar në RAG...")

        async def task_summary():
            try:
                # V38.1: Provo funksionin nëse ekziston; përndryshe fallback
                if hasattr(llm_service, "sterilize_legal_text") and hasattr(llm_service, "process_large_document_async"):
                    sterilized_text = llm_service.sterilize_legal_text(raw_text)
                    return await asyncio.wait_for(
                        llm_service.process_large_document_async(sterilized_text),
                        timeout=120.0  # V38.1: rritur nga 40s → 120s (llm_service V5.2 paralelizon chunks)
                    )
                else:
                    logger.warning(
                        "⚠️ [Summary V38.1] sterilize_legal_text / process_large_document_async "
                        "nuk ekzistojnë — përdor fallback (800 chars)."
                    )
                    return raw_text[:800]
            except Exception as e:
                logger.warning(f"Summary task timeout/fallback: {e}")
                return raw_text[:800]

        async def task_embeddings():
            """
            V38.0: Krijon chunks + thërret ingestion me raportim të detajuar.
            Kthen dict me status (success, ingested, total_chunks, duration).
            """
            try:
                t0 = time.time()

                enriched_chunks = await asyncio.to_thread(
                    EnhancedDocumentProcessor.process_document,
                    text_content=raw_text,
                    document_metadata={'file_name': doc_name, 'pages': real_page_count}
                )

                if enriched_chunks:
                    chunks_to_store = [c.content for c in enriched_chunks]
                    metadatas_to_store = []
                    current_detected_p = 1
                    for c in enriched_chunks:
                        current_detected_p = _detect_page_number_for_chunk(c.content, default_page=current_detected_p)
                        meta = dict(c.metadata)
                        meta["page"] = current_detected_p
                        meta["source"] = doc_name
                        metadatas_to_store.append(meta)
                else:
                    # Fallback me copëtim dinamik
                    chunk_step = 1200
                    chunks_to_store = [raw_text[i:i+1500] for i in range(0, len(raw_text), chunk_step)]
                    metadatas_to_store = []
                    current_p = 1
                    for chunk in chunks_to_store:
                        current_p = _detect_page_number_for_chunk(chunk, default_page=current_p)
                        metadatas_to_store.append({
                            "page": current_p,
                            "source": doc_name,
                            "total_pages": real_page_count
                        })

                logger.info(
                    f"📦 [Orchestrator V38.1] Duke filluar ingestion për "
                    f"{len(chunks_to_store)} chunks (doc={document_id_str})"
                )

                # ═══════════════════════════════════════════════════════════
                # V38.0: Thirrja kthen dict (jo bool)
                # ═══════════════════════════════════════════════════════════
                result = await asyncio.to_thread(
                    create_and_store_embeddings_from_chunks,
                    user_id=user_id,
                    document_id=document_id_str,
                    case_id=case_id_str,
                    file_name=doc_name,
                    chunks=chunks_to_store,
                    metadatas=metadatas_to_store
                )

                duration = round(time.time() - t0, 2)

                # Nëse ingestion nuk është dict (p.sh. bool nga version i vjetër), përshtat
                if not isinstance(result, dict):
                    logger.warning(
                        f"⚠️ [Orchestrator V38.1] Ingestion ktheu {type(result).__name__} "
                        f"(pritet dict). Trajtoj si {'sukses' if result else 'dështim'}."
                    )
                    result = {
                        "success": bool(result),
                        "total_chunks": len(chunks_to_store),
                        "ingested": len(chunks_to_store) if result else 0,
                        "failed": 0 if result else len(chunks_to_store),
                        "errors": [] if result else ["Unknown error (legacy bool return)"],
                        "duration_sec": duration,
                    }

                # Log i detajuar
                ingested = result.get("ingested", 0)
                total = result.get("total_chunks", len(chunks_to_store))
                success = result.get("success", False)
                errors = result.get("errors", [])

                if success:
                    logger.info(
                        f"✅ [Orchestrator V38.1] Ingestion i plotë: "
                        f"{ingested}/{total} chunks, duration={duration}s"
                    )
                else:
                    logger.error(
                        f"⚠️ [Orchestrator V38.1] Ingestion i pjesshëm ose dështuar: "
                        f"{ingested}/{total} chunks, errors={errors[:3]}"
                    )

                return result

            except Exception as e:
                logger.error(f"❌ [Orchestrator V38.1] Embedding task exception: {e}")
                return {
                    "success": False,
                    "total_chunks": 0,
                    "ingested": 0,
                    "failed": 0,
                    "errors": [str(e)],
                    "duration_sec": 0.0,
                }

        async def task_storage():
            try:
                return await asyncio.to_thread(storage_service.upload_processed_text, raw_text, user_id, case_id_str, document_id_str)
            except Exception:
                return ""

        async def task_preview():
            try:
                pdf_path = await asyncio.to_thread(conversion_service.convert_to_pdf, temp_original_file_path)
                key = await asyncio.to_thread(storage_service.upload_document_preview, pdf_path, user_id, case_id_str, document_id_str)
                if pdf_path and os.path.exists(pdf_path) and pdf_path != temp_original_file_path:
                    _safe_remove_temp_file(pdf_path)
                return key
            except Exception:
                return ""

        # Faza 4: 92% Përfundimi i Detyrave Paralele
        await _update_db_and_broadcast(db, collection, doc_id, user_id, document_id_str, 92, "Duke finalizuar...")

        try:
            results = await asyncio.wait_for(
                asyncio.gather(task_summary(), task_embeddings(), task_storage(), task_preview(), return_exceptions=True),
                timeout=180.0  # V38.0: rritur nga 75s → 180s (batch+retry kërkon më shumë)
            )
            if len(results) > 0 and isinstance(results[0], str):
                final_summary = results[0]
            if len(results) > 1 and isinstance(results[1], dict):
                ingestion_result = results[1]
            if len(results) > 2 and isinstance(results[2], str):
                text_key = results[2]
            if len(results) > 3 and isinstance(results[3], str):
                preview_storage_key = results[3]
        except Exception as par_err:
            logger.warning(f"Parallel tasks completed with fallback: {par_err}")

    except Exception as general_err:
        logger.error(f"Orchestrator pipeline exception on {doc_name}: {general_err}")
    
    finally:
        # ═══════════════════════════════════════════════════════════════
        # V38.0: Vendos statusin bazuar në ingestion_result
        # ═══════════════════════════════════════════════════════════════
        ingestion_ok = ingestion_result.get("success", False) if isinstance(ingestion_result, dict) else False
        ingestion_stats = {
            "ingested": ingestion_result.get("ingested", 0) if isinstance(ingestion_result, dict) else 0,
            "total_chunks": ingestion_result.get("total_chunks", 0) if isinstance(ingestion_result, dict) else 0,
            "failed": ingestion_result.get("failed", 0) if isinstance(ingestion_result, dict) else 0,
            "duration_sec": ingestion_result.get("duration_sec", 0) if isinstance(ingestion_result, dict) else 0,
        }

        # Status: READY nëse ingestion ka sukses, përndryshe READY_WITH_WARNINGS
        if ingestion_ok:
            final_status = DocumentStatus.READY
            status_message = "Gati"
        else:
            # Nëse ingestion dështoi → shëno me warning (jo READY)
            try:
                final_status = DocumentStatus.READY_WITH_WARNINGS
            except AttributeError:
                # Nëse enum-i nuk ka këtë vlerë, përdor READY (fallback)
                final_status = DocumentStatus.READY
            status_message = "Gati (me paralajmërime — disa pjesë nuk u indeksuan)"
            logger.error(
                f"⚠️ [Orchestrator V38.1] Dokument {document_id_str} u shënua "
                f"{final_status} sepse ingestion nuk ishte i plotë."
            )

        try:
            await asyncio.to_thread(
                db[collection].update_one,
                {"_id": doc_id},
                {
                    "$set": {
                        "page_count": real_page_count,
                        "pages": real_page_count,
                        "content": raw_text,
                        "extracted_text": raw_text,
                        "text": raw_text,
                        "summary": final_summary,
                        "processed_text_storage_key": text_key,
                        "preview_storage_key": preview_storage_key,
                        "status": final_status,
                        "progress_percent": 100,
                        "progress_message": status_message,
                        "ingestion_stats": ingestion_stats,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            logger.info(
                f"✅ [Orchestrator V38.1] Document {document_id_str} "
                f"({real_page_count} real pages) is {final_status} in {collection}. "
                f"Ingestion: {ingestion_stats['ingested']}/{ingestion_stats['total_chunks']} chunks"
            )
        except Exception as db_err:
            logger.error(f"Failed to update MongoDB document status: {db_err}")

        try:
            payload = {
                "type": "DOCUMENT_STATUS",
                "document_id": document_id_str,
                "status": final_status,
                "page_count": real_page_count,
                "ingestion_stats": ingestion_stats,
            }
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1.0)
            await redis_client.publish(f"user:{user_id}:updates", json.dumps(payload, default=str))
            await redis_client.close()
        except Exception:
            pass

        _safe_remove_temp_file(temp_original_file_path)