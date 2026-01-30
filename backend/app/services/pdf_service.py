# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - PDF SERVICE V4.0 (EMOJI INTEGRITY)
# 1. FIX: Implemented 'Auto-Heal' Font Loader. Downloads 'NotoEmoji-Regular.ttf' on the fly.
# 2. FEATURE: Supports full Unicode rendering (Emojis, Symbols) for legal evidence accuracy.
# 3. ROBUSTNESS: Uses 'urllib' (std lib) to avoid new PIP dependencies. Fallbacks to /tmp if needed.

import io
import os
import tempfile
import shutil
import logging
import urllib.request  # Standard library, no pip install needed
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

logger = logging.getLogger(__name__)

class PDFProcessor:
    _font_registered = False
    _unicode_font_name = "Helvetica" # Fallback start
    
    # Google's Noto Emoji (Monochrome) - Extremely reliable for PDFs
    FONT_URL = "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoEmoji-Regular.ttf"
    FONT_FILENAME = "NotoEmoji-Regular.ttf"

    @classmethod
    def _ensure_font_available(cls):
        """
        Self-healing mechanism: Checks for the Emoji font. 
        If missing, downloads it automatically.
        """
        if cls._font_registered and cls._unicode_font_name != "Helvetica":
            return

        # 1. Determine safe storage path
        # Try local assets first, then temp dir
        base_dirs = [
            os.path.join(os.path.dirname(__file__), "../assets/fonts"),
            tempfile.gettempdir()
        ]
        
        target_path = None
        
        for d in base_dirs:
            if not os.path.exists(d):
                try:
                    os.makedirs(d, exist_ok=True)
                except Exception:
                    continue # Cannot write here, try next
            
            # Check write permissions
            if os.access(d, os.W_OK):
                target_path = os.path.join(d, cls.FONT_FILENAME)
                break
        
        if not target_path:
            logger.warning("PDFService: Could not find a writable directory for fonts. Emojis may fail.")
            return

        # 2. Download if missing
        if not os.path.exists(target_path):
            try:
                logger.info(f"PDFService: Downloading Emoji font to {target_path}...")
                urllib.request.urlretrieve(cls.FONT_URL, target_path)
                logger.info("PDFService: Font download complete.")
            except Exception as e:
                logger.error(f"PDFService: Failed to download font: {e}")
                return

        # 3. Register the font
        try:
            font_name = "NotoEmoji"
            pdfmetrics.registerFont(TTFont(font_name, target_path))
            cls._unicode_font_name = font_name
            cls._font_registered = True
            logger.info(f"PDFService: Successfully registered {font_name}")
        except Exception as e:
            logger.error(f"PDFService: Failed to register font {target_path}: {e}")

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
        Converts raw bytes to PDF. Uses NotoEmoji to support legal evidence symbols.
        """
        PDFProcessor._ensure_font_available() # Auto-heal font
        
        ext = filename.split('.')[-1].lower() if '.' in filename else ""
        base_name = os.path.splitext(filename)[0]
        new_filename = f"{base_name}.pdf"

        # 1. Text to PDF
        if ext == "txt":
            try:
                # Decode UTF-8 (Vital for emojis)
                text_str = content.decode('utf-8', errors='replace')
                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                
                # Header
                c.setFont("Helvetica-Bold", 12)
                c.drawString(15 * mm, 290 * mm, "Document Evidence / Evidencë Dokumentare")
                c.line(15 * mm, 288 * mm, 195 * mm, 288 * mm)
                
                # Body - Use Emoji-Capable Font
                text_obj = c.beginText(15 * mm, 280 * mm)
                text_obj.setFont(PDFProcessor._unicode_font_name, 10)
                
                # Simple line wrapping
                for line in text_str.split('\n'):
                    # Basic wrap logic (approx 95 chars per line)
                    if len(line) > 95:
                        for i in range(0, len(line), 95):
                            text_obj.textLine(line[i:i+95])
                    else:
                        text_obj.textLine(line)
                        
                    # Page Break
                    if text_obj.getY() < 20 * mm:
                        c.drawText(text_obj)
                        c.showPage()
                        text_obj = c.beginText(15 * mm, 280 * mm)
                        text_obj.setFont(PDFProcessor._unicode_font_name, 10)
                        # Re-draw header on new pages
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(15 * mm, 290 * mm, "Document Evidence / Evidencë Dokumentare")
                        c.line(15 * mm, 288 * mm, 195 * mm, 288 * mm)
                        c.setFont(PDFProcessor._unicode_font_name, 10) # Reset to body font
                
                c.drawText(text_obj)
                c.save()
                return pdf_buffer.getvalue(), new_filename
            except Exception as e:
                logger.error(f"Text bytes conversion failed: {e}")
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
                logger.error(f"Image bytes conversion failed: {e}")
                return content, filename

        return content, filename

    @staticmethod
    def _apply_branding(pdf_bytes: bytes, case_id: str) -> bytes:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            writer = PdfWriter()
            for i, page in enumerate(reader.pages):
                watermark_stream = io.BytesIO()
                c = canvas.Canvas(watermark_stream, pagesize=page.mediabox)
                c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
                
                # Check for rotation
                page_width = float(page.mediabox.width)
                if page.get('/Rotate') in [90, 270]:
                    page_width = float(page.mediabox.height)

                c.drawCentredString(page_width / 2, 1 * cm, f"Rasti: {case_id} | Faqja {i + 1}")
                c.save()
                watermark_pdf = PdfReader(watermark_stream)
                page.merge_page(watermark_pdf.pages[0])
                writer.add_page(page)
            
            out = io.BytesIO()
            writer.write(out)
            return out.getvalue()
        except Exception as e:
            logger.error(f"Branding failed: {e}")
            return pdf_bytes

pdf_service = PDFProcessor()