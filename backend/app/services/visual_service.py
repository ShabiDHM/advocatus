# FILE: backend/app/services/visual_service.py
# PHOENIX PROTOCOL - VISION INTELLIGENCE (FIXED)
# 1. FIX: Added missing 'os' import.
# 2. TYPE SAFETY: Suppressed Pylance false positives for PyMuPDF.
# 3. LOGIC: Renders PDF to Images -> Sends to Local Vision AI.

import os
import fitz  # PyMuPDF
import base64
import logging
import httpx
import io
from PIL import Image
from typing import List, Dict, Any
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
VISION_MODEL = "llama3.2-vision"

def _pdf_page_to_base64(page: fitz.Page) -> str:
    """Renders a PDF page to a JPEG Base64 string."""
    # Zoom = 2.0 for decent resolution
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat) # type: ignore
    
    # PyMuPDF to PIL
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples) # type: ignore
    
    # Ensure RGB for JPEG
    if mode == "RGBA":
        img = img.convert("RGB")
    
    # Convert to JPEG Buffer
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def _analyze_image_with_ollama(base64_img: str, context_hint: str) -> str:
    """Asks the Vision Model to describe the image."""
    prompt = f"""
    Analyze this image of a legal document page ({context_hint}).
    Look specifically for:
    1. Handwritten notes or amendments (Describe them).
    2. Signatures (Are they present? Who signed?).
    3. Official Stamps or Seals.
    
    Return a concise summary. If nothing special is found, strictly say "No visual anomalies."
    """
    
    payload = {
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": prompt,
            "images": [base64_img]
        }],
        "stream": False
    }
    
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            if response.status_code == 404:
                logger.error("❌ Vision model not found in Ollama.")
                return "Error: Vision model missing."
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"Visual Analysis Failed: {e}")
        return ""

def perform_deep_scan(db: Database, document_id: str) -> List[Dict[str, Any]]:
    """
    Main entry point. Scans First and Last page of the document.
    """
    logger.info(f"👁️ Starting Deep Scan for {document_id}...")
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except:
        return []

    if not document: return []

    # Download File
    from .storage_service import download_original_document_stream
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

            # Scan First and Last Page
            pages_to_check = [0]
            if total_pages > 1:
                pages_to_check.append(total_pages - 1)

            for page_num in pages_to_check:
                page_label = "First Page" if page_num == 0 else "Last Page"
                logger.info(f"   ↳ Scanning Page {page_num + 1} ({page_label})...")
                
                b64_img = _pdf_page_to_base64(doc[page_num])
                analysis = _analyze_image_with_ollama(b64_img, page_label)
                
                if analysis and "No visual anomalies" not in analysis and "Error" not in analysis:
                    new_findings.append({
                        "case_id": document.get("case_id"),
                        "document_id": doc_oid,
                        "document_name": document.get("file_name"),
                        "finding_text": f"[👁️ Visual Scan - Pg {page_num+1}]: {analysis}",
                        "source_text": "Visual Analysis",
                        "page_number": page_num + 1,
                        "confidence_score": 0.95,
                        "created_at": datetime.now(timezone.utc)
                    })

        if new_findings:
            db.findings.insert_many(new_findings)
            logger.info(f"✅ Deep Scan complete. Found {len(new_findings)} visual items.")
        else:
            logger.info("✅ Deep Scan complete. No anomalies.")
            
        return new_findings

    except Exception as e:
        logger.error(f"Deep Scan Processing Error: {e}")
        return []