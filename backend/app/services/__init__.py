# FILE: backend/app/services/__init__.py

# This file marks the 'services' directory as a Python package.
# Explicitly import all service modules to make them available for package-level
# imports (e.g., `from app.services import user_service`), preventing import errors.

from . import admin_service
from . import albanian_ai_summary
from . import albanian_document_processor
from . import albanian_language_detector
from . import albanian_metadata_extractor
from . import albanian_model_manager
from . import albanian_ner_service
from . import albanian_rag_service
from . import api_key_service
from . import calendar_service
from . import case_service
from . import chat_service
from . import conversion_service
from . import deadline_service
from . import debug_albanian_detection
from . import document_processing_service
from . import document_service
from . import drafting_service
from . import embedding_service
from . import encryption_service
from . import findings_service
from . import llm_service
from . import notification_service
from . import ocr_service
from . import report_service
from . import search_service
from . import storage_service
from . import text_extraction_service
from . import text_sterilization_service
from . import user_service
from . import vector_store_service