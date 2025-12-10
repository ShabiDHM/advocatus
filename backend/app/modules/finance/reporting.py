# FILE: backend/app/modules/finance/reporting.py
# PHOENIX PROTOCOL - FINANCE REPORT GENERATOR
# 1. PURPOSE: Generates professional PDF Financial Statements (TVSH).
# 2. DESIGN: Clean, tabular layout with branding placeholders.
# 3. OUTPUT: Returns a BytesIO buffer ready for streaming.

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

# Import Data Models
from app.models.finance import WizardState
from app.models.user import UserInDB

def generate_monthly_report_pdf(state: WizardState, user: UserInDB, month: int, year: int) -> BytesIO:
    """
    Generates a PDF report for the Monthly Closing Wizard.
    Includes:
    1. Header with Firm Name.
    2. VAT Calculation Table (Box 10/30 equivalent).
    3. Audit Results.
    4. Signature Line.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # --- 1. HEADER SECTION ---
    # Firm Name (User Username for now, ideally BusinessProfile name)
    firm_name = user.username.upper()
    elements.append(Paragraph(f"<b>{firm_name}</b>", styles['Heading1']))
    
    # Report Title
    elements.append(Paragraph("Raporti Mujor Financiar (Deklarimi i TVSH-së)", styles['Title']))
    elements.append(Spacer(1, 0.2 * inch))

    # Period Info
    period_date = datetime(year, month, 1)
    period_str = period_date.strftime('%B %Y') # e.g., "December 2025"
    current_date = datetime.now().strftime('%d/%m/%Y')
    
    elements.append(Paragraph(f"<b>Periudha Tatimore:</b> {period_str}", styles['Normal']))
    elements.append(Paragraph(f"<b>Data e Gjenerimit:</b> {current_date}", styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # --- 2. FINANCIAL TABLE (VAT CALCULATION) ---
    calc = state.calculation
    currency = calc.currency

    # Table Data
    data = [
        ["Përshkrimi (Description)", "Vlera (Amount)"],
        # Sales
        ["Shitjet e Tatueshme (Total Sales - Gross)", f"{calc.total_sales_gross:,.2f} {currency}"],
        # Purchases
        ["Blerjet e Zbritshme (Total Purchases - Gross)", f"{calc.total_purchases_gross:,.2f} {currency}"],
        # Spacer
        ["", ""], 
        # VAT Logic
        ["TVSH e Mbledhur (Collected VAT - Output)", f"{calc.vat_collected:,.2f} {currency}"],
        ["TVSH e Zbritshme (Deductible VAT - Input)", f"{calc.vat_deductible:,.2f} {currency}"],
        # Net Result
        ["OBLIGIMI NETO (NET OBLIGATION)", f"{calc.net_obligation:,.2f} {currency}"]
    ]

    # Create Table
    t = Table(data, colWidths=[4.5*inch, 2*inch])

    # Styling
    t.setStyle(TableStyle([
        # Header Row
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#1e293b')), # Dark Slate
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'), # Align numbers to right
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        
        # Net Obligation Row (Last Row)
        ('BACKGROUND', (0, 6), (1, 6), colors.HexColor('#f1f5f9')), # Light Gray
        ('FONTNAME', (0, 6), (1, 6), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 6), (1, 6), colors.red if calc.net_obligation > 0 else colors.green),
        ('TOPPADDING', (0, 6), (1, 6), 12),
        ('BOTTOMPADDING', (0, 6), (1, 6), 12),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 0.5 * inch))

    # --- 3. AUDIT SUMMARY ---
    elements.append(Paragraph("<b>Auditimi Automatik (System Audit)</b>", styles['Heading2']))
    
    if not state.issues:
        # Success Message
        success_style = ParagraphStyle('Success', parent=styles['Normal'], textColor=colors.green)
        elements.append(Paragraph("✅ Nuk u gjetën probleme. Të dhënat janë konsistente për deklarim.", success_style))
    else:
        # List Issues
        for issue in state.issues:
            severity_color = "red" if issue.severity == "CRITICAL" else "orange"
            text = f"<font color='{severity_color}'><b>[{issue.severity}]</b></font> {issue.message}"
            elements.append(Paragraph(text, styles['Normal']))
            elements.append(Spacer(1, 0.05 * inch))

    # --- 4. FOOTER / SIGNATURE ---
    elements.append(Spacer(1, 1.5 * inch))
    
    # Signature Lines
    sig_data = [
        ["__________________________", "__________________________"],
        ["Nënshkrimi i Përfaqësuesit", "Nënshkrimi i Kontabilistit"]
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
    ]))
    elements.append(sig_table)

    # Disclaimer
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("<i>Ky dokument është gjeneruar automatikisht nga platforma Juristi AI.</i>", styles['Italic']))

    # Build the PDF
    doc.build(elements)
    
    # Reset buffer position to the beginning
    buffer.seek(0)
    return buffer