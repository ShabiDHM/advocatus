# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V2 (ALBANIAN OPTIMIZED)
# 1. LANGUAGE: Enabled 'sqi+eng' mode. Tesseract will now look for Albanian words first.
# 2. ACCURACY: Recognizes 'ë', 'ç' and Legal Terms (Neni, Gjykata) correctly.
# 3. FALLBACK: Graceful degradation if Albanian data is missing in the Docker container.

import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def extract_text_from_image(file_path: str) -> str:
    """
    Uses Tesseract OCR to extract text from an image file.
    Optimized for Kosovo Legal Documents (Albanian Language).

    Args:
        file_path: The local path to the image file (e.g., .png, .jpg).

    Returns:
        The extracted text as a string.
    """
    try:
        # Open the image file using Pillow (PIL)
        image = Image.open(file_path)
        
        # PHOENIX FIX: Use 'sqi' (Albanian) as primary language, 'eng' as secondary.
        # This ensures 'ë' and 'ç' are read correctly, which is CRITICAL for 
        # the Semantic Regex processor to find keywords like "Çështja".
        try:
            extracted_text = pytesseract.image_to_string(image, lang='sqi+eng')
        except pytesseract.TesseractError as e:
            if "tessdata" in str(e):
                logger.warning("⚠️ Albanian language pack (tessdata/sqi) missing. Falling back to English.")
                extracted_text = pytesseract.image_to_string(image, lang='eng')
            else:
                raise e
        
        logger.info(f"✅ Successfully extracted text from image: {file_path}")
        return extracted_text
        
    except Exception as e:
        logger.error(f"❌ Error during OCR processing for file {file_path}: {e}")
        # Re-raise the exception so the calling Celery task can catch it
        # and mark the document processing as FAILED.
        raise