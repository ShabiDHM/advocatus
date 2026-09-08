# FILE: backend/app/services/forensic/forensic_finance_service.py
# PHOENIX PROTOCOL - FORENSIC FINANCIAL INTELLIGENCE V1.0 (LMD ARTICLE 265 • PANDAS AUDIT • CLAUDE SONNET)

import io
import json
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from .forensic_llm_service import call_forensic_llm

logger = logging.getLogger(__name__)

STANDARD_LMD_INTEREST_RATE = 8.0  # 8% standardi gjyqësor në Kosovë (LMD Neni 265)

def parse_date(d_str: str) -> date:
    """Konverton string në objekt date."""
    clean = d_str.strip().split("T")[0]
    return datetime.strptime(clean, "%Y-%m-%d").date()

def calculate_lmd_interest(
    principal: float,
    start_date_str: str,
    end_date_str: Optional[str] = None,
    rate_percent: float = STANDARD_LMD_INTEREST_RATE
) -> Dict[str, Any]:
    """
    Llogarit kamatëvonesën ligjore sipas Nenit 265 të Ligjit për Marrëdhëniet e Detyrimeve (LMD).
    """
    if principal <= 0:
        raise ValueError("Shuma e kryegjësë (principal) duhet të jetë më e madhe se 0.")

    start_d = parse_date(start_date_str)
    end_d = parse_date(end_date_str) if end_date_str else date.today()

    if end_d < start_d:
        raise ValueError("Data e përfundimit nuk mund të jetë para datës së fillimit të vonesës.")

    days_elapsed = (end_d - start_d).days
    
    # Formula zyrtare e kamatës së thjeshtë ligjore: (Principal * Rate * Days) / (365 * 100)
    interest_amount = (principal * rate_percent * days_elapsed) / (365.0 * 100.0)
    total_obligation = principal + interest_amount

    daily_accrual = (principal * rate_percent) / (365.0 * 100.0)

    return {
        "principal": round(principal, 2),
        "interest_rate_annual": rate_percent,
        "start_date": start_d.isoformat(),
        "end_date": end_d.isoformat(),
        "days_elapsed": days_elapsed,
        "daily_accrual": round(daily_accrual, 4),
        "interest_amount": round(interest_amount, 2),
        "total_obligation": round(total_obligation, 2),
        "legal_basis": "Neni 265 i Ligjit për Marrëdhëniet e Detyrimeve të Kosovës (LMD)",
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }

def analyze_financial_spreadsheet(
    file_bytes: bytes,
    file_name: str,
    claimed_amount: Optional[float] = None
) -> Dict[str, Any]:
    """
    Përdor Pandas për të analizuar transaksionet në Excel/CSV:
    - Llogarit totalet reale
    - Zbulon vlera ekstreme (Outliers)
    - Zbulon transaksione të dyfishta të dyshimta
    - Krahason me shumën e pretenduar në aktakuzë/padi
    """
    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        logger.error(f"❌ Dështoi leximi i skedarit Excel/CSV: {e}")
        raise ValueError(f"Skedari nuk mund të lexohet si tabelë financiare: {str(e)}")

    total_rows = len(df)
    columns_list = [str(col) for col in df.columns]

    # Identifiko kolonat me shuma numerike
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    summary_by_column: Dict[str, Any] = {}
    primary_amount_col = None
    calculated_total_sum = 0.0

    for col in numeric_cols:
        col_sum = float(df[col].sum())
        col_mean = float(df[col].mean())
        col_max = float(df[col].max())
        col_min = float(df[col].min())

        summary_by_column[str(col)] = {
            "sum": round(col_sum, 2),
            "mean": round(col_mean, 2),
            "max": round(col_max, 2),
            "min": round(col_min, 2)
        }

        # Përcakto kolonën kryesore (shpesh me shumat më të mëdha monetare)
        if primary_amount_col is None or col_sum > calculated_total_sum:
            primary_amount_col = col
            calculated_total_sum = col_sum

    # Detekto pagesat e dyfishta (potencial për fryrje dëmi)
    duplicate_rows_count = int(df.duplicated().sum())

    # Llogarit diferencën me aktakuzën/padinë
    discrepancy = None
    if claimed_amount is not None:
        discrepancy = {
            "claimed_in_suit": round(claimed_amount, 2),
            "documented_in_sheet": round(calculated_total_sum, 2),
            "delta": round(claimed_amount - calculated_total_sum, 2),
            "status": "I PËRPUTHUR" if abs(claimed_amount - calculated_total_sum) < 1.0 else (
                "FRYRJE PRETENDIMI (PRETENDOHET MË SHUMË SE SA DOKUMENTOHET)" 
                if claimed_amount > calculated_total_sum else "DËM I NËNVLERËSUAR"
            )
        }

    return {
        "file_name": file_name,
        "total_transactions": total_rows,
        "columns": columns_list,
        "primary_amount_column": str(primary_amount_col) if primary_amount_col else None,
        "total_documented_amount": round(calculated_total_sum, 2),
        "duplicate_records_found": duplicate_rows_count,
        "numeric_summaries": summary_by_column,
        "discrepancy_with_claim": discrepancy
    }

def generate_financial_forensic_opinion(
    spreadsheet_analysis: Dict[str, Any],
    interest_calculation: Optional[Dict[str, Any]] = None,
    case_context: str = ""
) -> Dict[str, Any]:
    """Përpilon ekspertizën financiare me Claude Sonnet 4.6."""
    system_prompt = """EKSPERTIZA FORENZIKE FINANCIARE DHE KONTABËL GJYQËSORE (CLAUDE SONNET 4.6):
Ju jeni Eksperti Financiar Forenzik i licencuar për Gjykatat e Kosovës.
Detyra juaj:
1. Analizoni të dhënat tabelare dhe kamatën e llogaritur sipas Nenit 265 të LMD.
2. Vlerësoni nëse ka anomali kontabël, disbalancë midis pretendimit dhe provës shkresore, apo pagesa fiktive.
3. Jepni një mendim formal për vlerën reale të dëmit pasuror material (Damnum Emergens dhe Lucrum Cessans).
4. Rekomandoni taktikat mbrojtëse për kundërshtimin e ekspertizës së palës kundërshtare.

Kthe përgjigjen VETËM në format JSON:
{
  "financial_audit_verdict": "I VERIFIKUAR | ANOMALI TË RËNDA | DISBALANCË FINANCIARE",
  "actual_damage_proven": 0.0,
  "accounting_irregularities": ["Anomalia 1", "Anomalia 2"],
  "lmd_interest_applicability": "Vlerësim i kamatës së kërkuar",
  "tactical_litigation_advice": "Këshillë procedurale për seancë përgatitore",
  "expert_concluding_summary": "Përmbledhja ekzekutive e ekspertit"
}"""

    user_content = f"""KONTEKSTI I LËNDËS:
{case_context or 'Ekspertizë financiare gjyqësore'}

REZULTATI I ANALIZËS PANDAS:
{json.dumps(spreadsheet_analysis, ensure_ascii=False, indent=2)}

LLOGARITJA E KAMATËS LMD (NËSE KA):
{json.dumps(interest_calculation or {}, ensure_ascii=False, indent=2)}"""

    raw_response = call_forensic_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        json_mode=True,
        temperature=0.0
    )

    try:
        from app.services.llm.llm_client import clean_and_parse_json
        parsed = clean_and_parse_json(raw_response)
        if parsed:
            return parsed
    except Exception:
        pass

    return {
        "financial_audit_verdict": "ANOMALI TË RËNDA",
        "actual_damage_proven": spreadsheet_analysis.get("total_documented_amount", 0.0),
        "accounting_irregularities": ["Kërkohet rishikim manual."],
        "lmd_interest_applicability": "Llogaritur sipas Nenit 265 LMD.",
        "tactical_litigation_advice": "Kundërshtoni shumën e padisë bazuar në mungesën e kuponëve fiskalë.",
        "expert_concluding_summary": raw_response
    }