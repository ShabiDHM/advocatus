# FILE: backend/app/modules/finance/tax_engine/kosovo_adapter.py
class KosovoTaxAdapter:
    STANDARD_RATE = 0.18
    
    def calculate_vat_from_gross(self, gross_amount: float) -> float:
        if gross_amount <= 0: return 0.0
        return round(gross_amount - (gross_amount / (1 + self.STANDARD_RATE)), 2)

    def analyze_month(self, invoices: list, expenses: list, month: int, year: int) -> dict:
        valid_invoices = [inv for inv in invoices if inv.status != 'CANCELLED']
        total_sales = sum(inv.total_amount for inv in valid_invoices)
        
        # Simple Logic: All expenses treated as deductible for MVP
        total_purchases = sum(exp.amount for exp in expenses)
        
        vat_collected = self.calculate_vat_from_gross(total_sales)
        vat_deductible = self.calculate_vat_from_gross(total_purchases)
        net_obligation = round(vat_collected - vat_deductible, 2)
        
        return {
            "period_month": month,
            "period_year": year,
            "total_sales_gross": round(total_sales, 2),
            "total_purchases_gross": round(total_purchases, 2),
            "vat_collected": vat_collected,
            "vat_deductible": vat_deductible,
            "net_obligation": net_obligation,
            "status": "ESTIMATED",
            "currency": "EUR"
        }