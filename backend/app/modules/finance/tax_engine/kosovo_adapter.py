# FILE: backend/app/modules/finance/tax_engine/kosovo_adapter.py
# PHOENIX PROTOCOL - KOSOVO TAX ADAPTER v2.0
# 1. LOGIC: Implements €30,000 Threshold check.
# 2. LOGIC: Adds 'Small Business' (9% Gross) vs 'VAT' (18% Net) modes.

class KosovoTaxAdapter:
    """
    Logic for ATK (Tax Administration of Kosovo).
    
    Regimes:
    1. SMALL_BUSINESS (Turnover < €30,000/year):
       - Rate: 9% of Gross Income (Services/Professional).
       - Expenses: NOT deductible for tax.
       - Reporting: Quarterly (usually).
       
    2. VAT_REGISTERED (Turnover > €30,000/year):
       - Rate: 18% Standard.
       - Logic: Output VAT - Input VAT.
       - Reporting: Monthly.
    """
    
    VAT_THRESHOLD = 30000.00
    VAT_RATE = 0.18
    SMALL_BIZ_RATE = 0.09 # 9% for Services (Lawyers)
    
    def calculate_vat_from_gross(self, gross_amount: float) -> float:
        if gross_amount <= 0: return 0.0
        return round(gross_amount - (gross_amount / (1 + self.VAT_RATE)), 2)

    def analyze_month(self, invoices: list, expenses: list, month: int, year: int, annual_turnover_ytd: float) -> dict:
        """
        Calculates obligations based on the appropriate tax regime.
        """
        
        # 1. Calculate Monthly Totals
        valid_invoices = [inv for inv in invoices if inv.status != 'CANCELLED']
        monthly_sales = sum(inv.total_amount for inv in valid_invoices)
        monthly_expenses = sum(exp.amount for exp in expenses)
        
        # 2. Determine Regime
        # If YTD turnover (including this month) > 30k, they are VAT liable.
        # NOTE: A real system would check the exact registration date. 
        # Here we simulate the ATK rule: Once you cross it, you enter VAT.
        is_vat_liable = (annual_turnover_ytd + monthly_sales) > self.VAT_THRESHOLD
        
        regime = "VAT_STANDARD" if is_vat_liable else "SMALL_BUSINESS"
        
        result = {
            "period_month": month,
            "period_year": year,
            "total_sales_gross": round(monthly_sales, 2),
            "total_purchases_gross": round(monthly_expenses, 2),
            "currency": "EUR",
            "status": "ESTIMATED",
            "regime": regime 
        }

        if regime == "SMALL_BUSINESS":
            # 9% on Gross Income. Expenses irrelevant for Tax (but relevant for Profit).
            tax_due = monthly_sales * self.SMALL_BIZ_RATE
            
            result.update({
                "tax_rate_applied": "9% (Small Business / Services)",
                "vat_collected": 0.0,
                "vat_deductible": 0.0,
                "net_obligation": round(tax_due, 2),
                "description": "Tatimi në të Ardhura (Biznes i Vogël)"
            })
            
        else:
            # 18% VAT Logic
            vat_collected = self.calculate_vat_from_gross(monthly_sales)
            vat_deductible = self.calculate_vat_from_gross(monthly_expenses)
            net_obligation = vat_collected - vat_deductible
            
            result.update({
                "tax_rate_applied": "18% (TVSH)",
                "vat_collected": vat_collected,
                "vat_deductible": vat_deductible,
                "net_obligation": round(net_obligation, 2),
                "description": "Detyrimi për TVSH"
            })
            
        return result