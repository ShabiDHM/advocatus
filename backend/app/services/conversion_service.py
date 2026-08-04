# FILE: backend/app/services/conversion_service.py
# PHOENIX PROTOCOL - CONVERSION SERVICE V12.0 (LIBREOFFICE & PURE-PYTHON WORD/IMAGE FALLBACK)

import logging
import os
import subprocess
import tempfile
import shutil
from PIL import Image

logger = logging.getLogger(__name__)

def _text_to_pdf_fallback(text_content: str, dest_pdf_path: str, title: str = "Dokument") -> str:
    """Pure Python text-to-PDF fallback engine for cloud servers without LibreOffice."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit

        c = canvas.Canvas(dest_pdf_path, pagesize=letter)
        width, height = letter
        margin = 54
        usable_width = width - (2 * margin)

        # Header Title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, height - margin, title[:60])
        c.line(margin, height - margin - 6, width - margin, height - margin - 6)

        c.setFont("Helvetica", 10)
        y = height - margin - 30

        lines = text_content.split('\n')
        for line in lines:
            if not line.strip():
                y -= 10
                continue
            
            wrapped_lines = simpleSplit(line, "Helvetica", 10, usable_width)
            for wline in wrapped_lines:
                if y < margin:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = height - margin
                c.drawString(margin, y, wline)
                y -= 14

        c.save()
        return dest_pdf_path
    except Exception as e:
        logger.warning(f"Reportlab PDF fallback failed: {e}")
        return ""

def _extract_docx_text_python(source_path: str) -> str:
    """Extracts raw text from .docx using python-docx if available."""
    try:
        import docx
        doc = docx.Document(source_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        logger.warning(f"python-docx text extraction failed: {e}")
        return ""

def convert_to_pdf(source_path: str) -> str:
    """
    Converts DOCX, DOC, XLSX, TXT, JPG, PNG to PDF.
    Features LibreOffice native conversion with ReportLab/Pillow cloud fallbacks.
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

    # --- CASE 2: IMAGE TO PDF (Scanner Logic) ---
    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        try:
            logger.info(f"Converting Image to PDF: {source_path}")
            image = Image.open(source_path)
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image.save(dest_pdf_path, "PDF", resolution=100.0)
            logger.info(f"Successfully converted Image to PDF: {dest_pdf_path}")
            return dest_pdf_path
        except Exception as e:
            logger.error(f"Image conversion failed: {e}", exc_info=True)

    # --- CASE 3: WORD DOCS (.DOCX / .DOC) VIA LIBREOFFICE WITH PYTHON FALLBACK ---
    logger.info(f"Initiating Office conversion for '{file_name}{source_ext}'.")
    
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
            timeout=60
        )

        expected_output_path = os.path.join(output_dir, f"{file_name}.pdf")

        if process.returncode == 0 and os.path.exists(expected_output_path) and os.path.getsize(expected_output_path) > 0:
            shutil.move(expected_output_path, dest_pdf_path)
            logger.info(f"Successfully converted Office Doc to PDF via LibreOffice.")
            return dest_pdf_path
        else:
            logger.warning("LibreOffice not available or failed. Invoking pure-Python fallback...")
    except Exception as libre_err:
        logger.warning(f"LibreOffice execution skipped ({libre_err}). Invoking pure-Python fallback...")

    # --- FALLBACK: PURE PYTHON WORD TO PDF ---
    if ext in ['.docx', '.doc', '.txt']:
        extracted_text = _extract_docx_text_python(source_path)
        if not extracted_text:
            extracted_text = f"Dokument i ngarkuar: {file_name}{source_ext}"
            
        fallback_pdf = _text_to_pdf_fallback(extracted_text, dest_pdf_path, title=file_name)
        if fallback_pdf and os.path.exists(fallback_pdf):
            logger.info("Successfully converted Word doc to PDF using Pure-Python fallback!")
            return dest_pdf_path

    raise RuntimeError(f"Could not convert '{file_name}{source_ext}' to PDF preview.")