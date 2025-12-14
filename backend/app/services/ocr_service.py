# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V3.0 (HAWK-EYE)
# 1. PRE-PROCESSING: Uses OpenCV to Binarize, Denoise, and Upscale images.
# 2. LOGIC: Adaptive Thresholding removes shadows/stamps that confuse OCR.
# 3. CONFIG: Optimized Tesseract flags (--oem 3 --psm 3) for dense legal text.

import pytesseract
from PIL import Image
import logging
import cv2
import numpy as np
import re

logger = logging.getLogger(__name__)

def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    The 'Optometrist' Stage:
    Cleans the image using Computer Vision before Tesseract sees it.
    """
    try:
        # 1. Convert PIL to OpenCV format
        img_np = np.array(pil_image)
        
        # Handle RGB/RGBA -> Grayscale
        if len(img_np.shape) == 3:
            # Check if RGBA (4 channels) or RGB (3 channels)
            if img_np.shape[2] == 4:
                img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
            else:
                img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            img_gray = img_np # Already grayscale

        # 2. Upscaling (If image is too small, OCR fails)
        # Legal docs should be roughly 2000px wide. If < 1000, we double it.
        height, width = img_gray.shape
        if width < 1000:
            img_gray = cv2.resize(img_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # 3. Adaptive Thresholding (The "Shadow Killer")
        # Turns grey mud into crisp Black & White text.
        # ADAPTIVE_THRESH_GAUSSIAN_C handles uneven lighting (scans with dark corners).
        processed = cv2.adaptiveThreshold(
            img_gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            15, # Block Size (Area to look at)
            8   # Constant (Sensitivity)
        )

        # 4. Denoising (The "Dust Cleaner")
        # Removes small noise points (salt-and-pepper noise)
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.dilate(processed, kernel, iterations=1)
        processed = cv2.erode(processed, kernel, iterations=1)

        # Convert back to PIL
        return Image.fromarray(processed)

    except Exception as e:
        logger.warning(f"⚠️ Image Preprocessing failed: {e}. Falling back to raw image.")
        return pil_image

def clean_ocr_garbage(text: str) -> str:
    """
    The 'Editor' Stage:
    Fixes common OCR artifacts found in Albanian legal docs.
    """
    if not text: return ""
    
    # Fix broken newlines that break sentences
    # e.g., "Gjykata Themelore\nPrishtinë" -> "Gjykata Themelore Prishtinë"
    text = text.replace("-\n", "") # Hyphenated words
    
    # Common artifacts
    text = text.replace("|", "I") # Pipe to I
    text = text.replace("1l", "ll") # 1l to ll
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_text_from_image(file_path: str) -> str:
    """
    Main Pipeline: Load -> Preprocess -> OCR -> Clean
    """
    try:
        # 1. Load
        original_image = Image.open(file_path)
        
        # 2. Preprocess (Hawk-Eye)
        clean_image = preprocess_image_for_ocr(original_image)
        
        # 3. OCR (The Linguist)
        # --oem 3: Default Neural Net
        # --psm 3: Fully automatic page segmentation (Good for legal docs)
        custom_config = r'--oem 3 --psm 3'
        
        try:
            # Primary: Albanian + English
            raw_text = pytesseract.image_to_string(
                clean_image, 
                lang='sqi+eng', 
                config=custom_config
            )
        except pytesseract.TesseractError as e:
            if "tessdata" in str(e):
                logger.warning("⚠️ Albanian pack missing. Fallback to English.")
                raw_text = pytesseract.image_to_string(
                    clean_image, 
                    lang='eng', 
                    config=custom_config
                )
            else:
                raise e
        
        # 4. Post-Process (The Editor)
        final_text = clean_ocr_garbage(raw_text)
        
        # Validation: If result is too short, maybe preprocessing was too aggressive?
        # Fallback to original image if "clean" image failed hard.
        if len(final_text) < 50:
            logger.info("Preprocessing might have erased faint text. Retrying with raw image...")
            raw_text_backup = pytesseract.image_to_string(original_image, lang='sqi+eng')
            if len(raw_text_backup) > len(final_text):
                final_text = clean_ocr_garbage(raw_text_backup)

        logger.info(f"✅ OCR Complete: {len(final_text)} chars extracted.")
        return final_text
        
    except Exception as e:
        logger.error(f"❌ OCR Fatal Error for {file_path}: {e}")
        # Return empty string instead of crashing, allows Analysis Service fallback to work
        return ""