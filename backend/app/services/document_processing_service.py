# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - HIGH PERFORMANCE & GRAPH ENABLED
# 1. PARALLELISM: Runs Embeddings, Summary, Findings, Deadlines, Storage, AND GRAPH concurrently.
# 2. GRAPH INTEGRATION: Extracts entities/relations and pushes to Neo4j.
# 3. ROBUSTNESS: Graph failures are non-blocking (Safe).

import os
import tempfile
import logging
import shutil
import concurrent.futures
from typing import List, Dict, Any, Optional

from pymongo.database import Database
import redis
from bson import ObjectId
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Direct imports of CORE SERVICES
from . import (
    document_service, 
    storage_service, 
    vector_store_service, 
    llm_service, 
    text_extraction_service, 
    conversion_service,
    deadline_service,
    findings_service,
    graph_service # <--- ADDED
)
from .categorization_service import CATEGORIZATION_SERVICE
from .albanian_language_detector import AlbanianLanguageDetector
from ..models.document import DocumentStatus

logger = logging.getLogger(__name__)

class DocumentNotFoundInDBError(Exception):
    pass

def _process_and_split_text(full_text: str, document_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    base_metadata = document_metadata.copy()
    
    # Standard chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200, 
        length_function=len
    )
    text_chunks = text_splitter.split_text(full_text)
    
    return [
        {'content': chunk, 'metadata': {**base_metadata, 'chunk_index': i}}
        for i, chunk in enumerate(text_chunks)
    ]

def orchestrate_document_processing_mongo(
    db: Database,
    redis_client: redis.Redis,
    document_id_str: str
):
    try:
        doc_id = ObjectId(document_id_str)
    except Exception:
        logger.error(f"Invalid Document ID format: {document_id_str}.")
        return

    document = db.documents.find_one({"_id": doc_id})
    if not document:
        raise DocumentNotFoundInDBError(f"Document with ID {document_id_str} not found.")

    temp_original_file_path = ""
    temp_pdf_preview_path = ""
    preview_storage_key = None
    
    try:
        # --- PHASE 1: PREPARATION (Sequential IO) ---
        
        # 1. Download
        suffix = os.path.splitext(document.get("file_name", ""))[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        
        file_stream = storage_service.download_original_document_stream(document["storage_key"])
        with os.fdopen(temp_file_descriptor, 'wb') as temp_file:
            shutil.copyfileobj(file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # 2. PDF Preview (Can fail safely)
        try:
            temp_pdf_preview_path = conversion_service.convert_to_pdf(temp_original_file_path)
            preview_storage_key = storage_service.upload_document_preview(
                file_path=temp_pdf_preview_path,
                user_id=str(document.get("owner_id")),
                case_id=str(document.get("case_id")),
                original_doc_id=document_id_str
            )
        except Exception as e:
            logger.warning(f"Preview generation skipped: {e}")

        # 3. Text Extraction (Critical)
        extracted_text = text_extraction_service.extract_text(temp_original_file_path, document.get("mime_type", ""))
        if not extracted_text or not extracted_text.strip():
            raise ValueError("Text extraction returned no content.")

        # 4. Metadata Enrichment
        try:
            detected_category = CATEGORIZATION_SERVICE.categorize_document(extracted_text)
            db.documents.update_one({"_id": doc_id}, {"$set": {"category": detected_category}})
        except Exception:
            detected_category = "Unknown"

        is_albanian = AlbanianLanguageDetector.detect_language(extracted_text)
        detected_lang = 'albanian' if is_albanian else 'standard'

        # --- PHASE 2: PARALLEL EXECUTION (The Speed Boost) ---
        logger.info(f"🚀 Starting Parallel Processing for {document_id_str}...")
        
        # Define Task Wrappers
        
        def task_embeddings():
            """Chunks and uploads vectors to ChromaDB."""
            try:
                base_doc_metadata = {
                    'document_id': document_id_str,
                    'case_id': str(document.get("case_id")),
                    'user_id': str(document.get("owner_id")),
                    'file_name': document.get("file_name", "Unknown"),
                    'language': detected_lang,
                    'category': detected_category 
                }
                enriched_chunks = _process_and_split_text(extracted_text, base_doc_metadata)
                
                # Batch upload to Vector Store
                BATCH_SIZE = 10
                for i in range(0, len(enriched_chunks), BATCH_SIZE):
                    batch = enriched_chunks[i:i + BATCH_SIZE]
                    vector_store_service.create_and_store_embeddings_from_chunks(
                        document_id=document_id_str,
                        case_id=str(document.get("case_id")),
                        chunks=[c['content'] for c in batch],
                        metadatas=[c['metadata'] for c in batch]
                    )
                return True
            except Exception as e:
                logger.error(f"❌ Embedding Task Failed: {e}")
                return False

        def task_storage():
            """Uploads processed text to storage for retrieval."""
            try:
                return storage_service.upload_processed_text(
                    extracted_text, 
                    user_id=str(document.get("owner_id")),
                    case_id=str(document.get("case_id")), 
                    original_doc_id=document_id_str
                )
            except Exception as e:
                logger.error(f"❌ Storage Task Failed: {e}")
                return None

        def task_summary():
            """Generates AI summary (Optimized for Large Docs)."""
            try:
                # OPTIMIZATION: Take First 30k chars (~10 pages) + Last 15k chars (~5 pages).
                limit_start = 30000
                limit_end = 15000
                if len(extracted_text) > (limit_start + limit_end):
                    optimized_text = extracted_text[:limit_start] + "\n\n...[Tekst i shkurtuar]...\n\n" + extracted_text[-limit_end:]
                else:
                    optimized_text = extracted_text
                
                return llm_service.generate_summary(optimized_text)
            except Exception as e:
                logger.warning(f"⚠️ Summary Task Failed: {e}")
                return "Përmbledhja nuk është e disponueshme."

        def task_findings():
            try:
                findings_service.extract_and_save_findings(db, document_id_str, extracted_text)
            except Exception as e:
                logger.warning(f"⚠️ Findings Task Failed: {e}")

        def task_deadlines():
            try:
                deadline_service.extract_and_save_deadlines(db, document_id_str, extracted_text)
            except Exception as e:
                logger.warning(f"⚠️ Deadline Task Failed: {e}")

        # --- NEW: GRAPH EXTRACTION TASK ---
        def task_graph():
            """Extracts entities and relationships for Neo4j."""
            try:
                logger.info("🕸️ Starting Graph Extraction...")
                # 1. AI extracts structured JSON
                graph_data = llm_service.extract_graph_data(extracted_text)
                entities = graph_data.get("entities", [])
                relations = graph_data.get("relations", [])
                
                if not entities and not relations:
                    logger.info("🕸️ Graph Extraction returned empty.")
                    return

                # 2. Push to Neo4j
                graph_service.graph_service.ingest_entities_and_relations(
                    case_id=str(document.get("case_id")),
                    document_id=document_id_str,
                    entities=entities,
                    relations=relations
                )
                logger.info(f"✅ Graph Task Complete: {len(entities)} Nodes.")
            except Exception as e:
                logger.warning(f"⚠️ Graph Task Failed (Non-Critical): {e}")

        # EXECUTE IN PARALLEL
        summary_result = None
        text_storage_key = None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Launch all tasks
            future_embed = executor.submit(task_embeddings)
            future_storage = executor.submit(task_storage)
            future_summary = executor.submit(task_summary)
            future_findings = executor.submit(task_findings)
            future_deadlines = executor.submit(task_deadlines)
            future_graph = executor.submit(task_graph) # <--- NEW
            
            # PHOENIX FIX: Typed list to satisfy static analysis
            futures_list: List[concurrent.futures.Future] = [
                future_embed, future_storage, future_summary, 
                future_findings, future_deadlines, future_graph
            ]
            concurrent.futures.wait(futures_list)
            
            # Retrieve critical results
            summary_result = future_summary.result()
            text_storage_key = future_storage.result()
            
            # Check Embedding Status (Critical)
            if not future_embed.result():
                logger.warning("⚠️ Embeddings may have failed partially.")

        # --- PHASE 3: FINALIZE ---
        document_service.finalize_document_processing(
            db=db,
            redis_client=redis_client,
            doc_id_str=document_id_str, 
            summary=summary_result,
            processed_text_storage_key=text_storage_key,
            preview_storage_key=preview_storage_key
        )
        logger.info(f"✅ Document {document_id_str} processing completed successfully.")

    except Exception as e:
        error_message = f"Failed to process document {document_id_str}: {e}"
        logger.error(f"--- [CRITICAL FAILURE] {error_message} ---", exc_info=True)
        db.documents.update_one(
            {"_id": doc_id},
            {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
        )
        raise e
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)
        if temp_pdf_preview_path and os.path.exists(temp_pdf_preview_path): os.remove(temp_pdf_preview_path)