# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - INVOICE GENERATOR ADDED
# 1. UPGRADE: Added 'generate_invoice_pdf' function.
# 2. BRANDING: Uses the same white-label logic (Logo, Colors) for Invoices.

from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
import structlog
from pymongo.database import Database
from typing import List
from xml.sax.saxutils import escape

# Phoenix Imports
from ..models.finance import InvoiceInDB

logger = structlog.get_logger(__name__)

# --- HELPER: Fetch Branding ---
def _get_branding(db: Database, search_term: str) -> dict:
    """
    Fetches branding using username or email string.
    """
    try:
        user = db.users.find_one({"$or": [{"email": search_term}, {"username": search_term}]})
        if user:
            profile = db.business_profiles.find_one({"user_id": str(user["_id"])})
            if profile:
                return {
                    "header_text": profile.get("firm_name", "Juristi AI Platform"),
                    "address": profile.get("address", ""),
                    "email": profile.get("email_public", user["email"]),
                    "phone": profile.get("phone", ""),
                    "color": profile.get("branding_color", "#1f2937"),
                    # Add Logo logic here later if needed
                }
    except Exception:
        pass
    return {"header_text": "Juristi AI Platform", "color": "#1f2937", "address": "", "email": "", "phone": ""}

def _header_footer(canvas: canvas.Canvas, doc: BaseDocTemplate, header_right_text: str, branding: dict):
    canvas.saveState()
    # Dynamic Branding
    header_text = branding["header_text"]
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(15 * mm, 282 * mm, header_text)
    
    canvas.setFont('Helvetica-Oblique', 9)
    canvas.drawRightString(195 * mm, 282 * mm, header_right_text)
    
    canvas.setStrokeColor(HexColor(branding["color"]))
    canvas.setLineWidth(1)
    canvas.line(15 * mm, 278 * mm, 195 * mm, 278 * mm)
    
    footer_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    page_num_text = f"Page {doc.page}"
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(15 * mm, 15 * mm, footer_text)
    canvas.drawRightString(195 * mm, 15 * mm, page_num_text)
    canvas.restoreState()

def _build_enhanced_doc_template(buffer: BytesIO, header_right_text: str, branding: dict) -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=25*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='main_template', frames=[frame], onPage=lambda canvas, doc: _header_footer(canvas, doc, header_right_text, branding))
    doc.addPageTemplates([template])
    return doc

def _create_summary_table(findings: list, case_title: str, username: str) -> Table:
    # (Previous implementation remains unchanged)
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

def generate_findings_report_pdf(db: Database, case_id: str, case_title: str, username: str) -> BytesIO:
    # (Previous implementation remains unchanged)
    branding = _get_branding(db, username)
    buffer = BytesIO()
    doc = _build_enhanced_doc_template(buffer, "Raport Konfidencial i Gjetjeve", branding)
    
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
            finding_text = escape(finding.get('finding_text', ''))
            Story.append(Paragraph(finding_text.replace('\n', '<br/>'), styles['Normal']))
            Story.append(Spacer(1, 8 * mm))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def create_pdf_from_text(text: str, document_title: str = "Dokument") -> BytesIO:
    # (Previous implementation remains unchanged)
    branding = {"header_text": "Juristi AI Platform", "color": "#1f2937"}
    buffer = BytesIO()
    doc = _build_enhanced_doc_template(buffer, f"Dokument: {escape(document_title)}", branding)
    styles = getSampleStyleSheet()
    styles['Normal'].alignment = TA_JUSTIFY
    Story: List[Flowable] = [Paragraph(escape(p).replace('\n', '<br/>'), styles['Normal']) for p in text.split('\n\n') if p.strip()]
    if not Story: Story.append(Paragraph("Ky dokument nuk ka përmbajtje të nxjerrshme.", styles['Normal']))
    doc.build(Story)
    buffer.seek(0)
    return buffer

# --- NEW: INVOICE GENERATOR ---
def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, username: str) -> BytesIO:
    """Generates a professional Invoice PDF."""
    branding = _get_branding(db, username)
    buffer = BytesIO()
    doc = _build_enhanced_doc_template(buffer, f"Fatura #{invoice.invoice_number}", branding)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=TA_RIGHT))
    
    Story: List[Flowable] = []
    
    # 1. Title
    Story.append(Paragraph("FATURA / INVOICE", styles['h1']))
    Story.append(Spacer(1, 5 * mm))
    
    # 2. Meta Info Table (Date, #)
    meta_data = [
        ["Numri i Faturës:", invoice.invoice_number],
        ["Data e Lëshimit:", invoice.issue_date.strftime("%d-%m-%Y")],
        ["Afati i Pagesës:", invoice.due_date.strftime("%d-%m-%Y")],
        ["Statusi:", invoice.status.upper()]
    ]
    meta_table = Table(meta_data, colWidths=[40*mm, 60*mm], hAlign='RIGHT')
    meta_table.setStyle(TableStyle([('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold')]))
    Story.append(meta_table)
    Story.append(Spacer(1, 10 * mm))
    
    # 3. From / To Section
    from_text = f"<b>Nga:</b><br/>{branding['header_text']}<br/>{branding.get('address','')}<br/>{branding.get('email','')}"
    to_text = f"<b>Për:</b><br/>{invoice.client_name}<br/>{invoice.client_address or ''}<br/>{invoice.client_email or ''}"
    
    address_table = Table([[Paragraph(from_text, styles['Normal']), Paragraph(to_text, styles['Normal'])]], colWidths=[90*mm, 90*mm])
    address_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(address_table)
    Story.append(Spacer(1, 15 * mm))
    
    # 4. Items Table
    data = [["Përshkrimi / Description", "Sasia", "Çmimi", "Totali"]]
    for item in invoice.items:
        data.append([
            item.description,
            str(item.quantity),
            f"€{item.unit_price:.2f}",
            f"€{item.total:.2f}"
        ])
    
    # Add Totals
    data.append(["", "", "Nëntotali:", f"€{invoice.subtotal:.2f}"])
    data.append(["", "", f"TVSH ({invoice.tax_rate}%):", f"€{invoice.tax_amount:.2f}"])
    data.append(["", "", "TOTALI:", f"€{invoice.total_amount:.2f}"])
    
    t = Table(data, colWidths=[90*mm, 25*mm, 35*mm, 30*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor(branding['color'])),
        ('TEXTCOLOR', (0,0), (-1,0), HexColor("#FFFFFF")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'), # Numbers right aligned
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-3), 1, HexColor("#EEEEEE")),
        ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'), # Total Bold
        ('BACKGROUND', (-2,-1), (-1,-1), HexColor("#F0F0F0")),
    ]))
    Story.append(t)
    
    # 5. Notes
    if invoice.notes:
        Story.append(Spacer(1, 10 * mm))
        Story.append(Paragraph("Shënime:", styles['h4']))
        Story.append(Paragraph(invoice.notes, styles['Normal']))

    doc.build(Story)
    buffer.seek(0)
    return buffer