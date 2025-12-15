# FILE: backend/app/services/visual_service.py
# PHOENIX PROTOCOL - VISION SAFETY V4.2 (IMAGE SUPPORT)
# 1. FIX: Added direct support for JPG/PNG (bypassing PDF logic).
# 2. LOGIC: If input is image, analyze directly. If PDF, extract page 1.
# 3. STATUS: Vision enabled by default for immediate testing.

import os
import fitz  # PyMuPDF
import base64
import logging
import httpx
import io
import json
from PIL import Image
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone
from openai import OpenAI

# Phoenix Imports
from .storage_service import download_original_document_stream
from .ocr_service import extract_text_from_image

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# PHOENIX FIX: Default to TRUE for testing
VISION_ENABLED = os.getenv("VISION_ENABLED", "true").lower() == "true"
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "openrouter") 

# OpenRouter 
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_VISION_MODEL = "google/gemini-flash-1.5" 

# Local
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_VISION_MODEL = "llama3.2-vision"

def _image_to_base64(image_bytes: bytes) -> str:
    """Encodes raw image bytes to Base64."""
    return base64.b64encode(image_bytes).decode("utf-8")

def _pdf_page_to_base64(page: fitz.Page) -> str:
    """Renders a PDF page to a JPEG Base64 string."""
    try:
        mat = fitz.Matrix(1.5, 1.5) 
        pix = page.get_pixmap(matrix=mat) # type: ignore
        
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples) # type: ignore
        
        if mode == "RGBA":
            img = img.convert("RGB")
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Image Render Failed: {e}")
        return ""

def _analyze_image_openrouter(base64_img: str, context_hint: str) -> str:
    """
    Tier 1: Cloud Vision.
    """
    if not DEEPSEEK_API_KEY: return ""
    
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=OPENROUTER_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze this legal document ({context_hint}). 1. Extract the main text clearly. 2. Describe any stamps, signatures, or handwritten notes visible."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000 # Increased for text extraction
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"OpenRouter Vision Failed: {e}")
        return ""

def _analyze_image_local(base64_img: str, context_hint: str) -> str:
    """
    Tier 2: Local Vision.
    """
    payload = {
        "model": LOCAL_VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": f"Describe this legal document ({context_hint}). Extract visible text and identify stamps/signatures.",
            "images": [base64_img]
        }],
        "stream": False
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            if response.status_code != 200: return ""
            return response.json().get("message", {}).get("content", "")
    except Exception:
        return ""

def perform_deep_scan(db: Database, document_id: str) -> List[Dict[str, Any]]:
    """
    Orchestrator for Visual Analysis & OCR.
    """
    if not VISION_ENABLED:
        logger.info(f"👁️ Deep Scan skipped for {document_id} (Disabled).")
        return []

    logger.info(f"👁️ Starting Deep Scan for {document_id}...")
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except: return []

    if not document: return []

    # Download File
    try:
        file_stream = download_original_document_stream(document["storage_key"])
        file_bytes = file_stream.read()
        if hasattr(file_stream, 'close'): file_stream.close()
    except Exception as e:
        logger.error(f"Deep Scan Download Failed: {e}")
        return []
    
    new_findings = []
    mime_type = document.get("mime_type", "").lower()
    file_name = document.get("file_name", "").lower()
    
    analysis = ""

    # STRATEGY SELECTOR
    try:
        # PATH A: IMAGE FILE (JPG/PNG)
        if "image" in mime_type or file_name.endswith(('.jpg', '.jpeg', '.png')):
            logger.info("Deep Scan: Detected Image Format.")
            b64_img = _image_to_base64(file_bytes)
            
            if VISION_PROVIDER == "openrouter":
                analysis = _analyze_image_openrouter(b64_img, "Full Image")
            else:
                analysis = _analyze_image_local(b64_img, "Full Image")

        # PATH B: PDF FILE
        elif "pdf" in mime_type or file_name.endswith('.pdf'):
            logger.info("Deep Scan: Detected PDF Format.")
            with fitz.open(stream=file_bytes, filetype="pdf") as pdf_doc:
                if len(pdf_doc) > 0:
                    # Scan First Page
                    b64_img = _pdf_page_to_base64(pdf_doc[0])
                    if VISION_PROVIDER == "openrouter":
                        analysis = _analyze_image_openrouter(b64_img, "Page 1")
                    else:
                        analysis = _analyze_image_local(b64_img, "Page 1")

        # RESULT PROCESSING
        if analysis:
            new_findings.append({
                "case_id": document.get("case_id"),
                "document_id": doc_oid,
                "document_name": document.get("file_name"),
                "finding_text": f"[👁️ Analizë Vizuale]: {analysis}",
                "source_text": "AI Vision Scan",
                "category": "OCR_VISION",
                "page_number": 1,
                "confidence_score": 0.95,
                "created_at": datetime.now(timezone.utc)
            })

            # Also update the document summary if it was missing
            db.documents.update_one(
                {"_id": doc_oid},
                {"$set": {"summary": analysis[:500] + "..."}}
            )

        if new_findings:
            # Clear old visual findings to avoid duplicates
            db.findings.delete_many({"document_id": doc_oid, "category": "OCR_VISION"})
            db.findings.insert_many(new_findings)
            logger.info(f"✅ Deep Scan complete. Added visual analysis.")
            
        return new_findings

    except Exception as e:
        logger.error(f"Deep Scan Processing Error: {e}")
        return []