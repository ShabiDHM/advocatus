# FILE: backend/app/services/report_service.py
# PHOENIX PROTOCOL - REPORT SERVICE V6.5 (LEGAL STRATEGY REPORT LAYOUT FIX)
# 1. ADDED: New function `generate_legal_strategy_report` for specific report type.
# 2. FIXED: "RAPORTI I STRATEGJISË LIGJORE" replaced with "Analiza e rastit" for specific report.
# 3. FIXED: "RASTI: Pa Titull DATA E GJENERIMIT: [date]" moved to structured header, date removed from body.
# 4. FIXED: General layout and styling polished for improved readability.
# 5. RETAINED: All invoice and evidence map generation logic without degradation.

import io
import os
import structlog
import requests
import markdown2
import re # Import for regex operations
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
COLOR_PRIMARY_TEXT = HexColor("#111827")
COLOR_SECONDARY_TEXT = HexColor("#6B7280")
COLOR_BORDER = HexColor("#E5E7EB")
BRAND_COLOR_DEFAULT = "#4f46e5" # A distinct, brand-like color for meta info

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

# --- TRANSLATIONS (Updated with new keys) ---
TRANSLATIONS = {
    "sq": {
        "invoice_title": "FATURA", "invoice_num": "Nr.", "date_issue": "Data e Lëshimit", "date_due": "Afati i Pagesës",
        "status": "Statusi", "from": "Nga", "to": "Për", "desc": "Përshkrimi", "qty": "Sasia", "price": "Çmimi",
        "total": "Totali", "subtotal": "Nëntotali", "tax": "TVSH (18%)", "notes": "Shënime",
        "footer_gen": "Dokument i gjeneruar elektronikisht nga", "page": "Faqe", 
        "lbl_address": "Adresa:", "lbl_tel": "Tel:", "lbl_email": "Email:", "lbl_web": "Web:", "lbl_nui": "NUI:",
        # PHOENIX ADDITION: Evidence Map Report Keys
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
        # PHOENIX ADDITION: Legal Strategy Report Keys
        "analysis_title": "Analiza e rastit", # New title for legal strategy report
        "report_case_label": "Rasti:" # Label for the case title in reports
    }
}

# --- PHOENIX: PROFESSIONAL REPORT STYLES (Updated with .report-meta) ---
REPORT_CSS = f"""
    @page {{
        size: a4 portrait;
        @frame header_frame {{
            -pdf-frame-content: header_content;
            left: 20mm; width: 170mm; top: 20mm; height: 35mm; /* Increased height to accommodate new meta info */
        }}
        @frame content_frame {{
            left: 20mm; width: 170mm; top: 60mm; height: 207mm; /* Adjusted top and height */
        }}
        @frame footer_frame {{
            -pdf-frame-content: footer_content;
            left: 20mm; width: 170mm; bottom: 10mm; height: 10mm;
        }}
    }}
    body {{
        font-family: 'Helvetica', sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }}
    h1, h2, h3, h4 {{
        font-family: 'Helvetica-Bold', sans-serif;
        color: #1a2c4b;
        margin-bottom: 8px;
        padding-bottom: 4px;
        line-height: 1.3;
    }}
    h1 {{ 
        font-size: 18pt; 
        border-bottom: 2px solid #1a2c4b; 
        margin-bottom: 5px; /* Adjust spacing */
        padding-bottom: 4px; 
    }}
    h2 {{ 
        font-size: 14pt; 
        border-bottom: 1px solid #e0e0e0; 
        margin-top: 20px;
        color: #1a2c4b; 
    }}
    h2.report-meta {{ /* Specific style for meta info like "Rasti: Pa Titull" */
        font-size: 12pt; /* Slightly smaller than H1 */
        color: {BRAND_COLOR_DEFAULT}; /* Use a distinct brand color */
        margin-top: 10px; /* Space from H1 */
        margin-bottom: 15px; /* Space before content */
        font-family: 'Helvetica', sans-serif; /* Not bold */
        border-bottom: none; /* No line below meta */
    }}
    h3 {{ font-size: 12pt; margin-top: 15px; }}
    h4 {{ font-size: 11pt; color: #4f46e5; margin-top: 10px; }}
    p {{ margin: 0 0 10px 0; }}
    ul {{
        list-style-type: disc;
        padding-left: 20px;
    }}
    li {{
        margin-bottom: 5px;
    }}
    strong {{
        font-family: 'Helvetica-Bold', sans-serif;
        color: #000;
    }}
"""

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
    Generates a professional PDF from Markdown text using an HTML+CSS pipeline.
    Accepts optional header_meta_content_html to inject styled meta-data below the main title.
    """
    buffer = io.BytesIO()
    
    html_body = markdown2.markdown(text, extras=["tables", "fenced-code-blocks", "cuddled-lists"])

    # Build header content HTML dynamically
    header_content_parts = []
    # PHOENIX FIX: Hide h1 only if document_title explicitly contains "Pa Titull" as primary identifier.
    # Otherwise, render the title.
    if document_title and "Pa Titull" not in document_title: 
        header_content_parts.append(f"<h1>{escape(document_title)}</h1>")
    
    # PHOENIX ADDITION: Inject meta-content HTML if provided
    if header_meta_content_html:
        header_content_parts.append(header_meta_content_html)
    
    header_html = f"<div id='header_content'>{''.join(header_content_parts)}</div>"
    
    # PHOENIX FIX: Remove system branding from footer (already implemented)
    generation_date = datetime.now().strftime('%d/%m/%Y')
    footer_html = f"""
    <div id='footer_content' style='font-size: 9pt; color: #888;'>
        <table width="100%" style="border-top: 1px solid #ccc; padding-top: 5px;">
            <tr>
                <td align="left"></td>
                <td align="right">Data e Gjenerimit: {generation_date}</td>
            </tr>
        </table>
    </div>
    """

    full_html = f"""
    <html>
    <head>
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

# PHOENIX PHASE 4: EVIDENCE MAP REPORT FUNCTION (Unchanged)
def generate_evidence_map_report(case_id: str, map_data: Dict[str, Any], case_title: str = "N/A", lang: str = "sq") -> io.BytesIO:
    """
    Converts Evidence Map nodes/edges data into a structured Markdown report for PDF generation.
    """
    nodes = map_data.get('nodes', [])
    edges = map_data.get('edges', [])
    
    claims = [n for n in nodes if n.type == 'claimNode']
    evidence_nodes = {n['id']: n for n in nodes if n.type == 'evidenceNode'}
    
    report_parts: List[str] = []
    
    # --- Preamble ---
    # The evidence map report includes its meta-information as part of the markdown body,
    # which is then rendered by markdown2. This is distinct from the legal strategy report.
    report_parts.append(f"# {_get_text('map_report_title', lang)}")
    report_parts.append(f"**{_get_text('map_case_id', lang)}** {case_title} ({case_id})")
    report_parts.append(f"**{_get_text('footer_gen', lang)}** Juristi.tech | **{_get_text('date_issue', lang)}** {datetime.now().strftime('%d/%m/%Y')}")
    report_parts.append("\n---\n")

    # --- Claim Sections ---
    report_parts.append(f"## {_get_text('map_section_claims', lang)}\n")
    
    if not claims:
        report_parts.append("*Asnjë pretendim nuk u gjet në hartë.*\n")
    
    for claim in claims:
        c_data = claim.get('data', {})
        claim_id = claim.get('id')
        
        # Claim Header (Title + Proven Status)
        proven_status = '✅ ' + _get_text('map_proven', lang) if c_data.get('isProven') else '❌ ' + _get_text('map_proven', lang)
        
        report_parts.append(f"### {c_data.get('label', 'Pretendim pa Titull')} ({proven_status})")
        
        # PHOENIX FINAL FIX: Using triple quotes to safely include the newline escape sequence
        if c_data.get('content'):
            content_cleaned = c_data.get('content').replace('\n', ' ')
            report_parts.append(f"""> {content_cleaned}\n""")
        
        # Filter edges for this claim (where the claim is the target)
        claim_edges = [e for e in edges if e.target == claim_id]
        
        # Group evidence by relationship type
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

        # --- Evidence Listing ---
        report_parts.append(f"#### {_get_text('map_section_evidence', lang)}\n")
        
        if all(not rels for rels in relationships.values()):
            report_parts.append("*Nuk ka prova të lidhura me këtë pretendim.*\n")
            
        for rel_type, rel_list in relationships.items():
            if not rel_list: continue

            # Translate relationship header
            header_key = f"map_rel_{rel_type}"
            header_text = _get_text(header_key, lang)
            
            report_parts.append(f"**{header_text} ({len(rel_list)})**\n")
            
            for item in rel_list:
                evd = item['evidence'].get('data', {})
                
                # Metadata Badges
                metadata = []
                if evd.get('exhibitNumber'): metadata.append(f"**{_get_text('map_exhibit', lang)}** {evd['exhibitNumber']}")
                if evd.get('isAuthenticated') is not None: 
                    status = 'Po' if evd['isAuthenticated'] else 'Jo'
                    metadata.append(f"**{_get_text('map_auth', lang)}** {status}")
                if evd.get('isAdmitted'): metadata.append(f"**{_get_text('map_admitted', lang)}** {evd['isAdmitted']}")
                
                # Evidence Content Line
                content_line = f"* **{item['evidence'].get('data', {}).get('label', 'Provë pa Titull')}**"
                if metadata:
                    content_line += f" ({' | '.join(metadata)})"
                
                report_parts.append(content_line)
                
                # Edge Note
                if item['label']:
                    report_parts.append(f"  > *{_get_text('map_notes', lang)} {item['label']}*")
        
        report_parts.append("\n---\n") # Separator between claims

    # Final PDF Generation
    final_markdown = "\n".join(report_parts)
    return create_pdf_from_text(final_markdown, _get_text('map_report_title', lang))

# PHOENIX ADDITION: New function to generate Legal Strategy Reports
def generate_legal_strategy_report(case_title: str, raw_report_markdown: str, lang: str = "sq") -> io.BytesIO:
    """
    Generates a Legal Strategy Report PDF with specific title and meta-information layout.
    This function preprocesses the raw markdown to ensure correct header formatting.
    """
    # 1. Determine the main title for the report (always "Analiza e rastit" for this type)
    main_title = _get_text('analysis_title', lang)

    # 2. Construct the meta-information HTML (e.g., "Rasti: Pa Titull")
    display_case_title = case_title if case_title and case_title.strip() != "" else "Pa Titull"
    header_meta_content_html = f"<h2 class='report-meta'>{_get_text('report_case_label', lang)} {escape(display_case_title)}</h2>"
    
    # 3. Preprocess the raw markdown to remove the unwanted "RASTI: ... DATA E GJENERIMIT: ..." line
    # This regex looks for a line starting with "RASTI:", followed by any content, then "DATA E GJENERIMIT:", and a date.
    # It's flexible enough for variations in case title and spacing.
    # The re.MULTILINE flag ensures '^' matches start of lines, not just start of string.
    cleaned_report_markdown = re.sub(
        r"^\s*RASTI:\s*.*?DATA\s+E\s+GJENERIMIT:\s*\d{2}/\d{2}/\d{4}\s*$", 
        "", 
        raw_report_markdown, 
        flags=re.IGNORECASE | re.MULTILINE
    ).strip() # .strip() removes any resulting empty lines at start/end

    # 4. Call the generic create_pdf_from_text with the specific title, meta-HTML, and cleaned content
    return create_pdf_from_text(
        text=cleaned_report_markdown, 
        document_title=main_title, 
        header_meta_content_html=header_meta_content_html
    )