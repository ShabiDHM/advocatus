# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL MODIFICATION 12.0 (STATIC ANALYSIS HYGIENE):
# 1. QUALITY FIX: Added `# type: ignore` comments to the `get_pixmap` and `get_text` calls.
# 2. This is the standard, architecturally correct way to suppress false-positive errors
#    from static analysis tools like Pylance when a library (PyMuPDF) uses dynamic attributes.

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

logger = logging.getLogger(__name__)

def _perform_ocr_on_pdf_page(page: fitz.Page) -> str:
    try:
        zoom = 3
        mat = fitz.Matrix(zoom, zoom)
        # --- PHOENIX PROTOCOL FIX: Suppress false-positive static analysis error ---
        pix = page.get_pixmap(matrix=mat) # type: ignore
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        open_cv_image = np.array(img)
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        denoised = cv2.medianBlur(binary, 3)

        return pytesseract.image_to_string(denoised, lang='sqi+eng', timeout=180)

    except Exception as ocr_error:
        logger.error(f"Advanced OCR failed for a page: {ocr_error}", exc_info=True)
        return ""

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"--- [PDF Processing] Starting extraction for {file_path} ---")
    full_text = []
    try:
        with fitz.open(file_path) as doc:
            for i in range(len(doc)):
                page = doc[i]
                # --- PHOENIX PROTOCOL FIX: Suppress false-positive static analysis error ---
                text = page.get_text("text") # type: ignore
                
                if len(text.strip()) < 100:
                    logger.warning(f"--- [PDF Processing] Page {i+1}: Direct text is minimal. Attempting ADVANCED OCR fallback. ---")
                    ocr_text = _perform_ocr_on_pdf_page(page)
                    full_text.append(ocr_text)
                else:
                    full_text.append(text)
        
        final_text = "\n".join(full_text)
        logger.info(f"--- [PDF Processing] Completed. Total chars extracted: {len(final_text)} ---")
        return final_text

    except Exception as e:
        logger.error(f"Critical error processing PDF {file_path}: {e}", exc_info=True)
        return ""

# ... (All other extraction functions remain unchanged) ...
def _extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        logger.error(f"Error processing DOCX {file_path}: {e}", exc_info=True)
        return ""

def _extract_text_from_image(file_path: str) -> str:
    try:
        open_cv_image = cv2.imread(file_path)
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        denoised = cv2.medianBlur(binary, 3)
        return pytesseract.image_to_string(denoised, lang='sqi+eng', timeout=120)
    except Exception as e:
        logger.error(f"Error performing OCR on {file_path}: {e}", exc_info=True)
        return ""

def _extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return f.read()
    except Exception:
        try:
            with open(file_path, 'r', encoding='latin-1') as f: return f.read()
        except Exception as e2:
            logger.error(f"Error processing TXT {file_path}: {e2}", exc_info=True)
            return ""

def _extract_text_from_csv(file_path: str) -> str:
    all_rows = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                all_rows.append(", ".join(filter(None, row)))
        return "\n".join(all_rows)
    except Exception as e:
        logger.error(f"Error processing CSV {file_path}: {e}", exc_info=True)
        return ""

def _extract_text_from_excel(file_path: str) -> str:
    try:
        xls = pd.ExcelFile(file_path)
        full_text = []
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            if df.empty: continue
            full_text.append(f"--- Sheet: {sheet_name} ---")
            headers = [str(h) for h in df.columns]
            for index, row in df.iterrows():
                row_data = [f"{header}: {value}" for header, value in zip(headers, row) if pd.notna(value) and str(value).strip()]
                if row_data:
                    full_text.append(", ".join(row_data) + ".")
            full_text.append("")
        return "\n".join(full_text)
    except Exception as e:
        logger.error(f"Error processing Excel file {file_path}: {e}", exc_info=True)
        return ""

EXTRACTION_MAP: Dict[str, Callable] = {
    "application/pdf": _extract_text_from_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _extract_text_from_docx,
    "image/png": _extract_text_from_image, "image/jpeg": _extract_text_from_image, "image/tiff": _extract_text_from_image,
    "text/plain": _extract_text_from_txt, "text/csv": _extract_text_from_csv,
    "application/vnd.ms-excel": _extract_text_from_excel,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": _extract_text_from_excel
}

def extract_text(file_path: str, mime_type: str) -> str:
    normalized_mime_type = mime_type.split(';')[0].strip()
    extractor = EXTRACTION_MAP.get(normalized_mime_type)
    
    if not extractor:
        logger.warning(f"--- [Text Extraction] No extractor for MIME type: {normalized_mime_type}. ---")
        return ""
        
    logger.info(f"--- [Text Extraction] Using extractor for {normalized_mime_type}... ---")
    return extractor(file_path)