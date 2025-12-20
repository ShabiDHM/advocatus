# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - PDF SERVICE V3.3 (BYTES CONVERSION)
# 1. FEATURE: Added 'convert_bytes_to_pdf' for internally generated files.
# 2. LOGIC: Converts text/image bytes to PDF in memory.
# 3. USE CASE: Fixes "Generated Expense Receipt" saving as .txt.

import io
import os
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from fastapi import UploadFile
from typing import Tuple, Optional
from PIL import Image as PILImage 

from . import conversion_service

class PDFProcessor:
    @staticmethod
    async def process_and_brand_pdf(
        file: UploadFile, case_id: Optional[str] = "N/A"
    ) -> Tuple[bytes, str]:
        """
        Orchestrates the conversion, branding, and watermarking of any uploaded document.
        """
        original_ext = os.path.splitext(file.filename or ".tmp")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            source_path = tmp_file.name

        await file.seek(0)
        
        base_name = os.path.splitext(file.filename or "dokument")[0]
        final_pdf_name = f"{base_name}.pdf"

        converted_pdf_path = None
        try:
            converted_pdf_path = conversion_service.convert_to_pdf(source_path)
            with open(converted_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            branded_pdf_bytes = PDFProcessor._apply_branding(pdf_bytes, str(case_id))
            return branded_pdf_bytes, final_pdf_name

        finally:
            if os.path.exists(source_path): os.remove(source_path)
            if converted_pdf_path and os.path.exists(converted_pdf_path): os.remove(converted_pdf_path)

    @staticmethod
    async def convert_upload_to_pdf(file: UploadFile) -> Tuple[io.BytesIO, str]:
        """Converts an UploadFile to PDF stream."""
        content = await file.read()
        await file.seek(0)
        
        # Delegate to bytes converter
        pdf_bytes, new_name = PDFProcessor.convert_bytes_to_pdf(content, file.filename or "doc")
        return io.BytesIO(pdf_bytes), new_name

    @staticmethod
    def convert_bytes_to_pdf(content: bytes, filename: str) -> Tuple[bytes, str]:
        """
        PHOENIX FIX: Converts raw bytes (Text/Image) to PDF bytes.
        Used for internally generated files (like placeholder receipts).
        """
        ext = filename.split('.')[-1].lower() if '.' in filename else ""
        base_name = os.path.splitext(filename)[0]
        new_filename = f"{base_name}.pdf"

        # 1. Text to PDF
        if ext == "txt":
            try:
                text_str = content.decode('utf-8', errors='replace')
                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                
                text_obj = c.beginText(15 * mm, 280 * mm)
                text_obj.setFont("Helvetica", 10)
                
                # Header
                c.setFont("Helvetica-Bold", 12)
                c.drawString(15 * mm, 290 * mm, "Expense Note / Shënim Shpenzimi")
                c.line(15 * mm, 288 * mm, 195 * mm, 288 * mm)
                
                for line in text_str.split('\n'):
                    if len(line) > 95:
                        for i in range(0, len(line), 95):
                            text_obj.textLine(line[i:i+95])
                    else:
                        text_obj.textLine(line)
                        
                    if text_obj.getY() < 20 * mm:
                        c.drawText(text_obj)
                        c.showPage()
                        text_obj = c.beginText(15 * mm, 280 * mm)
                        text_obj.setFont("Helvetica", 10)
                
                c.drawText(text_obj)
                c.save()
                return pdf_buffer.getvalue(), new_filename
            except Exception as e:
                print(f"Text bytes conversion failed: {e}")
                return content, filename

        # 2. Image to PDF
        if ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp']:
            try:
                img = PILImage.open(io.BytesIO(content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                pdf_buffer = io.BytesIO()
                img.save(pdf_buffer, "PDF", resolution=100.0)
                return pdf_buffer.getvalue(), new_filename
            except Exception as e:
                print(f"Image bytes conversion failed: {e}")
                return content, filename

        # 3. Default: Return original
        return content, filename

    @staticmethod
    def _apply_branding(pdf_bytes: bytes, case_id: str) -> bytes:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            watermark_stream = io.BytesIO()
            c = canvas.Canvas(watermark_stream, pagesize=page.mediabox)
            c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
            c.drawCentredString(float(page.mediabox.width) / 2, 1 * cm, f"Rasti: {case_id} | Faqja {i + 1}")
            c.save()
            watermark_pdf = PdfReader(watermark_stream)
            page.merge_page(watermark_pdf.pages[0])
            writer.add_page(page)
        
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

pdf_service = PDFProcessor()