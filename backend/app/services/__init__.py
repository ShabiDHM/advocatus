# FILE: backend/app/services/__init__.py
# PHOENIX PROTOCOL - SERVICE REGISTRY V2.0
# 1. UPDATE: Registered 'social_service' for Open Graph image generation.
# 2. STATUS: All services linked.

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
    findings_service,
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
    social_service, # <--- REGISTERED
    
    # Albanian Specific Services (Active Only)
    albanian_document_processor,
    albanian_language_detector,
    albanian_metadata_extractor,
    albanian_ner_service,
    albanian_rag_service
)