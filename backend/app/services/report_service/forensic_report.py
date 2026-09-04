# FILE: backend/app/services/report_service/forensic_report.py
# PHOENIX PROTOCOL - EXECUTIVE FORENSIC PDF GENERATOR V70.0 (MASTER LEGAL-TECH POLISH • ORPHAN GUARD • BULLETPROOF TABLES)

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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle

from .helpers import clean_text_for_pdf

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """
    Numëron automatikisht faqet (Faqja X nga Y) dhe vendos në çdo faqe
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

        # 1. Vija ndarëse e footer-it (Executive Double Tint Line)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(margin_x, 16.5 * mm, page_width - margin_x, 16.5 * mm)

        # 2. Klauzola e Përgjegjësisë Ligjore (majtas)
        disclaimer_style = ParagraphStyle(
            'FooterDisclaimer',
            fontName='Helvetica',
            fontSize=5.6,
            leading=7.2,
            textColor=colors.HexColor('#64748b'),
            alignment=4  # Justify
        )

        disclaimer_text = (
            "<b>KLAUZOLË E PËRGJEGJËSISË LIGJORE:</b> Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga "
            "<b>(Juristi AI)</b> për qëllime informative, kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë "
            "përfaqësimin e autorizuar nga një Avokat i licencuar i Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, "
            "afatet procedurale dhe aktet duhet të verifikohen me legjislacionin pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë."
        )

        disclaimer_box_width = content_width - 32 * mm
        p_disc = Paragraph(disclaimer_text, disclaimer_style)
        w, h = p_disc.wrap(disclaimer_box_width, 14 * mm)
        p_disc.drawOn(self, margin_x, 4.5 * mm)

        # 3. Treguesi i Faqes (Badge i dizajnuar djathtas)
        badge_x = page_width - margin_x - 28 * mm
        badge_y = 7.5 * mm
        self.setFillColor(colors.HexColor("#f1f5f9"))
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.roundRect(badge_x, badge_y, 28 * mm, 5.5 * mm, 2, fill=1, stroke=1)

        self.setFont("Helvetica-Bold", 6.8)
        self.setFillColor(colors.HexColor("#0f172a"))
        page_str = f"FAQJA {self._pageNumber} NGA {page_count}"
        self.drawCentredString(badge_x + (14 * mm), badge_y + 1.8 * mm, page_str)

        self.restoreState()


def _sanitize_inline_formatting(text: str) -> str:
    """Sanitizon tekstin markdown duke garantuar etiketa të sakta XML pa prishur ReportLab-in."""
    if not text:
        return ""

    # Mbrojtja e ampersand-it
    text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|nbsp);)', '&amp;', text)

    # Konvertimi i bold (**tekst** ose __tekst__)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    # Konvertimi i italic (*tekst* ose _tekst_)
    text = re.sub(r'(?<!<b>)\*(.*?)\*(?!</b>)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!<b>)_(.*?)_(?!</b>)', r'<i>\1</i>', text)

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
    """
    Parser i pathyeshëm i tabelave markdown.
    Pranon rreshta edhe nëse mungon mbyllja '|', me llogaritje dinamike të gjerësisë së kolonave.
    """
    table_data = []

    # Heqim rreshtat ndarës të stilit |---|---|
    cleaned_lines = [
        l for l in table_lines 
        if not re.match(r'^\s*\|?[\s\-:|]+\|?\s*$', l) and '|' in l
    ]

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

    # Barazimi i kolonave
    num_cols = max(len(r) for r in table_data)
    for r in table_data:
        while len(r) < num_cols:
            r.append(Paragraph("-", styles['TableCell']))

    total_table_width = 182 * mm

    if num_cols == 2:
        actual_col_widths = [55 * mm, 127 * mm]
    elif num_cols == 3:
        actual_col_widths = [48 * mm, 74 * mm, 60 * mm]
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
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5.5),
        ('TOPPADDING', (0, 0), (-1, 0), 5.5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4.5),
        ('TOPPADDING', (0, 1), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#0284c7')),
    ]))
    return t


def create_pdf_from_text(
    text: str,
    document_title: str = "RAPORT I AUDITIMIT DHE STRATEGJISË LIGJORE",
    header_meta_content_html: str = ""
) -> io.BytesIO:
    """Gjeneron Raport Ekzekutiv Forenzik me Polish Institucional Suprem."""
    cleaned_input = clean_text_for_pdf(text)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=23 * mm
    )

    styles = {
        'BrandSuper': ParagraphStyle(
            'BrandSuper',
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor('#0284c7'),
            spaceAfter=3,
            textTransform='uppercase'
        ),
        'DocMainTitle': ParagraphStyle(
            'DocMainTitle',
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4,
            textTransform='uppercase'
        ),
        'MetaBox': ParagraphStyle(
            'MetaBox',
            fontName='Helvetica',
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor('#334155')
        ),
        'SectionBanner': ParagraphStyle(
            'SecBanner',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=0,
            spaceAfter=0
        ),
        'Heading2': ParagraphStyle(
            'H2',
            fontName='Helvetica-Bold',
            fontSize=9.2,
            leading=12.5,
            textColor=colors.HexColor('#0369a1'),
            spaceBefore=9,
            spaceAfter=3,
            keepWithNext=True
        ),
        'Heading3': ParagraphStyle(
            'H3',
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=6,
            spaceAfter=2,
            keepWithNext=True
        ),
        'SubHeaderWithNext': ParagraphStyle(
            'SubHeaderWithNext',
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True
        ),
        'Body': ParagraphStyle(
            'BodyText',
            fontName='Helvetica',
            fontSize=7.9,
            leading=11.4,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=3.5,
            alignment=4
        ),
        'TimelineEvent': ParagraphStyle(
            'TimelineEvent',
            fontName='Helvetica',
            fontSize=7.9,
            leading=11.4,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=3,
            leftIndent=11
        ),
        'Bullet': ParagraphStyle(
            'BulletText',
            fontName='Helvetica',
            fontSize=7.9,
            leading=11.4,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=2.5,
            leftIndent=11
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
        )
    }

    story = []

    # 1. KOKA E DOKUMENTIT (EXECUTIVE BANNER)
    story.append(Paragraph("JURISTI AI • PLATFORMA E FORENZIKËS DHE STRATEGJISË LIGJORE", styles['BrandSuper']))
    clean_doc_title = document_title.replace('Raporti Forenzik:', '').strip()
    story.append(Paragraph(clean_doc_title or "RAPORT I AUDITIMIT DHE STRATEGJISË LIGJORE", styles['DocMainTitle']))

    # Vija e dyfishtë luksoze poshtë titullit
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f172a'), spaceBefore=1, spaceAfter=2))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor('#0284c7'), spaceBefore=0, spaceAfter=4))

    # 2. PASAPORTA E LËNDËS (CARD DESIGN ME THEKSE CYAN)
    meta_date_str = datetime.now().strftime("%d.%m.%Y, %H:%M")
    meta_html = header_meta_content_html or f"<b>DATA E GJENERIMIT:</b> {meta_date_str}"
    if "DATA" not in meta_html:
        meta_html += f" &nbsp;|&nbsp; <b>DATA:</b> {meta_date_str}"

    meta_table = Table([[Paragraph(meta_html, styles['MetaBox'])]], colWidths=[182 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BORDER', (0, 0), (-1, -1), 0.6, colors.HexColor('#cbd5e1')),
        ('LINELEFT', (0, 0), (0, -1), 3.5, colors.HexColor('#0284c7')),
        ('PADDING', (0, 0), (-1, -1), 5.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 3.5 * mm))

    # 3. PARSIMI DHE STRUKTURIMI ME ORPHAN PROTECTION
    lines = cleaned_input.split('\n')
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw_line = lines[i]
        line = raw_line.strip()

        if not line:
            i += 1
            continue

        # A. TABELAT MARKDOWN (Mbështetje për rreshta të papërfunduar me '|')
        if '|' in line and not line.startswith('>') and not line.startswith('```'):
            # Kontrollojmë nëse kemi vërtet strukturë tabele
            table_lines = []
            while i < total_lines and '|' in lines[i].strip():
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                t_obj = _parse_markdown_table(table_lines, styles)
                if t_obj:
                    story.append(Spacer(1, 1.5 * mm))
                    story.append(t_obj)
                    story.append(Spacer(1, 2.5 * mm))
                    continue
            else:
                # Nëse ishte vetëm 1 rresht i izoluar, ktheje tekstit
                line = table_lines[0]

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

        # C. TITUJT KRYESORË NUMERIKË (# 1., # 2. ose 1. TITULLI NË ALL CAPS)
        major_section_match = re.match(r'^(?:#\s+)?(\d+\.\s+[A-ZÇË\s—\-\:\/]{5,})$', line)
        if major_section_match:
            sec_text = _sanitize_inline_formatting(major_section_match.group(1).strip())
            sec_table = Table([[Paragraph(f"<b>{sec_text}</b>", styles['SectionBanner'])]], colWidths=[182 * mm])
            sec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
                ('LINELEFT', (0, 0), (0, -1), 3.5, colors.HexColor('#0f172a')),
                ('BORDER', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            
            # Mbrojtje nga orfanizimi: Titulli lidhet me elementin e radhës
            story.append(Spacer(1, 3 * mm))
            story.append(sec_table)
            story.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # D. TITUJT NIVELE (#, ##, ###)
        if line.startswith('# '):
            h_text = _sanitize_inline_formatting(line[2:])
            story.append(KeepTogether([
                Paragraph(h_text, styles['Heading2']),
                HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#0f172a'), spaceAfter=3)
            ]))
            i += 1
            continue

        if line.startswith('## '):
            h_text = _sanitize_inline_formatting(line[3:])
            story.append(Paragraph(h_text, styles['Heading2']))
            i += 1
            continue

        if line.startswith('### '):
            h_text = _sanitize_inline_formatting(line[4:])
            story.append(Paragraph(h_text, styles['Heading3']))
            i += 1
            continue

        # E. NËNTITUJT ME DY PIKA NË FUND (ORPHAN GUARD: FAKTET E PROVUARA:, PROCEDURA I:, etj.)
        subheading_match = re.match(r'^(?:[\*•\-]\s*)?(\*?[A-ZÇË\s—\-\d\(\)\.\/]{4,}\:?\*?)$', line)
        if (line.isupper() and len(line) < 80) or (line.endswith(':') and len(line) < 70 and not line.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9'))):
            sub_text = _sanitize_inline_formatting(line.strip('*').strip())
            story.append(Spacer(1, 1.5 * mm))
            story.append(Paragraph(f"<b>{sub_text}</b>", styles['SubHeaderWithNext']))
            i += 1
            continue

        # F. VIJAT NDARËSE
        if line in ['---', '***', '===', '═══════════════════════════════════════════════']:
            story.append(Spacer(1, 1 * mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceAfter=3))
            i += 1
            continue

        # G. BLOCKQUOTE (> ...)
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

        # H. NGJARJET KRONOLOGJIKE (Timeline me data: DD.MM.YYYY:)
        date_match = re.match(r'^(?:[■•\-\*]\s+)?(\d{2}\.\d{2}\.\d{4}(?:\s*—\s*\d{2}\.\d{2}\.\d{4})?\:)\s*(.*)', line)
        if date_match:
            date_prefix = date_match.group(1).strip()
            rest_text = _sanitize_inline_formatting(date_match.group(2).strip())
            formatted_timeline = f"<font color='#0369a1'><b>{date_prefix}</b></font> &nbsp; {rest_text}"
            story.append(Paragraph(formatted_timeline, styles['TimelineEvent']))
            i += 1
            continue

        # I. SHKELJET DHE ANOMALITË PROCEDURALE (Badges me theks të lartë ligjor)
        alert_match = re.match(r'^(?:[■•\-\*]\s+)?(\*(?:SHKELJE|ANOMALI)\s*\d*.*?\:\*?)\s*(.*)', line, re.IGNORECASE)
        if alert_match:
            alert_tag = _sanitize_inline_formatting(alert_match.group(1).strip())
            alert_rest = _sanitize_inline_formatting(alert_match.group(2).strip())
            formatted_alert = f"<font color='#b91c1c'><b>{alert_tag}</b></font> {alert_rest}"
            story.append(Paragraph(formatted_alert, styles['SubHeaderWithNext']))
            i += 1
            continue

        # J. LISTAT ME NUMRA (1., 2., 3.)
        num_match = re.match(r'^(\d+\.)\s+(.*)', line)
        if num_match:
            prefix = num_match.group(1)
            b_text = _sanitize_inline_formatting(num_match.group(2).strip())
            story.append(Paragraph(f"<b><font color='#0284c7'>{prefix}</font></b> &nbsp; {b_text}", styles['Bullet']))
            i += 1
            continue

        # K. LISTAT ME PIKA
        bullet_match = re.match(r'^(?:[•\-]\s+|\*(?!\*)\s+)(.*)', line)
        if bullet_match:
            b_text = _sanitize_inline_formatting(bullet_match.group(1).strip())
            story.append(Paragraph(f"<font color='#0284c7'>•</font> &nbsp; {b_text}", styles['Bullet']))
            i += 1
            continue

        # L. PARAGRAFI I ZAKONSHËM
        p_text = _sanitize_inline_formatting(line)
        story.append(Paragraph(p_text, styles['Body']))
        i += 1

    # 4. NDËRTIMI DHE KTHIMI I DOKUMENTIT
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer