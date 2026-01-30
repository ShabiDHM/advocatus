# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - PDF SERVICE V3.4 (UNICODE/EMOJI SUPPORT)
# 1. FIX: Integrated dynamic TrueType Font registration to support UTF-8/Emojis.
# 2. FEATURE: Scans system paths for 'DejaVuSans' or 'Arial' to replace 'Helvetica'.
# 3. STATUS: Resolves "Rectangles" issue in generated PDFs.

import io
import os
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fastapi import UploadFile
from typing import Tuple, Optional
from PIL import Image as PILImage 

from . import conversion_service

class PDFProcessor:
    _font_registered = False
    _unicode_font_name = "Helvetica" # Default fallback

    @classmethod
    def _register_unicode_font(cls):
        """
        Attempts to register a TrueType font that supports Unicode (UTF-8).
        Critical for rendering emojis and non-latin characters.
        """
        if cls._font_registered:
            return

        # List of candidate fonts in order of preference
        # DejaVuSans is common in Linux/Docker and supports many symbols
        candidate_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\seguiemj.ttf", # Windows Emoji font
            "/System/Library/Fonts/Helvetica.ttc"
        ]

        for font_path in candidate_fonts:
            if os.path.exists(font_path):
                try:
                    font_name = "CustomUnicodeFont"
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    cls._unicode_font_name = font_name
                    cls._font_registered = True
                    print(f"PDFService: Registered Unicode font from {font_path}")
                    return
                except Exception as e:
                    print(f"PDFService: Failed to register font {font_path}: {e}")
        
        print("PDFService: No Unicode font found. Falling back to Helvetica (Emojis may break).")
        cls._font_registered = True

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
        Uses registered Unicode font for .txt files to support Emojis.
        """
        PDFProcessor._register_unicode_font() # Ensure font is ready
        
        ext = filename.split('.')[-1].lower() if '.' in filename else ""
        base_name = os.path.splitext(filename)[0]
        new_filename = f"{base_name}.pdf"

        # 1. Text to PDF
        if ext == "txt":
            try:
                # 'replace' handles un-decodable bytes, but font handles glyphs
                text_str = content.decode('utf-8', errors='replace')
                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                
                # Start text object
                text_obj = c.beginText(15 * mm, 280 * mm)
                
                # USE THE REGISTERED UNICODE FONT
                text_obj.setFont(PDFProcessor._unicode_font_name, 10)
                
                # Header
                c.setFont("Helvetica-Bold", 12) # Header can stay simple
                c.drawString(15 * mm, 290 * mm, "Document View / Pamja e Dokumentit")
                c.line(15 * mm, 288 * mm, 195 * mm, 288 * mm)
                
                # Reset font for body
                c.setFont(PDFProcessor._unicode_font_name, 10)

                for line in text_str.split('\n'):
                    # Basic wrapping
                    if len(line) > 95:
                        for i in range(0, len(line), 95):
                            text_obj.textLine(line[i:i+95])
                    else:
                        text_obj.textLine(line)
                        
                    if text_obj.getY() < 20 * mm:
                        c.drawText(text_obj)
                        c.showPage()
                        text_obj = c.beginText(15 * mm, 280 * mm)
                        text_obj.setFont(PDFProcessor._unicode_font_name, 10)
                
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