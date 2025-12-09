# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - PDF SERVICE V2 (SMART ENCODING)
# 1. ACCURACY: Switched from 'latin-1' to 'cp1252' (Windows-1252).
#    - Why? 'latin-1' destroys the Euro (€) symbol. 'cp1252' preserves it.
#    - Result: The AI can now detect "5000 €" correctly instead of "5000 ?".
# 2. LOGIC: Magic Byte detection remains for security.

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
        
        # 2. PREPARE FILENAME
        raw_name = file.filename or "untitled_document"
        base_name = raw_name.rsplit('.', 1)[0]

        # 3. MAGIC BYTE DETECTION
        # Check if it's ALREADY a PDF (Signature: %PDF)
        if content.startswith(b'%PDF'):
            await file.seek(0)
            return content, f"{base_name}.pdf"

        # Check for Common Images
        if (content.startswith(b'\xff\xd8\xff') or  # JPEG
            content.startswith(b'\x89PNG') or       # PNG
            content.startswith(b'BM') or            # BMP
            content.startswith(b'II*\x00') or       # TIFF
            content.startswith(b'MM\x00*')):
            try:
                return PDFConverter._image_to_pdf(content, raw_name)
            except Exception as e:
                print(f"Image conversion failed: {e}")
                await file.seek(0)
                return content, raw_name

        # 4. TEXT FILE HANDLING
        # Only treat as text if extension is text-like AND content looks like text
        filename_lower = raw_name.lower()
        if filename_lower.endswith(('.txt', '.md', '.csv', '.log')):
            try:
                # Basic binary check: look for null bytes
                if b'\x00' in content[:1024]: 
                    await file.seek(0)
                    return content, raw_name
                
                return PDFConverter._text_to_pdf(content, raw_name)
            except Exception as e:
                print(f"Text conversion failed: {e}")
                await file.seek(0)
                return content, raw_name

        # 5. DEFAULT / UNSUPPORTED
        await file.seek(0)
        return content, raw_name

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
        return pdf_bytes.getvalue(), f"{base_name}.pdf"

    @staticmethod
    def _text_to_pdf(text_bytes: bytes, original_name: str) -> Tuple[bytes, str]:
        # Decode UTF-8 (Standard for modern web/editors)
        text = text_bytes.decode('utf-8', errors='replace')
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # PHOENIX FIX: Use 'cp1252' (Windows-1252) instead of 'latin-1'
        # cp1252 supports the Euro (€) symbol (0x80) and smart quotes.
        # latin-1 does NOT support Euro, turning "500€" into "500?".
        sanitized_text = text.encode('cp1252', 'replace').decode('cp1252')
        
        pdf.multi_cell(0, 10, sanitized_text)
        
        output = pdf.output(dest='S')
        
        pdf_output_bytes: bytes
        if isinstance(output, str):
            pdf_output_bytes = output.encode('latin-1') # FPDF internal storage
        elif isinstance(output, bytearray):
            pdf_output_bytes = bytes(output)
        else:
            pdf_output_bytes = bytes(output)
        
        base_name = original_name.rsplit('.', 1)[0]
        return pdf_output_bytes, f"{base_name}.pdf"

pdf_service = PDFConverter()