# FILE: backend/app/services/report_service/invoice_report.py
# PHOENIX PROTOCOL - INVOICE PDF GENERATOR

import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.platypus import Image as ReportLabImage
from reportlab.lib.colors import HexColor
from pymongo.database import Database
from typing import List
from xml.sax.saxutils import escape
from PIL import Image as PILImage

from app.models.finance import InvoiceInDB
from .styles import STYLES, COLOR_BORDER, COLOR_PRIMARY_TEXT, COLOR_SECONDARY_TEXT, BRAND_COLOR_DEFAULT
from .helpers import _get_text, _get_branding, _fetch_logo_buffer

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
    from reportlab.lib.pagesizes import A4
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
    t_totals = Table(totals_data, colWidths=[35*mm, 35*mm], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LINEABOVE', (0, 2), (1, 2), 1.5, COLOR_PRIMARY_TEXT), ('TOPPADDING', (0, 2), (1, 2), 6), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 0)])
    Story.append(Table([["", t_totals]], colWidths=[110*mm, 70*mm], style=[('ALIGN', (1,0), (1,0), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))

    if invoice.notes:
        Story.append(Spacer(1, 10*mm))
        Story.append(Paragraph(_get_text('notes', lang), STYLES['NotesLabel']))
        Story.append(Paragraph(escape(invoice.notes).replace('\n', '<br/>'), STYLES['AddressText']))

    doc.build(Story)
    buffer.seek(0)
    return buffer