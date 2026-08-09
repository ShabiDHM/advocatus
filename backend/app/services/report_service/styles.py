# FILE: backend/app/services/report_service/styles.py
# PHOENIX PROTOCOL - REPORT STYLES & ONTOLOGY-GRADE REPORT CSS

from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT

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
        "analysis_title": "RAPORTI I STRATEGJISË LIGJORE DHE DEKLARATËS SË RASTIT",
        "report_case_label": "LËNDA:"
    }
}

# ⚡ ONTOLOGY-GRADE: CLEAN HIGH-TRUST WHITE PAPER REPORT CSS
EXECUTIVE_PRESENTATION_CSS = """
    @page {
        size: a4 portrait;
        margin: 12mm 14mm 16mm 14mm;
        @frame footer_frame {
            -pdf-frame-content: footer_content;
            left: 14mm; width: 182mm; bottom: 6mm; height: 10mm;
        }
    }
    body {
        font-family: 'Helvetica', sans-serif;
        font-size: 9.5pt;
        line-height: 1.5;
        color: #0f172a;
        background-color: #ffffff;
    }
    .report-title-header {
        border-bottom: 2px solid #0f172a;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    .report-title-header h1 {
        font-size: 13pt;
        font-weight: bold;
        color: #0f172a;
        margin: 0 0 4px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .report-meta-bar {
        font-size: 8.5pt;
        color: #475569;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 6px 12px;
        border-radius: 4px;
        margin-bottom: 18px;
    }
    h1 {
        font-size: 11pt;
        font-weight: bold;
        color: #0f172a;
        border-bottom: 1.5px solid #0f172a;
        margin-top: 18px;
        margin-bottom: 10px;
        padding-bottom: 4px;
        text-transform: uppercase;
    }
    h2 {
        font-size: 10pt;
        font-weight: bold;
        color: #0f172a;
        background-color: #f1f5f9;
        border-left: 4px solid #0284c7;
        padding: 6px 10px;
        margin-top: 14px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    h3 {
        font-size: 9.5pt;
        font-weight: bold;
        color: #1e293b;
        margin-top: 12px;
        margin-bottom: 6px;
    }
    p {
        margin: 0 0 8px 0;
        color: #1e293b;
        text-align: justify;
    }
    ul, ol {
        margin-top: 4px;
        margin-bottom: 10px;
        padding-left: 16px;
    }
    li {
        margin-bottom: 4px;
        line-height: 1.4;
        color: #334155;
    }
    strong {
        font-weight: bold;
        color: #0f172a;
    }
    blockquote {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 4px solid #059669;
        margin: 10px 0;
        padding: 8px 12px;
        color: #0f172a;
        border-radius: 4px;
    }
    code, pre {
        font-family: 'Courier', monospace;
        font-size: 8pt;
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        padding: 8px 12px;
        border-radius: 4px;
        color: #0f172a;
        display: block;
        white-space: pre-wrap;
        word-wrap: break-word;
        margin: 10px 0;
        line-height: 1.4;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 8px;
        margin-bottom: 14px;
    }
    th {
        background-color: #f1f5f9;
        color: #0f172a;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 8pt;
        padding: 6px 8px;
        border: 1px solid #cbd5e1;
        text-align: left;
    }
    td {
        background-color: #ffffff;
        color: #1e293b;
        font-size: 8.5pt;
        padding: 6px 8px;
        border: 1px solid #e2e8f0;
    }
    tr:nth-child(even) td {
        background-color: #f8fafc;
    }
    .badge {
        font-size: 7.5pt;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 3px;
        text-transform: uppercase;
    }
    .badge-blue { background-color: #e0f2fe; color: #0284c7; }
    .badge-red { background-color: #fee2e2; color: #dc2626; }
    .badge-green { background-color: #dcfce7; color: #15803d; }
"""