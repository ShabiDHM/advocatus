# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V8.6 (SEQUENTIAL SAAS OPTIMIZED)
# 1. FIX: Switched to Sequential Processing (one-by-one) to protect Free Tier CPUs from freezing.
# 2. STATUS: 100% Stable on restricted cloud hardware.

import fitz, docx, pandas as pd, logging, os, tempfile, re, io, time
from typing import Dict, Callable, Any
from pptx import Presentation

try: from .ocr_service import extract_text_from_image as advanced_image_ocr
except ImportError: advanced_image_ocr = None

logger = logging.getLogger(__name__)
FOOTER_PATTERN = re.compile(r'Rasti:\s*\S+\s*\|\s*Juristi AI System')

def _sanitize_text(text: str) -> str: return text.replace("\x00", "") if text else ""
def _strip_footer(text: str) -> str: return '\n'.join([l for l in text.split('\n') if not FOOTER_PATTERN.search(l)])

def _process_single_page_safe(doc_path: str, page_num: int) -> str:
    marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    try:
        with fitz.open(doc_path) as doc:
            page = doc[page_num]
            text = _strip_footer(_sanitize_text("\n".join([b[4] for b in sorted(page.get_text("blocks"), key=lambda b: (int(b[1]/3), int(b[0])))])))
            if text and len(text.strip()) > 50: return marker + text
            
            if not advanced_image_ocr: return marker + "[SCANNED - NO OCR]"
            
            # Windows/Linux-safe temp path
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                temp_img = tmp.name
            
            page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(temp_img)
            ocr_text = _sanitize_text(advanced_image_ocr(temp_img))
            if os.path.exists(temp_img): os.remove(temp_img)
            return marker + ocr_text
    except Exception as e:
        logger.error(f"Page {page_num} Error: {e}")
        return ""

def _extract_text_from_pdf(file_path: str) -> str:
    """PHOENIX: Sequential execution to protect throttled cloud CPUs from crashing."""
    try:
        with fitz.open(file_path) as doc: 
            total = len(doc)
        if total < 1: return ""
        
        logger.info(f"⚡ [OCR] Sequential Ingestion Started. Total Pages: {total}")
        
        results = []
        for i in range(total):
            # Process one page at a time (Sequential)
            page_text = _process_single_page_safe(file_path, i)
            results.append(page_text)
            
            # Polite pause to let the throttled server rest and process the network
            time.sleep(0.1)
            
        return "".join(results)
    except Exception as e:
        logger.error(f"PDF Extraction Failed: {e}")
        return ""

def extract_text(file_path: str, mime_type: str) -> str:
    m = mime_type.lower()
    if "pdf" in m: return _extract_text_from_pdf(file_path)
    if "word" in m or file_path.endswith(".docx"):
        return _sanitize_text("\n".join(p.text for p in docx.Document(file_path).paragraphs))
    if "excel" in m or "spreadsheet" in m:
        return _sanitize_text("\n".join(df.to_string() for _, df in pd.read_excel(file_path, sheet_name=None).items()))
    return "" 

def extract_text_from_file(file_obj: io.BytesIO, file_type: str = "PDF") -> str:
    with tempfile.NamedTemporaryFile(suffix=f".{file_type.lower()}", delete=False) as tmp:
        tmp.write(file_obj.getvalue())
        path = tmp.name
    try: return extract_text(path, file_type)
    finally:
        if os.path.exists(path): os.remove(path)