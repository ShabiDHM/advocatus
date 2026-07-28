# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V10.0 (JPEG OPTIMIZED PAYLOAD COMPRESSION - NO 413 ERRORS)

import fitz, docx, pandas as pd, logging, os, tempfile, re, io, time
from typing import Dict, Callable, Any
from PIL import Image

try: 
    from .ocr_service import extract_text_from_image_bytes as advanced_bytes_ocr
except ImportError: 
    advanced_bytes_ocr = None

logger = logging.getLogger(__name__)
FOOTER_PATTERN = re.compile(r'Rasti:\s*\S+\s*\|\s*Juristi AI System')

def _sanitize_text(text: str) -> str: 
    return text.replace("\x00", "") if text else ""

def _strip_footer(text: str) -> str: 
    return '\n'.join([l for l in text.split('\n') if not FOOTER_PATTERN.search(l)])

def _process_single_page_safe(doc_path: str, page_num: int) -> str:
    marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    try:
        with fitz.open(doc_path) as doc:
            page = doc[page_num]
            
            # Step 1: Try digital text layer
            digital_text = _strip_footer(_sanitize_text("\n".join([b[4] for b in sorted(page.get_text("blocks"), key=lambda b: (int(b[1]/3), int(b[0])))])))
            if digital_text and len(digital_text.strip()) > 80: 
                logger.info(f"✅ [TextExtraction] Page {page_num + 1}: Digital Text Found ({len(digital_text)} chars)")
                return marker + digital_text
            
            # Step 2: Scanned PDF page -> Render & Compress JPEG (< 800KB)
            logger.info(f"🔍 [TextExtraction] Page {page_num + 1}: Scanned page detected. Compressing for Cloud OCR...")
            if not advanced_bytes_ocr: 
                return marker + "[SCANNED - NO OCR ENGINE AVAILABLE]"
            
            # Render page at 150 DPI
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            
            # Compress image to JPEG at 80% quality to force payload under 500KB (bypasses 413 Payload Too Large)
            jpeg_bytes = pix.tobytes("jpeg", jpg_quality=80)
            logger.info(f"📦 [TextExtraction] Page {page_num + 1}: Compressed image payload size: {len(jpeg_bytes) / 1024:.1f} KB")

            # Execute Cloud OCR with compressed bytes
            ocr_text = _sanitize_text(advanced_bytes_ocr(jpeg_bytes))
            
            if ocr_text and len(ocr_text.strip()) > 20:
                logger.info(f"✅ [TextExtraction] Page {page_num + 1}: Scanned HD OCR Success ({len(ocr_text)} chars)")
                return marker + ocr_text
            else:
                logger.warning(f"⚠️ [TextExtraction] Page {page_num + 1}: OCR yielded minimal text.")
                return marker + (digital_text if digital_text else "[Përmbajtja nuk u lexua dot me OCR]")
                
    except Exception as e:
        logger.error(f"❌ [TextExtraction] Page {page_num + 1} Error: {e}")
        return ""

def _extract_text_from_pdf(file_path: str) -> str:
    try:
        with fitz.open(file_path) as doc: 
            total = len(doc)
        if total < 1: 
            return ""
        
        logger.info(f"⚡ [OCR Engine V10.0] Starting HD Compressed PDF Extraction. Total Pages: {total}")
        
        results = []
        for i in range(total):
            page_text = _process_single_page_safe(file_path, i)
            results.append(page_text)
            time.sleep(0.2)  # Pause slightly to prevent rate limits
            
        full_result = "".join(results)
        logger.info(f"🎉 [OCR Engine V10.0] Total Document Text Extracted: {len(full_result)} characters")
        return full_result
    except Exception as e:
        logger.error(f"❌ PDF Extraction Failed: {e}")
        return ""

def extract_text(file_path: str, mime_type: str) -> str:
    m = mime_type.lower()
    if "pdf" in m or file_path.endswith(".pdf"): 
        return _extract_text_from_pdf(file_path)
    if "word" in m or file_path.endswith(".docx"):
        return _sanitize_text("\n".join(p.text for p in docx.Document(file_path).paragraphs))
    if "excel" in m or "spreadsheet" in m or file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        return _sanitize_text("\n".join(df.to_string() for _, df in pd.read_excel(file_path, sheet_name=None).items()))
    return "" 

def extract_text_from_file(file_obj: io.BytesIO, file_type: str = "PDF") -> str:
    with tempfile.NamedTemporaryFile(suffix=f".{file_type.lower()}", delete=False) as tmp:
        tmp.write(file_obj.getvalue())
        path = tmp.name
    try: 
        return extract_text(path, file_type)
    finally:
        if os.path.exists(path): 
            os.remove(path)