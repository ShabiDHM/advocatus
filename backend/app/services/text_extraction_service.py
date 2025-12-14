# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V6.3 (PYLANCE SILENCED)
# 1. FIX: Added '# type: ignore' to page.get_text and page.get_pixmap.
# 2. STATUS: No red squiggles.

import fitz  # PyMuPDF
import docx
import pytesseract
from PIL import Image
import pandas as pd
import csv
from typing import Dict, Callable
import logging
import cv2
import numpy as np
import io
import concurrent.futures
import time

logger = logging.getLogger(__name__)

# Config: Max worker threads for OCR
MAX_WORKERS = 3 

def _sanitize_text(text: str) -> str:
    """Removes null bytes and non-printable characters."""
    if not text: return ""
    return text.replace("\x00", "")

def _process_single_page_safe(doc_path: str, page_num: int) -> str:
    """
    Robust single page processor.
    """
    page_marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    try:
        with fitz.open(doc_path) as doc:
            page = doc[page_num]
            
            # 1. Try Text Layer (Fast)
            # PHOENIX FIX: Silence Pylance on dynamic attribute
            text = page.get_text("text") # type: ignore
            if len(text.strip()) > 50:
                return page_marker + _sanitize_text(text)
            
            # 2. Try OCR (Slow)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            # PHOENIX FIX: Silence Pylance on dynamic attribute
            pix = page.get_pixmap(matrix=mat) # type: ignore
            img_data = pix.tobytes("png")
            
            img = Image.open(io.BytesIO(img_data))
            open_cv_image = np.array(img)
            
            if len(open_cv_image.shape) == 3:
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = open_cv_image

            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            denoised = cv2.medianBlur(binary, 3)

            # Extended timeout for stability
            ocr_text = pytesseract.image_to_string(denoised, lang='sqi+eng', config='--psm 1', timeout=180)
            return page_marker + _sanitize_text(ocr_text)

    except Exception as e:
        logger.warning(f"Page {page_num} failed: {e}")
        return "" 

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"🚀 Processing PDF: {file_path}")
    
    total_pages = 0
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
    except Exception:
        return ""

    # STRATEGY 1: TURBO (Parallel)
    try:
        page_args = [(file_path, i) for i in range(total_pages)]
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process_single_page_wrapper, arg): arg[1] for arg in page_args}
            
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results.append((futures[future], res))
        
        # Sort by page number
        results.sort(key=lambda x: x[0])
        final_text = "".join([r[1] for r in results])
        
        # CHECK: Did it fail?
        if "Gabim gjatë leximit" in final_text or len(final_text) < 50:
            raise ValueError("Parallel processing produced poor results.")
            
        return final_text

    except Exception as e:
        logger.warning(f"⚠️ Turbo Mode failed ({e}). Switching to SAFE MODE (Sequential)...")
        return _extract_text_sequentially(file_path, total_pages)

def _process_single_page_wrapper(args):
    # Wrapper to catch exceptions inside threads
    try:
        return _process_single_page_safe(*args)
    except Exception:
        return "Gabim gjatë leximit."

def _extract_text_sequentially(file_path: str, total_pages: int) -> str:
    """
    Slow but indestructible. Processes one page at a time.
    """
    buffer = []
    for i in range(total_pages):
        text = _process_single_page_safe(file_path, i)
        buffer.append(text)
        time.sleep(0.1) 
    return "".join(buffer)

def _extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return _sanitize_text("\n".join(para.text for para in doc.paragraphs))
    except Exception as e:
        logger.error(f"DOCX Error: {e}")
        return ""

def _extract_text_from_image(file_path: str) -> str:
    try:
        open_cv_image = cv2.imread(file_path)
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(binary, lang='sqi+eng', timeout=120) 
        return _sanitize_text(text)
    except Exception as e:
        logger.error(f"Image OCR Error: {e}")
        return ""

def _extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return _sanitize_text(f.read())
    except Exception: return ""

def _extract_text_from_csv(file_path: str) -> str:
    all_rows = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader: all_rows.append(", ".join(filter(None, row)))
        return _sanitize_text("\n".join(all_rows))
    except Exception: return ""

def _extract_text_from_excel(file_path: str) -> str:
    try:
        xls = pd.ExcelFile(file_path)
        full_text = []
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            if df.empty: continue
            full_text.append(f"--- Sheet: {sheet_name} ---")
            full_text.append(df.to_string(index=False, na_rep=""))
        return _sanitize_text("\n".join(full_text))
    except Exception: return ""

EXTRACTION_MAP: Dict[str, Callable] = {
    "application/pdf": _extract_text_from_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _extract_text_from_docx,
    "image/png": _extract_text_from_image, 
    "image/jpeg": _extract_text_from_image, 
    "image/tiff": _extract_text_from_image,
    "image/jpg": _extract_text_from_image,
    "text/plain": _extract_text_from_txt, 
    "text/csv": _extract_text_from_csv,
    "application/vnd.ms-excel": _extract_text_from_excel,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": _extract_text_from_excel
}

def extract_text(file_path: str, mime_type: str) -> str:
    normalized_mime_type = mime_type.split(';')[0].strip().lower()
    extractor = EXTRACTION_MAP.get(normalized_mime_type)
    
    if not extractor:
        if "text/" in normalized_mime_type: return _extract_text_from_txt(file_path)
        return ""
        
    return extractor(file_path)