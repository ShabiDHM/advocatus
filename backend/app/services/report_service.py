# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REPORT ENGINE v2.3 (TYPE FIX)
# 1. FIX: _fetch_logo_image now accepts Optional[str] for url.
# 2. STATUS: Fully typed and compliant.

import io
import structlog
import requests
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.utils import ImageReader
from pymongo.database import Database
from typing import List, Optional, Any
from xml.sax.saxutils import escape

# Phoenix Imports
from ..models.finance import InvoiceInDB
from ..services import storage_service

logger = structlog.get_logger(__name__)

# --- TRANSLATIONS ---
TRANSLATIONS = {
    "sq": {
        "invoice_title": "FATURA",
        "invoice_num": "Nr. Faturës",
        "date_issue": "Data e Lëshimit",
        "date_due": "Afati i Pagesës",
        "status": "Statusi",
        "from": "Nga",
        "to": "Për",
        "desc": "Përshkrimi",
        "qty": "Sasia",
        "price": "Çmimi",
        "total": "Totali",
        "subtotal": "Nëntotali",
        "tax": "TVSH",
        "notes": "Shënime",
        "footer_gen": "Gjeneruar më",
        "page": "Faqe",
        "report_title": "Raport i Gjetjeve",
        "finding": "Gjetja",
        "no_findings": "Nuk u gjetën asnjë gjetje për këtë rast.",
        "case": "Rasti",
        "generated_for": "Gjeneruar për"
    },
    "en": {
        "invoice_title": "INVOICE",
        "invoice_num": "Invoice No",
        "date_issue": "Date of Issue",
        "date_due": "Due Date",
        "status": "Status",
        "from": "From",
        "to": "Bill To",
        "desc": "Description",
        "qty": "Qty",
        "price": "Price",
        "total": "Total",
        "subtotal": "Subtotal",
        "tax": "VAT",
        "notes": "Notes",
        "footer_gen": "Generated on",
        "page": "Page",
        "report_title": "Findings Report",
        "finding": "Finding",
        "no_findings": "No findings found for this case.",
        "case": "Case",
        "generated_for": "Generated for"
    },
    "sr": {
        "invoice_title": "FAKTURA",
        "invoice_num": "Broj Fakture",
        "date_issue": "Datum Izdavanja",
        "date_due": "Rok Plaćanja",
        "status": "Status",
        "from": "Od",
        "to": "Za",
        "desc": "Opis",
        "qty": "Količina",
        "price": "Cijena",
        "total": "Ukupno",
        "subtotal": "Međuzbir",
        "tax": "PDV",
        "notes": "Napomene",
        "footer_gen": "Generisano dana",
        "page": "Stranica",
        "report_title": "Izveštaj o Nalazima",
        "finding": "Nalaz",
        "no_findings": "Nisu pronađeni nalazi za ovaj slučaj.",
        "case": "Slučaj",
        "generated_for": "Generisano za"
    }
}

def _get_text(key: str, lang: str = "sq") -> str:
    lang_map = TRANSLATIONS.get(lang, TRANSLATIONS["sq"])
    return lang_map.get(key, key)

# --- BRANDING & ASSETS ---
def _get_branding(db: Database, search_term: str) -> dict:
    """Fetches branding including Logo Storage Key."""
    try:
        user = db.users.find_one({"$or": [{"email": search_term}, {"username": search_term}]})
        if user:
            profile = db.business_profiles.find_one({"user_id": user["_id"]})
            if profile:
                return {
                    "header_text": profile.get("firm_name", "Juristi AI Platform"),
                    "address": profile.get("address", ""),
                    "email": profile.get("email_public", user["email"]),
                    "phone": profile.get("phone", ""),
                    "color": profile.get("branding_color", "#1f2937"),
                    "logo_url": profile.get("logo_url"),
                    "logo_storage_key": profile.get("logo_storage_key"),
                    "website": profile.get("website", "")
                }
    except Exception as e:
        logger.warning(f"Branding fetch failed: {e}")
    return {"header_text": "Juristi AI Platform", "color": "#1f2937", "address": "", "email": "", "phone": ""}

# PHOENIX FIX: Changed url type to Optional[str]
def _fetch_logo_image(url: Optional[str], storage_key: Optional[str] = None) -> Optional[ImageReader]:
    """
    Downloads logo. 
    Priority 1: Direct from Storage (Fastest/Safest).
    Priority 2: Public URL (Fallback).
    """
    # 1. Try Direct Storage Access
    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            return ImageReader(io.BytesIO(stream.read()))
        except Exception as e:
            logger.warning(f"Failed to fetch logo from storage: {e}")

    # 2. Try URL Fallback
    if url and not url.startswith("/"):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return ImageReader(io.BytesIO(response.content))
        except Exception as e:
            logger.warning(f"Failed to download logo from URL: {e}")
            
    return None

def _header_footer(canvas: canvas.Canvas, doc: BaseDocTemplate, header_right_text: str, branding: dict, lang: str):
    canvas.saveState()
    
    # 1. Logo
    logo_drawn = False
    logo_key = branding.get("logo_storage_key")
    logo_url = branding.get("logo_url")
    
    if logo_key or logo_url:
        logo_img = _fetch_logo_image(logo_url, logo_key)
        if logo_img:
            iw, ih = logo_img.getSize()
            aspect = ih / float(iw)
            width = 40 * mm
            height = width * aspect
            if height > 20 * mm:
                height = 20 * mm
                width = height / aspect
            
            canvas.drawImage(logo_img, 15 * mm, 272 * mm, width=width, height=height, mask='auto')
            logo_drawn = True

    # 2. Header Text (Firm Name)
    text_x = 15 * mm if not logo_drawn else 60 * mm
    canvas.setFont('Helvetica-Bold', 12)
    canvas.setFillColor(HexColor(branding["color"]))
    canvas.drawString(text_x, 285 * mm, branding["header_text"])
    
    # 3. Right Header Text (Invoice #)
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawRightString(195 * mm, 285 * mm, header_right_text)
    
    # Divider
    canvas.setStrokeColor(HexColor(branding["color"]))
    canvas.setLineWidth(1)
    canvas.line(15 * mm, 270 * mm, 195 * mm, 270 * mm)
    
    # Footer
    footer_text = f"{_get_text('footer_gen', lang)}: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    page_num_text = f"{_get_text('page', lang)} {doc.page}"
    
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor("#888888"))
    canvas.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    canvas.drawString(15 * mm, 10 * mm, footer_text)
    
    if branding.get("website"):
        canvas.drawCentredString(105 * mm, 10 * mm, branding["website"])
        
    canvas.drawRightString(195 * mm, 10 * mm, page_num_text)
    
    canvas.restoreState()

def _build_doc(buffer: io.BytesIO, header_text: str, branding: dict, lang: str = "sq") -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=35*mm, bottomMargin=25*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 10*mm, id='normal')
    template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer(c, d, header_text, branding, lang))
    doc.addPageTemplates([template])
    return doc

# --- PUBLIC GENERATORS ---

def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, username: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, username)
    buffer = io.BytesIO()
    
    title_text = f"{_get_text('invoice_title', lang)} #{invoice.invoice_number}"
    doc = _build_doc(buffer, title_text, branding, lang)
    
    styles = getSampleStyleSheet()
    brand_color = HexColor(branding["color"])
    
    Story: List[Flowable] = []
    
    # Styles
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=8, textColor=HexColor("#666666"))
    val_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=10, leading=12)
    meta_label_style = ParagraphStyle('MetaLabel', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8, textColor=HexColor("#666666"))
    meta_val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=10)
    meta_val_bold_style = ParagraphStyle('MetaValBold', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=10, fontName='Helvetica-Bold')
    
    # 1. HEADER (From/To/Meta)
    from_block = [
        Paragraph(f"<b>{_get_text('from', lang)}:</b>", label_style),
        Paragraph(f"<b>{branding['header_text']}</b>", val_style),
        Paragraph(branding.get('address','') or "", val_style),
        Paragraph(branding.get('email','') or "", val_style),
        Paragraph(branding.get('phone','') or "", val_style),
        Spacer(1, 5*mm),
        Paragraph(f"<b>{_get_text('to', lang)}:</b>", label_style),
        Paragraph(f"<b>{invoice.client_name}</b>", val_style),
        Paragraph(invoice.client_address or "", val_style),
        Paragraph(invoice.client_email or "", val_style),
    ]
    
    meta_block = [
        Spacer(1, 2*mm),
        Paragraph(_get_text('invoice_num', lang), meta_label_style),
        Paragraph(f"<b>{invoice.invoice_number}</b>", meta_val_style),
        Spacer(1, 3*mm),
        Paragraph(_get_text('date_issue', lang), meta_label_style),
        Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), meta_val_style),
        Spacer(1, 3*mm),
        Paragraph(_get_text('date_due', lang), meta_label_style),
        Paragraph(invoice.due_date.strftime("%d/%m/%Y"), meta_val_style),
        Spacer(1, 3*mm),
        Paragraph(_get_text('status', lang), meta_label_style),
        Paragraph(f"<b>{invoice.status.upper()}</b>", meta_val_bold_style),
    ]
    
    header_table = Table([[from_block, meta_block]], colWidths=[110*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    Story.append(header_table)
    Story.append(Spacer(1, 15*mm))
    
    # 2. ITEMS TABLE
    h_style = ParagraphStyle('THead', parent=styles['Normal'], textColor=HexColor("#FFFFFF"), fontName='Helvetica-Bold', fontSize=10)
    
    headers = [
        Paragraph(_get_text('desc', lang), h_style),
        Paragraph(_get_text('qty', lang), ParagraphStyle('HQty', parent=h_style, alignment=TA_RIGHT)),
        Paragraph(_get_text('price', lang), ParagraphStyle('HPrice', parent=h_style, alignment=TA_RIGHT)),
        Paragraph(_get_text('total', lang), ParagraphStyle('HTotal', parent=h_style, alignment=TA_RIGHT)),
    ]
    
    table_data: List[List[Any]] = [headers]
    
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=10)
    cell_right = ParagraphStyle('CellRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=10)
    
    for item in invoice.items:
        table_data.append([
            Paragraph(item.description, cell_style),
            Paragraph(str(item.quantity), cell_right),
            Paragraph(f"€{item.unit_price:,.2f}", cell_right),
            Paragraph(f"€{item.total:,.2f}", cell_right)
        ])
    
    t = Table(table_data, colWidths=[90*mm, 20*mm, 35*mm, 35*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_color),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('TOPPADDING', (0,0), (-1,0), 10),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor("#EEEEEE")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    Story.append(t)
    
    # 3. TOTALS
    total_lbl_style = ParagraphStyle('TLbl', parent=styles['Normal'], fontSize=12, textColor=brand_color, alignment=TA_RIGHT)
    total_val_style = ParagraphStyle('TVal', parent=styles['Normal'], fontSize=12, textColor=brand_color, alignment=TA_RIGHT, fontName='Helvetica-Bold')
    
    def _p_right(text, bold=False):
        return Paragraph(text, total_val_style if bold else total_lbl_style)

    totals_rows = [
        [_p_right(_get_text('subtotal', lang) + ":"), _p_right(f"€{invoice.subtotal:,.2f}")],
        [_p_right(f"{_get_text('tax', lang)} ({invoice.tax_rate}%):"), _p_right(f"€{invoice.tax_amount:,.2f}")],
        [_p_right(_get_text('total', lang) + ":", True), _p_right(f"€{invoice.total_amount:,.2f}", True)]
    ]
    
    totals_table = Table(totals_rows, colWidths=[50*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ('LINEABOVE', (0,-1), (-1,-1), 1, brand_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    outer_table = Table([[ "", totals_table ]], colWidths=[95*mm, 85*mm])
    outer_table.setStyle(TableStyle([('ALIGN', (-1,0), (-1,-1), 'RIGHT')]))
    
    Story.append(Spacer(1, 2*mm))
    Story.append(outer_table)
    
    # 4. NOTES
    if invoice.notes:
        Story.append(Spacer(1, 15*mm))
        Story.append(Paragraph(f"<b>{_get_text('notes', lang)}:</b>", styles['Normal']))
        Story.append(Paragraph(invoice.notes, styles['Normal']))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def generate_findings_report_pdf(db: Database, case_id: str, case_title: str, username: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, username)
    buffer = io.BytesIO()
    doc = _build_doc(buffer, _get_text('report_title', lang), branding, lang)
    styles = getSampleStyleSheet()
    Story: List[Flowable] = []
    
    Story.append(Paragraph(_get_text('report_title', lang), styles['h1']))
    Story.append(Spacer(1, 10 * mm))
    
    meta_data = [
        [Paragraph(f"<b>{_get_text('case', lang)}:</b>", styles['Normal']), Paragraph(case_title, styles['Normal'])],
        [Paragraph(f"<b>{_get_text('generated_for', lang)}:</b>", styles['Normal']), Paragraph(username, styles['Normal'])]
    ]
    t = Table(meta_data, colWidths=[40*mm, 120*mm])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")), ('BACKGROUND', (0,0), (0,-1), HexColor("#F5F5F5"))]))
    Story.append(t)
    Story.append(Spacer(1, 10 * mm))
    
    from . import findings_service
    findings = findings_service.get_findings_for_case(db=db, case_id=case_id)
    
    if not findings:
        Story.append(Paragraph(_get_text('no_findings', lang), styles['Normal']))
    else:
        for i, finding in enumerate(findings, 1):
            title = f"{_get_text('finding', lang)} #{i}: {escape(finding.get('document_name', ''))}"
            Story.append(Paragraph(title, styles['h3']))
            text = escape(finding.get('finding_text', ''))
            Story.append(Paragraph(text.replace('\n', '<br/>'), styles['Normal']))
            Story.append(Spacer(1, 5 * mm))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def create_pdf_from_text(text: str, document_title: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _build_doc(buffer, document_title, {"header_text": "Juristi AI", "color": "#333333"}, "sq")
    Story: List[Flowable] = [Paragraph(escape(text).replace('\n', '<br/>'), getSampleStyleSheet()['Normal'])]
    doc.build(Story)
    buffer.seek(0)
    return buffer