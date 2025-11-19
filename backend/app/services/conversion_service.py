# FILE: backend/app/services/conversion_service.py
# PHOENIX PROTOCOL - IMAGE TO PDF SUPPORT
# 1. Uses 'Pillow' (PIL) to instantly convert JPG/PNG -> PDF.
# 2. Falls back to LibreOffice for Word/Excel/Text.
# 3. Supports the "Mobile Scan" use case.

import logging
import os
import subprocess
import tempfile
import shutil
from PIL import Image  # Standard Python Image Library

logger = logging.getLogger(__name__)

def convert_to_pdf(source_path: str) -> str:
    """
    Converts a given document file (DOCX, XLSX, TXT, JPG, PNG) to a PDF.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found at path: {source_path}")

    file_name, source_ext = os.path.splitext(os.path.basename(source_path))
    ext = source_ext.lower()
    
    output_dir = tempfile.gettempdir()
    dest_pdf_path = os.path.join(output_dir, f"{file_name}_preview.pdf")

    # --- CASE 1: ALREADY PDF ---
    if ext == '.pdf':
        logger.info(f"Source is already PDF. Copying...")
        shutil.copy2(source_path, dest_pdf_path)
        return dest_pdf_path

    # --- CASE 2: IMAGE TO PDF (The "Scanner" Logic) ---
    # Uses Python's Pillow library for fast, high-quality conversion
    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        try:
            logger.info(f"Converting Image to PDF: {source_path}")
            image = Image.open(source_path)
            
            # Convert to RGB to handle PNG transparency or weird color modes
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save as PDF
            image.save(dest_pdf_path, "PDF", resolution=100.0)
            
            logger.info(f"Successfully converted Image to PDF: {dest_pdf_path}")
            return dest_pdf_path
        except Exception as e:
            logger.error(f"Image conversion failed: {e}", exc_info=True)
            # Fallthrough to LibreOffice just in case, though unlikely to work better
    
    # --- CASE 3: OFFICE DOCUMENTS (LibreOffice) ---
    logger.info(f"Initiating LibreOffice conversion for '{file_name}{source_ext}'.")
    
    command = [
        "soffice",
        "--headless",
        "--convert-to", "pdf:writer_pdf_Export",
        "--outdir", output_dir,
        source_path,
    ]

    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120
        )

        if process.returncode != 0:
            stderr_output = process.stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"LibreOffice conversion failed: {stderr_output}")

        # LibreOffice saves it as {filename}.pdf in the outdir
        expected_output_path = os.path.join(output_dir, f"{file_name}.pdf")

        if not os.path.exists(expected_output_path):
             raise RuntimeError(f"PDF not found at {expected_output_path}")
            
        if os.path.getsize(expected_output_path) == 0:
            os.remove(expected_output_path)
            raise RuntimeError("Conversion produced a zero-byte PDF.")

        # Rename to ensure it matches our destination naming convention
        shutil.move(expected_output_path, dest_pdf_path)
        
        logger.info(f"Successfully converted Office Doc to PDF.")
        return dest_pdf_path

    except Exception as e:
        logger.error(f"Conversion error: {e}", exc_info=True)
        raise