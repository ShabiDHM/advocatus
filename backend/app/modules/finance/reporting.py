# FILE: backend/app/modules/finance/reporting.py
# PHOENIX PROTOCOL - FINANCE REPORT GENERATOR v3.0 (BEAUTIFUL EDITION)
# 1. FIX: Enforced Albanian Month Names (Janar, Shkurt, etc.).
# 2. DESIGN: Upgraded to a modern, professional invoice-style layout.
# 3. LAYOUT: Added colored headers, zebra-striping, and summary cards.

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from datetime import datetime

from app.models.finance import WizardState
from app.models.user import UserInDB

# --- CONSTANTS ---
ALBANIAN_MONTHS = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
}

# Corporate Colors
COLOR_PRIMARY = colors.HexColor("#1e293b")  # Navy Blue
COLOR_ACCENT = colors.HexColor("#4f46e5")   # Indigo
COLOR_SUCCESS = colors.HexColor("#10b981")  # Emerald
COLOR_BG_HEADER = colors.HexColor("#f8fafc") # Light Gray
COLOR_BORDER = colors.HexColor("#e2e8f0")

def generate_monthly_report_pdf(state: WizardState, user: UserInDB, month: int, year: int) -> BytesIO:
    buffer = BytesIO()
    
    # Margins: Top, Bottom, Left, Right
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm, 
        topMargin=20*mm, bottomMargin=20*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # --- CUSTOM STYLES ---
    style_firm_name = ParagraphStyle(
        'FirmName', 
        parent=styles['Heading1'], 
        fontSize=24, 
        textColor=COLOR_PRIMARY,
        spaceAfter=10
    )
    style_report_title = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.gray,
        spaceAfter=20,
        textTransform='uppercase'
    )
    style_label = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray
    )
    style_value = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.black,
        leading=14
    )

    # --- 1. HEADER SECTION ---
    # Firm Name & Title
    firm_name = user.username.upper()
    report_type = "RAPORTI MUJOR I TVSH-së" if state.calculation.regime == "VAT_STANDARD" else "RAPORTI I BIZNESIT TË VOGËL"
    
    elements.append(Paragraph(firm_name, style_firm_name))
    elements.append(Paragraph(report_type, style_report_title))
    
    # Draw a line
    elements.append(Spacer(1, 5*mm))
    
    # --- 2. INFO GRID (Date, Status, Generated) ---
    # Manually map the month to Albanian
    month_name_sq = ALBANIAN_MONTHS.get(month, "")
    period_str = f"{month_name_sq} {year}"
    current_date = datetime.now().strftime('%d/%m/%Y')
    
    # We use a table for the "Info Box" layout
    info_data = [
        [
            Paragraph("<b>PERIUDHA TATIMORE</b>", style_label),
            Paragraph("<b>DATA E GJENERIMIT</b>", style_label),
            Paragraph("<b>REGJIMI TATIMOR</b>", style_label)
        ],
        [
            Paragraph(period_str, style_value),
            Paragraph(current_date, style_value),
            Paragraph(state.calculation.tax_rate_applied, style_value)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    elements.append(info_table)
    
    elements.append(Spacer(1, 10*mm))

    # --- 3. FINANCIAL TABLE ---
    calc = state.calculation
    currency = calc.currency

    # Define Data based on Regime
    if calc.regime == "SMALL_BUSINESS":
        table_data = [
            ["PËRSHKRIMI", "VLERA"], # Header
            ["Shitjet Bruto (Totale)", f"{calc.total_sales_gross:,.2f} {currency}"],
            ["Norma Tatimore", "9%"],
            ["Shpenzimet (Pa efekt tatimor)", f"({calc.total_purchases_gross:,.2f} {currency})"],
            ["", ""], # Spacer
            ["DETYRIMI TATIMOR", f"{calc.net_obligation:,.2f} {currency}"] # Total
        ]
    else:
        table_data = [
            ["PËRSHKRIMI", "VLERA"], # Header
            ["Shitjet e Tatueshme (Bruto)", f"{calc.total_sales_gross:,.2f} {currency}"],
            ["Blerjet e Zbritshme (Bruto)", f"{calc.total_purchases_gross:,.2f} {currency}"],
            ["TVSH e Mbledhur (Output)", f"{calc.vat_collected:,.2f} {currency}"],
            ["TVSH e Zbritshme (Input)", f"({calc.vat_deductible:,.2f} {currency})"],
            ["", ""],
            ["DETYRIMI NETO PËR TVSH", f"{calc.net_obligation:,.2f} {currency}"] # Total
        ]

    # Create the Table
    t = Table(table_data, colWidths=[4.5*inch, 2.5*inch])
    
    # Styling
    t.setStyle(TableStyle([
        # Header Style
        ('BACKGROUND', (0, 0), (1, 0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (1, 0), 10),
        ('TOPPADDING', (0, 0), (1, 0), 10),
        
        # Body Style
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 12),
        
        # Zebra Striping (Gray Rows)
        ('BACKGROUND', (0, 1), (-1, 1), COLOR_BG_HEADER), # Row 1
        ('BACKGROUND', (0, 3), (-1, 3), COLOR_BG_HEADER), # Row 3
        
        # Line below header
        ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_PRIMARY),
        
        # Total Row (Last Row)
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_ACCENT),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 15*mm))

    # --- 4. AUDIT SECTION ---
    elements.append(Paragraph("AUDITIMI I SISTEMIT", style_report_title))
    
    if not state.issues:
        # Success Box
        data_audit = [[
            Paragraph(
                "<font color='#10b981'><b>✓ Të dhënat janë konsistente.</b></font><br/>"
                "<font size=10 color='gray'>Sistemi nuk ka gjetur parregullsi në faturat apo shpenzimet e këtij muaji.</font>", 
                style_value
            )
        ]]
        t_audit = Table(data_audit, colWidths=[7*inch])
        t_audit.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ecfdf5")), # Light Green
            ('BOX', (0,0), (-1,-1), 1, COLOR_SUCCESS),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(t_audit)
    else:
        # Issues List
        for issue in state.issues:
            severity_color = "red" if issue.severity == "CRITICAL" else "orange"
            p = Paragraph(
                f"<font color='{severity_color}'><b>[{issue.severity}]</b></font> {issue.message}", 
                style_value
            )
            elements.append(p)
            elements.append(Spacer(1, 2*mm))

    # --- 5. FOOTER / SIGNATURES ---
    elements.append(Spacer(1, 30*mm))
    
    sig_data = [
        ["__________________________", "__________________________"],
        [f"{firm_name}", "Kontabilisti / Përfaqësuesi"]
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.gray),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig_table)

    # Disclaimer Footer
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(
        "Ky dokument është gjeneruar automatikisht nga platforma Juristi AI. "
        "Ju lutemi konsultohuni me kontabilistin tuaj para deklarimit final në ATK.", 
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=1)
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer