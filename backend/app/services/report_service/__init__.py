# FILE: backend/app/services/report_service/__init__.py
# PHOENIX PROTOCOL - REPORT SERVICE HUB V6.0 (INVOICE & PDF UTILITY RE-EXPORTER)

import io
import logging
from typing import Optional, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)

# Importo gjeneruesin e faturave ekzistuese
try:
    from .invoice_report import generate_invoice_pdf
except ImportError:
    def generate_invoice_pdf(invoice_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> io.BytesIO:
        """Fallback invoice generator nëse mungon moduli i brendshëm."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(f"FATURË: {invoice_data.get('invoice_number', 'N/A')}", styles['Heading1']),
            Spacer(1, 10),
            Paragraph(f"Shuma: €{invoice_data.get('total_amount', 0.0):,.2f}", styles['Normal']),
        ]
        doc.build(story)
        buffer.seek(0)
        return buffer


def create_pdf_from_text(
    text: str,
    document_title: str = "DOKUMENT ZYRTAR",
    header_meta_content_html: str = ""
) -> io.BytesIO:
    """Gjeneron dokument PDF me format të pastër nga teksti i dhënë."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=12
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    story = []

    if document_title:
        story.append(Paragraph(document_title, title_style))
        story.append(Spacer(1, 8))

    if header_meta_content_html:
        meta_style = ParagraphStyle(
            'DocMeta',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=12
        )
        story.append(Paragraph(header_meta_content_html, meta_style))
        story.append(Spacer(1, 10))

    for line in text.split('\n'):
        clean_line = line.strip()
        if clean_line:
            story.append(Paragraph(clean_line, body_style))
        else:
            story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    return buffer