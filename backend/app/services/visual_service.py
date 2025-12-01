# FILE: backend/app/services/visual_service.py
# PHOENIX PROTOCOL - VISION SAFETY V4.1
# 1. SAFETY: Disabled by default to protect 16GB Server RAM.
# 2. FEATURE: Added 'OPENROUTER' support for Vision (if enabled).
# 3. LOGIC: Returns "Skipped" instead of crashing if no model is available.

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

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Default to FALSE to save RAM on 16GB server
VISION_ENABLED = os.getenv("VISION_ENABLED", "false").lower() == "true"
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "openrouter") # 'local' or 'openrouter'

# OpenRouter (Cheap & Fast Vision)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Google Gemini Flash is excellent and cheap for vision via OpenRouter
OPENROUTER_VISION_MODEL = "google/gemini-flash-1.5" 

# Local (Heavy)
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_VISION_MODEL = "llama3.2-vision"

def _pdf_page_to_base64(page: fitz.Page) -> str:
    """Renders a PDF page to a JPEG Base64 string."""
    try:
        mat = fitz.Matrix(1.5, 1.5) # Lower resolution to save bandwidth
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
    Tier 1: Cloud Vision (Fast, Cheap, No RAM usage).
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
                        {"type": "text", "text": f"Analyze this legal document page ({context_hint}). Identify: Signatures, Stamps, Handwritten notes."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=200
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"OpenRouter Vision Failed: {e}")
        return ""

def _analyze_image_local(base64_img: str, context_hint: str) -> str:
    """
    Tier 2: Local Vision (Heavy). Use with caution.
    """
    payload = {
        "model": LOCAL_VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": f"Describe this image ({context_hint}). Look for signatures or stamps.",
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
    Orchestrator for Visual Analysis.
    """
    if not VISION_ENABLED:
        logger.info(f"👁️ Deep Scan skipped for {document_id} (Feature Disabled).")
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
    
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            total_pages = len(doc)
            if total_pages == 0: return []

            # Scan First Page Only (Optimization)
            page_num = 0
            b64_img = _pdf_page_to_base64(doc[page_num])
            
            if b64_img:
                if VISION_PROVIDER == "openrouter":
                    analysis = _analyze_image_openrouter(b64_img, "First Page")
                else:
                    analysis = _analyze_image_local(b64_img, "First Page")
                
                if analysis:
                    new_findings.append({
                        "case_id": document.get("case_id"),
                        "document_id": doc_oid,
                        "document_name": document.get("file_name"),
                        "finding_text": f"[👁️ Analizë Vizuale]: {analysis}",
                        "source_text": "Visual Scan",
                        "page_number": 1,
                        "confidence_score": 0.90,
                        "created_at": datetime.now(timezone.utc)
                    })

        if new_findings:
            db.findings.insert_many(new_findings)
            logger.info(f"✅ Deep Scan complete. {len(new_findings)} visual notes added.")
            
        return new_findings

    except Exception as e:
        logger.error(f"Deep Scan Processing Error: {e}")
        return []