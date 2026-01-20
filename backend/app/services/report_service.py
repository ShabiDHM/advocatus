# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REPORT SERVICE V4.6 (PERFECT GRID)
# 1. FIX: Added 'TableHeaderRight' to align numeric headers with data.
# 2. GEOMETRY: Adjusted column widths (Desc:90, Qty:20, Price:35, Total:35) to creating a seamless vertical grid.
# 3. FIX: Removed padding from footer wrapper to prevent layout drift.

import io
import os
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
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from pymongo.database import Database
from typing import List, Optional
from bson import ObjectId
from xml.sax.saxutils import escape
from PIL import Image as PILImage

from app.models.finance import InvoiceInDB
from app.services import storage_service

logger = structlog.get_logger(__name__)

# --- STYLES & CONSTANTS ---
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
STYLES.add(ParagraphStyle(name='TableHeader', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=white, alignment=TA_LEFT))
# PHOENIX FIX: Right-aligned header for numeric columns
STYLES.add(ParagraphStyle(name='TableHeaderRight', parent=STYLES['TableHeader'], alignment=TA_RIGHT))
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
        "invoice_title": "FATURA", "invoice_num": "Nr.", "date_issue": "Data e Lëshimit", "date_due": "Afati i Pagesës",
        "status": "Statusi", "from": "Nga", "to": "Për", "desc": "Përshkrimi", "qty": "Sasia", "price": "Çmimi",
        "total": "Totali", "subtotal": "Nëntotali", "tax": "TVSH (18%)", "notes": "Shënime",
        "footer_gen": "Dokument i gjeneruar elektronikisht nga", "page": "Faqe", 
        "lbl_address": "Adresa:", "lbl_tel": "Tel:", "lbl_email": "Email:", "lbl_web": "Web:", "lbl_nui": "NUI:"
    }
}

def _get_text(key: str, lang: str = "sq") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["sq"]).get(key, key)

# --- DATA FETCHING ---
def _get_branding(db: Database, user_id: str) -> dict:
    try:
        try: oid = ObjectId(user_id)
        except: oid = user_id
        
        profile = db.business_profiles.find_one({"user_id": oid})
        if not profile:
            profile = db.business_profiles.find_one({"user_id": str(user_id)})

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
    return {"firm_name": "Juristi.tech", "branding_color": BRAND_COLOR_DEFAULT}

# --- LOGO LOGIC ---
def _process_image_bytes(data: bytes) -> Optional[io.BytesIO]:
    try:
        img = PILImage.open(io.BytesIO(data))
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'P': img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[3]) 
            img = bg
        elif img.mode != 'RGB': 
            img = img.convert('RGB')
        
        out_buffer = io.BytesIO()
        img.save(out_buffer, format='JPEG', quality=100)
        out_buffer.seek(0)
        return out_buffer
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return None

def _fetch_logo_buffer(url: Optional[str], storage_key: Optional[str] = None) -> Optional[io.BytesIO]:
    if not url and not storage_key: return None

    if url and "static" in url:
        clean_path = url.split("static/", 1)[-1] 
        candidates = [f"/app/static/{clean_path}", f"app/static/{clean_path}", f"static/{clean_path}", f"/usr/src/app/static/{clean_path}"]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    with open(cand, "rb") as f: return _process_image_bytes(f.read())
                except Exception: pass

    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            if hasattr(stream, 'read'): return _process_image_bytes(stream.read())
            if isinstance(stream, bytes): return _process_image_bytes(stream)
        except Exception: pass

    if url and url.startswith("http"):
        try:
            response = requests.get(url, timeout=2) 
            if response.status_code == 200: return _process_image_bytes(response.content)
        except Exception: pass
            
    return None

# --- PDF GENERATOR CORE ---

def _header_footer_invoice(c: canvas.Canvas, doc: BaseDocTemplate, branding: dict, lang: str):
    c.saveState()
    c.setStrokeColor(COLOR_BORDER)
    c.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    c.setFont('Helvetica', 8)
    c.setFillColor(COLOR_SECONDARY_TEXT)
    firm = branding.get('firm_name', 'Juristi.tech')
    footer = f"{_get_text('footer_gen', lang)} {firm} | {datetime.now().strftime('%d/%m/%Y')}"
    c.drawString(15 * mm, 10 * mm, footer)
    c.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    c.restoreState()

def _header_footer_report(c: canvas.Canvas, doc: BaseDocTemplate, header_text: str, branding: dict, lang: str):
    c.saveState()
    brand_color = HexColor(branding.get("branding_color", BRAND_COLOR_DEFAULT))
    c.setFillColor(brand_color)
    c.rect(0, 280 * mm, 210 * mm, 17 * mm, fill=1, stroke=0) 
    firm_name = str(branding.get("firm_name", "Juristi.tech"))
    c.setFont('Helvetica-Bold', 16); c.setFillColor(white)
    c.drawString(15 * mm, 284 * mm, firm_name)
    c.setFont('Helvetica-Bold', 14); c.setFillColor(white)
    c.drawRightString(195 * mm, 284 * mm, header_text)
    c.setStrokeColor(HexColor("#E5E7EB")); c.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    c.setFont('Helvetica', 8); c.setFillColor(HexColor("#6B7280"))
    footer_msg = f"{_get_text('footer_gen', lang)} {firm_name} | {datetime.now().strftime('%d/%m/%Y')}"
    c.drawString(15 * mm, 10 * mm, footer_msg)
    c.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    c.restoreState()

def _build_doc(buffer: io.BytesIO, type: str, branding: dict, lang: str, header_text: str = "") -> BaseDocTemplate:
    if type == 'invoice':
        doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=25*mm)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
        template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer_invoice(c, d, branding, lang))
    else:
        doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=25*mm, bottomMargin=25*mm)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 20*mm, id='normal')
        template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer_report(c, d, header_text, branding, lang))
    
    doc.addPageTemplates([template])
    return doc

def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, user_id: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, user_id)
    buffer = io.BytesIO()
    doc = _build_doc(buffer, 'invoice', branding, lang)
    brand_color = HexColor(branding.get("branding_color", BRAND_COLOR_DEFAULT))
    Story: List[Flowable] = []

    logo_buffer = _fetch_logo_buffer(branding.get("logo_url"), branding.get("logo_storage_key"))
    logo_obj = Spacer(0, 0)
    if logo_buffer:
        try:
            p_img = PILImage.open(logo_buffer)
            iw, ih = p_img.size
            aspect = ih / float(iw)
            w = 40 * mm; h = w * aspect
            if h > 30 * mm: h = 30 * mm; w = h / aspect
            logo_buffer.seek(0)
            logo_obj = ReportLabImage(logo_buffer, width=w, height=h); logo_obj.hAlign = 'LEFT'
        except: pass

    firm_content: List[Flowable] = []
    if branding.get("firm_name"): firm_content.append(Paragraph(str(branding.get("firm_name")), STYLES['FirmName']))
    for key, label_key in [("address", "lbl_address"), ("nui", "lbl_nui"), ("email_public", "lbl_email"), ("phone", "lbl_tel"), ("website", "lbl_web")]:
        val = branding.get(key)
        if val: firm_content.append(Paragraph(f"<b>{_get_text(label_key, lang)}</b> {val}", STYLES['FirmMeta']))

    Story.append(Table([[logo_obj, firm_content]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(Spacer(1, 15*mm))

    meta_data = [
        [Paragraph(f"{_get_text('invoice_num', lang)} {invoice.invoice_number}", STYLES['MetaValue'])],
        [Spacer(1, 3*mm)],
        [Paragraph(_get_text('date_issue', lang), STYLES['MetaLabel'])], [Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
        [Spacer(1, 2*mm)],
        [Paragraph(_get_text('date_due', lang), STYLES['MetaLabel'])], [Paragraph(invoice.due_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
    ]
    Story.append(Table([[Paragraph(_get_text('invoice_title', lang), STYLES['H1']), Table(meta_data, colWidths=[80*mm], style=[('ALIGN', (0,0), (-1,-1), 'RIGHT')])]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(Spacer(1, 15*mm))

    client_content: List[Flowable] = []
    client_content.append(Paragraph(f"<b>{invoice.client_name}</b>", STYLES['AddressText']))
    c_address = getattr(invoice, 'client_address', '')
    c_city = getattr(invoice, 'client_city', '')
    full_address = f"{c_address}, {c_city}" if c_address and c_city else (c_address or c_city)
    if full_address: client_content.append(Paragraph(f"<b>{_get_text('lbl_address', lang)}</b> {full_address}", STYLES['AddressText']))
    if getattr(invoice, 'client_tax_id', ''): client_content.append(Paragraph(f"<b>{_get_text('lbl_nui', lang)}</b> {invoice.client_tax_id}", STYLES['AddressText']))
    if getattr(invoice, 'client_email', ''): client_content.append(Paragraph(f"<b>{_get_text('lbl_email', lang)}</b> {invoice.client_email}", STYLES['AddressText']))
    if getattr(invoice, 'client_phone', ''): client_content.append(Paragraph(f"<b>{_get_text('lbl_tel', lang)}</b> {invoice.client_phone}", STYLES['AddressText']))
    if getattr(invoice, 'client_website', ''): client_content.append(Paragraph(f"<b>{_get_text('lbl_web', lang)}</b> {invoice.client_website}", STYLES['AddressText']))

    t_addr = Table([[Paragraph(_get_text('to', lang), STYLES['AddressLabel']), client_content]], colWidths=[20*mm, 160*mm])
    t_addr.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(t_addr)
    Story.append(Spacer(1, 10*mm))

    # --- ITEMS TABLE GEOMETRY (Total 180mm) ---
    # Desc: 90mm | Qty: 20mm | Price: 35mm | Total: 35mm
    data = [[
        Paragraph(_get_text('desc', lang), STYLES['TableHeader']),
        Paragraph(_get_text('qty', lang), STYLES['TableHeaderRight']),
        Paragraph(_get_text('price', lang), STYLES['TableHeaderRight']),
        Paragraph(_get_text('total', lang), STYLES['TableHeaderRight'])
    ]]
    for item in invoice.items:
        data.append([
            Paragraph(item.description, STYLES['TableCell']),
            Paragraph(str(item.quantity), STYLES['TableCellRight']),
            Paragraph(f"{item.unit_price:,.2f} EUR", STYLES['TableCellRight']),
            Paragraph(f"{item.total:,.2f} EUR", STYLES['TableCellRight']),
        ])
    t_items = Table(data, colWidths=[90*mm, 20*mm, 35*mm, 35*mm])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")]),
        ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6)
    ]))
    Story.append(t_items)

    # --- TOTALS TABLE GEOMETRY ---
    # Spacer: 110mm (90+20) | Footer Table: 70mm (35+35)
    # Inner Footer: Label: 35mm | Value: 35mm
    totals_data = [
        [Paragraph(_get_text('subtotal', lang), STYLES['TotalLabel']), Paragraph(f"{invoice.subtotal:,.2f} EUR", STYLES['TotalLabel'])],
        [Paragraph(_get_text('tax', lang), STYLES['TotalLabel']), Paragraph(f"{invoice.tax_amount:,.2f} EUR", STYLES['TotalLabel'])],
        [Paragraph(f"<b>{_get_text('total', lang)}</b>", STYLES['TotalValue']), Paragraph(f"<b>{invoice.total_amount:,.2f} EUR</b>", STYLES['TotalValue'])],
    ]
    
    t_totals = Table(totals_data, colWidths=[35*mm, 35*mm], style=[
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0, 2), (1, 2), 1.5, COLOR_PRIMARY_TEXT),
        ('TOPPADDING', (0, 2), (1, 2), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6)
    ])
    
    # WRAPPER: No padding to ensure perfect math (110+70 = 180)
    Story.append(Table([["", t_totals]], colWidths=[110*mm, 70*mm], style=[
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)
    ]))

    if invoice.notes:
        Story.append(Spacer(1, 10*mm))
        Story.append(Paragraph(_get_text('notes', lang), STYLES['NotesLabel']))
        Story.append(Paragraph(escape(invoice.notes).replace('\n', '<br/>'), STYLES['AddressText']))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def create_pdf_from_text(text: str, document_title: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _build_doc(buffer, 'report', {"firm_name": "Juristi.tech", "branding_color": "#333333"}, "sq", document_title)
    doc.build([Spacer(1, 15*mm), Paragraph(escape(text).replace('\n', '<br/>'), STYLES['Normal'])])
    buffer.seek(0)
    return buffer