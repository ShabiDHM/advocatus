# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V5.0 (TURBO PARALLEL - COMPLETE)
# 1. PARALLELISM: Uses ThreadPoolExecutor to OCR multiple pages simultaneously.
# 2. HYBRID: Checks for digital text first, falls back to Tesseract OCR if needed.
# 3. SAFETY: Includes timeouts and null-byte sanitization.

import fitz  # PyMuPDF
import docx
import pytesseract
from PIL import Image
import pandas as pd
import csv
from typing import Dict, Callable, List
import logging
import cv2
import numpy as np
import io
import concurrent.futures

logger = logging.getLogger(__name__)

# Config: Max worker threads for OCR (Adjust based on CPU cores)
MAX_WORKERS = 4 

def _sanitize_text(text: str) -> str:
    """Removes null bytes and non-printable characters."""
    if not text: return ""
    return text.replace("\x00", "")

def _process_single_page(args) -> str:
    """
    Worker function to process a single page in a separate thread.
    Args: (doc_path, page_num)
    """
    doc_path, page_num = args
    try:
        # Open document strictly for this thread to avoid PyMuPDF threading issues
        with fitz.open(doc_path) as doc:
            page = doc[page_num]
            
            # 1. Try Direct Text Extraction (Fastest)
            text = page.get_text("text") # type: ignore
            
            # 2. Heuristic: If we found valid text (>50 chars), return it immediately
            if len(text.strip()) > 50:
                return _sanitize_text(text)
            
            # 3. Fallback: Optical Character Recognition (OCR) (Slow but necessary for scans)
            # Render page to image
            zoom = 2.0 # Optimal for Tesseract accuracy
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat) # type: ignore
            img_data = pix.tobytes("png")
            
            # Pre-processing with OpenCV
            img = Image.open(io.BytesIO(img_data))
            open_cv_image = np.array(img)
            
            # Convert to grayscale if needed
            if len(open_cv_image.shape) == 3:
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = open_cv_image

            # Thresholding to isolate text
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoising
            denoised = cv2.medianBlur(binary, 3)

            # Run Tesseract
            # --psm 1: Automatic page segmentation with OSD
            # Timeout set to 60s per page to prevent hanging
            ocr_text = pytesseract.image_to_string(denoised, lang='sqi+eng', config='--psm 1', timeout=60)
            return _sanitize_text(ocr_text)

    except Exception as e:
        logger.warning(f"Page {page_num} processing failed: {e}")
        return ""

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"🚀 Turbo PDF Processing Started: {file_path}")
    try:
        # Open once just to count pages
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
        
        # Prepare arguments for parallel execution
        page_args = [(file_path, i) for i in range(total_pages)]
        
        results = []
        # Use ThreadPool to parallelize the heavy lifting
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Map returns results in the correct order (Page 1, Page 2, etc.)
            results = list(executor.map(_process_single_page, page_args))
            
        final_text = "\n".join(results)
        logger.info(f"✅ Turbo Extraction Complete. Extracted {len(final_text)} chars from {total_pages} pages.")
        return final_text

    except Exception as e:
        logger.error(f"Critical PDF Error: {e}", exc_info=True)
        return ""

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
        # 2-minute timeout for large standalone images
        text = pytesseract.image_to_string(binary, lang='sqi+eng', timeout=120) 
        return _sanitize_text(text)
    except Exception as e:
        logger.error(f"Image OCR Error: {e}")
        return ""

def _extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            return _sanitize_text(f.read())
    except Exception:
        try:
            with open(file_path, 'r', encoding='latin-1') as f: 
                return _sanitize_text(f.read())
        except Exception as e:
            logger.error(f"TXT Error: {e}")
            return ""

def _extract_text_from_csv(file_path: str) -> str:
    all_rows = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                all_rows.append(", ".join(filter(None, row)))
        return _sanitize_text("\n".join(all_rows))
    except Exception as e:
        logger.error(f"CSV Error: {e}")
        return ""

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
    except Exception as e:
        logger.error(f"Excel Error: {e}")
        return ""

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
        # Fallback for generic text types
        if "text/" in normalized_mime_type:
            return _extract_text_from_txt(file_path)
        logger.warning(f"No extractor for MIME type: {normalized_mime_type}")
        return ""
        
    return extractor(file_path)