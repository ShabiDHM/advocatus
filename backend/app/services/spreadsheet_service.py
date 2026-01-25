# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - HONEST ADVISOR ENGINE V5.0
# 1. IMPLEMENTED: "Honest Advisor" protocol with dynamic, context-aware AI prompts.
# 2. ADDED: New anomaly type "SIGNIFICANT_CASHFLOW_DEFICIT" for smarter pre-analysis.
# 3. ENHANCED: AI now generates a single, high-quality, strategic memo tailored to the specific evidence found.
# 4. FIXED: All previous quality regressions. The output is now realistic and valuable for legal professionals.

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

# --- CONSTANTS AND ENUMS ---
class RiskLevel(str, Enum):
    LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; CRITICAL = "CRITICAL"

class AnomalyType(str, Enum):
    STRUCTURING = "CURRENCY_STRUCTURING"
    SIGNIFICANT_CASHFLOW_DEFICIT = "SIGNIFICANT_CASHFLOW_DEFICIT"

THRESHOLD_STRUCTURING_MIN = Decimal('1800.00')
THRESHOLD_STRUCTURING_MAX = Decimal('1999.99')

# --- DYNAMIC AI PROMPTS ---
PROMPT_HONEST_ADVISOR_BASE = """
Ti je "Këshilltar i Brendshëm Forenzik" në një firmë ligjore prestigjioze në Kosovë.
DETYRA: Shkruaj një MEMORANDUM të brendshëm konfidencial për avokatin kryesor të rastit.
TONI: Objektiv, i qartë dhe strategjik. Fokusohesh në fakte dhe implikimet e tyre ligjore.
QËLLIMI: Të ofrosh një vlerësim të sinqertë të provave dhe hapat e ardhshëm më të mençur.

STRUKTURA E DETYRUESHME (Markdown):
### **MEMORANDUM I BRENDSHËM KONFIDENCIAL**
**PËR:** Avokatin Kryesor
**NGA:** Njësia e Analizës Forenzike AI
**RASTI NR:** {case_id}
**SUBJEKTI:** Vlerësimi Fillestar i Provave Financiare
---
**1. Përmbledhja Ekzekutive (BLUF)**
(Një ose dy fjali që përmbledhin gjetjen kryesore dhe rëndësinë e saj.)

**2. Gjetjet Kryesore & Vlerësimi i Provave**
(Listo faktin/et më të rëndësishme. Për secilin, shpjego implikimin ligjor dhe vlerëso sinqerisht fuqinë e provës: e Lartë, Mesatare, apo e Ulët.)

**3. Dobësitë & Kundër-Argumentet e Pritshme**
(Çfarë do të thotë pala kundërshtare? Si mund ta parandalojmë argumentin e tyre?)

**4. Rekomandimet për Hapat e Ardhshëm**
(Listë e qartë dhe me prioritet e veprimeve ligjore të rekomanduara.)
"""

PROMPT_SCENARIO_SMOKING_GUN = """
KONTEKSTI: Është gjetur një provë specifike me rrezik të lartë (një "smoking gun").
FOKUSI YT: Përqendro të gjithë memorandumin rreth kësaj prove. Bëje atë pikën qendrore të analizës. Shpjego pse është kaq e rëndësishme dhe si mund të shfrytëzohet maksimalisht.
"""

PROMPT_SCENARIO_DEFICIT = """
KONTEKSTI: Nuk është gjetur asnjë shkelje specifike (si strukturimi). Gjetja më e rëndësishme është një deficit i madh dhe i pashpjeguar në fluksin e parasë.
FOKUSI YT: Përqendro të gjithë memorandumin rreth këtij deficiti. Trajtoje atë jo si provë direkte të mashtrimit, por si një mjet strategjik për të vënë në dyshim transparencën dhe besueshmërinë financiare të palës kundërshtare. Thekso se si ky deficit mund të përdoret për të kërkuar një auditim të plotë.
"""

# --- DATA STRUCTURES ---
@dataclass
class AnomalyEvidence:
    anomaly_id: str
    type: AnomalyType
    risk_level: RiskLevel
    transaction_date: str
    amount: Decimal
    description: str
    legal_hook: str

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
async def _generate_unified_strategic_memo(case_id: str, stats: Dict, top_anomalies: List[Dict], scenario: str) -> str:
    scenario_prompt = PROMPT_SCENARIO_SMOKING_GUN if scenario == "SMOKING_GUN" else PROMPT_SCENARIO_DEFICIT
    system_prompt = PROMPT_HONEST_ADVISOR_BASE.format(case_id=case_id) + "\n" + scenario_prompt
    user_prompt = f"TË DHËNAT PËR ANALIZË:\n- Statistikat: {json.dumps(stats, ensure_ascii=False)}\n- Gjetjet Kryesore: {json.dumps(top_anomalies, ensure_ascii=False)}\n\nGjenero memorandumin sipas udhëzimeve."
    
    response = await asyncio.to_thread(getattr(llm_service, "_call_llm"), system_prompt, user_prompt, False, 0.1)
    return response or "Gjenerimi i memorandumit dështoi."

async def _forensic_detect_anomalies_kosovo(records: List[Dict]) -> List[AnomalyEvidence]:
    anomalies = []
    
    # 1. Detect Specific Violations (e.g., Structuring)
    for record in records:
        amt = abs(record['amount'])
        if THRESHOLD_STRUCTURING_MIN <= amt <= THRESHOLD_STRUCTURING_MAX:
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()), type=AnomalyType.STRUCTURING, risk_level=RiskLevel.HIGH,
                transaction_date=record['date'], amount=record['amount'], description=record['description'],
                legal_hook=f"Transaksioni (€{amt}) është afër pragut ligjor (€2,000) për raportim sipas Ligjit Nr. 06/L-075, Neni 4."
            ))
            
    # 2. Detect "Mega-Anomaly" of Cash Flow Deficit
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = abs(sum(r['amount'] for r in records if r['amount'] < 0))
    deficit = total_out - total_in
    
    if deficit > 5000 and total_out > total_in * Decimal('1.2'):
        latest_date = max(r['date'] for r in records if r['date'] != "N/A") if any(r['date'] != "N/A" for r in records) else "Gjatë periudhës"
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
        try:
            amount = Decimal(str(row[col_amount]).replace('€', '').replace(',', '').strip())
        except:
            amount = Decimal('0.00')
        records.append({ "row_id": idx, "date": str(row.get('date', 'N/A')), "description": str(row.get('description', 'Pa Përshkrim')), "amount": amount })

    anomalies_found = await _forensic_detect_anomalies_kosovo(records)
    
    # Determine the scenario for the dynamic prompt
    has_structuring = any(a.type == AnomalyType.STRUCTURING for a in anomalies_found)
    scenario = "SMOKING_GUN" if has_structuring else "DEFICIT"

    # Prepare data for the AI
    stats_for_llm = {
        "Numri i Transaksioneve": len(records),
        "Hyrjet Totale": f"€{sum(r['amount'] for r in records if r['amount'] > 0):,.2f}",
        "Daljet Totale": f"€{abs(sum(r['amount'] for r in records if r['amount'] < 0)):,.2f}",
    }
    top_anomalies_for_llm = [
        {"Lloji": a.type.name, "Data": a.transaction_date, "Përshkrimi": a.description, "Shuma": f"€{a.amount:,.2f}", "Implikimi Ligjor": a.legal_hook}
        for a in sorted(anomalies_found, key=lambda x: x.risk_level.value, reverse=True)[:3]
    ]

    executive_summary = await _generate_unified_strategic_memo(case_id, stats_for_llm, top_anomalies_for_llm, scenario)
    
    await _vectorize_and_store(records, case_id, db)

    return {
        "executive_summary": executive_summary, 
        "anomalies": json_friendly_encoder([asdict(a) for a in anomalies_found]),
        "trends": [
            {"category": "Totali i Hyrjeve", "percentage": stats_for_llm["Hyrjet Totale"]},
            {"category": "Totali i Daljeve", "percentage": stats_for_llm["Daljet Totale"]}
        ]
    }

# --- PUBLIC FUNCTIONS ---
async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    report = await _run_unified_analysis(content, filename, case_id, db)
    report["forensic_metadata"] = { 
        "evidence_hash": generate_evidence_hash(content),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "record_count": len(report.get("anomalies", []))
    }
    return report

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
    
    scored_rows = sorted(
        [(np.dot(q_vector, row.get("embedding")), row) for row in rows if row.get("embedding")],
        key=lambda x: x[0], reverse=True
    )
    top_rows = scored_rows[:15]
    
    context_lines = [row["content"] for _, row in top_rows]
    if not context_lines: return {"answer": "Nuk u gjetën të dhëna relevante në skedar për t'iu përgjigjur kësaj pyetjeje."}
    
    answer = await asyncio.to_thread(llm_service.forensic_interrogation, question, context_lines)
    return { "answer": answer, "supporting_evidence_count": len(top_rows) }

async def _vectorize_and_store(records: List[Dict], case_id: str, db: Database):
    vectors = []
    for r in records:
        semantic_text = f"Data: {r['date']}. Shuma: {r['amount']} EUR. Përshkrimi: {r['description']}."
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        vectors.append({
            "case_id": ObjectId(case_id), "row_id": r['row_id'], "content": semantic_text,
            "metadata": {"raw": str(r.get("raw_row", {}))}, "embedding": embedding, "created_at": datetime.now(timezone.utc)
        })
    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)

async def forensic_interrogate_evidence(case_id: str, question: str, db: Database) -> Dict[str, Any]:
    return await ask_financial_question(case_id, question, db)