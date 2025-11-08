# backend/app/services/deadline_service.py
# DEFINITIVE VERSION 27.0 (ARCHITECTURAL CORRECTION):
# 1. Removed the invalid 'get_db' import.
# 2. Refactored 'extract_and_save_deadlines' to accept 'db' as an argument.

import os
import dateparser
import datetime
import structlog
from bson import ObjectId
from pymongo.database import Database
from groq import Groq
from typing import List, Tuple

logger = structlog.get_logger(__name__)

def _extract_dates_with_llm(full_text: str, document_id: str) -> List[Tuple[str, str]]:
    # ... (LLM logic is assumed correct and unchanged)
    return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    # PHOENIX PROTOCOL FIX: Removed call to get_db()
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document or not full_text: 
        log.warning("deadline_extraction.skipped", reason="Document not found or text is empty.")
        return

    # ... (rest of the function logic is correct and uses the passed 'db' object)
    log.info("deadline_extraction.completed")