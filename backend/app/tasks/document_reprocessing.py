# FILE: app/tasks/document_reprocessing.py

import logging
from typing import Optional

# PHOENIX PROTOCOL CURE: Use a relative import to break the circular dependency for the linter.
from ..celery_app import celery_app
from ..core.db import db_instance, redis_sync_client
from ..services import (
    storage_service,
    llm_service,
    vector_store_service,
    document_service
)
from ..models.document import DocumentStatus

logger = logging.getLogger(__name__)

def log_structured(document_id: str, case_id: Optional[str], stage: str, status: str, message: str = "", **extra):
    log_entry = {
        "document_id": document_id, 
        "case_id": case_id or "Unknown", 
        "stage": stage, 
        "status": status, 
        "message": message, 
        **extra
    }
    logger.info(str(log_entry))

@celery_app.task(name="reprocess_text_task")
def reprocess_text_task(document_id: str, corrected_text: str):
    case_id: Optional[str] = None
    log_structured(document_id, case_id, "start_reprocessing", "initiated", "Reprocessing task received.")
    
    db_instance.documents.update_one({"_id": document_id}, {"$set": {"status": DocumentStatus.PENDING}})
    
    try:
        document = db_instance.documents.find_one({"_id": document_id})
        if not document:
            raise ValueError(f"Document with id {document_id} not found.")
            
        case_id = str(document.get("case_id"))
        text_storage_key = document.get("processed_text_storage_key")
        owner_id = str(document.get("owner_id"))
        
        if not all([case_id, text_storage_key, owner_id]):
            raise ValueError("Missing case_id, processed_text_storage_key, or owner_id required for reprocessing.")
        
        storage_service.upload_processed_text(
            text_content=corrected_text,
            user_id=owner_id,
            case_id=case_id,
            original_doc_id=document_id
        )
        log_structured(document_id, case_id, "overwrite_text", "success")
        
        new_summary = llm_service.generate_summary(corrected_text)
        log_structured(document_id, case_id, "re_summarization", "success")
        
        document_service.finalize_document_processing(
            db=db_instance,
            redis_client=redis_sync_client,
            doc_id_str=document_id,
            summary=new_summary,
            processed_text_storage_key=text_storage_key
        )
        
        vector_store_service.delete_document_embeddings(document_id=document_id)
        
        celery_app.send_task('process_document_task', args=[document_id])
        
        log_structured(document_id, case_id, "re_embedding_triggered", "success", "Triggered main processing task for re-embedding.")
        log_structured(document_id, case_id, "finish_reprocessing", "completed")
        
    except Exception as e:
        log_structured(document_id, case_id, "reprocessing_error", "failed", str(e))
        db_instance.documents.update_one(
            {"_id": document_id}, 
            {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
        )
        raise