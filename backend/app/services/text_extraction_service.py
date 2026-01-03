# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR ENGINE V8.4 (ROBUST STREAM HANDLER)
# 1. FIX: 'extract_text_from_file' now correctly parses the filename to determine the extension.
# 2. STATUS: Resolves the 500 Internal Server Error during Deposition Analysis.

import fitz  # PyMuPDF
import docx
from pptx import Presentation
import pandas as pd
import csv
from typing import Dict, Callable, Any, Optional
import logging
import io
import concurrent.futures
import time
import os
import tempfile
import uuid

# Link to OCR (optional)
try:
    from .ocr_service import extract_text_from_image as advanced_image_ocr
except ImportError:
    advanced_image_ocr = None

logger = logging.getLogger(__name__)

MAX_WORKERS = 2 

def _sanitize_text(text: str) -> str:
    if not text: return ""
    return text.replace("\x00", "")

def _sort_blocks(blocks):
    return sorted(blocks, key=lambda b: (int(b[1] / 3), int(b[0])))

def _process_single_page_safe(doc_path: str, page_num: int) -> str:
    page_marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    try:
        with fitz.open(doc_path) as doc:
            page: Any = doc[page_num]
            
            blocks = page.get_text("blocks")
            text = ""
            if blocks:
                sorted_blocks = _sort_blocks(blocks)
                text = "\n".join([b[4] for b in sorted_blocks])

            if text and len(text.strip()) > 50:
                return page_marker + _sanitize_text(text)
            
            logger.info(f"Page {page_num} seems scanned. Engaging Optical OCR...")
            
            if not advanced_image_ocr:
                return page_marker + "[SCANNED DOCUMENT - NO OCR AVAILABLE]"

            zoom = 2.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat) 
            img_data = pix.tobytes("png")
            
            temp_img_path = f"/tmp/page_{page_num}_{uuid.uuid4()}.png"
            with open(temp_img_path, "wb") as f:
                f.write(img_data)
            
            ocr_text = ""
            try:
                ocr_text = advanced_image_ocr(temp_img_path)
            except Exception as ocr_err:
                logger.error(f"OCR Failed for page {page_num}: {ocr_err}")
            finally:
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)

            return page_marker + _sanitize_text(ocr_text)

    except Exception as e:
        logger.error(f"Page {page_num} CRITICAL FAILURE: {e}")
        return "" 

def _process_single_page_wrapper(args) -> str:
    try: return _process_single_page_safe(*args)
    except Exception: return ""

def _extract_text_sequentially(file_path: str, total_pages: int) -> str:
    buffer = []
    for i in range(total_pages):
        buffer.append(_process_single_page_safe(file_path, i))
        time.sleep(0.05) 
    return "".join(buffer)

def _extract_text_from_pdf(file_path: str) -> str:
    logger.info(f"🚀 Processing PDF: {file_path}")
    total_pages = 0
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
    except Exception: return ""

    if total_pages < 5:
         return _extract_text_sequentially(file_path, total_pages)

    try:
        page_args = [(file_path, i) for i in range(total_pages)]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process_single_page_wrapper, arg): arg[1] for arg in page_args}
            for future in concurrent.futures.as_completed(futures):
                results.append((futures[future], future.result()))
        
        results.sort(key=lambda x: x[0])
        return "".join([r[1] for r in results])
    except Exception as e:
        logger.error(f"Parallel PDF extraction failed: {e}")
        return _extract_text_sequentially(file_path, total_pages)

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
        text_runs = [shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")]
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
    try:
        all_rows = []
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader: all_rows.append(", ".join(filter(None, row)))
        return _sanitize_text("\n".join(all_rows))
    except Exception: return ""

def _extract_text_from_excel(file_path: str) -> str:
    try:
        xls = pd.ExcelFile(file_path)
        full_text = [f"--- Sheet: {sheet_name} ---\n{xls.parse(sheet_name).to_string(index=False, na_rep='')}" for sheet_name in xls.sheet_names if not xls.parse(sheet_name).empty]
        return _sanitize_text("\n".join(full_text))
    except Exception: return ""

EXTRACTION_MAP: Dict[str, Callable[[str], str]] = {
    ".pdf": _extract_text_from_pdf,
    ".docx": _extract_text_from_docx,
    ".pptx": _extract_text_from_pptx,
    ".png": _extract_text_from_image, 
    ".jpeg": _extract_text_from_image, 
    ".tiff": _extract_text_from_image,
    ".jpg": _extract_text_from_image,
    ".txt": _extract_text_from_txt, 
    ".csv": _extract_text_from_csv,
    ".xls": _extract_text_from_excel,
    ".xlsx": _extract_text_from_excel
}

def extract_text(file_path: str, mime_type: Optional[str] = None) -> str:
    """
    Internal Entry Point (Path-Based). Determines extractor from file extension.
    """
    _, ext = os.path.splitext(file_path)
    extractor = EXTRACTION_MAP.get(ext.lower())
    
    if extractor:
        return extractor(file_path)
    
    logger.warning(f"No specific extractor for extension '{ext}'. Falling back to plain text.")
    return _extract_text_from_txt(file_path)

# --- PHOENIX BRIDGE: STREAM HANDLER (Corrected) ---
def extract_text_from_file(file_obj: io.BytesIO, filename: str) -> str:
    """
    Public Entry Point (Stream-Based).
    Correctly determines file type from the provided filename.
    """
    # 1. Get extension from filename
    _, ext = os.path.splitext(filename)
    if not ext:
        logger.warning(f"Filename '{filename}' has no extension. Assuming .txt")
        ext = ".txt"

    # 2. Write Stream to Temp File
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_obj.getvalue())
        tmp_path = tmp.name

    try:
        # 3. Delegate to the path-based logic
        return extract_text(tmp_path)
    finally:
        # 4. Clean up
        if os.path.exists(tmp_path):
            os.remove(tmp_path)