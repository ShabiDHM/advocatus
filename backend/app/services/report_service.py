# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REPORT ENGINE v2.4 (VISUAL POLISH)
# 1. DESIGN: Updated invoice layout to "Corporate Clean" style.
# 2. DATE: Enforced DD/MM/YYYY formatting.
# 3. TYPING: Fixed Optional[str] for logo fetching.

import io
import structlog
import requests
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black, lightgrey
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
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
        "from": "Nga (Lëshuesi)",
        "to": "Për (Marrësi)",
        "desc": "Përshkrimi i Shërbimit / Produktit",
        "qty": "Sasia",
        "price": "Çmimi Njësi",
        "total": "Totali",
        "subtotal": "Nëntotali",
        "tax": "TVSH (18%)",
        "notes": "Udhëzime Pagese / Shënime",
        "footer_gen": "Dokument i gjeneruar elektronikisht nga",
        "page": "Faqe",
        "report_title": "Raport i Gjetjeve",
        "finding": "Gjetja",
        "no_findings": "Nuk u gjetën asnjë gjetje për këtë rast.",
        "case": "Rasti",
        "generated_for": "Gjeneruar për"
    }
}

def _get_text(key: str, lang: str = "sq") -> str:
    lang_map = TRANSLATIONS.get(lang, TRANSLATIONS["sq"])
    return lang_map.get(key, key)

# --- BRANDING & ASSETS ---
def _get_branding(db: Database, search_term: str) -> dict:
    try:
        user = db.users.find_one({"$or": [{"email": search_term}, {"username": search_term}]})
        if user:
            profile = db.business_profiles.find_one({"user_id": user["_id"]})
            if profile:
                return {
                    "header_text": profile.get("firm_name", "Juristi.tech"),
                    "address": profile.get("address", ""),
                    "email": profile.get("email_public", user["email"]),
                    "phone": profile.get("phone", ""),
                    "color": profile.get("branding_color", "#111827"), # Default to dark blue/black
                    "logo_url": profile.get("logo_url"),
                    "logo_storage_key": profile.get("logo_storage_key"),
                    "website": profile.get("website", "")
                }
    except Exception as e:
        logger.warning(f"Branding fetch failed: {e}")
    return {"header_text": "Juristi.tech", "color": "#111827", "address": "", "email": "", "phone": ""}

def _fetch_logo_image(url: Optional[str], storage_key: Optional[str] = None) -> Optional[ImageReader]:
    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            return ImageReader(io.BytesIO(stream.read()))
        except Exception: pass
    if url and not url.startswith("/"):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return ImageReader(io.BytesIO(response.content))
        except Exception: pass
    return None

# --- LAYOUT ENGINE ---
def _header_footer(canvas: canvas.Canvas, doc: BaseDocTemplate, header_right_text: str, branding: dict, lang: str):
    canvas.saveState()
    
    # 1. Top Bar
    brand_color = HexColor(branding["color"])
    canvas.setFillColor(brand_color)
    canvas.rect(0, 280 * mm, 210 * mm, 17 * mm, fill=1, stroke=0) # Top banner
    
    # 2. Logo (White on Dark) or Fallback Text
    logo_drawn = False
    logo_key = branding.get("logo_storage_key")
    logo_url = branding.get("logo_url")
    
    if logo_key or logo_url:
        logo_img = _fetch_logo_image(logo_url, logo_key)
        if logo_img:
            iw, ih = logo_img.getSize()
            aspect = ih / float(iw)
            width = 35 * mm
            height = width * aspect
            if height > 15 * mm: height = 15 * mm; width = height / aspect
            # Draw logo over banner
            canvas.drawImage(logo_img, 15 * mm, 281 * mm, width=width, height=height, mask='auto')
            logo_drawn = True

    if not logo_drawn:
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(white)
        canvas.drawString(15 * mm, 285 * mm, branding["header_text"])

    # 3. Invoice Number (Top Right)
    canvas.setFont('Helvetica-Bold', 14)
    canvas.setFillColor(white)
    canvas.drawRightString(195 * mm, 285 * mm, header_right_text)
    
    # Footer
    canvas.setStrokeColor(HexColor("#E5E7EB"))
    canvas.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
    
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor("#6B7280"))
    footer_msg = f"{_get_text('footer_gen', lang)} Juristi.tech | {datetime.now().strftime('%d/%m/%Y')}"
    canvas.drawString(15 * mm, 10 * mm, footer_msg)
    
    canvas.drawRightString(195 * mm, 10 * mm, f"{_get_text('page', lang)} {doc.page}")
    
    canvas.restoreState()

def _build_doc(buffer: io.BytesIO, header_text: str, branding: dict, lang: str = "sq") -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=25*mm, bottomMargin=25*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 20*mm, id='normal')
    template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer(c, d, header_text, branding, lang))
    doc.addPageTemplates([template])
    return doc

# --- MAIN GENERATOR ---
def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, username: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, username)
    buffer = io.BytesIO()
    
    # Ensure Title reflects the invoice number format (e.g. "FATURA #Faktura-2025-0001")
    title_text = f"{invoice.invoice_number}"
    doc = _build_doc(buffer, title_text, branding, lang)
    
    styles = getSampleStyleSheet()
    brand_color = HexColor(branding["color"])
    
    Story: List[Flowable] = []
    Story.append(Spacer(1, 15*mm)) # Space for the header banner
    
    # Styles
    lbl_style = ParagraphStyle('L', parent=styles['Normal'], fontSize=8, textColor=HexColor("#6B7280"), spaceAfter=2)
    val_style = ParagraphStyle('V', parent=styles['Normal'], fontSize=10, textColor=black, leading=12)
    val_bold = ParagraphStyle('VB', parent=val_style, fontName='Helvetica-Bold')
    
    # --- METADATA BAR ---
    # Issue Date | Due Date | Status
    meta_data = [
        [
            Paragraph(f"<b>{_get_text('date_issue', lang)}</b>", lbl_style),
            Paragraph(f"<b>{_get_text('date_due', lang)}</b>", lbl_style),
            Paragraph(f"<b>{_get_text('status', lang)}</b>", lbl_style),
        ],
        [
            Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), val_style),
            Paragraph(invoice.due_date.strftime("%d/%m/%Y"), val_style),
            Paragraph(invoice.status.upper(), val_bold),
        ]
    ]
    t_meta = Table(meta_data, colWidths=[60*mm, 60*mm, 60*mm])
    t_meta.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,1), (-1,1), 1, HexColor("#E5E7EB")),
        ('BOTTOMPADDING', (0,1), (-1,1), 15),
    ]))
    Story.append(t_meta)
    Story.append(Spacer(1, 10*mm))

    # --- ADDRESS BLOCK (2 Columns) ---
    # Left: From (Firm) | Right: To (Client)
    
    # Format multiline address from DB
    client_addr_lines = (invoice.client_address or "").split('\n')
    client_block = [Paragraph(f"<b>{invoice.client_name}</b>", val_bold)]
    for line in client_addr_lines:
        if line.strip(): client_block.append(Paragraph(line.strip(), val_style))
    client_block.append(Paragraph(invoice.client_email or "", val_style))

    firm_block = [
        Paragraph(f"<b>{branding['header_text']}</b>", val_bold),
        Paragraph(branding.get('address','') or "", val_style),
        Paragraph(branding.get('phone','') or "", val_style),
        Paragraph(branding.get('email','') or "", val_style),
        Paragraph(branding.get('website','') or "", val_style),
    ]

    addr_table = Table([
        [Paragraph(_get_text('from', lang).upper(), lbl_style), Paragraph(_get_text('to', lang).upper(), lbl_style)],
        [firm_block, client_block]
    ], colWidths=[90*mm, 90*mm])
    
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    Story.append(addr_table)
    Story.append(Spacer(1, 15*mm))
    
    # --- ITEMS TABLE ---
    headers = [
        _get_text('desc', lang),
        _get_text('qty', lang),
        _get_text('price', lang),
        _get_text('total', lang)
    ]
    
    # Header Row
    t_data = [[Paragraph(h, ParagraphStyle('TH', fontSize=9, textColor=white, fontName='Helvetica-Bold')) for h in headers]]
    
    # Rows
    for item in invoice.items:
        t_data.append([
            Paragraph(item.description, val_style),
            Paragraph(str(item.quantity), ParagraphStyle('TR', parent=val_style, alignment=TA_RIGHT)),
            Paragraph(f"€{item.unit_price:,.2f}", ParagraphStyle('TR', parent=val_style, alignment=TA_RIGHT)),
            Paragraph(f"€{item.total:,.2f}", ParagraphStyle('TR', parent=val_style, alignment=TA_RIGHT))
        ])
        
    t_items = Table(t_data, colWidths=[90*mm, 25*mm, 30*mm, 35*mm])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_color), # Header BG
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'), # Numbers right aligned
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor("#E5E7EB")), # Subtle grid
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, HexColor("#F9FAFB")]), # Zebra striping
    ]))
    Story.append(t_items)
    
    # --- TOTALS SECTION ---
    # Right aligned
    def total_row(label, val, is_final=False):
        s_lbl = ParagraphStyle('TL', parent=val_style, alignment=TA_RIGHT, fontSize=10)
        s_val = ParagraphStyle('TV', parent=val_style, alignment=TA_RIGHT, fontSize=10, fontName='Helvetica-Bold' if is_final else 'Helvetica')
        return [Paragraph(label, s_lbl), Paragraph(val, s_val)]

    t_totals_data = [
        total_row(_get_text('subtotal', lang), f"€{invoice.subtotal:,.2f}"),
        total_row(_get_text('tax', lang), f"€{invoice.tax_amount:,.2f}"),
        total_row(_get_text('total', lang), f"€{invoice.total_amount:,.2f}", True)
    ]
    
    t_totals = Table(t_totals_data, colWidths=[40*mm, 35*mm])
    t_totals.setStyle(TableStyle([
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, brand_color), # Bold line above grand total
        ('TOPPADDING', (0,-1), (-1,-1), 8),
    ]))
    
    # Place totals on the right
    layout_t = Table([["", t_totals]], colWidths=[105*mm, 75*mm])
    layout_t.setStyle(TableStyle([('ALIGN', (-1,0), (-1,-1), 'RIGHT')]))
    Story.append(layout_t)
    
    # --- NOTES ---
    if invoice.notes:
        Story.append(Spacer(1, 15*mm))
        Story.append(Paragraph(f"<b>{_get_text('notes', lang)}</b>", lbl_style))
        Story.append(Spacer(1, 2*mm))
        Story.append(Paragraph(escape(invoice.notes).replace('\n', '<br/>'), val_style))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def generate_findings_report_pdf(db: Database, case_id: str, case_title: str, username: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, username)
    buffer = io.BytesIO()
    doc = _build_doc(buffer, _get_text('report_title', lang), branding, lang)
    styles = getSampleStyleSheet()
    Story: List[Flowable] = []
    
    Story.append(Spacer(1, 10*mm))
    Story.append(Paragraph(_get_text('report_title', lang), styles['h1']))
    
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
    doc = _build_doc(buffer, document_title, {"header_text": "Juristi.tech", "color": "#333333"}, "sq")
    Story: List[Flowable] = [
        Spacer(1, 15*mm),
        Paragraph(escape(text).replace('\n', '<br/>'), getSampleStyleSheet()['Normal'])
    ]
    doc.build(Story)
    buffer.seek(0)
    return buffer