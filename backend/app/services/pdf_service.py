# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - UNIVERSAL DOCUMENT CONVERTER (STRICT MODE)
# 1. FIX: Explicit 'None' check for filename (Solves "lower" error).
# 2. FIX: Positional arguments for FPDF (Solves "txt" parameter error).
# 3. FIX: Output type checking (Solves "bytearray" encode error).

import io
from PIL import Image
from fpdf import FPDF
from fastapi import UploadFile
from typing import Tuple

class PDFConverter:
    @staticmethod
    async def convert_to_pdf(file: UploadFile) -> Tuple[bytes, str]:
        """
        Converts incoming file to PDF bytes.
        Returns: (pdf_bytes, new_filename)
        """
        # 1. FIX: Type Guard to ensure we never operate on None
        # We assign to a strictly typed variable 'original_name'
        raw_filename = file.filename
        if raw_filename is None:
            original_name: str = "untitled_document"
        else:
            original_name: str = raw_filename

        filename_lower = original_name.lower()
        content = await file.read()
        
        # Scenario A: Already PDF -> Return as is
        if filename_lower.endswith('.pdf'):
            await file.seek(0)
            return content, original_name

        # Scenario B: Image -> Convert
        if filename_lower.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')):
            try:
                return PDFConverter._image_to_pdf(content, original_name)
            except Exception as e:
                print(f"Image conversion failed: {e}")
                # Fallback to original if conversion crashes
                await file.seek(0)
                return content, original_name

        # Scenario C: Text -> Convert
        if filename_lower.endswith('.txt'):
            try:
                return PDFConverter._text_to_pdf(content, original_name)
            except Exception as e:
                print(f"Text conversion failed: {e}")
                await file.seek(0)
                return content, original_name

        # Scenario D: Unsupported -> Return original
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
        
        # 2. FIX: Use positional arguments (0, 10, text) instead of keywords
        pdf.multi_cell(0, 10, sanitized_text)
        
        # 3. FIX: Handle variable return types from different FPDF versions
        output = pdf.output(dest='S')
        
        pdf_output_bytes: bytes
        if isinstance(output, str):
            # Older FPDF returns string -> encode it
            pdf_output_bytes = output.encode('latin-1')
        elif isinstance(output, bytearray):
            # Newer FPDF returns bytearray -> cast to bytes
            pdf_output_bytes = bytes(output)
        else:
            # Fallback for unknown types (safe cast)
            pdf_output_bytes = bytes(output)
        
        base_name = original_name.rsplit('.', 1)[0]
        new_name = f"{base_name}.pdf"
        return pdf_output_bytes, new_name

pdf_service = PDFConverter()