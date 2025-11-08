# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL MODIFICATION 4.1 (FINAL & COMPLETE VERSION):
# 1. This is the fully-expanded, definitive version of the file. No functions have been
#    simplified or omitted, adhering to the "complete file replacement" protocol.
# 2. CRITICAL CRASH FIX: All text content is now correctly escaped before being passed
#    to the `reportlab` library, resolving the `500 Internal Server Error` on download.

from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
import structlog
from pymongo.database import Database
from typing import List
from xml.sax.saxutils import escape

logger = structlog.get_logger(__name__)

# --- Fully Expanded Helper Functions ---

def _header_footer(canvas: canvas.Canvas, doc: BaseDocTemplate, header_right_text: str):
    """
    Adds a header and footer to each page of the PDF.
    """
    canvas.saveState()
    # Header
    header_text = "Advocatus AI Platform"
    canvas.setFont('Helvetica', 9)
    canvas.drawString(15 * mm, 282 * mm, header_text)
    canvas.setFont('Helvetica-Oblique', 9)
    canvas.drawRightString(195 * mm, 282 * mm, header_right_text)
    canvas.line(15 * mm, 278 * mm, 195 * mm, 278 * mm)
    
    # Footer
    footer_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    page_num_text = f"Page {doc.page}"
    canvas.setFont('Helvetica', 8)
    canvas.drawString(15 * mm, 15 * mm, footer_text)
    canvas.drawRightString(195 * mm, 15 * mm, page_num_text)
    
    canvas.restoreState()

def _build_enhanced_doc_template(buffer: BytesIO, header_right_text: str) -> BaseDocTemplate:
    """
    Creates a BaseDocTemplate with custom headers and footers.
    """
    doc = BaseDocTemplate(buffer,
                        pagesize=A4,
                        leftMargin=20*mm,
                        rightMargin=20*mm,
                        topMargin=25*mm,
                        bottomMargin=25*mm)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    
    template = PageTemplate(id='main_template',
                            frames=[frame],
                            onPage=lambda canvas, doc: _header_footer(canvas, doc, header_right_text))
    
    doc.addPageTemplates([template])
    return doc

def _create_summary_table(findings: list, case_title: str, username: str) -> Table:
    """
    Creates a summary table for the findings report.
    """
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(name='HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

    data = [
        [Paragraph('Case Title:', header_style), Paragraph(escape(case_title), styles['Normal'])],
        [Paragraph('Generated For:', header_style), Paragraph(escape(username), styles['Normal'])],
        [Paragraph('Total Findings:', header_style), Paragraph(str(len(findings)), styles['Normal'])],
    ]

    table = Table(data, colWidths=[40*mm, None])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#F0F0F0")),
        ('GRID', (0, 0), (-1, -1), 1, HexColor("#FFFFFF")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    return table

# --- Core Service Functions ---

def generate_findings_report_pdf(db: Database, case_id: str, case_title: str, username: str) -> BytesIO:
    log = logger.bind(case_id=case_id, username=username)
    log.info("report_service.enhanced_findings_pdf.started")
    buffer = BytesIO()
    doc = _build_enhanced_doc_template(buffer, "Raport Konfidencial i Gjetjeve")
    
    styles = getSampleStyleSheet()
    styles['h1'].alignment = TA_CENTER
    styles['Normal'].alignment = TA_JUSTIFY
    
    Story: List[Flowable] = []
    
    Story.append(Paragraph("RAPORT I GJETJEVE", styles['h1']))
    Story.append(Spacer(1, 12 * mm))
    
    from . import findings_service
    findings = findings_service.get_findings_for_case(db=db, case_id=case_id)
    
    Story.append(_create_summary_table(findings, case_title, username))
    Story.append(Spacer(1, 10 * mm))
    
    if not findings:
        Story.append(Paragraph("Nuk u gjetën asnjë gjetje për këtë rast.", styles['Normal']))
    else:
        finding_header_style = ParagraphStyle(name='FindingHeader', parent=styles['h2'], fontSize=12, spaceAfter=2*mm)
        for i, finding in enumerate(findings, 1):
            header = f"Gjetja #{i}: {escape(finding.get('document_name', ''))} (Faqe {finding.get('page_number', 'N/A')})"
            Story.append(Paragraph(header, finding_header_style))
            
            # --- PHOENIX PROTOCOL: Escape content to prevent crashes ---
            finding_text = escape(finding.get('finding_text', ''))
            Story.append(Paragraph(finding_text.replace('\n', '<br/>'), styles['Normal']))
            Story.append(Spacer(1, 8 * mm))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def create_pdf_from_text(text: str, document_title: str = "Dokument") -> BytesIO:
    buffer = BytesIO()
    doc = _build_enhanced_doc_template(buffer, f"Dokument: {escape(document_title)}")
    
    styles = getSampleStyleSheet()
    styles['Normal'].alignment = TA_JUSTIFY
    
    # --- PHOENIX PROTOCOL FIX: Escape all text content before passing to Paragraph ---
    Story: List[Flowable] = [
        Paragraph(escape(p).replace('\n', '<br/>'), styles['Normal'])
        for p in text.split('\n\n') if p.strip()
    ]
    
    if not Story:
        Story.append(Paragraph("Ky dokument nuk ka përmbajtje të nxjerrshme.", styles['Normal']))

    doc.build(Story)
    buffer.seek(0)
    return buffer