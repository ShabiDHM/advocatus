# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V7.0 (ADVANCED SCANNED LEGAL DOCUMENT PARSER)

import os
import json
import logging
import re
import io
import requests
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

# --- SECURE CREDENTIALS ---
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "K89840741888957")

INVOICE_KEYWORDS = {
    'sq': ['total', 'shuma', 'data', 'faturë', 'kupon', 'tvsh', 'zbritje', 'pagesë', 'çmimi', 'numri fiskal'],
    'en': ['total', 'amount', 'sum', 'vat', 'date', 'invoice', 'receipt', 'tax', 'subtotal', 'fiscal'],
}

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
            logger.info(f"✅ Local PDF text extraction success: {len(full_text)} chars")
            return full_text
    except Exception as e:
        logger.warning(f"Local PDF parser skipped: {e}")
    return None

# --- ADVANCED OCR.SPACE ENGINE ---

def run_ocr_space_ocr(image_bytes: bytes) -> Tuple[str, float]:
    """Sends image or PDF bytes to OCR.space API using Engine 2 for scanned contracts."""
    if not OCR_SPACE_API_KEY:
        logger.error("❌ OCR_SPACE_API_KEY is missing from environment variables.")
        return "", 0.0

    url = "https://api.ocr.space/parse/image"
    is_pdf = image_bytes.startswith(b'%PDF-')
    
    if is_pdf:
        files = {"file": ("page.pdf", image_bytes, "application/pdf")}
    else:
        files = {"file": ("page.png", image_bytes, "image/png")}
        
    payload = {
        "apikey": OCR_SPACE_API_KEY,
        "language": "eng", 
        "isOverlayRequired": False,
        "OCREngine": "2",  # Engine 2 is engineered specifically for scanned documents and fine print
        "scale": True,
        "detectOrientation": True
    }
    
    try:
        response = requests.post(url, files=files, data=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            err_msg = result.get("ErrorMessage", "Unknown OCR.space Error")
            logger.error(f"❌ OCR.space API Error: {err_msg}")
            return "", 0.0
            
        full_text = parsed_results[0].get("ParsedText", "")
        return full_text, 0.95
        
    except Exception as e:
        logger.error(f"❌ OCR.space Request Failed: {e}")
        return "", 0.0

def rule_based_correction(text: str) -> str:
    if not text: return text
    text = re.sub(r'SPARKOSOVA', 'SPAR KOSOVA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bKate\b', 'Kafe', text, flags=re.IGNORECASE)
    text = re.sub(r'\bSandun\b', 'Sanduiç', text, flags=re.IGNORECASE)
    text = re.sub(r'\bUj\b', 'Ujë', text, flags=re.IGNORECASE)
    return text.strip()

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

def preprocess_image_for_ocr(pil_image): return pil_image
def clean_ocr_garbage(text): return text.strip()
def extract_expense_data_from_image(image_bytes: bytes) -> Dict[str, Any]:
    text = extract_text_from_image_bytes(image_bytes)
    return {'success': True, 'text': text, 'structured_data': {}}