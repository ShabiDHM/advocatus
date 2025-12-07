# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REVISION 2
# 1. FIX: Logo now loads directly from Storage Service bytes (bypassing HTTP loopback).
# 2. FEATURE: Added intelligent prefix injection for Client Details (Address, Tel, NUI).
# 3. STABILITY: Enhanced PIL image processing to handle RGBA/Palette transparency for PDFs.

import io
import structlog
import requests
import re
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.platypus import Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from pymongo.database import Database
from typing import List, Optional, Union, Any
from bson import ObjectId
from xml.sax.saxutils import escape
from PIL import Image as PILImage

from app.models.finance import InvoiceInDB
from app.services import storage_service, findings_service

logger = structlog.get_logger(__name__)

# --- STYLES & COLORS ---
COLOR_PRIMARY_TEXT = HexColor("#111827")
COLOR_SECONDARY_TEXT = HexColor("#6B7280")
COLOR_BORDER = HexColor("#E5E7EB")
BRAND_COLOR_DEFAULT = "#4f46e5"

STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='H1', parent=STYLES['h1'], fontSize=22, textColor=COLOR_PRIMARY_TEXT, alignment=TA_RIGHT, fontName='Helvetica-Bold'))
STYLES.add(ParagraphStyle(name='MetaLabel', parent=STYLES['Normal'], fontSize=8, textColor=COLOR_SECONDARY_TEXT, alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='MetaValue', parent=STYLES['Normal'], fontSize=10, textColor=COLOR_PRIMARY_TEXT, alignment=TA_RIGHT, spaceBefore=2))
STYLES.add(ParagraphStyle(name='AddressLabel', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=COLOR_PRIMARY_TEXT, spaceBottom=6))
STYLES.add(ParagraphStyle(name='AddressText', parent=STYLES['Normal'], fontSize=9, textColor=COLOR_SECONDARY_TEXT, leading=14))
STYLES.add(ParagraphStyle(name='TableHeader', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=white))
STYLES.add(ParagraphStyle(name='TableCell', parent=STYLES['Normal'], fontSize=9, textColor=COLOR_PRIMARY_TEXT))
STYLES.add(ParagraphStyle(name='TableCellRight', parent=STYLES['TableCell'], alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='TotalLabel', parent=STYLES['TableCellRight']))
STYLES.add(ParagraphStyle(name='TotalValue', parent=STYLES['TableCellRight'], fontName='Helvetica-Bold'))
STYLES.add(ParagraphStyle(name='NotesLabel', parent=STYLES['AddressLabel'], spaceBefore=10))
STYLES.add(ParagraphStyle(name='FirmName', parent=STYLES['h3'], alignment=TA_RIGHT, fontSize=14, spaceAfter=4, textColor=COLOR_PRIMARY_TEXT))
STYLES.add(ParagraphStyle(name='FirmMeta', parent=STYLES['Normal'], alignment=TA_RIGHT, fontSize=9, textColor=COLOR_SECONDARY_TEXT, leading=12))

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
                "branding_color": profile.get("branding_color", BRAND_COLOR_DEFAULT), 
                "logo_url": profile.get("logo_url"),
                "logo_storage_key": profile.get("logo_storage_key"), 
                "website": profile.get("website", ""),
                "nui": profile.get("tax_id", "") 
            }
    except Exception as e:
        logger.error(f"Branding fetch failed: {e}")
    return {"firm_name": "Juristi.tech", "branding_color": BRAND_COLOR_DEFAULT, "address": "", "email_public": "", "phone": "", "nui": ""}

def _fetch_logo_buffer(url: Optional[str], storage_key: Optional[str] = None) -> Optional[io.BytesIO]:
    """
    Retrieves the logo as a BytesIO buffer suitable for ReportLab.
    Prioritizes direct byte retrieval from Storage Service to avoid Docker DNS issues.
    """
    raw_data = None
    
    # 1. Try Direct Storage (Fastest & Most Reliable in Docker)
    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            if hasattr(stream, 'read'): 
                raw_data = stream.read()
            elif isinstance(stream, bytes):
                raw_data = stream
        except Exception as e: 
            logger.warning(f"Storage logo fetch failed for key {storage_key}: {e}")

    # 2. Fallback to URL (Only if storage key failed or missing)
    if not raw_data and url and url.startswith("http"):
        try:
            # PHOENIX FIX: Set short timeout to prevent hanging
            response = requests.get(url, timeout=3)
            if response.status_code == 200: 
                raw_data = response.content
        except Exception as e: 
            logger.warning(f"URL logo fetch failed: {e}")

    # 3. Process Image Bytes
    if raw_data:
        try:
            img = PILImage.open(io.BytesIO(raw_data))
            
            # Handle Transparency (RGBA/P) -> RGB with White Background
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                bg = PILImage.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P': img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[3]) 
                img = bg
            elif img.mode != 'RGB': 
                img = img.convert('RGB')
            
            out_buffer = io.BytesIO()
            img.save(out_buffer, format='JPEG', quality=95)
            out_buffer.seek(0)
            return out_buffer
        except Exception as e: 
            logger.error(f"Logo processing error: {e}")
            
    return None

# --- PDF GENERATOR ---

def _header_footer_invoice(c: canvas.Canvas, doc: BaseDocTemplate, branding: dict, lang: str):
    c.saveState()
    c.setStrokeColor(COLOR_BORDER)
    c.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    c.setFont('Helvetica', 8)
    c.setFillColor(COLOR_SECONDARY_TEXT)
    
    firm = branding.get('firm_name', 'Juristi.tech')
    date_str = datetime.now().strftime('%d/%m/%Y')
    footer = f"{_get_text('footer_gen', lang)} {firm} | {date_str}"
    
    c.drawString(15 * mm, 10 * mm, footer)
    c.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    c.restoreState()

def _header_footer_report(c: canvas.Canvas, doc: BaseDocTemplate, header_right_text: str, branding: dict, lang: str):
    c.saveState()
    brand_color = HexColor(branding.get("branding_color", "#4f46e5"))
    c.setFillColor(brand_color)
    c.rect(0, 280 * mm, 210 * mm, 17 * mm, fill=1, stroke=0) 
    
    firm_name = str(branding.get("firm_name", "Juristi.tech"))
    c.setFont('Helvetica-Bold', 16); c.setFillColor(white)
    c.drawString(15 * mm, 284 * mm, firm_name)
    
    c.setFont('Helvetica-Bold', 14); c.setFillColor(white)
    c.drawRightString(195 * mm, 284 * mm, header_right_text)
    
    c.setStrokeColor(HexColor("#E5E7EB")); c.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    c.setFont('Helvetica', 8); c.setFillColor(HexColor("#6B7280"))
    footer_msg = f"{_get_text('footer_gen', lang)} {firm_name} | {datetime.now().strftime('%d/%m/%Y')}"
    c.drawString(15 * mm, 10 * mm, footer_msg)
    c.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    c.restoreState()

def _build_doc_invoice(buffer: io.BytesIO, branding: dict, lang: str = "sq") -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=25*mm)
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

def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, user_id: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, user_id)
    buffer = io.BytesIO()
    doc = _build_doc_invoice(buffer, branding, lang)
    brand_color = HexColor(branding.get("branding_color", BRAND_COLOR_DEFAULT))
    
    Story: List[Flowable] = []

    # 1. Logo Section
    logo_buffer = _fetch_logo_buffer(branding.get("logo_url"), branding.get("logo_storage_key"))
    logo_obj = Spacer(0, 0)
    
    if logo_buffer:
        try:
            p_img = PILImage.open(logo_buffer)
            iw, ih = p_img.size
            aspect = ih / float(iw)
            w = 40 * mm
            h = w * aspect
            if h > 30 * mm: h = 30 * mm; w = h / aspect
            logo_buffer.seek(0)
            logo_obj = ReportLabImage(logo_buffer, width=w, height=h)
            logo_obj.hAlign = 'LEFT'
        except Exception: 
            pass

    # 2. Firm Details Section
    firm_details_content: List[Flowable] = []
    
    fn = branding.get("firm_name")
    if fn: firm_details_content.append(Paragraph(str(fn), STYLES['FirmName']))
    
    # PHOENIX FIX: Strict Check for missing firm details
    addr = branding.get("address")
    if addr: firm_details_content.append(Paragraph(f"<b>{_get_text('lbl_address', lang)}</b> {addr}", STYLES['FirmMeta']))
        
    nui = branding.get("nui")
    if nui: firm_details_content.append(Paragraph(f"<b>{_get_text('lbl_nui', lang)}</b> {nui}", STYLES['FirmMeta']))

    em = branding.get("email_public")
    if em: firm_details_content.append(Paragraph(f"<b>{_get_text('lbl_email', lang)}</b> {em}", STYLES['FirmMeta']))

    ph = branding.get("phone")
    if ph: firm_details_content.append(Paragraph(f"<b>{_get_text('lbl_tel', lang)}</b> {ph}", STYLES['FirmMeta']))
    
    wb = branding.get("website")
    if wb: firm_details_content.append(Paragraph(f"<b>{_get_text('lbl_web', lang)}</b> {wb}", STYLES['FirmMeta']))

    header_table = Table([[logo_obj, firm_details_content]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    Story.append(header_table)
    Story.append(Spacer(1, 15*mm))

    # 3. Invoice Meta (Title, Date, Number)
    meta_table_data = [
        [Paragraph(f"{_get_text('invoice_num', lang)} {invoice.invoice_number}", STYLES['MetaValue'])],
        [Spacer(1, 3*mm)],
        [Paragraph(_get_text('date_issue', lang), STYLES['MetaLabel'])], [Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
        [Spacer(1, 2*mm)],
        [Paragraph(_get_text('date_due', lang), STYLES['MetaLabel'])], [Paragraph(invoice.due_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
    ]
    meta_table = Table(meta_table_data, colWidths=[80*mm], style=[('ALIGN', (0,0), (-1,-1), 'RIGHT')])
    title_table = Table([[Paragraph(_get_text('invoice_title', lang), STYLES['H1']), meta_table]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    Story.append(title_table)
    Story.append(Spacer(1, 15*mm))

    # 4. Client Section (Intelligent Prefixing)
    client_content: List[Flowable] = []
    
    # Client Name (Always Bold)
    client_content.append(Paragraph(f"<b>{invoice.client_name}</b>", STYLES['AddressText']))
    
    # Intelligent Field Processing
    raw_addr = invoice.client_address or ""
    lines = [l.strip() for l in raw_addr.split('\n') if l.strip()]
    address_line_found = False
    
    # Regex Patterns for guessing content
    re_phone = re.compile(r'(\+?\d[\d\s\-\(\)]{6,})')
    re_nui = re.compile(r'(\d{8,})') # Assuming 8+ digits for Tax ID
    
    for line in lines:
        lower = line.lower()
        formatted = line
        
        # Check if line already has a prefix
        has_prefix = ':' in line or 'Tel' in line or 'NUI' in line or 'Email' in line
        
        if not has_prefix:
            if re_phone.search(line):
                formatted = f"<b>{_get_text('lbl_tel', lang)}</b> {line}"
            elif re_nui.search(line) and len(line) < 15: # Avoid confusing long addresses with NUI
                formatted = f"<b>{_get_text('lbl_nui', lang)}</b> {line}"
            elif '@' in line:
                formatted = f"<b>{_get_text('lbl_email', lang)}</b> {line}"
            elif not address_line_found:
                 formatted = f"<b>{_get_text('lbl_address', lang)}</b> {line}"
                 address_line_found = True
        else:
            # Clean up existing prefixes if they are rough
            if lower.startswith('tel'):
                parts = re.split(r'[:.]', line, 1)
                if len(parts) > 1: formatted = f"<b>{_get_text('lbl_tel', lang)}</b> {parts[1].strip()}"
            elif lower.startswith('nui') or lower.startswith('fiscal'):
                parts = re.split(r'[:.]', line, 1)
                if len(parts) > 1: formatted = f"<b>{_get_text('lbl_nui', lang)}</b> {parts[1].strip()}"

        client_content.append(Paragraph(formatted, STYLES['AddressText']))

    # Append explicitly stored fields if not already in text
    if invoice.client_email and '@' not in raw_addr:
        client_content.append(Paragraph(f"<b>{_get_text('lbl_email', lang)}</b> {invoice.client_email}", STYLES['AddressText']))
    
    address_wrapper = Table([[Paragraph(_get_text('to', lang), STYLES['AddressLabel']), client_content]], colWidths=[20*mm, 160*mm])
    address_wrapper.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(address_wrapper)
    Story.append(Spacer(1, 10*mm))
    
    # 5. Items Table
    headers = [_get_text('desc', lang), _get_text('qty', lang), _get_text('price', lang), _get_text('total', lang)]
    header_row = [Paragraph(h, STYLES['TableHeader']) for h in headers]
    data = [header_row]
    for item in invoice.items:
        row = [
            Paragraph(item.description, STYLES['TableCell']),
            Paragraph(str(item.quantity), STYLES['TableCellRight']),
            Paragraph(f"€{item.unit_price:,.2f}", STYLES['TableCellRight']),
            Paragraph(f"€{item.total:,.2f}", STYLES['TableCellRight']),
        ]
        data.append(row)
    t = Table(data, colWidths=[95*mm, 20*mm, 30*mm, 35*mm], style=[('BACKGROUND', (0,0), (-1,0), brand_color), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LINEBELOW', (0,-1), (-1,-1), 1, COLOR_BORDER), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")])])
    Story.append(t)
    
    # 6. Totals Section
    totals_data = [
        [Paragraph(_get_text('subtotal', lang), STYLES['TotalLabel']), Paragraph(f"€{invoice.subtotal:,.2f}", STYLES['TotalLabel'])],
        [Paragraph(_get_text('tax', lang), STYLES['TotalLabel']), Paragraph(f"€{invoice.tax_amount:,.2f}", STYLES['TotalLabel'])],
        [Paragraph(f"<b>{_get_text('total', lang)}</b>", STYLES['TotalValue']), Paragraph(f"<b>€{invoice.total_amount:,.2f}</b>", STYLES['TotalValue'])],
    ]
    t_totals = Table(totals_data, colWidths=[40*mm, 35*mm], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LINEABOVE', (0, 2), (1, 2), 1.5, COLOR_PRIMARY_TEXT), ('TOPPADDING', (0, 2), (1, 2), 6)])
    wrapper = Table([["", t_totals]], colWidths=[110*mm, 75*mm], style=[('ALIGN', (1,0), (1,0), 'RIGHT')])
    Story.append(wrapper)

    # 7. Notes
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
    Story: List[Flowable] = []
    
    Story.append(Spacer(1, 10*mm))
    Story.append(Paragraph(_get_text('report_title', lang), STYLES['h1']))
    
    meta_data = [
        [Paragraph(f"<b>{_get_text('case', lang)}:</b>", STYLES['Normal']), Paragraph(case_title, STYLES['Normal'])],
    ]
    t = Table(meta_data, colWidths=[40*mm, 120*mm])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")), ('BACKGROUND', (0,0), (0,-1), HexColor("#F5F5F5"))]))
    Story.append(t)
    Story.append(Spacer(1, 10 * mm))
    
    findings = findings_service.get_findings_for_case(db=db, case_id=case_id)
    
    if not findings:
        Story.append(Paragraph(_get_text('no_findings', lang), STYLES['Normal']))
    else:
        for i, finding in enumerate(findings, 1):
            title = f"{_get_text('finding', lang)} #{i}: {escape(finding.get('document_name', ''))}"
            Story.append(Paragraph(title, STYLES['h3']))
            text = escape(finding.get('finding_text', ''))
            Story.append(Paragraph(text.replace('\n', '<br/>'), STYLES['Normal']))
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