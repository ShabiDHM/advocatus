# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V4.1
# 1. HYBRID OCR: Uses PyMuPDF for digital text and Tesseract for scans.
# 2. ALBANIAN SUPPORT: Configured Tesseract with 'sqi+eng' language data.
# 3. SAFETY: Null-byte sanitization to prevent Database/LLM injection errors.

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

logger = logging.getLogger(__name__)

def _sanitize_text(text: str) -> str:
    """Removes null bytes and non-printable characters that crash downstream services."""
    if not text: return ""
    return text.replace("\x00", "")

def _perform_ocr_on_pdf_page(page: fitz.Page) -> str:
    """
    Renders a PDF page as an image and runs Tesseract OCR.
    Used when direct text extraction yields empty results (Scanned PDF).
    """
    try:
        # Zoom = 2.0 is a good balance between speed and accuracy for legal docs
        zoom = 2.0 
        mat = fitz.Matrix(zoom, zoom)
        
        # Suppress static analysis errors for dynamic PyMuPDF attributes
        pix = page.get_pixmap(matrix=mat) # type: ignore
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Pre-processing with OpenCV
        open_cv_image = np.array(img)
        
        # Convert to grayscale
        if len(open_cv_image.shape) == 3:
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
        else:
            gray = open_cv_image

        # Thresholding to isolate text
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoising
        denoised = cv2.medianBlur(binary, 3)

        # Run Tesseract with Albanian + English support
        # --psm 1: Automatic page segmentation with OSD (Orientation and Script Detection)
        text = pytesseract.image_to_string(denoised, lang='sqi+eng', config='--psm 1', timeout=120)
        return _sanitize_text(text)

    except Exception as ocr_error:
        logger.error(f"OCR failed for page: {ocr_error}")
        return ""

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"📄 Processing PDF: {file_path}")
    full_text = []
    try:
        with fitz.open(file_path) as doc:
            for i in range(len(doc)):
                page = doc[i]
                
                # 1. Try fast direct extraction
                text = page.get_text("text") # type: ignore
                
                # 2. Heuristic: If less than 50 chars, assume it's a scan/image
                if len(text.strip()) < 50:
                    logger.info(f"Page {i+1} appears scanned. Running OCR...")
                    ocr_text = _perform_ocr_on_pdf_page(page)
                    full_text.append(ocr_text)
                else:
                    full_text.append(_sanitize_text(text))
        
        final_text = "\n".join(full_text)
        logger.info(f"✅ PDF Extraction Complete. Length: {len(final_text)} chars.")
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
            
            # Convert full dataframe to string representation
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
    # Normalize MIME type (remove charset info)
    normalized_mime_type = mime_type.split(';')[0].strip().lower()
    
    extractor = EXTRACTION_MAP.get(normalized_mime_type)
    
    if not extractor:
        # Fallback for generic text types
        if "text/" in normalized_mime_type:
            return _extract_text_from_txt(file_path)
            
        logger.warning(f"No extractor for MIME type: {normalized_mime_type}")
        return ""
        
    return extractor(file_path)