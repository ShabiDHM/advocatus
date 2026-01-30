# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - PDF SERVICE V6.0 (BULLETPROOF EMOJI SUPPORT)
# 1. CHANGE: Primary font is now 'NotoEmoji-Regular' (Best for Text + Emojis in PDF).
# 2. ROBUSTNESS: Disables SSL verification for font downloads to bypass container restrictions.
# 3. FALLBACK: If font fails, strictly sanitizes text to remove rectangles (clean text is better than broken glyphs).

import io
import os
import tempfile
import shutil
import logging
import urllib.request
import ssl
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from fastapi import UploadFile
from typing import Tuple, Optional
from PIL import Image as PILImage 

from . import conversion_service

logger = logging.getLogger(__name__)

class PDFProcessor:
    _font_registered = False
    _active_font_name = "Helvetica" # Default standard PDF font
    
    # NotoEmoji-Regular is excellent for mixed text and monochrome emojis
    FONT_URL = "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoEmoji-Regular.ttf"
    FONT_FILENAME = "NotoEmoji-Regular.ttf"

    @classmethod
    def _ensure_font_available(cls):
        """
        Attempts to download and register NotoEmoji.
        If successful, sets _active_font_name to 'NotoEmoji'.
        If failed, keeps 'Helvetica'.
        """
        if cls._font_registered and cls._active_font_name != "Helvetica":
            return

        # 1. Define storage path (Assets or Temp)
        base_dirs = [
            os.path.join(os.path.dirname(__file__), "../assets/fonts"),
            "/tmp", 
            tempfile.gettempdir()
        ]
        
        target_path = None
        for d in base_dirs:
            if not os.path.exists(d):
                try: os.makedirs(d, exist_ok=True)
                except: continue
            if os.access(d, os.W_OK):
                target_path = os.path.join(d, cls.FONT_FILENAME)
                break
        
        if not target_path:
            logger.warning("PDFService: No writable directory for fonts.")
            return

        # 2. Download if missing (with SSL bypass)
        if not os.path.exists(target_path) or os.path.getsize(target_path) < 1000:
            try:
                logger.info(f"PDFService: Downloading Font from {cls.FONT_URL}...")
                
                # Create unverified context to bypass strict Docker SSL issues
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                with urllib.request.urlopen(cls.FONT_URL, context=ctx, timeout=10) as response, open(target_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                logger.info("PDFService: Font download complete.")
            except Exception as e:
                logger.error(f"PDFService: Failed to download font: {e}")
                return

        # 3. Register the font
        try:
            font_name = "NotoEmoji"
            pdfmetrics.registerFont(TTFont(font_name, target_path))
            cls._active_font_name = font_name
            cls._font_registered = True
            logger.info(f"PDFService: Active font set to {font_name}")
        except Exception as e:
            logger.error(f"PDFService: Failed to register font: {e}")
            # If registration fails, delete the potentially corrupt file
            try: os.remove(target_path)
            except: pass

    @staticmethod
    def _sanitize_for_standard_font(text: str) -> str:
        """
        If we are stuck with Helvetica, we MUST strip emojis to avoid rectangles.
        We replace them with a generic marker or space.
        """
        # Encode to Latin-1 (standard PDF support) and ignore errors (drops emojis)
        return text.encode('latin-1', 'ignore').decode('latin-1')

    @staticmethod
    async def process_and_brand_pdf(
        file: UploadFile, case_id: Optional[str] = "N/A"
    ) -> Tuple[bytes, str]:
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
        content = await file.read()
        await file.seek(0)
        pdf_bytes, new_name = PDFProcessor.convert_bytes_to_pdf(content, file.filename or "doc")
        return io.BytesIO(pdf_bytes), new_name

    @staticmethod
    def convert_bytes_to_pdf(content: bytes, filename: str) -> Tuple[bytes, str]:
        """
        Uses Platypus Engine for robust Text-to-PDF conversion.
        Auto-detects font availability to decide whether to render emojis or strip them.
        """
        PDFProcessor._ensure_font_available()
        
        ext = filename.split('.')[-1].lower() if '.' in filename else ""
        base_name = os.path.splitext(filename)[0]
        new_filename = f"{base_name}.pdf"

        # 1. Text to PDF (Chat Logs, etc.)
        if ext == "txt":
            try:
                # Decode UTF-8
                text_str = content.decode('utf-8', errors='replace')
                
                # INTELLIGENT SANITIZATION
                # If we failed to load the Emoji font, we MUST strip the emojis 
                # so the user sees clean text instead of broken rectangles.
                if PDFProcessor._active_font_name == "Helvetica":
                    text_str = PDFProcessor._sanitize_for_standard_font(text_str)

                # Buffer for PDF
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(
                    pdf_buffer,
                    pagesize=A4,
                    rightMargin=20*mm, leftMargin=20*mm,
                    topMargin=20*mm, bottomMargin=20*mm
                )

                styles = getSampleStyleSheet()
                
                # Define Custom Style based on active font
                chat_style = ParagraphStyle(
                    'ChatLog',
                    parent=styles['Normal'],
                    fontName=PDFProcessor._active_font_name,
                    fontSize=10,
                    leading=14,
                    spaceAfter=4,
                    wordWrap='CJK'
                )

                header_style = ParagraphStyle(
                    'Header',
                    parent=styles['Heading3'],
                    fontName=PDFProcessor._active_font_name,
                    textColor=colors.darkblue,
                    spaceAfter=10,
                    borderWidth=1,
                    borderColor=colors.grey,
                    borderPadding=5
                )

                story = []
                story.append(Paragraph("Document Evidence / Evidencë Dokumentare", header_style))
                story.append(Spacer(1, 5*mm))

                # Process lines
                for line in text_str.split('\n'):
                    if not line.strip():
                        story.append(Spacer(1, 2*mm))
                        continue
                    
                    # Sanitize XML chars for Platypus
                    clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(clean_line, chat_style))

                doc.build(story)
                return pdf_buffer.getvalue(), new_filename

            except Exception as e:
                logger.error(f"Text conversion failed: {e}")
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
                logger.error(f"Image conversion failed: {e}")
                return content, filename

        return content, filename

    @staticmethod
    def _apply_branding(pdf_bytes: bytes, case_id: str) -> bytes:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            writer = PdfWriter()
            
            watermark_stream = io.BytesIO()
            c = canvas.Canvas(watermark_stream)
            c.setFont("Helvetica", 8) # Standard font is safe for branding
            c.setFillColor(colors.grey)
            
            c.drawCentredString(A4[0] / 2, 1 * cm, f"Rasti: {case_id} | Juristi AI System")
            c.save()
            watermark_stream.seek(0)
            watermark_pdf = PdfReader(watermark_stream)
            watermark_page = watermark_pdf.pages[0]

            for page in reader.pages:
                page.merge_page(watermark_page)
                writer.add_page(page)
            
            out = io.BytesIO()
            writer.write(out)
            return out.getvalue()
        except Exception as e:
            logger.error(f"Branding failed: {e}")
            return pdf_bytes

pdf_service = PDFProcessor()