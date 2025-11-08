# app/tasks/document_reprocessing.py (Final, Verified Version)
import os
import tempfile
import json
# --- CRITICAL FIX: Import the central celery_app instance ---
from app.celery_app import celery_app
# ---------------------------------------------------------
from app.services import (
    database_service,
    storage_service,
    llm_service,
    embedding_service,
    vector_store_service
)

def log_structured(document_id: str, case_id: str, stage: str, status: str, message: str = "", **extra):
    # ... (implementation unchanged)
    log_entry = { "document_id": document_id, "case_id": case_id, "stage": stage, "status": status, "message": message, **extra }
    print(json.dumps(log_entry))

@celery_app.task(name="reprocess_text_task")
def reprocess_text_task(document_id: str, corrected_text: str):
    case_id = None
    log_structured(document_id, case_id, "start_reprocessing", "initiated", "Reprocessing task received.")
    database_service.update_document_status(document_id, "REPROCESSING")
    temp_text_file_path = None
    try:
        document = database_service.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document with id {document_id} not found.")
        case_id = document.get("case_id")
        text_storage_key = document.get("processed_text_storage_key")
        if not all([case_id, text_storage_key]):
            raise ValueError(f"Missing case_id or processed_text_storage_key.")
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as temp_text_file:
            temp_text_file.write(corrected_text)
            temp_text_file_path = temp_text_file.name
            
        storage_service.s3_client.upload_file(
            temp_text_file_path, storage_service.B2_BUCKET_NAME, text_storage_key
        )
        log_structured(document_id, case_id, "overwrite_text", "success")
        
        new_summary = llm_service.generate_summary(corrected_text)
        log_structured(document_id, case_id, "re_summarization", "success")
        
        new_embedding = embedding_service.generate_embedding(corrected_text)
        log_structured(document_id, case_id, "re_embedding", "success")
        
        database_service.update_document_summary(document_id, new_summary)
        log_structured(document_id, case_id, "re_integrate_summary", "success")
        
        vector_store_service.store_document_embedding(document_id, case_id, new_embedding, corrected_text)
        log_structured(document_id, case_id, "re_integrate_vector", "success")
        
        database_service.update_document_status(document_id, "COMPLETED")
        log_structured(document_id, case_id, "finish_reprocessing", "completed")
        
    except Exception as e:
        log_structured(document_id, case_id, "reprocessing_error", "failed", str(e))
        database_service.update_document_status(document_id, "FAILED")
        
    finally:
        if temp_text_file_path and os.path.exists(temp_text_file_path):
            os.remove(temp_text_file_path)