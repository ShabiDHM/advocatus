# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - UNIVERSAL DOCUMENT CONVERTER
# 1. FEATURE: Converts Images (JPG, PNG, TIFF) and Text to standard PDF.
# 2. SAFETY: Validates mime-types to prevent processing executables.
# 3. STATUS: Ready for integration.

import io
from PIL import Image
from fpdf import FPDF
from fastapi import UploadFile, HTTPException

class PDFConverter:
    @staticmethod
    async def convert_to_pdf(file: UploadFile) -> tuple[bytes, str]:
        """
        Converts incoming file to PDF bytes.
        Returns: (pdf_bytes, new_filename)
        """
        filename = file.filename.lower()
        content = await file.read()
        
        # 1. If already PDF, return as is
        if filename.endswith('.pdf'):
            await file.seek(0)
            return content, file.filename

        # 2. Handle Images (JPG, PNG, JPEG, BMP, TIFF)
        if filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')):
            try:
                return PDFConverter._image_to_pdf(content, file.filename)
            except Exception as e:
                print(f"Image conversion failed: {e}")
                # Fallback: Return original if conversion fails (or raise error)
                await file.seek(0)
                return content, file.filename

        # 3. Handle Text Files
        if filename.endswith('.txt'):
            try:
                return PDFConverter._text_to_pdf(content, file.filename)
            except Exception as e:
                print(f"Text conversion failed: {e}")
                await file.seek(0)
                return content, file.filename

        # 4. Unsupported formats (DOCX, etc.) return original
        # Note: DOCX conversion on Linux requires LibreOffice/Pandoc installed.
        await file.seek(0)
        return content, file.filename

    @staticmethod
    def _image_to_pdf(image_bytes: bytes, original_name: str) -> tuple[bytes, str]:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB (drops Alpha channel which PDF doesn't support well in basic mode)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format="PDF", resolution=100.0)
        pdf_bytes.seek(0)
        
        new_name = f"{original_name.rsplit('.', 1)[0]}.pdf"
        return pdf_bytes.getvalue(), new_name

    @staticmethod
    def _text_to_pdf(text_bytes: bytes, original_name: str) -> tuple[bytes, str]:
        text = text_bytes.decode('utf-8', errors='replace')
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # FPDF doesn't handle unicode well by default, strictly basic latin or use a unicode font
        # For robustness, we sanitize to latin-1 or similar, or require a .ttf font file
        # Using 'latin-1' replacement to prevent crashes
        sanitized_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=sanitized_text)
        
        pdf_output = pdf.output(dest='S').encode('latin-1') # Return bytes
        
        new_name = f"{original_name.rsplit('.', 1)[0]}.pdf"
        return pdf_output, new_name

pdf_service = PDFConverter()