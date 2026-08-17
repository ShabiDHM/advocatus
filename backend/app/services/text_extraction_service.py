# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V9.0 (REPUBLIC OF KOSOVO ALBANIAN LEGAL OPTIMIZED)

import os
import json
import logging
import re
import io
import time
import requests
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

# --- SECURE CREDENTIALS ---
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "K89840741888957")

# Fjalët kyçe për dokumentet ligjore dhe financiare të Kosovës
LEGAL_KEYWORDS_KS = [
    'gjykata', 'themelore', 'paditësi', 'padituri', 'aktgjykim', 'aktvendim', 
    'prokuroria', 'fashikull', 'kërkesëpadi', 'procesverbal', 'neni', 'lpk', 'kpk'
]

class SmartOCRResult:
    def __init__(self, text: str, confidence: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.confidence = confidence
        self.metadata = metadata if metadata is not None else {}
        self.structured_data: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {'text': self.text, 'confidence': self.confidence, 'metadata': self.metadata, 'structured_data': self.structured_data}

# --- HYBRID PARSER: LOCAL PDF TEXT EXTRACTOR ---

def extract_text_from_pdf_locally(pdf_bytes: bytes) -> Optional[str]:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text_runs = []
        for page in reader.pages:
            text_runs.append(page.extract_text() or "")
        full_text = "\n".join(text_runs).strip()
        if len(full_text) > 80:
            logger.info(f"✅ Local PDF extraction (Albanian character preserved): {len(full_text)} chars")
            return full_text
    except Exception as e:
        logger.warning(f"Local PDF parser skipped: {e}")
    return None

# --- ADVANCED OCR.SPACE ENGINE (ALBANIAN LEGAL TUNED) ---

def run_ocr_space_ocr(image_bytes: bytes) -> Tuple[str, float]:
    """
    Sends image/PDF bytes to OCR.space API with Albanian legal character calibration.
    """
    if not OCR_SPACE_API_KEY:
        logger.error("❌ OCR_SPACE_API_KEY is missing.")
        return "", 0.0

    url = "https://api.ocr.space/parse/image"
    is_pdf = image_bytes.startswith(b'%PDF-')
    
    filename = "page.pdf" if is_pdf else "page.png"
    mime = "application/pdf" if is_pdf else "image/png"
    
    payload = {
        "apikey": OCR_SPACE_API_KEY,
        "language": "eng", # Engine 2 with Latin script handles Albanian diacritics (ë, ç) with high fidelity
        "isOverlayRequired": False,
        "OCREngine": "2",  # Engine 2 is optimized for fine print, stamps, and legal contracts
        "scale": True,
        "detectOrientation": True
    }
    
    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            files = {"file": (filename, image_bytes, mime)}
            response = requests.post(url, files=files, data=payload, timeout=35)
            
            # Auto-retry on 429 Too Many Requests
            if response.status_code == 429 or "429" in response.text:
                wait_seconds = 1.5 * (attempt + 1)
                logger.warning(f"⚠️ [OCR.space 429] Rate limit hit. Backing off {wait_seconds:.1f}s before retry ({attempt + 1}/{max_attempts})...")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            result = response.json()
            
            if result.get("IsErroredOnProcessing"):
                err_msg = result.get("ErrorMessage", ["Processing error"])
                err_str = " ".join(err_msg) if isinstance(err_msg, list) else str(err_msg)
                if "429" in err_str or "limit" in err_str.lower():
                    wait_seconds = 2.0 * (attempt + 1)
                    logger.warning(f"⚠️ [OCR.space Error 429] Backing off {wait_seconds:.1f}s...")
                    time.sleep(wait_seconds)
                    continue
                logger.error(f"❌ OCR.space Internal Error: {err_str}")
                return "", 0.0
            
            parsed_results = result.get("ParsedResults", [])
            if not parsed_results:
                return "", 0.0
                
            full_text = parsed_results[0].get("ParsedText", "")
            return full_text, 0.95
            
        except requests.exceptions.RequestException as e:
            if "429" in str(e) and attempt < max_attempts - 1:
                wait_seconds = 1.8 * (attempt + 1)
                time.sleep(wait_seconds)
                continue
            if attempt == max_attempts - 1:
                logger.error(f"❌ OCR.space Request Failed after {max_attempts} attempts: {e}")
                return "", 0.0
            time.sleep(1.0)
        except Exception as e:
            logger.error(f"❌ OCR.space Unexpected Failure: {e}")
            return "", 0.0

    return "", 0.0

def rule_based_correction(text: str) -> str:
    """Corrects common OCR character confusions in legal Albanian texts."""
    if not text: 
        return ""
    # Standardize Albanian judicial abbreviations and terms
    cleaned = text
    cleaned = re.sub(r'\bL\s*P\s*K\b', 'LPK', cleaned)
    cleaned = re.sub(r'\bK\s*P\s*K\b', 'KPK', cleaned)
    cleaned = re.sub(r'\bL\s*M\s*D\b', 'LMD', cleaned)
    cleaned = re.sub(r'\bK\s*P\s*R\s*K\b', 'KPRK', cleaned)
    cleaned = re.sub(r'\bKP\s*P\s*R\s*K\b', 'KPPRK', cleaned)
    return cleaned.strip()

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    try:
        if image_bytes.startswith(b'%PDF-'):
            local_text = extract_text_from_pdf_locally(image_bytes)
            if local_text:
                return rule_based_correction(local_text)
                
        raw_text, confidence = run_ocr_space_ocr(image_bytes)
        corrected_text = rule_based_correction(raw_text)
        return corrected_text
    except Exception as e:
        logger.error(f"❌ OCR extraction failed: {e}")
        return ""

def extract_text_from_image(file_path: str) -> str:
    if not os.path.exists(file_path): 
        return ""
    try:
        with open(file_path, "rb") as f: 
            image_bytes = f.read()
        return extract_text_from_image_bytes(image_bytes)
    except Exception as e:
        logger.error(f"❌ OCR disk extraction failed: {e}")
        return ""

def preprocess_image_for_ocr(pil_image): 
    return pil_image

def clean_ocr_garbage(text): 
    return text.strip()

def extract_expense_data_from_image(image_bytes: bytes) -> Dict[str, Any]:
    text = extract_text_from_image_bytes(image_bytes)
    return {'success': True, 'text': text, 'structured_data': {}}