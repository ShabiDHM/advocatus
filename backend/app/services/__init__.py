# FILE: backend/app/services/__init__.py
# PHOENIX PROTOCOL - SERVICE REGISTRY V3.1 (PARSING SERVICE ADDED)
# 1. ADDED: parsing_service to register the new POS import logic.

from . import (
    admin_service,
    analysis_service,
    business_service,
    calendar_service,
    case_service,
    chat_service,
    conversion_service,
    deadline_service,
    document_processing_service,
    document_service,
    drafting_service,
    email_service,
    embedding_service,
    encryption_service,
    llm_service,
    ocr_service,
    report_service,
    storage_service,
    text_extraction_service,
    text_sterilization_service,
    user_service,
    vector_store_service,
    
    # PHOENIX NEW SERVICES
    archive_service,
    finance_service,
    graph_service,
    pdf_service,
    social_service,
    parsing_service, # PHOENIX FIX: Added the new service
    
    # Albanian Specific Services
    albanian_document_processor,
    albanian_language_detector,
    albanian_metadata_extractor,
    albanian_ner_service,
    albanian_rag_service
)