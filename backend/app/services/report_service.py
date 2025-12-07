# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REPORT SERVICE V2.2 (TYPE SAFETY)
# 1. FIX: Explicit string casting and default values for all Paragraph text inputs.
# 2. STATUS: Resolves Pylance "Argument of type None cannot be assigned to parameter text" errors.

import io
import structlog
import requests
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from pymongo.database import Database
from typing import List, Optional, Union, Any
from bson import ObjectId
from xml.sax.saxutils import escape
from PIL import Image

from ..models.finance import InvoiceInDB
from . import storage_service

logger = structlog.get_logger(__name__)

# --- STYLES & COLORS ---
COLOR_PRIMARY_TEXT = HexColor("#111827")
COLOR_SECONDARY_TEXT = HexColor("#6B7280")
COLOR_BORDER = HexColor("#E5E7EB")

STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='H1', parent=STYLES['h1'], fontSize=22, textColor=COLOR_PRIMARY_TEXT, alignment=TA_RIGHT, fontName='Helvetica-Bold'))
STYLES.add(ParagraphStyle(name='MetaLabel', parent=STYLES['Normal'], fontSize=8, textColor=COLOR_SECONDARY_TEXT, alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='MetaValue', parent=STYLES['Normal'], fontSize=10, textColor=COLOR_PRIMARY_TEXT, alignment=TA_RIGHT, spaceBefore=2))
STYLES.add(ParagraphStyle(name='AddressLabel', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_PRIMARY_TEXT, spaceBottom=4))
STYLES.add(ParagraphStyle(name='AddressText', parent=STYLES['Normal'], fontSize=9, textColor=COLOR_SECONDARY_TEXT, leading=12))
STYLES.add(ParagraphStyle(name='TableHeader', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=white))
STYLES.add(ParagraphStyle(name='TableCell', parent=STYLES['Normal'], fontSize=9, textColor=COLOR_PRIMARY_TEXT))
STYLES.add(ParagraphStyle(name='TableCellRight', parent=STYLES['TableCell'], alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='TotalLabel', parent=STYLES['TableCellRight']))
STYLES.add(ParagraphStyle(name='TotalValue', parent=STYLES['TableCellRight'], fontName='Helvetica-Bold'))
STYLES.add(ParagraphStyle(name='NotesLabel', parent=STYLES['AddressLabel'], spaceBefore=10))

# --- TRANSLATIONS ---
TRANSLATIONS = {
    "sq": {
        "invoice_title": "FATURA", "invoice_num": "Fatura #", "date_issue": "Data e Lëshimit", "date_due": "Afati i Pagesës",
        "status": "Statusi", "from": "Nga", "to": "Për", "desc": "Përshkrimi", "qty": "Sasia", "price": "Çmimi",
        "total": "Totali", "subtotal": "Nëntotali", "tax": "TVSH (18%)", "notes": "Shënime",
        "footer_gen": "Dokument i gjeneruar elektronikisht nga", "page": "Faqe", "report_title": "Raport i Gjetjeve",
        "finding": "Gjetja", "no_findings": "Nuk u gjetën asnjë gjetje për këtë rast.", "case": "Rasti", "generated_for": "Gjeneruar për",
        "lbl_address": "Adresa:", "lbl_tel": "Tel:", "lbl_email": "Email:", "lbl_web": "Web:", "lbl_nui": "NUI:"
    }
}

def _get_text(key: str, lang: str = "sq") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["sq"]).get(key, key)

# --- BRANDING & ASSETS ---
def _get_branding(db: Database, user_id: str) -> dict:
    try:
        try:
            oid = ObjectId(user_id)
            profile = db.business_profiles.find_one({"user_id": oid})
        except:
            profile = None
        
        if not profile:
            profile = db.business_profiles.find_one({"user_id": user_id})

        if profile:
            return {
                "firm_name": profile.get("firm_name", "Juristi.tech"), 
                "address": profile.get("address", ""),
                "email_public": profile.get("email_public", ""), 
                "phone": profile.get("phone", ""),
                "branding_color": profile.get("branding_color", "#4f46e5"), 
                "logo_url": profile.get("logo_url"),
                "logo_storage_key": profile.get("logo_storage_key"), 
                "website": profile.get("website", ""),
                "nui": profile.get("tax_id", "") 
            }
    except Exception as e:
        logger.error(f"Branding fetch failed: {e}")
        
    return {"firm_name": "Juristi.tech", "branding_color": "#4f46e5", "address": "", "email_public": "", "phone": "", "nui": ""}

def _fetch_logo_image(url: Optional[str], storage_key: Optional[str] = None) -> Optional[ImageReader]:
    raw_data = None
    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            if hasattr(stream, 'read'): raw_data = stream.read()
        except Exception as e: logger.warning(f"Failed to fetch logo from storage: {e}")

    if not raw_data and url and url.startswith("http"):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200: raw_data = response.content
        except Exception as e: logger.warning(f"Failed to download logo from URL: {e}")

    if raw_data:
        try:
            img = Image.open(io.BytesIO(raw_data))
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P': img = img.convert('RGBA')
                background.paste(img, mask=img.split()[3]) 
                img = background
            elif img.mode != 'RGB': img = img.convert('RGB')
            final_buffer = io.BytesIO()
            img.save(final_buffer, format='JPEG', quality=95)
            final_buffer.seek(0)
            return ImageReader(final_buffer)
        except Exception as e: logger.error(f"Image processing failed: {e}")
    return None

# --- LAYOUT ENGINE ---
def _header_footer_invoice(canvas: canvas.Canvas, doc: BaseDocTemplate, branding: dict, lang: str):
    canvas.saveState()
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(COLOR_SECONDARY_TEXT)
    firm_name = str(branding.get('firm_name', 'Juristi.tech'))
    footer_msg = f"{_get_text('footer_gen', lang)} {firm_name} | {datetime.now().strftime('%d/%m/%Y')}"
    canvas.drawString(15 * mm, 10 * mm, footer_msg)
    canvas.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    canvas.restoreState()

def _header_footer_report(canvas: canvas.Canvas, doc: BaseDocTemplate, header_right_text: str, branding: dict, lang: str):
    canvas.saveState()
    brand_color = HexColor(branding.get("branding_color", "#4f46e5"))
    canvas.setFillColor(brand_color)
    canvas.rect(0, 280 * mm, 210 * mm, 17 * mm, fill=1, stroke=0) 
    logo_drawn = False
    logo_key = branding.get("logo_storage_key")
    logo_url = branding.get("logo_url")
    if logo_key or logo_url:
        try:
            logo_img = _fetch_logo_image(logo_url, logo_key)
            if logo_img:
                iw, ih = logo_img.getSize()
                aspect = ih / float(iw)
                width = 35 * mm; height = width * aspect
                max_h = 13 * mm
                if height > max_h: height = max_h; width = height / aspect
                y_pos = 280 * mm + (17 * mm - height) / 2
                canvas.drawImage(logo_img, 15 * mm, y_pos, width=width, height=height, mask='auto')
                logo_drawn = True
        except Exception as e: logger.error(f"Error drawing logo on PDF: {e}")
    
    firm_name = str(branding.get("firm_name", "Juristi.tech"))
    if not logo_drawn:
        canvas.setFont('Helvetica-Bold', 16); canvas.setFillColor(white)
        canvas.drawString(15 * mm, 284 * mm, firm_name)
    canvas.setFont('Helvetica-Bold', 14); canvas.setFillColor(white)
    canvas.drawRightString(195 * mm, 284 * mm, header_right_text)
    canvas.setStrokeColor(HexColor("#E5E7EB")); canvas.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    canvas.setFont('Helvetica', 8); canvas.setFillColor(HexColor("#6B7280"))
    footer_msg = f"{_get_text('footer_gen', lang)} {firm_name} | {datetime.now().strftime('%d/%m/%Y')}"
    canvas.drawString(15 * mm, 10 * mm, footer_msg)
    canvas.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    canvas.restoreState()

def _build_doc_invoice(buffer: io.BytesIO, branding: dict, lang: str = "sq") -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=20*mm, bottomMargin=25*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer_invoice(c, d, branding, lang))
    doc.addPageTemplates([template])
    return doc

def _build_doc_report(buffer: io.BytesIO, header_text: str, branding: dict, lang: str = "sq") -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=25*mm, bottomMargin=25*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 20*mm, id='normal')
    template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer_report(c, d, header_text, branding, lang))
    doc.addPageTemplates([template])
    return doc

# --- MAIN GENERATOR ---
def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, user_id: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, user_id)
    buffer = io.BytesIO()
    doc = _build_doc_invoice(buffer, branding, lang)
    brand_color = HexColor(branding.get("branding_color", "#4f46e5"))
    Story: List[Flowable] = []

    # Logo
    logo_img = _fetch_logo_image(branding.get("logo_url"), branding.get("logo_storage_key"))
    logo_flowable = Spacer(0, 0)
    if logo_img:
        try:
            iw, ih = logo_img.getSize()
            aspect = ih / float(iw)
            width = 40 * mm
            height = width * aspect
            if height > 30 * mm: height = 30 * mm; width = height / aspect
            from reportlab.platypus import Image as ReportLabImage
            logo_flowable = ReportLabImage(logo_img, width=width, height=height)
            logo_flowable.hAlign = 'LEFT'
        except Exception as e: logger.error(f"Failed to place logo flowable: {e}")

    # PHOENIX FIX: Type-Safe Header Construction
    firm_details_content: List[Flowable] = []
    
    # 1. Firm Name
    firm_name = branding.get("firm_name")
    if firm_name:
        firm_details_content.append(Paragraph(str(firm_name), ParagraphStyle('FirmName', parent=STYLES['h3'], alignment=TA_RIGHT, fontSize=12, spaceAfter=4)))
    
    # 2. Address
    address = branding.get("address")
    if address:
        addr_html = f"<b>{_get_text('lbl_address', lang)}</b> {address}"
        firm_details_content.append(Paragraph(addr_html, ParagraphStyle('FirmAddress', parent=STYLES['AddressText'], alignment=TA_RIGHT)))
        
    # 3. NUI
    nui = branding.get("nui")
    if nui:
        nui_html = f"<b>{_get_text('lbl_nui', lang)}</b> {nui}"
        firm_details_content.append(Paragraph(nui_html, ParagraphStyle('FirmMeta', parent=STYLES['AddressText'], alignment=TA_RIGHT)))
        
    # 4. Email
    email = branding.get("email_public")
    if email:
        email_html = f"<b>{_get_text('lbl_email', lang)}</b> {email}"
        firm_details_content.append(Paragraph(email_html, ParagraphStyle('FirmMeta', parent=STYLES['AddressText'], alignment=TA_RIGHT)))
        
    # 5. Phone
    phone = branding.get("phone")
    if phone:
        phone_html = f"<b>{_get_text('lbl_tel', lang)}</b> {phone}"
        firm_details_content.append(Paragraph(phone_html, ParagraphStyle('FirmMeta', parent=STYLES['AddressText'], alignment=TA_RIGHT)))
        
    # 6. Website
    website = branding.get("website")
    if website:
        web_html = f"<b>{_get_text('lbl_web', lang)}</b> {website}"
        firm_details_content.append(Paragraph(web_html, ParagraphStyle('FirmMeta', parent=STYLES['AddressText'], alignment=TA_RIGHT)))

    header_table = Table([[logo_flowable, firm_details_content]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    Story.append(header_table)
    Story.append(Spacer(1, 15*mm))

    meta_table_data = [
        [Paragraph(f"{_get_text('invoice_num', lang)} {invoice.invoice_number}", STYLES['MetaValue'])],
        [Spacer(1, 2*mm)],
        [Paragraph(_get_text('date_issue', lang), STYLES['MetaLabel'])], [Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
        [Spacer(1, 2*mm)],
        [Paragraph(_get_text('date_due', lang), STYLES['MetaLabel'])], [Paragraph(invoice.due_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
    ]
    meta_table = Table(meta_table_data, colWidths=[80*mm], style=[('ALIGN', (0,0), (-1,-1), 'RIGHT')])
    title_table = Table([[Paragraph(_get_text('invoice_title', lang), STYLES['H1']), meta_table]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    Story.append(title_table)
    Story.append(Spacer(1, 15*mm))

    client_address_lines = [line.strip() for line in (invoice.client_address or "").split('\n') if line.strip()]
    client_block = [Paragraph(f"<b>{invoice.client_name}</b>", STYLES['AddressText'])] + [Paragraph(line, STYLES['AddressText']) for line in client_address_lines]
    if invoice.client_email: client_block.append(Paragraph(invoice.client_email, STYLES['AddressText']))
    address_table = Table([[Paragraph(_get_text('to', lang), STYLES['AddressLabel']), client_block]], colWidths=[20*mm, 160*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    Story.append(address_table)
    Story.append(Spacer(1, 10*mm))
    
    headers = [Paragraph(h, STYLES['TableHeader']) for h in [_get_text('desc', lang), _get_text('qty', lang), _get_text('price', lang), _get_text('total', lang)]]
    items_data = [headers]
    for item in invoice.items:
        items_data.append([
            Paragraph(item.description, STYLES['TableCell']),
            Paragraph(str(item.quantity), STYLES['TableCellRight']),
            Paragraph(f"€{item.unit_price:,.2f}", STYLES['TableCellRight']),
            Paragraph(f"€{item.total:,.2f}", STYLES['TableCellRight']),
        ])
    items_table = Table(items_data, colWidths=[95*mm, 20*mm, 30*mm, 35*mm], style=[
        ('BACKGROUND', (0,0), (-1,0), brand_color), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, COLOR_BORDER), ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")])
    ])
    Story.append(items_table)
    
    totals_data = [
        [Paragraph(_get_text('subtotal', lang), STYLES['TotalLabel']), Paragraph(f"€{invoice.subtotal:,.2f}", STYLES['TotalLabel'])],
        [Paragraph(_get_text('tax', lang), STYLES['TotalLabel']), Paragraph(f"€{invoice.tax_amount:,.2f}", STYLES['TotalLabel'])],
        [Paragraph(f"<b>{_get_text('total', lang)}</b>", STYLES['TotalValue']), Paragraph(f"<b>€{invoice.total_amount:,.2f}</b>", STYLES['TotalValue'])],
    ]
    totals_table = Table(totals_data, colWidths=[40*mm, 35*mm], style=[
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LINEABOVE', (0, 2), (1, 2), 1.5, COLOR_PRIMARY_TEXT),
        ('TOPPADDING', (0, 2), (1, 2), 6),
    ])
    summary_table = Table([["", totals_table]], colWidths=[110*mm, 70*mm], style=[('ALIGN', (1,0), (1,0), 'RIGHT')])
    Story.append(summary_table)

    if invoice.notes:
        Story.append(Spacer(1, 10*mm))
        Story.append(Paragraph(_get_text('notes', lang), STYLES['NotesLabel']))
        Story.append(Paragraph(escape(invoice.notes).replace('\n', '<br/>'), STYLES['AddressText']))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def generate_findings_report_pdf(db: Database, case_id: str, case_title: str, user_id: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, user_id)
    buffer = io.BytesIO()
    doc = _build_doc_report(buffer, _get_text('report_title', lang), branding, lang)
    styles = getSampleStyleSheet()
    Story: List[Flowable] = []
    
    Story.append(Spacer(1, 10*mm))
    Story.append(Paragraph(_get_text('report_title', lang), styles['h1']))
    
    meta_data = [
        [Paragraph(f"<b>{_get_text('case', lang)}:</b>", styles['Normal']), Paragraph(case_title, styles['Normal'])],
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
    doc = _build_doc_report(buffer, document_title, {"firm_name": "Juristi.tech", "branding_color": "#333333"}, "sq")
    Story: List[Flowable] = [
        Spacer(1, 15*mm),
        Paragraph(escape(text).replace('\n', '<br/>'), getSampleStyleSheet()['Normal'])
    ]
    doc.build(Story)
    buffer.seek(0)
    return buffer