# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V6.6 (SYNTAX COMPLIANCE)
# 1. FIXED: Expanded one-line try/except blocks to standard multi-line.
# 2. STATUS: Resolves 'Expected expression' and 'Return type' errors.

import fitz  # PyMuPDF
import docx
import pytesseract
from PIL import Image
import pandas as pd
import csv
from typing import Dict, Callable, Any
import logging
import cv2
import numpy as np
import io
import concurrent.futures
import time

logger = logging.getLogger(__name__)

# Config: Reduced workers to prevent RAM exhaustion on 23+ files
MAX_WORKERS = 2 

def _sanitize_text(text: str) -> str:
    """Removes null bytes and non-printable characters."""
    if not text: 
        return ""
    return text.replace("\x00", "")

def _process_single_page_safe(doc_path: str, page_num: int) -> str:
    page_marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    try:
        with fitz.open(doc_path) as doc:
            page: Any = doc[page_num] # Cast to Any for Pylance
            
            # 1. Try Direct Text Extraction (Fast & Clean)
            text = page.get_text("text") 
            if len(text.strip()) > 50:
                return page_marker + _sanitize_text(text)
            
            # 2. Fallback: OCR
            zoom = 1.5 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            pil_image = Image.open(io.BytesIO(img_data))
            
            # Strategy A: Advanced Pre-processing
            try:
                open_cv_image = np.array(pil_image)
                if len(open_cv_image.shape) == 3:
                    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
                else:
                    gray = open_cv_image

                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                ocr_text = pytesseract.image_to_string(binary, lang='sqi+eng', config='--psm 1', timeout=60)
                return page_marker + _sanitize_text(ocr_text)
            
            except Exception as cv_err:
                # Strategy B: Raw Image Fallback
                logger.warning(f"OpenCV failed on page {page_num}, trying raw Tesseract: {cv_err}")
                raw_text = pytesseract.image_to_string(pil_image, lang='sqi+eng', config='--psm 1', timeout=60)
                return page_marker + _sanitize_text(raw_text)

    except Exception as e:
        logger.error(f"Page {page_num} CRITICAL FAILURE: {e}")
        return "" 

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"🚀 Processing PDF: {file_path}")
    total_pages = 0
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
    except Exception: 
        return ""

    try:
        # Sequential fallback for very small docs to avoid thread overhead
        if total_pages < 3:
             return _extract_text_sequentially(file_path, total_pages)

        page_args = [(file_path, i) for i in range(total_pages)]
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process_single_page_wrapper, arg): arg[1] for arg in page_args}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results.append((futures[future], res))
        
        results.sort(key=lambda x: x[0])
        final_text = "".join([r[1] for r in results])
        
        if len(final_text.strip()) < 10:
             raise ValueError("Extracted text is empty.")
             
        return final_text

    except Exception as e:
        logger.warning(f"⚠️ Turbo Mode failed ({e}). Switching to SAFE MODE...")
        return _extract_text_sequentially(file_path, total_pages)

def _process_single_page_wrapper(args) -> str:
    try: 
        return _process_single_page_safe(*args)
    except Exception: 
        return ""

def _extract_text_sequentially(file_path: str, total_pages: int) -> str:
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
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang='sqi+eng')
        return _sanitize_text(text)
    except Exception: 
        return ""

def _extract_text_from_txt(file_path: str) -> str:
    try: 
        with open(file_path, 'r', encoding='utf-8') as f: 
            return _sanitize_text(f.read())
    except Exception: 
        return ""

def _extract_text_from_csv(file_path: str) -> str:
    all_rows = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader: 
                all_rows.append(", ".join(filter(None, row)))
        return _sanitize_text("\n".join(all_rows))
    except Exception: 
        return ""

def _extract_text_from_excel(file_path: str) -> str:
    try:
        xls = pd.ExcelFile(file_path)
        full_text = []
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            if df.empty: 
                continue
            full_text.append(f"--- Sheet: {sheet_name} ---")
            full_text.append(df.to_string(index=False, na_rep=""))
        return _sanitize_text("\n".join(full_text))
    except Exception: 
        return ""

EXTRACTION_MAP: Dict[str, Callable[[str], str]] = {
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
        if "text/" in normalized_mime_type: 
            return _extract_text_from_txt(file_path)
        return ""
        
    return extractor(file_path)