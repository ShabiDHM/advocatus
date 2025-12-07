# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REVISION 3 (ROBUSTNESS UPDATE)
# 1. FIX: "Physical File Discovery" for logos. Searches disk directly to bypass Docker DNS issues.
# 2. FIX: "Smart Labeling" for Address block. Forces 'Adresa:' and 'Email:' prefixes on raw text.
# 3. CLEANUP: Refactored image processing into a safe helper function.

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
from reportlab.lib.enums import TA_RIGHT
from pymongo.database import Database
from typing import List, Optional
from bson import ObjectId
from xml.sax.saxutils import escape
from PIL import Image as PILImage

from app.models.finance import InvoiceInDB
from app.services import storage_service, findings_service

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

# --- DATA FETCHING ---
def _get_branding(db: Database, user_id: str) -> dict:
    try:
        try: oid = ObjectId(user_id)
        except: oid = user_id
        
        # Try finding by ObjectId first, then string
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

# --- LOGO LOGIC (ROBUST) ---

def _process_image_bytes(data: bytes) -> Optional[io.BytesIO]:
    """Helper to convert raw bytes into a ReportLab-friendly JPEG buffer."""
    try:
        img = PILImage.open(io.BytesIO(data))
        # Handle Transparency (RGBA/P) -> RGB with White Background
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
    """
    Strategies to find the logo:
    1. Disk Search (Most Robust in Docker): Maps URL to local file system.
    2. Storage Service: Uses the abstract stream.
    3. HTTP Request: Last resort fallback.
    """
    if not url and not storage_key: return None

    # STRATEGY 1: DISK SEARCH (Bypasses Network)
    if url and "static" in url:
        # Clean the path to find it on the container disk
        # e.g., "http://localhost:8000/static/uploads/logo.png" -> "/app/static/uploads/logo.png"
        clean_path = url.split("static/", 1)[-1] # Get everything after static/
        
        candidates = [
            f"/app/static/{clean_path}",      # Standard Docker
            f"app/static/{clean_path}",       # Relative
            f"static/{clean_path}",           # Relative root
            f"/usr/src/app/static/{clean_path}" # Common Node/Python path
        ]

        for cand in candidates:
            if os.path.exists(cand):
                try:
                    with open(cand, "rb") as f:
                        logger.info(f"PDF: Loaded logo from disk: {cand}")
                        return _process_image_bytes(f.read())
                except Exception as e:
                    logger.warning(f"PDF: Found file {cand} but failed to read: {e}")

    # STRATEGY 2: STORAGE SERVICE
    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            if hasattr(stream, 'read'): return _process_image_bytes(stream.read())
            if isinstance(stream, bytes): return _process_image_bytes(stream)
        except Exception: pass

    # STRATEGY 3: HTTP FALLBACK (Low Timeout)
    if url and url.startswith("http"):
        try:
            response = requests.get(url, timeout=2) # 2s timeout to avoid hanging
            if response.status_code == 200:
                return _process_image_bytes(response.content)
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

    # 1. HEADER (Logo + Firm Details)
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
    
    # Iterate known fields to ensure labels
    for key, label_key in [("address", "lbl_address"), ("nui", "lbl_nui"), ("email_public", "lbl_email"), ("phone", "lbl_tel"), ("website", "lbl_web")]:
        val = branding.get(key)
        if val: firm_content.append(Paragraph(f"<b>{_get_text(label_key, lang)}</b> {val}", STYLES['FirmMeta']))

    Story.append(Table([[logo_obj, firm_content]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(Spacer(1, 15*mm))

    # 2. INVOICE META
    meta_data = [
        [Paragraph(f"{_get_text('invoice_num', lang)} {invoice.invoice_number}", STYLES['MetaValue'])],
        [Spacer(1, 3*mm)],
        [Paragraph(_get_text('date_issue', lang), STYLES['MetaLabel'])], [Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
        [Spacer(1, 2*mm)],
        [Paragraph(_get_text('date_due', lang), STYLES['MetaLabel'])], [Paragraph(invoice.due_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
    ]
    Story.append(Table([[Paragraph(_get_text('invoice_title', lang), STYLES['H1']), Table(meta_data, colWidths=[80*mm], style=[('ALIGN', (0,0), (-1,-1), 'RIGHT')])]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(Spacer(1, 15*mm))

    # 3. CLIENT DETAILS (SMART LABELING)
    client_content: List[Flowable] = []
    client_content.append(Paragraph(f"<b>{invoice.client_name}</b>", STYLES['AddressText']))
    
    # Split raw address block
    raw_addr = invoice.client_address or ""
    lines = [l.strip() for l in raw_addr.split('\n') if l.strip()]
    
    labeled_address = False
    
    for line in lines:
        # Check if line already starts with a label (case insensitive)
        if re.match(r'^(Tel|NUI|Email|Web|Adresa|Mob|Nr\.|Fiscal)[:.]', line, re.IGNORECASE):
            # Already formatted, just print
            formatted = line
            # Force bolding the label part if not bolded
            if ':' in line:
                parts = line.split(':', 1)
                formatted = f"<b>{parts[0].strip()}:</b> {parts[1].strip()}"
        else:
            # Heuristic guessing
            if '@' in line:
                formatted = f"<b>{_get_text('lbl_email', lang)}</b> {line}"
            elif line.lower().startswith('www') or line.lower().startswith('http'):
                formatted = f"<b>{_get_text('lbl_web', lang)}</b> {line}"
            elif not labeled_address:
                # First unknown line is assumed to be Address
                formatted = f"<b>{_get_text('lbl_address', lang)}</b> {line}"
                labeled_address = True
            else:
                # Subsequent unknown lines (e.g. City) just print as is
                formatted = line
        
        client_content.append(Paragraph(formatted, STYLES['AddressText']))

    # If email exists in DB but wasn't in the text block
    if invoice.client_email and '@' not in raw_addr:
        client_content.append(Paragraph(f"<b>{_get_text('lbl_email', lang)}</b> {invoice.client_email}", STYLES['AddressText']))

    t_addr = Table([[Paragraph(_get_text('to', lang), STYLES['AddressLabel']), client_content]], colWidths=[20*mm, 160*mm])
    t_addr.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(t_addr)
    Story.append(Spacer(1, 10*mm))

    # 4. ITEMS
    headers = [_get_text('desc', lang), _get_text('qty', lang), _get_text('price', lang), _get_text('total', lang)]
    data = [[Paragraph(h, STYLES['TableHeader']) for h in headers]]
    for item in invoice.items:
        data.append([
            Paragraph(item.description, STYLES['TableCell']),
            Paragraph(str(item.quantity), STYLES['TableCellRight']),
            Paragraph(f"€{item.unit_price:,.2f}", STYLES['TableCellRight']),
            Paragraph(f"€{item.total:,.2f}", STYLES['TableCellRight']),
        ])
    t_items = Table(data, colWidths=[95*mm, 20*mm, 30*mm, 35*mm])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")])
    ]))
    Story.append(t_items)

    # 5. TOTALS
    totals_data = [
        [Paragraph(_get_text('subtotal', lang), STYLES['TotalLabel']), Paragraph(f"€{invoice.subtotal:,.2f}", STYLES['TotalLabel'])],
        [Paragraph(_get_text('tax', lang), STYLES['TotalLabel']), Paragraph(f"€{invoice.tax_amount:,.2f}", STYLES['TotalLabel'])],
        [Paragraph(f"<b>{_get_text('total', lang)}</b>", STYLES['TotalValue']), Paragraph(f"<b>€{invoice.total_amount:,.2f}</b>", STYLES['TotalValue'])],
    ]
    t_totals = Table(totals_data, colWidths=[40*mm, 35*mm], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LINEABOVE', (0, 2), (1, 2), 1.5, COLOR_PRIMARY_TEXT), ('TOPPADDING', (0, 2), (1, 2), 6)])
    Story.append(Table([["", t_totals]], colWidths=[110*mm, 75*mm], style=[('ALIGN', (1,0), (1,0), 'RIGHT')]))

    # 6. NOTES
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
    doc = _build_doc(buffer, 'report', branding, lang, _get_text('report_title', lang))
    Story = [Spacer(1, 10*mm), Paragraph(_get_text('report_title', lang), STYLES['h1'])]
    
    t = Table([[Paragraph(f"<b>{_get_text('case', lang)}:</b>", STYLES['Normal']), Paragraph(case_title, STYLES['Normal'])]], colWidths=[40*mm, 120*mm])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")), ('BACKGROUND', (0,0), (0,-1), HexColor("#F5F5F5"))]))
    Story.append(t); Story.append(Spacer(1, 10 * mm))
    
    findings = findings_service.get_findings_for_case(db=db, case_id=case_id)
    if not findings: Story.append(Paragraph(_get_text('no_findings', lang), STYLES['Normal']))
    else:
        for i, f in enumerate(findings, 1):
            Story.append(Paragraph(f"{_get_text('finding', lang)} #{i}: {escape(f.get('document_name', ''))}", STYLES['h3']))
            Story.append(Paragraph(escape(f.get('finding_text', '')).replace('\n', '<br/>'), STYLES['Normal']))
            Story.append(Spacer(1, 5 * mm))
    doc.build(Story); buffer.seek(0); return buffer

def create_pdf_from_text(text: str, document_title: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _build_doc(buffer, 'report', {"firm_name": "Juristi.tech", "branding_color": "#333333"}, "sq", document_title)
    doc.build([Spacer(1, 15*mm), Paragraph(escape(text).replace('\n', '<br/>'), STYLES['Normal'])])
    buffer.seek(0); return buffer