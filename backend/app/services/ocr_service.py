# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V3.2 (TABLE LAYOUT PRESERVATION)
# 1. FIX: Removed aggressive space collapsing. Preserves visual gaps for Table detection.
# 2. CONFIG: Added '--preserve-interword-spaces' to Tesseract config.
# 3. LOGIC: Stop replacing '|' with 'I' to keep table borders intact.

import pytesseract
from PIL import Image
import logging
import cv2
import numpy as np
import re

logger = logging.getLogger(__name__)

def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    The 'Optometrist' Stage (Fallback Mode):
    Aggressively cleans the image. Only used if the raw image fails.
    """
    try:
        # 1. Convert PIL to OpenCV format
        img_np = np.array(pil_image)
        
        # Handle RGB/RGBA -> Grayscale
        if len(img_np.shape) == 3:
            if img_np.shape[2] == 4:
                img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
            else:
                img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            img_gray = img_np 

        # 2. Upscaling (If image is too small)
        height, width = img_gray.shape
        if width < 1500:
            scale_factor = 2000 / width
            img_gray = cv2.resize(img_gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

        # 3. Adaptive Thresholding (The "Shadow Killer")
        processed = cv2.adaptiveThreshold(
            img_gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 
            10  
        )

        # 4. Denoising
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
    Fixes artifacts but PRESERVES LAYOUT (Spaces & Newlines) for AI Table Analysis.
    """
    if not text: return ""
    
    # 1. Fix broken hyphenations at end of lines
    text = text.replace("-\n", "") 
    
    # 2. PHOENIX FIX: Do NOT destroy table separators
    # Old logic replaced '|' with 'I'. We removed that.
    
    # 3. PHOENIX FIX: Preserve Visual Structure!
    # We DO NOT collapse multiple spaces anymore. 
    # The AI needs the gaps to see "Column A       Column B".
    
    # Only remove excessive vertical whitespace (3+ blank lines -> 2)
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    return text.strip()

def extract_text_from_image(file_path: str) -> str:
    """
    Main Pipeline: Smart Strategy (Raw First -> Filter Fallback)
    """
    try:
        original_image = Image.open(file_path)
        
        # PHOENIX CONFIG: --preserve-interword-spaces is CRITICAL for Tables
        # --psm 3 (Auto) usually works, but preserving spaces helps the LLM distinguish columns.
        custom_config = r'--oem 3 --psm 3 -c preserve_interword_spaces=1'
        
        # ATTEMPT 1: Raw Image (Best for clear photos/scans)
        try:
            raw_text_1 = pytesseract.image_to_string(
                original_image, 
                lang='sqi+eng', 
                config=custom_config
            )
        except Exception: 
            raw_text_1 = ""

        clean_text_1 = clean_ocr_garbage(raw_text_1)

        # CRITERIA: Is the result good?
        if len(clean_text_1) > 100:
            logger.info(f"✅ OCR Success (Raw Mode): {len(clean_text_1)} chars.")
            return clean_text_1

        # ATTEMPT 2: The "Hawk-Eye" Filter (Fallback for bad lighting/shadows)
        logger.info("⚠️ Raw OCR yielded low results. Engaging Hawk-Eye Preprocessing...")
        processed_image = preprocess_image_for_ocr(original_image)
        
        try:
            raw_text_2 = pytesseract.image_to_string(
                processed_image, 
                lang='sqi+eng', 
                config=custom_config
            )
        except Exception:
            raw_text_2 = ""
            
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