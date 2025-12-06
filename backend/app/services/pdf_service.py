# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - UNIVERSAL DOCUMENT CONVERTER (MAGIC BYTE DETECTION)
# 1. FIX: Detects file type by content (Magic Bytes) to prevent corrupting mismatched extensions.
# 2. FEATURE: Automatically fixes extensions (e.g., renames .txt to .pdf if content is PDF).
# 3. ROBUSTNESS: Handles binary files masquerading as text.

import io
from PIL import Image
from fpdf import FPDF
from fastapi import UploadFile
from typing import Tuple

class PDFConverter:
    @staticmethod
    async def convert_to_pdf(file: UploadFile) -> Tuple[bytes, str]:
        """
        Converts incoming file to PDF bytes based on CONTENT, not just extension.
        Returns: (pdf_bytes, new_filename)
        """
        # 1. READ CONTENT
        content = await file.read()
        file_size = len(content)
        
        # 2. PREPARE FILENAME
        raw_name = file.filename
        if raw_name is None:
            original_name: str = "untitled_document"
        else:
            original_name: str = raw_name
            
        base_name = original_name.rsplit('.', 1)[0]

        # 3. MAGIC BYTE DETECTION
        # Check if it's ALREADY a PDF (Signature: %PDF)
        if content.startswith(b'%PDF'):
            await file.seek(0)
            # Fix extension if it was wrong (e.g. user uploaded .txt but it was a pdf)
            return content, f"{base_name}.pdf"

        # Check for Common Images
        # JPEG: FF D8 FF
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        # BMP: 42 4D
        # TIFF: 49 49 2A 00 or 4D 4D 00 2A
        if (content.startswith(b'\xff\xd8\xff') or 
            content.startswith(b'\x89PNG') or 
            content.startswith(b'BM') or 
            content.startswith(b'II*\x00') or 
            content.startswith(b'MM\x00*')):
            try:
                return PDFConverter._image_to_pdf(content, original_name)
            except Exception as e:
                print(f"Image conversion failed: {e}")
                # Fallback to original
                await file.seek(0)
                return content, original_name

        # 4. TEXT FILE HANDLING
        # Only treat as text if extension is text-like AND content looks like text
        # If it's a binary file (not PDF/Image) named .txt, we don't want to convert it (garbage output)
        filename_lower = original_name.lower()
        if filename_lower.endswith(('.txt', '.md', '.csv', '.log')):
            try:
                # Basic binary check: look for null bytes
                if b'\x00' in content[:1024]: 
                    # Likely a binary file misnamed as txt -> Return original to be safe
                    await file.seek(0)
                    return content, original_name
                
                return PDFConverter._text_to_pdf(content, original_name)
            except Exception as e:
                print(f"Text conversion failed: {e}")
                await file.seek(0)
                return content, original_name

        # 5. DEFAULT / UNSUPPORTED (DOCX, ZIP, etc.)
        # Return as is
        await file.seek(0)
        return content, original_name

    @staticmethod
    def _image_to_pdf(image_bytes: bytes, original_name: str) -> Tuple[bytes, str]:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB (drops Alpha channel which helps PDF compatibility)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format="PDF", resolution=100.0)
        pdf_bytes.seek(0)
        
        base_name = original_name.rsplit('.', 1)[0]
        new_name = f"{base_name}.pdf"
        return pdf_bytes.getvalue(), new_name

    @staticmethod
    def _text_to_pdf(text_bytes: bytes, original_name: str) -> Tuple[bytes, str]:
        # Handle decoding errors gracefully
        text = text_bytes.decode('utf-8', errors='replace')
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Sanitize text to Latin-1 to prevent FPDF unicode crashes
        sanitized_text = text.encode('latin-1', 'replace').decode('latin-1')
        
        # Use positional arguments
        pdf.multi_cell(0, 10, sanitized_text)
        
        # Handle output type variance
        output = pdf.output(dest='S')
        
        pdf_output_bytes: bytes
        if isinstance(output, str):
            pdf_output_bytes = output.encode('latin-1')
        elif isinstance(output, bytearray):
            pdf_output_bytes = bytes(output)
        else:
            pdf_output_bytes = bytes(output)
        
        base_name = original_name.rsplit('.', 1)[0]
        new_name = f"{base_name}.pdf"
        return pdf_output_bytes, new_name

pdf_service = PDFConverter()