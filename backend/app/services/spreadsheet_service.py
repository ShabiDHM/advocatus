# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - HONEST ADVISOR ENGINE V6.0 (FINAL)
# 1. NEW PROMPT: Re-engineered the AI prompt from the ground up to match the user's high-quality example.
# 2. NEW PERSONA: "In-House Forensic Accountant" providing objective, strategic advice.
# 3. FIXED: AI will no longer generate headers, signatures, or other unwanted text.
# 4. ENHANCED: The system now delivers a single, polished, and legally-focused memorandum.

import pandas as pd
import io
import logging
import hashlib
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, cast
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import numpy as np
from pymongo.database import Database
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from decimal import Decimal, ROUND_HALF_UP

# Internal Services
from . import llm_service

logger = logging.getLogger(__name__)

# --- CONSTANTS & DATA STRUCTURES ---
class RiskLevel(str, Enum):
    HIGH = "HIGH"; CRITICAL = "CRITICAL"

class AnomalyType(str, Enum):
    STRUCTURING = "CURRENCY_STRUCTURING"
    SIGNIFICANT_CASHFLOW_DEFICIT = "SIGNIFICANT_CASHFLOW_DEFICIT"

THRESHOLD_STRUCTURING_MIN = Decimal('1800.00')
THRESHOLD_STRUCTURING_MAX = Decimal('1999.99')

PROMPT_UNIFIED_MEMORANDUM = """
Ti je "Këshilltar i Brendshëm Forenzik" në një firmë ligjore prestigjioze në Kosovë.
DETYRA: Shkruaj trupin e një MEMORANDUMI konfidencial për avokatin kryesor.
TONI: Objektiv, i qartë, dhe strategjik. Fokusohesh në fakte dhe implikimet e tyre ligjore.
RREGULLA STRICTE: MOS shto tituj si "MEMORANDUM...", "PËR:", "NGA:", "SUBJEKTI", ose "Nënshkrim". Gjenero VETËM përmbajtjen duke filluar nga pika 1.

STRUKTURA E DETYRUESHME:
**1. Përmbledhja Ekzekutive (BLUF)**
(Një ose dy fjali që përmbledhin gjetjet më kritike dhe rëndësinë e tyre.)

---

**2. Gjetjet Kryesore & Vlerësimi i Provave**
(Për secilën gjetje, krijo një seksion me numër. Listo faktet, implikimin ligjor, dhe vlerëso fuqinë e provës: E Lartë, Mesatare, ose e Ulët.)

---

**3. Dobësitë & Kundër-Argumentet e Pritshme**
(Çfarë do të thotë pala kundërshtare? Si mund ta parandalojmë argumentin e tyre?)

---

**4. Rekomandimet për Hapat e Ardhshëm**
(Listë e qartë dhe me prioritet e veprimeve ligjore të rekomanduara.)
"""

@dataclass
class AnomalyEvidence:
    anomaly_id: str; type: AnomalyType; risk_level: RiskLevel; transaction_date: str
    amount: Decimal; description: str; legal_hook: str

# --- HELPERS ---
def json_friendly_encoder(obj: Any) -> Any:
    if isinstance(obj, dict): return {k: json_friendly_encoder(v) for k, v in obj.items()}
    if isinstance(obj, list): return [json_friendly_encoder(i) for i in obj]
    if isinstance(obj, Enum): return obj.value
    if isinstance(obj, Decimal): return float(obj)
    if isinstance(obj, (datetime, ObjectId)): return str(obj)
    return obj

def generate_evidence_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

# --- CORE LOGIC ---
async def _generate_unified_strategic_memo(case_id: str, stats: Dict, top_anomalies: List[Dict]) -> str:
    user_prompt = f"TË DHËNAT PËR ANALIZË:\n- Statistikat: {json.dumps(stats, ensure_ascii=False)}\n- Gjetjet Kryesore: {json.dumps(top_anomalies, ensure_ascii=False)}\n\nGjenero trupin e memorandumit sipas udhëzimeve."
    response = await asyncio.to_thread(getattr(llm_service, "_call_llm"), PROMPT_UNIFIED_MEMORANDUM, user_prompt, False, 0.1)
    return response or "Gjenerimi i memorandumit dështoi."

async def _forensic_detect_anomalies(records: List[Dict]) -> List[AnomalyEvidence]:
    anomalies = []
    # 1. Detect Specific Violations (Structuring)
    for record in records:
        amt = abs(record['amount'])
        if THRESHOLD_STRUCTURING_MIN <= amt <= THRESHOLD_STRUCTURING_MAX:
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()), type=AnomalyType.STRUCTURING, risk_level=RiskLevel.HIGH,
                transaction_date=record['date'], amount=record['amount'], description=record['description'],
                legal_hook=f"Transaksioni (€{amt:,.2f}) është afër pragut ligjor (€2,000) për raportim sipas Ligjit Nr. 06/L-075, Neni 4."
            ))
    # 2. Detect Cash Flow Deficit
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = abs(sum(r['amount'] for r in records if r['amount'] < 0))
    deficit = total_out - total_in
    if deficit > 5000 and total_out > total_in * Decimal('1.2'):
        latest_date = max((r['date'] for r in records if r['date'] != "N/A"), default="Gjatë periudhës")
        anomalies.append(AnomalyEvidence(
            anomaly_id=str(uuid.uuid4()), type=AnomalyType.SIGNIFICANT_CASHFLOW_DEFICIT, risk_level=RiskLevel.CRITICAL,
            transaction_date=latest_date, amount=Decimal(f"-{deficit:.2f}"), description="Deficit i pashpjeguar në fluksin e parasë",
            legal_hook=f"Daljet tejkalojnë hyrjet me €{deficit:,.2f}. Kjo ngre pyetje për burime të padeklaruara fondesh ose kontabilitet jo të rregullt (Kodi Penal, Neni 307)."
        ))
    return anomalies

async def _run_unified_analysis(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    try:
        df = pd.read_csv(io.BytesIO(content)) if filename.lower().endswith('.csv') else pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Formati i skedarit nuk është valid: {e}")
    df.columns = [str(c).lower().strip() for c in df.columns]
    col_amount = next((c for c in df.columns if 'amount' in c or 'shuma' in c), None)
    if not col_amount: raise ValueError("Mungon kolona 'Shuma' ose 'Amount'.")
    
    records = []
    for idx, row in df.fillna('').iterrows():
        try: amount = Decimal(str(row[col_amount]).replace('€', '').replace(',', '').strip())
        except: amount = Decimal('0.00')
        records.append({ "row_id": idx, "date": str(row.get('date', 'N/A')), "description": str(row.get('description', 'Pa Përshkrim')), "amount": amount })
    
    anomalies_found = await _forensic_detect_anomalies(records)
    
    # Pre-process data for the AI
    stats_for_llm = {
        "Hyrjet Totale": f"€{sum(r['amount'] for r in records if r['amount'] > 0):,.2f}",
        "Daljet Totale": f"€{abs(sum(r['amount'] for r in records if r['amount'] < 0)):,.2f}",
    }
    top_anomalies_for_llm = [
        {"Lloji": a.type.name, "Data": a.transaction_date, "Përshkrimi": a.description, "Shuma": f"€{a.amount:,.2f}", "Implikimi Ligjor": a.legal_hook}
        for a in sorted(anomalies_found, key=lambda x: x.risk_level.value, reverse=True)[:2]
    ]
    
    executive_summary = await _generate_unified_strategic_memo(case_id, stats_for_llm, top_anomalies_for_llm)
    await _vectorize_and_store(records, case_id, db)
    
    return {
        "executive_summary": executive_summary, 
        "anomalies": json_friendly_encoder([asdict(a) for a in anomalies_found]),
    }

# --- PUBLIC FUNCTIONS ---
async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    return await _run_unified_analysis(content, filename, case_id, db)

async def forensic_analyze_spreadsheet(content: bytes, filename: str, case_id: str, db: Database, analyst_id: Optional[str] = None) -> Dict[str, Any]:
    report = await _run_unified_analysis(content, filename, case_id, db)
    report["forensic_metadata"] = { 
        "evidence_hash": generate_evidence_hash(content),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "record_count": len(report.get("anomalies", []))
    }
    return report

async def ask_financial_question(case_id: str, question: str, db: Database) -> Dict[str, Any]:
    q_vector = await asyncio.to_thread(llm_service.get_embedding, question)
    rows = await asyncio.to_thread(list, db.financial_vectors.find({"case_id": ObjectId(case_id)}))
    scored_rows = sorted([(np.dot(q_vector, row.get("embedding", [])), row) for row in rows if row.get("embedding")], key=lambda x: x[0], reverse=True)
    context_lines = [row["content"] for _, row in scored_rows[:15]]
    if not context_lines: return {"answer": "Nuk u gjetën të dhëna relevante në skedar."}
    answer = await asyncio.to_thread(llm_service.forensic_interrogation, question, context_lines)
    return { "answer": answer, "supporting_evidence_count": len(context_lines) }

async def _vectorize_and_store(records: List[Dict], case_id: str, db: Database):
    vectors = []
    for r in records:
        semantic_text = f"Data: {r['date']}. Shuma: {r['amount']} EUR. Përshkrimi: {r['description']}."
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        vectors.append({"case_id": ObjectId(case_id), "content": semantic_text, "embedding": embedding})
    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)

async def forensic_interrogate_evidence(case_id: str, question: str, db: Database) -> Dict[str, Any]:
    return await ask_financial_question(case_id, question, db)