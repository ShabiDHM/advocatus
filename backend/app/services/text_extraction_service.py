# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V7.1 (TYPE SAFETY FIX)
# 1. FIX: Cast 'page' to 'Any' to silence Pylance error on 'get_text'.
# 2. STATUS: Error free.

import fitz  # PyMuPDF
import docx
from pptx import Presentation # Requires python-pptx
import pandas as pd
import csv
from typing import Dict, Callable, Any
import logging
import cv2
import numpy as np
import io
import concurrent.futures
import time
import os

# Link to our advanced OCR engine
try:
    from .ocr_service import extract_text_from_image as advanced_image_ocr
except ImportError:
    advanced_image_ocr = None

logger = logging.getLogger(__name__)

MAX_WORKERS = 2 

def _sanitize_text(text: str) -> str:
    if not text: return ""
    return text.replace("\x00", "")

def _process_single_page_safe(doc_path: str, page_num: int) -> str:
    page_marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    try:
        with fitz.open(doc_path) as doc:
            # PHOENIX FIX: Cast to Any to silence Pylance error regarding 'get_text'
            page: Any = doc[page_num]
            
            # 1. Direct Text
            text = page.get_text("text") 
            if len(text.strip()) > 50:
                return page_marker + _sanitize_text(text)
            
            # 2. Fallback: Render to Image and use Advanced OCR
            zoom = 1.5 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat) 
            img_data = pix.tobytes("png")
            
            # Save temp file for OCR service (it expects a path)
            temp_img_path = f"/tmp/page_{page_num}_{os.getpid()}.png"
            with open(temp_img_path, "wb") as f:
                f.write(img_data)
            
            try:
                if advanced_image_ocr:
                    ocr_text = advanced_image_ocr(temp_img_path)
                else:
                    ocr_text = "" # Fallback if import failed
            finally:
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)

            return page_marker + _sanitize_text(ocr_text)

    except Exception as e:
        logger.error(f"Page {page_num} CRITICAL FAILURE: {e}")
        return "" 

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"🚀 Processing PDF: {file_path}")
    total_pages = 0
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
    except Exception: return ""

    if total_pages < 3:
         return _extract_text_sequentially(file_path, total_pages)

    try:
        page_args = [(file_path, i) for i in range(total_pages)]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process_single_page_wrapper, arg): arg[1] for arg in page_args}
            for future in concurrent.futures.as_completed(futures):
                results.append((futures[future], future.result()))
        
        results.sort(key=lambda x: x[0])
        final_text = "".join([r[1] for r in results])
        
        if len(final_text.strip()) < 10: raise ValueError("Empty result")
        return final_text
    except Exception:
        return _extract_text_sequentially(file_path, total_pages)

def _process_single_page_wrapper(args) -> str:
    try: return _process_single_page_safe(*args)
    except Exception: return ""

def _extract_text_sequentially(file_path: str, total_pages: int) -> str:
    buffer = []
    for i in range(total_pages):
        buffer.append(_process_single_page_safe(file_path, i))
        time.sleep(0.1) 
    return "".join(buffer)

def _extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return _sanitize_text("\n".join(para.text for para in doc.paragraphs))
    except Exception as e:
        logger.error(f"DOCX Error: {e}")
        return ""

def _extract_text_from_pptx(file_path: str) -> str:
    try:
        prs = Presentation(file_path)
        text_runs = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text_runs.append(shape.text)
        return _sanitize_text("\n".join(text_runs))
    except Exception as e:
        logger.error(f"PPTX Error: {e}")
        return ""

def _extract_text_from_image(file_path: str) -> str:
    if advanced_image_ocr:
        return _sanitize_text(advanced_image_ocr(file_path))
    return ""

def _extract_text_from_txt(file_path: str) -> str:
    try: 
        with open(file_path, 'r', encoding='utf-8') as f: 
            return _sanitize_text(f.read())
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

EXTRACTION_MAP: Dict[str, Callable[[str], str]] = {
    "application/pdf": _extract_text_from_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _extract_text_from_docx,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": _extract_text_from_pptx,
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
        # Fallback for images masquerading as octet-stream
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            return _extract_text_from_image(file_path)
        if "text/" in normalized_mime_type: 
            return _extract_text_from_txt(file_path)
        return ""
        
    return extractor(file_path)