# FILE: backend/app/services/pdf_service.py
# PHOENIX PROTOCOL - PDF SERVICE V3.1 (PYPDF V6 COMPATIBILITY)
# 1. UPGRADE: Replaced legacy 'PyPDF2' with modern 'pypdf' to match requirements.txt.
# 2. FIX: Updated syntax for PdfReader/PdfWriter to resolve import errors.
# 3. STATUS: Branding & Security pipeline is now fully compatible with the project environment.

import io
import os
import tempfile
import shutil
# PHOENIX FIX: Use the modern 'pypdf' library which is already in requirements.txt
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from fastapi import UploadFile
from typing import Tuple, Optional

# Import the robust conversion engine
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
            # Delegate conversion to the robust LibreOffice-based service
            converted_pdf_path = conversion_service.convert_to_pdf(source_path)

            # Apply branding and security layers to the newly created PDF
            with open(converted_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            branded_pdf_bytes = PDFProcessor._apply_branding(pdf_bytes, str(case_id))
            
            return branded_pdf_bytes, final_pdf_name

        finally:
            # Cleanup all temporary files
            if os.path.exists(source_path):
                os.remove(source_path)
            if converted_pdf_path and os.path.exists(converted_pdf_path):
                os.remove(converted_pdf_path)

    @staticmethod
    def _apply_branding(pdf_bytes: bytes, case_id: str) -> bytes:
        """
        Adds Header, Footer, and Watermark to an existing PDF's bytes using pypdf.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        
        for i, page in enumerate(reader.pages):
            # Create a transparent layer (watermark) for merging
            watermark_stream = io.BytesIO()
            c = canvas.Canvas(watermark_stream, pagesize=page.mediabox)
            
            # --- FOOTER ---
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.grey)
            footer_text = f"Rasti: {case_id} | Faqja {i + 1} / {len(reader.pages)}"
            c.drawCentredString(float(page.mediabox.width) / 2, 1 * cm, footer_text)

            # --- HEADER ---
            header_text = "KONFIDENCIALE | Gjeneruar nga Juristi AI"
            c.drawCentredString(float(page.mediabox.width) / 2, float(page.mediabox.height) - 1 * cm, header_text)

            # --- DIAGONAL WATERMARK ---
            c.setFont("Helvetica-Bold", 48)
            c.setFillColor(colors.lightgrey, alpha=0.15)
            # Position and rotate the canvas for the diagonal text
            c.translate(float(page.mediabox.width)/2, float(page.mediabox.height)/2)
            c.rotate(45)
            c.drawCentredString(0, 0, "DOKUMENT PUNE")
            
            c.save()
            
            # Merge the watermark layer with the original page content
            watermark_pdf = PdfReader(watermark_stream)
            # PHOENIX FIX: pypdf uses merge_page(), not a direct attribute
            page.merge_page(watermark_pdf.pages[0])
            writer.add_page(page)

        # Write the final branded PDF to a memory buffer
        output_stream = io.BytesIO()
        writer.write(output_stream)
        
        return output_stream.getvalue()

# Singleton instance
pdf_service = PDFProcessor()