# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V7.1 (10s HARD API TIMEOUT)

import os
import json
import logging
import re
import io
import requests
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "K89840741888957")

def extract_text_from_pdf_locally(pdf_bytes: bytes) -> Optional[str]:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text_runs = []
        for page in reader.pages:
            text_runs.append(page.extract_text() or "")
        full_text = "\n".join(text_runs).strip()
        if len(full_text) > 80:
            return full_text
    except Exception:
        pass
    return None

def run_ocr_space_ocr(image_bytes: bytes) -> Tuple[str, float]:
    if not OCR_SPACE_API_KEY:
        return "", 0.0

    url = "https://api.ocr.space/parse/image"
    is_pdf = image_bytes.startswith(b'%PDF-')
    
    files = {"file": ("page.pdf" if is_pdf else "page.png", image_bytes, "application/pdf" if is_pdf else "image/png")}
    payload = {
        "apikey": OCR_SPACE_API_KEY,
        "language": "eng", 
        "OCREngine": "2",
        "scale": True,
        "detectOrientation": True
    }
    
    try:
        response = requests.post(url, files=files, data=payload, timeout=10) # 10s strict timeout
        response.raise_for_status()
        result = response.json()
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            return "", 0.0
        return parsed_results[0].get("ParsedText", ""), 0.95
    except Exception as e:
        logger.warning(f"⚠️ OCR.space API timeout or error: {e}")
        return "", 0.0

def rule_based_correction(text: str) -> str:
    if not text: return text
    text = re.sub(r'SPARKOSOVA', 'SPAR KOSOVA', text, flags=re.IGNORECASE)
    return text.strip()

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    try:
        if image_bytes.startswith(b'%PDF-'):
            local_text = extract_text_from_pdf_locally(image_bytes)
            if local_text:
                return rule_based_correction(local_text)
                
        raw_text, confidence = run_ocr_space_ocr(image_bytes)
        return rule_based_correction(raw_text)
    except Exception as e:
        logger.error(f"❌ OCR extraction failed: {e}")
        return ""

def extract_text_from_image(file_path: str) -> str:
    if not os.path.exists(file_path): return ""
    try:
        with open(file_path, "rb") as f: image_bytes = f.read()
        return extract_text_from_image_bytes(image_bytes)
    except Exception:
        return ""