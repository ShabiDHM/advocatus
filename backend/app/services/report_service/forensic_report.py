# FILE: backend/app/services/report_service/forensic_report.py
# PHOENIX PROTOCOL - EXECUTIVE FORENSIC PDF GENERATOR (A4 NUMBERED CANVAS • MARKDOWN TABLES • COMPLIANT)

import io
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .helpers import clean_text_for_pdf

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Numëron automatikisht faqet (Faqja X nga Y) dhe vendos footer-in zyrtar në çdo faqe."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Vija ndarëse e footer-it
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)

        # Teksti majtas në footer
        left_text = "Juristi AI / Advocatus • Raport i Auditimit dhe Konsulencës Strategjike"
        self.drawString(15 * mm, 7 * mm, left_text)

        # Numri i faqes djathtas
        page_str = f"Faqja {self._pageNumber} nga {page_count}"
        self.drawRightString(A4[0] - 15 * mm, 7 * mm, page_str)

        self.restoreState()


def _parse_markdown_table(table_lines: List[str], styles: Dict[str, ParagraphStyle], col_widths: List[float]) -> Optional[Table]:
    """Konverton rreshtat e tabelës markdown në Table objekt të ReportLab me stilizim modern."""
    table_data = []
    
    cleaned_lines = [l for l in table_lines if not re.match(r'^\s*\|?[\s\-:|]+\|?\s*$', l)]

    for idx, line in enumerate(cleaned_lines):
        raw_cells = [c.strip() for c in line.strip().strip('|').split('|')]
        row_cells = []
        is_header = (idx == 0)

        cell_style = styles['TableHeader'] if is_header else styles['TableCell']

        for c in raw_cells:
            formatted_text = c.replace('**', '<b>').replace('__', '<b>')
            if formatted_text.count('<b>') % 2 != 0:
                formatted_text += '</b>'
            formatted_text = re.sub(r'<b>(.*?)<b>', r'<b>\1</b>', formatted_text)
            row_cells.append(Paragraph(formatted_text or "-", cell_style))

        if row_cells:
            table_data.append(row_cells)

    if not table_data:
        return None

    max_cols = max(len(r) for r in table_data)
    for r in table_data:
        while len(r) < max_cols:
            r.append(Paragraph("-", styles['TableCell']))

    total_width = sum(col_widths[:max_cols])
    actual_col_widths = [w * (180 * mm / total_width) for w in col_widths[:max_cols]]

    t = Table(table_data, colWidths=actual_col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    return t


def create_pdf_from_text(
    text: str,
    document_title: str = "RAPORT I AUDITIMIT DHE STRATEGJISË LIGJORE",
    header_meta_content_html: str = ""
) -> io.BytesIO:
    """Gjeneron Raport Ekzekutiv PDF profesional në formatin A4."""
    cleaned_input = clean_text_for_pdf(text)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm
    )

    base_styles = getSampleStyleSheet()

    styles = {
        'BrandSuper': ParagraphStyle('BrandSuper', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#0284c7'), spaceAfter=2, textTransform='uppercase'),
        'DocMainTitle': ParagraphStyle('DocMainTitle', fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=colors.HexColor('#0f172a'), spaceAfter=6, textTransform='uppercase'),
        'MetaBox': ParagraphStyle('MetaBox', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#334155')),
        'Heading1': ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor('#0f172a'), spaceBefore=12, spaceAfter=6, keepWithNext=True),
        'Heading2': ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=colors.HexColor('#0284c7'), spaceBefore=10, spaceAfter=4, keepWithNext=True),
        'Heading3': ParagraphStyle('H3', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#1e293b'), spaceBefore=6, spaceAfter=2, keepWithNext=True),
        'Body': ParagraphStyle('BodyText', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#1e293b'), spaceAfter=5, alignment=4),
        'Bullet': ParagraphStyle('BulletText', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#1e293b'), spaceAfter=3, leftIndent=12),
        'Blockquote': ParagraphStyle('QuoteText', fontName='Helvetica-Oblique', fontSize=8, leading=11, textColor=colors.HexColor('#0f172a'), spaceBefore=4, spaceAfter=6, leftIndent=10),
        'CodeBlock': ParagraphStyle('CodeText', fontName='Courier', fontSize=7.5, leading=10, textColor=colors.HexColor('#0f172a')),
        'TableHeader': ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.white),
        'TableCell': ParagraphStyle('TD', fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#0f172a')),
        'Disclaimer': ParagraphStyle('Disc', fontName='Helvetica-Oblique', fontSize=7, leading=9, textColor=colors.HexColor('#64748b'), spaceBefore=10, alignment=4)
    }

    story = []

    # 1. KOKA E DOKUMENTIT
    story.append(Paragraph("JURISTI AI • PLATFORMA E FORENZIKËS DHE STRATEGJISË LIGJORE", styles['BrandSuper']))
    clean_doc_title = document_title.replace('Raporti Forenzik:', '').strip()
    story.append(Paragraph(clean_doc_title or "RAPORT I AUDITIMIT DHE STRATEGJISË LIGJORE", styles['DocMainTitle']))

    # 2. PASAPORTA E LËNDËS
    meta_date_str = datetime.now().strftime("%d.%m.%Y, %H:%M")
    meta_html = header_meta_content_html or f"<b>DATA E GJENERIMIT:</b> {meta_date_str}"
    if "DATA" not in meta_html:
        meta_html += f" &nbsp;|&nbsp; <b>DATA:</b> {meta_date_str}"

    meta_table = Table([[Paragraph(meta_html, styles['MetaBox'])]], colWidths=[180 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BORDER', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    # 3. INTERPRETIMI I TEKSTIT MARKDOWN
    lines = cleaned_input.split('\n')
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # A. TABELAT MARKDOWN
        if line.startswith('|') and line.endswith('|'):
            table_lines = []
            while i < total_lines and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_lines.append(lines[i].strip())
                i += 1

            t_obj = _parse_markdown_table(table_lines, styles, [40, 50, 50, 40])
            if t_obj:
                story.append(Spacer(1, 2 * mm))
                story.append(t_obj)
                story.append(Spacer(1, 3 * mm))
            continue

        # B. BLLOQET E KODIT
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < total_lines and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1

            code_text = "<br/>".join([c.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for c in code_lines])
            code_table = Table([[Paragraph(code_text, styles['CodeBlock'])]], colWidths=[180 * mm])
            code_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
                ('BORDER', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(code_table)
            story.append(Spacer(1, 3 * mm))
            continue

        # C. TITUJT (#, ##, ###)
        if line.startswith('# '):
            h_text = line[2:].strip().replace('**', '')
            story.append(Paragraph(h_text, styles['Heading1']))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#0f172a'), spaceAfter=4))
            i += 1
            continue

        if line.startswith('## '):
            h_text = line[3:].strip().replace('**', '')
            story.append(Paragraph(h_text, styles['Heading2']))
            i += 1
            continue

        if line.startswith('### '):
            h_text = line[4:].strip().replace('**', '')
            story.append(Paragraph(h_text, styles['Heading3']))
            i += 1
            continue

        # D. VIJAT NDARËSE
        if line in ['---', '***', '===', '═══════════════════════════════════════════════']:
            story.append(Spacer(1, 1 * mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=4))
            i += 1
            continue

        # E. BLOCKQUOTE (> ...)
        if line.startswith('> '):
            q_text = line[2:].strip()
            q_table = Table([[Paragraph(q_text, styles['Blockquote'])]], colWidths=[180 * mm])
            q_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('LINELEFT', (0, 0), (0, -1), 2.5, colors.HexColor('#0284c7')),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(q_table)
            story.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # F. LISTAT ME PIKA DHE NUMRA
        if line.startswith(('-', '*', '•')):
            b_text = line[1:].strip()
            b_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', b_text)
            story.append(Paragraph(f"• &nbsp; {b_text}", styles['Bullet']))
            i += 1
            continue

        if re.match(r'^\d+\.\s+', line):
            num_match = re.match(r'^(\d+\.)\s+(.*)', line)
            if num_match:
                prefix = num_match.group(1)
                b_text = num_match.group(2)
                b_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', b_text)
                story.append(Paragraph(f"<b>{prefix}</b> &nbsp; {b_text}", styles['Bullet']))
                i += 1
                continue

        # G. KLAUZOLA LIGJORE (DISCLAIMER)
        if "KLAUZOLË" in line or "DISCLAIMER" in line or "Juristi AI" in line:
            clean_disc = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            story.append(Spacer(1, 3 * mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceAfter=3))
            story.append(Paragraph(clean_disc, styles['Disclaimer']))
            i += 1
            continue

        # H. PARAGRAFI I ZAKONSHËM
        p_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        p_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', p_text)
        story.append(Paragraph(p_text, styles['Body']))
        i += 1

    # 4. NDËRTIMI DHE KTHIMI I BUFFER-IT
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer