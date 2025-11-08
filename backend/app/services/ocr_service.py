# app/services/ocr_service.py
import pytesseract
from PIL import Image

def extract_text_from_image(file_path: str) -> str:
    """
    Uses Tesseract OCR to extract text from an image file.

    Args:
        file_path: The local path to the image file (e.g., .png, .jpg).

    Returns:
        The extracted text as a string.
    """
    try:
        # Open the image file using Pillow (PIL)
        image = Image.open(file_path)
        
        # Use pytesseract to perform OCR on the image
        extracted_text = pytesseract.image_to_string(image)
        
        print(f"Successfully extracted text from image: {file_path}")
        return extracted_text
        
    except Exception as e:
        print(f"Error during OCR processing for file {file_path}: {e}")
        # Re-raise the exception so the calling Celery task can catch it
        # and mark the document processing as FAILED.
        raise