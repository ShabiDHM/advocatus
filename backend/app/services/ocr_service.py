# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V3.3 (ROBUST FALLBACK)
# 1. FIX: Added 'sqi' -> 'eng' language fallback. If Albanian data is missing, it won't crash.
# 2. LOGGING: Catches and logs specific Tesseract errors instead of silent failure.
# 3. ROBUSTNESS: Handles 'TesseractNotFoundError' gracefully.

import pytesseract
from pytesseract import TesseractError
from PIL import Image
import logging
import cv2
import numpy as np
import re
import os

logger = logging.getLogger(__name__)

def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    The 'Optometrist' Stage (Fallback Mode):
    Aggressively cleans the image. Only used if the raw image fails.
    """
    try:
        img_np = np.array(pil_image)
        
        # Handle RGB/RGBA -> Grayscale
        if len(img_np.shape) == 3:
            if img_np.shape[2] == 4:
                img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
            else:
                img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            img_gray = img_np 

        # Upscaling
        height, width = img_gray.shape
        if width < 1500:
            scale_factor = 2000 / width
            img_gray = cv2.resize(img_gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

        # Adaptive Thresholding
        processed = cv2.adaptiveThreshold(
            img_gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 
            10  
        )

        # Denoising
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.dilate(processed, kernel, iterations=1)
        processed = cv2.erode(processed, kernel, iterations=1)

        return Image.fromarray(processed)

    except Exception as e:
        logger.warning(f"⚠️ Image Preprocessing failed: {e}. Returning original.")
        return pil_image

def clean_ocr_garbage(text: str) -> str:
    """
    The 'Editor' Stage:
    Fixes artifacts but PRESERVES LAYOUT.
    """
    if not text: return ""
    
    # Fix broken hyphenations
    text = text.replace("-\n", "") 
    
    # Only remove excessive vertical whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    return text.strip()

def _run_tesseract(image, config: str) -> str:
    """
    Helper to run Tesseract with Language Fallback.
    """
    # Attempt 1: Albanian + English (Ideal)
    try:
        return pytesseract.image_to_string(image, lang='sqi+eng', config=config)
    except TesseractError as e:
        # Check if it's a missing language data error
        err_msg = str(e).lower()
        if "data" in err_msg or "lang" in err_msg or "tessdata" in err_msg:
            logger.warning("⚠️ OCR Warning: 'sqi' language data missing. Falling back to 'eng' (Standard Mode).")
            # Attempt 2: English Only (Fallback)
            try:
                return pytesseract.image_to_string(image, lang='eng', config=config)
            except Exception as e2:
                logger.error(f"❌ OCR Failed (English Fallback): {e2}")
                return ""
        else:
            logger.error(f"❌ OCR Tesseract Error: {e}")
            return ""
    except FileNotFoundError:
        logger.critical("❌ OCR CRITICAL: Tesseract binary not found! Install 'tesseract-ocr' in Docker.")
        return ""
    except Exception as e:
        logger.error(f"❌ OCR Unknown Error: {e}")
        return ""

def extract_text_from_image(file_path: str) -> str:
    """
    Main Pipeline: Smart Strategy (Raw First -> Filter Fallback)
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ OCR Error: File not found at {file_path}")
        return ""

    try:
        original_image = Image.open(file_path)
        
        # PHOENIX CONFIG: Preserve layout for Tables
        custom_config = r'--oem 3 --psm 3 -c preserve_interword_spaces=1'
        
        # ATTEMPT 1: Raw Image
        raw_text_1 = _run_tesseract(original_image, custom_config)
        clean_text_1 = clean_ocr_garbage(raw_text_1)

        # CRITERIA: Is the result good?
        if len(clean_text_1) > 100:
            logger.info(f"✅ OCR Success (Raw Mode): {len(clean_text_1)} chars.")
            return clean_text_1

        # ATTEMPT 2: The "Hawk-Eye" Filter
        logger.info("⚠️ Raw OCR yielded low results. Engaging Hawk-Eye Preprocessing...")
        processed_image = preprocess_image_for_ocr(original_image)
        
        raw_text_2 = _run_tesseract(processed_image, custom_config)
        clean_text_2 = clean_ocr_garbage(raw_text_2)
        
        # Compare results
        if len(clean_text_2) > len(clean_text_1):
            logger.info(f"✅ OCR Success (Filter Mode): {len(clean_text_2)} chars.")
            return clean_text_2
        else:
            logger.info(f"✅ OCR Success (Reverted to Raw): {len(clean_text_1)} chars.")
            return clean_text_1
        
    except Exception as e:
        logger.error(f"❌ OCR Fatal Error for {file_path}: {e}")
        return ""