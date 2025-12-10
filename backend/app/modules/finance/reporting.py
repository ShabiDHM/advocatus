# FILE: backend/app/modules/finance/reporting.py
# PHOENIX PROTOCOL - FINANCE REPORT GENERATOR v2.1 (DATE FIX)
# 1. FIX: Forces Albanian Month names in PDF (removes English 'December').
# 2. STATUS: Fully Localized.

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

from app.models.finance import WizardState
from app.models.user import UserInDB

# PHOENIX: Explicit Albanian Month Mapping to bypass server locale
ALBANIAN_MONTHS = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
}

def generate_monthly_report_pdf(state: WizardState, user: UserInDB, month: int, year: int) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # --- 1. HEADER SECTION ---
    firm_name = user.username.upper()
    elements.append(Paragraph(f"<b>{firm_name}</b>", styles['Heading1']))
    
    title_text = "Raporti Mujor Financiar (TVSH)" if state.calculation.regime == "VAT_STANDARD" else "Raporti Mujor (Biznes i Vogël)"
    elements.append(Paragraph(title_text, styles['Title']))
    elements.append(Spacer(1, 0.2 * inch))

    # PHOENIX: Use Albanian Month Name
    month_name_sq = ALBANIAN_MONTHS.get(month, "")
    period_str = f"{month_name_sq} {year}"
    
    current_date = datetime.now().strftime('%d/%m/%Y')
    
    elements.append(Paragraph(f"<b>Periudha:</b> {period_str}", styles['Normal']))
    elements.append(Paragraph(f"<b>Gjeneruar më:</b> {current_date}", styles['Normal']))
    elements.append(Paragraph(f"<b>Statusi Tatimor:</b> {state.calculation.tax_rate_applied}", styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # --- 2. FINANCIAL TABLE ---
    calc = state.calculation
    currency = calc.currency

    if calc.regime == "SMALL_BUSINESS":
        data = [
            ["Përshkrimi", "Vlera"],
            ["Shitjet Bruto (Totale)", f"{calc.total_sales_gross:,.2f} {currency}"],
            ["Norma Tatimore", "9%"],
            ["", ""],
            ["TATIMI PËR T'U PAGUAR", f"{calc.net_obligation:,.2f} {currency}"]
        ]
    else:
        data = [
            ["Përshkrimi", "Vlera"],
            ["Shitjet e Tatueshme (Bruto)", f"{calc.total_sales_gross:,.2f} {currency}"],
            ["Blerjet e Zbritshme (Bruto)", f"{calc.total_purchases_gross:,.2f} {currency}"],
            ["", ""], 
            ["TVSH e Mbledhur (Shitje)", f"{calc.vat_collected:,.2f} {currency}"],
            ["TVSH e Zbritshme (Blerje)", f"{calc.vat_deductible:,.2f} {currency}"],
            ["DETYRIMI NETO", f"{calc.net_obligation:,.2f} {currency}"]
        ]

    t = Table(data, colWidths=[4.5*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (1, -1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.black),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 0.5 * inch))

    # --- 3. AUDIT SUMMARY ---
    elements.append(Paragraph("<b>Auditimi Automatik</b>", styles['Heading2']))
    
    if not state.issues:
        success_style = ParagraphStyle('Success', parent=styles['Normal'], textColor=colors.green)
        elements.append(Paragraph("✅ Të dhënat janë në rregull.", success_style))
    else:
        for issue in state.issues:
            severity_color = "red" if issue.severity == "CRITICAL" else "orange"
            text = f"<font color='{severity_color}'><b>[{issue.severity}]</b></font> {issue.message}"
            elements.append(Paragraph(text, styles['Normal']))
            elements.append(Spacer(1, 0.05 * inch))

    # --- 4. SIGNATURE ---
    elements.append(Spacer(1, 1.5 * inch))
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

    doc.build(elements)
    buffer.seek(0)
    return buffer