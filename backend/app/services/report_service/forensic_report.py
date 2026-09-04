# FILE: backend/app/services/report_service/forensic_report.py
# PHOENIX PROTOCOL - EXECUTIVE FORENSIC PDF GENERATOR V65.0 (PREMIUM POLISH • DYNAMIC PROPORTIONS • LEGAL DISCLAIMER)

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
    """
    Numëron faqet dinamikisht (Faqja X nga Y) dhe vizaton në çdo faqe
    Klauzolën Zyrtare të Përgjegjësisë Ligjore sipas kërkesave të Odës së Avokatëve.
    """
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

        page_width, page_height = A4
        margin_x = 14 * mm
        content_width = page_width - (2 * margin_x)

        # 1. Vija ndarëse e footer-it
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(margin_x, 16.5 * mm, page_width - margin_x, 16.5 * mm)

        # 2. Klauzola e plotë ligjore (majtas)
        disclaimer_style = ParagraphStyle(
            'FooterDisclaimer',
            fontName='Helvetica',
            fontSize=5.8,
            leading=7.4,
            textColor=colors.HexColor('#64748b'),
            alignment=4  # Justify
        )

        disclaimer_text = (
            "<b>KLAUZOLË E PËRGJEGJËSISË LIGJORE:</b> Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga "
            "<b>(Juristi AI)</b> për qëllime informative, kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë "
            "përfaqësimin e autorizuar nga një Avokat i licencuar i Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, "
            "afatet procedurale dhe aktet duhet të verifikohen me legjislacionin pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë."
        )

        disclaimer_width = content_width - 26 * mm
        p_disc = Paragraph(disclaimer_text, disclaimer_style)
        w, h = p_disc.wrap(disclaimer_width, 14 * mm)
        p_disc.drawOn(self, margin_x, 4.5 * mm)

        # 3. Treguesi i faqes (djathtas)
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#334155"))
        page_str = f"Faqja {self._pageNumber} nga {page_count}"
        self.drawRightString(page_width - margin_x, 9.5 * mm, page_str)

        self.restoreState()


def _sanitize_inline_formatting(text: str) -> str:
    """Konverton markdown bold/italic në etiketa të sigurta XML për ReportLab."""
    if not text:
        return ""

    # Mbrojtja e ampersand-it
    text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|nbsp);)', '&amp;', text)
    
    # Konvertimi i bold (**tekst**)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    # Konvertimi i italic (*tekst*)
    text = re.sub(r'(?<!<b>)\*(.*?)\*(?!</b>)', r'<i>\1</i>', text)
    
    # Rregullimi i etiketave të pambyllura
    open_b = text.count('<b>')
    close_b = text.count('</b>')
    if open_b > close_b:
        text += '</b>' * (open_b - close_b)

    open_i = text.count('<i>')
    close_i = text.count('</i>')
    if open_i > close_i:
        text += '</i>' * (open_i - close_i)

    return text.strip()


def _parse_markdown_table(table_lines: List[str], styles: Dict[str, ParagraphStyle]) -> Optional[Table]:
    """Konverton tabelat markdown në objekte elegante ReportLab me proporcione të përsosura."""
    table_data = []
    
    cleaned_lines = [l for l in table_lines if not re.match(r'^\s*\|?[\s\-:|]+\|?\s*$', l)]

    for idx, line in enumerate(cleaned_lines):
        raw_cells = [c.strip() for c in line.strip().strip('|').split('|')]
        row_cells = []
        is_header = (idx == 0)

        cell_style = styles['TableHeader'] if is_header else styles['TableCell']

        for c in raw_cells:
            formatted_text = _sanitize_inline_formatting(c)
            row_cells.append(Paragraph(formatted_text or "-", cell_style))

        if row_cells:
            table_data.append(row_cells)

    if not table_data:
        return None

    num_cols = max(len(r) for r in table_data)
    for r in table_data:
        while len(r) < num_cols:
            r.append(Paragraph("-", styles['TableCell']))

    total_table_width = 182 * mm

    # Llogaritja dinamike e kolonave sipas natyrës së përmbajtjes ligjore
    if num_cols == 2:
        actual_col_widths = [55 * mm, 127 * mm]
    elif num_cols == 3:
        actual_col_widths = [50 * mm, 74 * mm, 58 * mm]
    elif num_cols == 4:
        actual_col_widths = [36 * mm, 44 * mm, 58 * mm, 44 * mm]
    elif num_cols == 5:
        actual_col_widths = [28 * mm, 36 * mm, 44 * mm, 40 * mm, 34 * mm]
    else:
        actual_col_widths = [total_table_width / num_cols] * num_cols

    t = Table(table_data, colWidths=actual_col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4.5),
        ('TOPPADDING', (0, 1), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor('#0284c7')),
    ]))
    return t


def create_pdf_from_text(
    text: str,
    document_title: str = "RAPORT I AUDITIMIT DHE STRATEGJISË LIGJORE",
    header_meta_content_html: str = ""
) -> io.BytesIO:
    """Gjeneron Raport Ekzekutiv Forenzik të nivelit të lartë institucional."""
    cleaned_input = clean_text_for_pdf(text)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=23 * mm  # Lirësi e mjaftueshme për footer-in e ri
    )

    styles = {
        'BrandSuper': ParagraphStyle(
            'BrandSuper',
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0284c7'),
            spaceAfter=2,
            textTransform='uppercase'
        ),
        'DocMainTitle': ParagraphStyle(
            'DocMainTitle',
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=19,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6,
            textTransform='uppercase'
        ),
        'MetaBox': ParagraphStyle(
            'MetaBox',
            fontName='Helvetica',
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor('#334155')
        ),
        'Heading1': ParagraphStyle(
            'H1',
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=11,
            spaceAfter=4,
            keepWithNext=True
        ),
        'Heading2': ParagraphStyle(
            'H2',
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#0284c7'),
            spaceBefore=9,
            spaceAfter=3,
            keepWithNext=True
        ),
        'Heading3': ParagraphStyle(
            'H3',
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=6,
            spaceAfter=2,
            keepWithNext=True
        ),
        'Body': ParagraphStyle(
            'BodyText',
            fontName='Helvetica',
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=4,
            alignment=4  # Justified
        ),
        'Bullet': ParagraphStyle(
            'BulletText',
            fontName='Helvetica',
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=2.5,
            leftIndent=10
        ),
        'Blockquote': ParagraphStyle(
            'QuoteText',
            fontName='Helvetica-Oblique',
            fontSize=7.8,
            leading=10.5,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=3,
            spaceAfter=5,
            leftIndent=8
        ),
        'CodeBlock': ParagraphStyle(
            'CodeText',
            fontName='Courier',
            fontSize=7.2,
            leading=9.5,
            textColor=colors.HexColor('#0f172a')
        ),
        'TableHeader': ParagraphStyle(
            'TH',
            fontName='Helvetica-Bold',
            fontSize=7.2,
            leading=9.2,
            textColor=colors.white
        ),
        'TableCell': ParagraphStyle(
            'TD',
            fontName='Helvetica',
            fontSize=7.2,
            leading=9.8,
            textColor=colors.HexColor('#0f172a')
        ),
        'DisclaimerInBody': ParagraphStyle(
            'DiscInBody',
            fontName='Helvetica-Oblique',
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#64748b'),
            spaceBefore=8,
            alignment=4
        )
    }

    story = []

    # 1. KOKA E DOKUMENTIT (BRANDING INSTITUCIONAL)
    story.append(Paragraph("JURISTI AI • PLATFORMA E FORENZIKËS DHE STRATEGJISË LIGJORE", styles['BrandSuper']))
    clean_doc_title = document_title.replace('Raporti Forenzik:', '').strip()
    story.append(Paragraph(clean_doc_title or "RAPORT I AUDITIMIT DHE STRATEGJISË LIGJORE", styles['DocMainTitle']))

    # 2. PASAPORTA E LËNDËS
    meta_date_str = datetime.now().strftime("%d.%m.%Y, %H:%M")
    meta_html = header_meta_content_html or f"<b>DATA E GJENERIMIT:</b> {meta_date_str}"
    if "DATA" not in meta_html:
        meta_html += f" &nbsp;|&nbsp; <b>DATA:</b> {meta_date_str}"

    meta_table = Table([[Paragraph(meta_html, styles['MetaBox'])]], colWidths=[182 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BORDER', (0, 0), (-1, -1), 0.6, colors.HexColor('#e2e8f0')),
        ('LINELEFT', (0, 0), (0, -1), 3.0, colors.HexColor('#0284c7')),
        ('PADDING', (0, 0), (-1, -1), 5.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    # 3. INTERPRETIMI DHE RENDITJA E STRUKTURUAR
    lines = cleaned_input.split('\n')
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw_line = lines[i]
        line = raw_line.strip()

        if not line:
            i += 1
            continue

        # A. TABELAT MARKDOWN
        if line.startswith('|') and line.endswith('|'):
            table_lines = []
            while i < total_lines and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_lines.append(lines[i].strip())
                i += 1

            t_obj = _parse_markdown_table(table_lines, styles)
            if t_obj:
                story.append(Spacer(1, 1.5 * mm))
                story.append(t_obj)
                story.append(Spacer(1, 2.5 * mm))
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
            code_table = Table([[Paragraph(code_text, styles['CodeBlock'])]], colWidths=[182 * mm])
            code_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
                ('BORDER', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(code_table)
            story.append(Spacer(1, 2.5 * mm))
            continue

        # C. TITUJT KRYESORË (#, ##, ###) DHE TITUJT E NUMËRUAR
        if line.startswith('# '):
            h_text = _sanitize_inline_formatting(line[2:])
            story.append(Paragraph(h_text, styles['Heading1']))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#0f172a'), spaceAfter=4))
            i += 1
            continue

        if line.startswith('## '):
            h_text = _sanitize_inline_formatting(line[3:])
            story.append(Paragraph(h_text, styles['Heading2']))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=3))
            i += 1
            continue

        if line.startswith('### '):
            h_text = _sanitize_inline_formatting(line[4:])
            story.append(Paragraph(h_text, styles['Heading3']))
            i += 1
            continue

        # D. VIJAT NDARËSE
        if line in ['---', '***', '===', '═══════════════════════════════════════════════']:
            story.append(Spacer(1, 1 * mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceAfter=3))
            i += 1
            continue

        # E. BLOCKQUOTE (> ...)
        if line.startswith('>'):
            q_text = _sanitize_inline_formatting(line.lstrip('>').strip())
            q_table = Table([[Paragraph(q_text, styles['Blockquote'])]], colWidths=[182 * mm])
            q_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('LINELEFT', (0, 0), (0, -1), 2.5, colors.HexColor('#0284c7')),
                ('PADDING', (0, 0), (-1, -1), 4.5),
            ]))
            story.append(q_table)
            story.append(Spacer(1, 1.5 * mm))
            i += 1
            continue

        # F. LISTAT ME PIKA (PA PRISHUR BOLD/ASTERISKAT)
        bullet_match = re.match(r'^(?:[•\-]\s+|\*(?!\*)\s+)(.*)', line)
        if bullet_match:
            b_text = _sanitize_inline_formatting(bullet_match.group(1).strip())
            story.append(Paragraph(f"<font color='#0284c7'>■</font> &nbsp; {b_text}", styles['Bullet']))
            i += 1
            continue

        # G. LISTAT ME NUMRA (1., 2., ...)
        num_match = re.match(r'^(\d+\.)\s+(.*)', line)
        if num_match:
            prefix = num_match.group(1)
            b_text = _sanitize_inline_formatting(num_match.group(2).strip())
            story.append(Paragraph(f"<b><font color='#0284c7'>{prefix}</font></b> &nbsp; {b_text}", styles['Bullet']))
            i += 1
            continue

        # H. PARAGRAFI I ZAKONSHËM
        p_text = _sanitize_inline_formatting(line)
        story.append(Paragraph(p_text, styles['Body']))
        i += 1

    # 4. NDËRTIMI I DOKUMENTIT ME NUMBERED CANVAS
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer