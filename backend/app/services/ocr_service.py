# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V3.1 (STRUCTURE PRESERVATION)
# 1. FIX: 'clean_ocr_garbage' now preserves NEWLINES (\n). Structure is vital for AI.
# 2. LOGIC: Reordered pipeline. Tries Raw Image first (best for clear photos), then Filtered (for bad scans).
# 3. STATUS: Full document structure retention.

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
        # Uses larger block size (21) to avoid breaking large text characters
        processed = cv2.adaptiveThreshold(
            img_gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 
            10  
        )

        # 4. Denoising
        # Remove small noise points
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
    Fixes artifacts but PRESERVES STRUCTURE (Newlines).
    """
    if not text: return ""
    
    # 1. Fix broken hyphenations at end of lines
    text = text.replace("-\n", "") 
    
    # 2. Common OCR artifacts
    text = text.replace("|", "I")
    
    # 3. PHOENIX FIX: Preserve Newlines!
    # Replace multiple spaces (tabs/spaces) with single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Replace 3+ newlines with 2 (Paragraph breaks)
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    return text.strip()

def extract_text_from_image(file_path: str) -> str:
    """
    Main Pipeline: Smart Strategy (Raw First -> Filter Fallback)
    """
    try:
        original_image = Image.open(file_path)
        custom_config = r'--oem 3 --psm 3'
        
        # ATTEMPT 1: Raw Image (Best for clear photos/scans)
        # We assume the user uploaded a decent photo. Tesseract handles this best natively.
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
        # If we got >100 characters, we assume success.
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
        
        # Compare results (Pick the longer one, usually means more content read)
        if len(clean_text_2) > len(clean_text_1):
            logger.info(f"✅ OCR Success (Filter Mode): {len(clean_text_2)} chars.")
            return clean_text_2
        else:
            logger.info(f"✅ OCR Success (Reverted to Raw): {len(clean_text_1)} chars.")
            return clean_text_1
        
    except Exception as e:
        logger.error(f"❌ OCR Fatal Error for {file_path}: {e}")
        return ""