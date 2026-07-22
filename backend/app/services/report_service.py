# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REPORT SERVICE V7.1 (FIXED UNICODE ESCAPE SYNTAX ERRORS)

import io
import os
import structlog
import requests
import markdown2
import re
from xhtml2pdf import pisa
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
from typing import List, Optional, Dict, Any
from bson import ObjectId
from xml.sax.saxutils import escape
from PIL import Image as PILImage

from app.models.finance import InvoiceInDB
from app.services import storage_service

logger = structlog.get_logger(__name__)

# --- STYLES & CONSTANTS ---
COLOR_PRIMARY_TEXT = HexColor("#0f172a")
COLOR_SECONDARY_TEXT = HexColor("#64748b")
COLOR_BORDER = HexColor("#e2e8f0")
BRAND_COLOR_DEFAULT = "#4f46e5"

STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='H1', parent=STYLES['h1'], fontSize=22, textColor=COLOR_PRIMARY_TEXT, alignment=TA_RIGHT, fontName='Helvetica-Bold'))
STYLES.add(ParagraphStyle(name='MetaLabel', parent=STYLES['Normal'], fontSize=8, textColor=COLOR_SECONDARY_TEXT, alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='MetaValue', parent=STYLES['Normal'], fontSize=10, textColor=COLOR_PRIMARY_TEXT, alignment=TA_RIGHT, spaceBefore=2))
STYLES.add(ParagraphStyle(name='AddressLabel', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=COLOR_PRIMARY_TEXT, spaceBottom=6))
STYLES.add(ParagraphStyle(name='AddressText', parent=STYLES['Normal'], fontSize=9, textColor=COLOR_SECONDARY_TEXT, leading=14))
STYLES.add(ParagraphStyle(name='TableHeader', parent=STYLES['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=white, alignment=TA_LEFT))
STYLES.add(ParagraphStyle(name='TableHeaderRight', parent=STYLES['TableHeader'], alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='TableCell', parent=STYLES['Normal'], fontSize=9, textColor=COLOR_PRIMARY_TEXT))
STYLES.add(ParagraphStyle(name='TableCellRight', parent=STYLES['TableCell'], alignment=TA_RIGHT))
STYLES.add(ParagraphStyle(name='TotalLabel', parent=STYLES['TableCellRight']))
STYLES.add(ParagraphStyle(name='TotalValue', parent=STYLES['TableCellRight'], fontName='Helvetica-Bold'))
STYLES.add(ParagraphStyle(name='NotesLabel', parent=STYLES['AddressLabel'], spaceBefore=10))
STYLES.add(ParagraphStyle(name='FirmName', parent=STYLES['h3'], alignment=TA_RIGHT, fontSize=14, spaceAfter=4, textColor=COLOR_PRIMARY_TEXT))
STYLES.add(ParagraphStyle(name='FirmMeta', parent=STYLES['Normal'], alignment=TA_RIGHT, fontSize=9, textColor=COLOR_SECONDARY_TEXT, leading=12))

TRANSLATIONS = {
    "sq": {
        "invoice_title": "FATURA", "invoice_num": "Nr.", "date_issue": "Data e Lëshimit", "date_due": "Afati i Pagesës",
        "status": "Statusi", "from": "Nga", "to": "Për", "desc": "Përshkrimi", "qty": "Sasia", "price": "Çmimi",
        "total": "Totali", "subtotal": "Nëntotali", "tax": "TVSH (18%)", "notes": "Shënime",
        "footer_gen": "Dokument i gjeneruar elektronikisht nga", "page": "Faqe", 
        "lbl_address": "Adresa:", "lbl_tel": "Tel:", "lbl_email": "Email:", "lbl_web": "Web:", "lbl_nui": "NUI:",
        "map_report_title": "Raporti i Hartës së Korrelacionit të Provave",
        "map_case_id": "Nr. i Rastit:",
        "map_section_claims": "Pretendimet Ligjore Kryesore",
        "map_section_evidence": "Provat e Lidhura",
        "map_exhibit": "Nr. Ekspozitës:",
        "map_proven": "Vërtetuar:",
        "map_admitted": "Pranim:",
        "map_auth": "Autentikuar:",
        "map_rel_supports": "Mbështet",
        "map_rel_contradicts": "Kundërthotë",
        "map_rel_related": "Lidhet me",
        "map_notes": "Shënime: ",
        "analysis_title": "Analiza e rastit",
        "report_case_label": "LËNDA:"
    }
}

# --- PHOENIX: EXECUTIVE PUBLICATION-GRADE REPORT CSS ---
REPORT_CSS = """
    @page {
        size: a4 portrait;
        margin: 18mm 15mm 18mm 15mm;
        @frame footer_frame {
            -pdf-frame-content: footer_content;
            left: 15mm; width: 180mm; bottom: 6mm; height: 10mm;
        }
    }
    body {
        font-family: 'Helvetica', sans-serif;
        font-size: 10pt;
        line-height: 1.55;
        color: #1e293b;
    }
    .header-card {
        background-color: #0f172a;
        color: #ffffff;
        padding: 22px 26px;
        border-radius: 8px;
        border-left: 6px solid #4f46e5;
        margin-bottom: 25px;
    }
    .header-badge {
        font-size: 8pt;
        font-weight: bold;
        letter-spacing: 2px;
        color: #818cf8;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .header-title {
        font-size: 20pt;
        font-weight: bold;
        color: #ffffff;
        margin: 0 0 10px 0;
        letter-spacing: -0.5px;
        text-transform: uppercase;
    }
    .header-meta {
        font-size: 9.5pt;
        color: #94a3b8;
        border-top: 1px solid #334155;
        padding-top: 10px;
        margin-top: 10px;
    }
    h1 {
        font-size: 15pt;
        font-weight: bold;
        color: #0f172a;
        border-bottom: 2px solid #4f46e5;
        margin-top: 24px;
        margin-bottom: 12px;
        padding-bottom: 6px;
        text-transform: uppercase;
    }
    h2 {
        font-size: 12pt;
        font-weight: bold;
        color: #1e293b;
        background-color: #f8fafc;
        border-left: 4px solid #4f46e5;
        padding: 8px 14px;
        margin-top: 20px;
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    h3 {
        font-size: 10.5pt;
        font-weight: bold;
        color: #334155;
        margin-top: 14px;
        margin-bottom: 8px;
    }
    p {
        margin: 0 0 10px 0;
        text-align: justify;
    }
    ul, ol {
        margin-top: 4px;
        margin-bottom: 12px;
        padding-left: 18px;
    }
    li {
        margin-bottom: 6px;
        line-height: 1.5;
        color: #334155;
    }
    strong {
        font-weight: bold;
        color: #0f172a;
    }
    blockquote {
        background-color: #f8fafc;
        border-left: 4px solid #6366f1;
        margin: 12px 0;
        padding: 10px 16px;
        font-style: italic;
        color: #334155;
        border-radius: 4px;
    }
    code, pre {
        font-family: 'Courier', monospace;
        font-size: 8.5pt;
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        padding: 10px 14px;
        border-radius: 6px;
        color: #0f172a;
        display: block;
        white-space: pre-wrap;
        word-wrap: break-word;
        margin: 12px 0;
        line-height: 1.4;
    }
"""

def clean_text_for_pdf(text: str) -> str:
    """Strips all unrenderable emojis, black box glyphs ('■'), stray 'None' values, and translates English markers."""
    if not text:
        return ""
    
    clean = text
    
    # 1. Strip all unrenderable symbols and black square glyphs
    bad_chars = [
        "■", "□", "▪", "▫", "◆", "◇", "●", "○", "★", "☆", "✔", "✓", "✅", "❌", "✖",
        "⚖", "👨", "💼", "⚖️", "👨‍💼", "👨‍⚖️", "🛡", "⚔", "🛡️", "⚔️", "💀", "⏱", "⏱️", "⏱", "⏱️",
        "⚡", "⚡", "⏱", "⏱️", "📁", "📂", "🔍"
    ]
    for char in bad_chars:
        clean = clean.replace(char, "")

    # Clean out any remaining 4-byte UTF-8 emojis using correct 16-bit \u and 32-bit \U hex digit padding
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons (32-bit: 8 digits)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs (32-bit: 8 digits)
        "\U0001F680-\U0001F6FF"  # transport & map symbols (32-bit: 8 digits)
        "\U0001F1E0-\U0001F1FF"  # flags (32-bit: 8 digits)
        "\u2702-\u27B0"          # dingbats (16-bit: 4 digits)
        "\u24C2-\U0001F251"      # regional indicators (16-bit to 32-bit)
        "\u2600-\u26FF"          # miscellaneous symbols (16-bit: 4 digits)
        "\u2700-\u27BF"          # dingbats (16-bit: 4 digits)
        "]+", flags=re.UNICODE
    )
    clean = emoji_pattern.sub("", clean)

    # 2. Translate English markers to pristine Albanian
    replacements = {
        "Conflict: CRITICAL": "Mospërputhje: KRITIKE",
        "Conflict: HIGH": "Mospërputhje: E LARTË",
        "Conflict: MEDIUM": "Mospërputhje: E MESME",
        "Conflict: LOW": "Mospërputhje: E ULËT",
        "Konflikt: CRITICAL": "Mospërputhje: KRITIKE",
        "Konflikt: HIGH": "Mospërputhje: E LARTË",
        "Konflikt: MEDIUM": "Mospërputhje: E MESME",
        "Konflikt: LOW": "Mospërputhje: E ULËT",
        "Severity: CRITICAL": "Rrezikshmëria: KRITIKE",
        "Severity: HIGH": "Rrezikshmëria: E LARTË",
        "Severity: MEDIUM": "Rrezikshmëria: E MESME",
        "Severity: LOW": "Rrezikshmëria: E ULËT",
        "Rrezikshmëria: CRITICAL": "Rrezikshmëria: KRITIKE",
        "Rrezikshmëria: HIGH": "Rrezikshmëria: E LARTË",
        "Rrezikshmëria: MEDIUM": "Rrezikshmëria: E MESME",
        "Rrezikshmëria: LOW": "Rrezikshmëria: E ULËT",
        "supports": "mbështet",
        "contradicts": "kundërshton",
        "related": "lidhet me",
        "opponent_strategy": "strategjia_e_kundershtarit",
        "weakness_attacks": "pikat_e_sulmit"
    }
    for eng, alb in replacements.items():
        clean = re.sub(r'\b' + re.escape(eng) + r'\b', alb, clean, flags=re.IGNORECASE)

    # 3. Clean up stray "None" values
    clean = re.sub(r'^\s*(None|\*\*None\*\*)\s*$', '', clean, flags=re.MULTILINE | re.IGNORECASE)

    # 4. Clean up consecutive empty lines
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    
    return clean.strip()

def _get_text(key: str, lang: str = "sq") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["sq"]).get(key, key)

def _get_branding(db: Database, user_id: str) -> dict:
    try:
        try: oid = ObjectId(user_id)
        except: oid = user_id
        
        profile = db.business_profiles.find_one({"user_id": oid})
        if not profile: profile = db.business_profiles.find_one({"user_id": str(user_id)})

        if profile:
            return {
                "firm_name": profile.get("firm_name", "Juristi.tech"), "address": profile.get("address", ""),"email_public": profile.get("email_public", ""), "phone": profile.get("phone", ""),"branding_color": profile.get("branding_color", BRAND_COLOR_DEFAULT), "logo_url": profile.get("logo_url"), "logo_storage_key": profile.get("logo_storage_key"), "website": profile.get("website", ""), "nui": profile.get("tax_id", "") 
            }
    except Exception as e: logger.error(f"Branding fetch failed: {e}")
    return {"firm_name": "Juristi.tech", "branding_color": BRAND_COLOR_DEFAULT}

def _process_image_bytes(data: bytes) -> Optional[io.BytesIO]:
    try:
        img = PILImage.open(io.BytesIO(data))
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'P': img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[3]) 
            img = bg
        elif img.mode != 'RGB': img = img.convert('RGB')
        
        out_buffer = io.BytesIO()
        img.save(out_buffer, format='JPEG', quality=100)
        out_buffer.seek(0)
        return out_buffer
    except Exception as e: logger.error(f"Image processing failed: {e}")
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

def _build_doc(buffer: io.BytesIO, branding: dict, lang: str) -> BaseDocTemplate:
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=25*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='main', frames=[frame], onPage=lambda c, d: _header_footer_invoice(c, d, branding, lang))
    doc.addPageTemplates([template])
    return doc

def generate_invoice_pdf(invoice: InvoiceInDB, db: Database, user_id: str, lang: str = "sq") -> io.BytesIO:
    branding = _get_branding(db, user_id)
    buffer = io.BytesIO()
    doc = _build_doc(buffer, branding, lang)
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
        [Paragraph(f"{_get_text('invoice_num', lang)} {invoice.invoice_number}", STYLES['MetaValue'])], [Spacer(1, 3*mm)],
        [Paragraph(_get_text('date_issue', lang), STYLES['MetaLabel'])], [Paragraph(invoice.issue_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
        [Spacer(1, 2*mm)],
        [Paragraph(_get_text('date_due', lang), STYLES['MetaLabel'])], [Paragraph(invoice.due_date.strftime("%d/%m/%Y"), STYLES['MetaValue'])],
    ]
    Story.append(Table([[Paragraph(_get_text('invoice_title', lang), STYLES['H1']), Table(meta_data, colWidths=[80*mm], style=[('ALIGN', (0,0), (-1,-1), 'RIGHT')])]], colWidths=[100*mm, 80*mm], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
    Story.append(Spacer(1, 15*mm))

    client_content: List[Flowable] = [Paragraph(f"<b>{invoice.client_name}</b>", STYLES['AddressText'])]
    c_address = getattr(invoice, 'client_address', ''); c_city = getattr(invoice, 'client_city', '')
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

    data = [[Paragraph(_get_text('desc', lang), STYLES['TableHeader']), Paragraph(_get_text('qty', lang), STYLES['TableHeaderRight']), Paragraph(_get_text('price', lang), STYLES['TableHeaderRight']), Paragraph(_get_text('total', lang), STYLES['TableHeaderRight'])]]
    for item in invoice.items:
        data.append([Paragraph(item.description, STYLES['TableCell']), Paragraph(str(item.quantity), STYLES['TableCellRight']), Paragraph(f"{item.unit_price:,.2f} EUR", STYLES['TableCellRight']), Paragraph(f"{item.total:,.2f} EUR", STYLES['TableCellRight'])])
    t_items = Table(data, colWidths=[90*mm, 20*mm, 35*mm, 35*mm])
    t_items.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), brand_color), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LINEBELOW', (0,-1), (-1,-1), 1, COLOR_BORDER), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")]), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6)]))
    Story.append(t_items)

    totals_data = [[Paragraph(_get_text('subtotal', lang), STYLES['TotalLabel']), Paragraph(f"{invoice.subtotal:,.2f} EUR", STYLES['TotalLabel'])], [Paragraph(_get_text('tax', lang), STYLES['TotalLabel']), Paragraph(f"{invoice.tax_amount:,.2f} EUR", STYLES['TotalLabel'])], [Paragraph(f"<b>{_get_text('total', lang)}</b>", STYLES['TotalValue']), Paragraph(f"<b>{invoice.total_amount:,.2f} EUR</b>", STYLES['TotalValue'])]]
    t_totals = Table(totals_data, colWidths=[35*mm, 35*mm], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LINEABOVE', (0, 2), (1, 2), 1.5, COLOR_PRIMARY_TEXT), ('TOPPADDING', (0, 2), (1, 2), 6), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6)])
    Story.append(Table([["", t_totals]], colWidths=[110*mm, 70*mm], style=[('ALIGN', (1,0), (1,0), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))

    if invoice.notes:
        Story.append(Spacer(1, 10*mm))
        Story.append(Paragraph(_get_text('notes', lang), STYLES['NotesLabel']))
        Story.append(Paragraph(escape(invoice.notes).replace('\n', '<br/>'), STYLES['AddressText']))

    doc.build(Story)
    buffer.seek(0)
    return buffer

def create_pdf_from_text(text: str, document_title: str, header_meta_content_html: Optional[str] = None) -> io.BytesIO:
    """
    Generates an executive, publication-grade PDF from Markdown text using an HTML+CSS pipeline.
    Applies strict emoji/black square stripping, executive navy header card, and shaded callout boxes.
    """
    buffer = io.BytesIO()
    
    # 1. Clean emojis, black squares, and 'None' strings
    clean_text = clean_text_for_pdf(text)

    # 2. Convert markdown to HTML
    html_body = markdown2.markdown(clean_text, extras=["tables", "fenced-code-blocks", "cuddled-lists"])

    generation_date = datetime.now().strftime('%d/%m/%Y')
    display_title = escape(document_title) if document_title and "Pa Titull" not in document_title else "ANALIZA E RASTIT"
    meta_html = header_meta_content_html or ""

    # 3. Build Executive Header Card
    header_html = f"""
    <div class="header-card">
        <div class="header-badge">JURISTI AI — SISTEMI I STRATEGJISË LIGJORE & DHOMA E LUFTËS</div>
        <div class="header-title">{display_title}</div>
        <div class="header-meta">
            {meta_html}
            <span style="float: right;"><b>Data e Gjenerimit:</b> {generation_date}</span>
        </div>
    </div>
    """
    
    footer_html = f"""
    <div id='footer_content' style='font-size: 8pt; color: #64748b;'>
        <table width="100%" style="border-top: 1px solid #e2e8f0; padding-top: 4px;">
            <tr>
                <td align="left">Juristi AI System — Dokument Konfidencial Zyrtar</td>
                <td align="right">Data e Gjenerimit: {generation_date}</td>
            </tr>
        </table>
    </div>
    """

    full_html = f"""
    <html>
    <head>
        <meta charset="utf-8"/>
        <style>{REPORT_CSS}</style>
    </head>
    <body>
        {header_html}
        {footer_html}
        {html_body}
    </body>
    </html>
    """

    pisa_status = pisa.CreatePDF(src=full_html, dest=buffer)

    error_code = getattr(pisa_status, 'err', 1)
    if error_code:
        logger.error("PDF generation failed", error_code=error_code)
        raise IOError("Could not generate PDF report.")

    buffer.seek(0)
    return buffer

def generate_evidence_map_report(case_id: str, map_data: Dict[str, Any], case_title: str = "N/A", lang: str = "sq") -> io.BytesIO:
    """
    Converts Evidence Map nodes/edges data into a structured Markdown report for PDF generation.
    """
    nodes = map_data.get('nodes', [])
    edges = map_data.get('edges', [])
    
    claims = [n for n in nodes if n.type == 'claimNode']
    evidence_nodes = {n['id']: n for n in nodes if n.type == 'evidenceNode'}
    
    report_parts: List[str] = []
    
    report_parts.append(f"# {_get_text('map_report_title', lang)}")
    report_parts.append(f"**{_get_text('map_case_id', lang)}** {case_title} ({case_id})")
    report_parts.append(f"**{_get_text('footer_gen', lang)}** Juristi.tech | **{_get_text('date_issue', lang)}** {datetime.now().strftime('%d/%m/%Y')}")
    report_parts.append("\n---\n")

    report_parts.append(f"## {_get_text('map_section_claims', lang)}\n")
    
    if not claims:
        report_parts.append("*Asnjë pretendim nuk u gjet në hartë.*\n")
    
    for claim in claims:
        c_data = claim.get('data', {})
        claim_id = claim.get('id')
        
        proven_status = ' Vërtetuar' if c_data.get('isProven') else ' Pa Vërtetuar'
        
        report_parts.append(f"### {c_data.get('label', 'Pretendim pa Titull')} ({proven_status})")
        
        if c_data.get('content'):
            content_cleaned = c_data.get('content').replace('\n', ' ')
            report_parts.append(f"""> {content_cleaned}\n""")
        
        claim_edges = [e for e in edges if e.target == claim_id]
        
        relationships: Dict[str, List[Dict[str, Any]]] = {
            'supports': [], 'contradicts': [], 'related': []
        }

        for edge in claim_edges:
            source_id = edge.source
            if source_id in evidence_nodes:
                rel_type = edge.type or 'related'
                rel_label = edge.data.get('label', '') if edge.data else ''
                
                evidence = evidence_nodes[source_id]
                relationships[rel_type].append({
                    'evidence': evidence,
                    'label': rel_label,
                    'strength': edge.data.get('strength', 3) if edge.data else 3
                })

        report_parts.append(f"#### {_get_text('map_section_evidence', lang)}\n")
        
        if all(not rels for rels in relationships.values()):
            report_parts.append("*Nuk ka prova të lidhura med këtë pretendim.*\n")
            
        for rel_type, rel_list in relationships.items():
            if not rel_list: continue

            header_key = f"map_rel_{rel_type}"
            header_text = _get_text(header_key, lang)
            
            report_parts.append(f"**{header_text} ({len(rel_list)})**\n")
            
            for item in rel_list:
                evd = item['evidence'].get('data', {})
                
                metadata = []
                if evd.get('exhibitNumber'): metadata.append(f"**{_get_text('map_exhibit', lang)}** {evd['exhibitNumber']}")
                if evd.get('isAuthenticated') is not None: 
                    status = 'Po' if evd['isAuthenticated'] else 'Jo'
                    metadata.append(f"**{_get_text('map_auth', lang)}** {status}")
                if evd.get('isAdmitted'): metadata.append(f"**{_get_text('map_admitted', lang)}** {evd['isAdmitted']}")
                
                content_line = f"* **{item['evidence'].get('data', {}).get('label', 'Provë pa Titull')}**"
                if metadata:
                    content_line += f" ({' | '.join(metadata)})"
                
                report_parts.append(content_line)
                
                if item['label']:
                    report_parts.append(f"  > *{_get_text('map_notes', lang)} {item['label']}*")
        
        report_parts.append("\n---\n")

    final_markdown = "\n".join(report_parts)
    return create_pdf_from_text(final_markdown, _get_text('map_report_title', lang))

def generate_legal_strategy_report(case_title: str, raw_report_markdown: str, lang: str = "sq") -> io.BytesIO:
    """
    Generates an executive Legal Strategy Report PDF with specific title and meta-information layout.
    """
    main_title = _get_text('analysis_title', lang)
    display_case_title = case_title if case_title and case_title.strip() != "" else "Pa Titull"
    header_meta_content_html = f"<span><b>{_get_text('report_case_label', lang)}</b> {escape(display_case_title)}</span>"
    
    cleaned_report_markdown = re.sub(
        r"^\s*RASTI:\s*.*?DATA\s+E\s+GJENERIMIT:\s*\d{2}/\d{2}/\d{4}\s*$", 
        "", 
        raw_report_markdown, 
        flags=re.IGNORECASE | re.MULTILINE
    ).strip()

    return create_pdf_from_text(
        text=cleaned_report_markdown, 
        document_title=main_title, 
        header_meta_content_html=header_meta_content_html
    )