# FILE: backend/app/services/__init__.py
# PHOENIX PROTOCOL - SERVICE REGISTRY
# Added 'email_service'

from . import (
    admin_service,
    analysis_service,
    api_key_service,
    calendar_service,
    case_service,
    chat_service,
    conversion_service,
    deadline_service,
    document_processing_service,
    document_service,
    drafting_service,
    email_service, # <--- ADDED
    embedding_service,
    encryption_service,
    findings_service,
    llm_service,
    ocr_service,
    report_service,
    storage_service,
    text_extraction_service,
    text_sterilization_service,
    user_service,
    vector_store_service,
    
    # Albanian Specific Services
    albanian_ai_summary,
    albanian_document_processor,
    albanian_language_detector,
    albanian_metadata_extractor,
    albanian_model_manager,
    albanian_ner_service,
    albanian_rag_service
)