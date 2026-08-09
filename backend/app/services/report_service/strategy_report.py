# FILE: backend/app/services/report_service/strategy_report.py
# PHOENIX PROTOCOL - ONTOLOGY-GRADE EXECUTIVE STRATEGY REPORT GENERATOR V34.0

import io
import re
import markdown2
import structlog
from xhtml2pdf import pisa
from datetime import datetime
from xml.sax.saxutils import escape
from typing import Optional

from .styles import EXECUTIVE_PRESENTATION_CSS
from .helpers import clean_text_for_pdf, _get_text

logger = structlog.get_logger(__name__)

def create_pdf_from_text(text: str, document_title: str, header_meta_content_html: Optional[str] = None) -> io.BytesIO:
    """
    Generates a publication-grade PDF report matching clean table/card layout.
    No raw hex ObjectIDs, includes required legal disclaimer footer on every page.
    """
    buffer = io.BytesIO()
    
    clean_text = clean_text_for_pdf(text)
    html_body = markdown2.markdown(clean_text, extras=["tables", "fenced-code-blocks", "cuddled-lists"])

    generation_date = datetime.now().strftime('%d.%m.%Y %H:%M')
    display_title = "RAPORTI I ANALIZËS"
    meta_html = header_meta_content_html or ""

    header_html = f"""
    <div class="report-title-header">
        <h1>{display_title}</h1>
    </div>
    <div class="report-meta-bar">
        {meta_html} &nbsp;|&nbsp; <b>Data e Gjenerimit:</b> {generation_date}
    </div>
    """
    
    footer_html = f"""
    <div id='footer_content' style='font-size: 8pt; color: #64748b;'>
        <table width="100%" style="border-top: 1px solid #e2e8f0; padding-top: 4px;">
            <tr>
                <td align="left" style="color: #64748b;">Ky raport është për referencë ligjore dhe duhet të verifikohet.</td>
                <td align="right" style="color: #64748b;">Data e Gjenerimit: {generation_date}</td>
            </tr>
        </table>
    </div>
    """

    full_html = f"""
    <html>
    <head>
        <meta charset="utf-8"/>
        <style>{EXECUTIVE_PRESENTATION_CSS}</style>
    </head>
    <body>
        {header_html}
        {html_body}
        {footer_html}
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

def generate_legal_strategy_report(case_title: str, raw_report_markdown: str, lang: str = "sq") -> io.BytesIO:
    """Generates an executive Legal Strategy Report PDF in clean Ontology style."""
    main_title = "RAPORTI I ANALIZËS"
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