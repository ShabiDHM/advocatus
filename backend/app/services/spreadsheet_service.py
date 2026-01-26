# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - FORENSIC ENGINE V7.5 (CLEAN OUTPUT)
# 1. FIXED: Removed all "To/From/Signature" hallucinations via Strict Prompt Engineering.
# 2. ENHANCED: Persona now focuses purely on "Evidence Analysis" rather than "Memo Writing".
# 3. RETAINED: All algorithmic forensic checks (Benford, Structuring, etc.).

import pandas as pd
import io
import logging
import hashlib
import json
import uuid
import math
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
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AnomalyType(str, Enum):
    STRUCTURING = "CURRENCY_STRUCTURING"
    SIGNIFICANT_CASHFLOW_DEFICIT = "SIGNIFICANT_CASHFLOW_DEFICIT"
    BENFORDS_LAW_VIOLATION = "BENFORDS_LAW_VIOLATION"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    ROUND_NUMBER_ANOMALY = "ROUND_NUMBER_ANOMALY"
    SUSPICIOUS_WEEKEND_ACTIVITY = "SUSPICIOUS_WEEKEND_ACTIVITY"

THRESHOLD_STRUCTURING_MIN = Decimal('1800.00')
THRESHOLD_STRUCTURING_MAX = Decimal('1999.99')

# --- INTERNATIONALIZATION ENGINE (KOSOVO FOCUSED) ---
I18N_STRINGS = {
    'sq': {
        'prompt_persona': """
Ti je "Këshilltar i Brendshëm Forenzik" për tregun e Kosovës.
DETYRA: Analizo të dhënat dhe gjenero RAPORTIN E GJETJEVE (Jo Memorandum administrativ).
TONI: Profesional, skeptik, i bazuar në prova.
GJUHA: SHQIP.

RREGULLA KRITIKE (TË PANEGOCIUESHME):
1. MOS përfshi: "Për:", "Nga:", "Data:", "Lënda:", ose Nënshkrime në fund.
2. MOS përdor kllapa katrore [] ose placeholders.
3. Fillo direkt me seksionin 1.

STRUKTURA E DETYRUESHME:
**1. Përmbledhja Ekzekutive (BLUF)**
(Përmblidh rreziqet kryesore të zbuluara nga algoritmet: Benford, Dublifikime, etj. Jepi përparësi fakteve numerike.)

---

**2. Analiza e Detajuar e Parregullsive**
(Përshkruaj çdo anomali të gjetur. Shpjego pse 'Ligji i Benfordit' ose 'Numrat e Rrumbullakët' tregojnë manipulim të mundshëm.)

---

**3. Implikimet Ligjore & Tatimore**
(Referoju ATK-së dhe standardeve të kontabilitetit në Kosovë.)

---

**4. Plani i Veprimit**
(Auditimi i brendshëm, intervistimi i personave përgjegjës.)
""",
        'prompt_user_input': "TË DHËNAT NGA ALGORITMET:\n- Statistikat: {stats}\n- Anomalitë e Detektuara: {anomalies}\n\nShkruaj analizën forenzike direkt.",
        'hook_structuring': "Transaksioni (€{amount}) afër pragut ligjor (€2,000) sugjeron 'Structuring' për të shmangur raportimin AML.",
        'hook_deficit': "Deficit prej €{amount}. Indikator i mundshëm i fondeve të padeklaruara (Kodi Penal, Neni 307).",
        'hook_benford': "Shkelje e Ligjit të Benfordit (Devijim {score}%). Të dhënat mund të jenë të fabrikuara artificialisht.",
        'hook_duplicate': "Transaksion i dyfishtë potencial: {count} pagesa identike prej €{amount} më {date}.",
        'hook_round': "Përqindje e lartë ({pct}%) e numrave të rrumbullakët. Shpenzimet reale rrallë janë fiks (p.sh. 500.00€).",
        'hook_weekend': "Transaksion i madh (€{amount}) të Dielën. Rrezik i shpenzimeve personale ose fiktive.",
        
        'desc_deficit': "Mungesë e pajustifikuar parash",
        'desc_benford': "Indikator i Manipulimit Statistikor",
        'desc_duplicate': "Dublifikim i Transaksioneve",
        'desc_round': "Anomali e Numrave të Rrumbullakët",
        'desc_weekend': "Aktivitet i Dyshimtë në Vikend",
        
        'err_format': "Formati i skedarit nuk është valid.",
        'err_column': "Mungon kolona 'Shuma' ose 'Amount'.",
        'err_fail': "Analiza dështoi.",
        'txt_no_desc': "Pa Përshkrim",
        'msg_no_data': "Nuk u gjetën të dhëna."
    },
    'en': {
        'prompt_persona': """
You are a Forensic Auditor.
TASK: Generate a FINDINGS REPORT (Not a Memo).
TONE: Professional, skeptical, evidence-based.
LANGUAGE: ENGLISH.

CRITICAL RULES:
1. NO headers like "To:", "From:", "Date:", "Subject:".
2. NO signatures or placeholders [].
3. Start directly with Section 1.

STRUCTURE:
**1. Executive Summary (BLUF)**
...
**2. Detailed Anomaly Analysis**
...
**3. Legal & Tax Implications**
...
**4. Action Plan**
...
""", 
        'err_fail': "Analysis failed."
    }
}

def get_text(key: str, lang: str = 'sq', **kwargs) -> str:
    lang_dict = I18N_STRINGS.get(lang, I18N_STRINGS['sq'])
    text_template = lang_dict.get(key, I18N_STRINGS['sq'].get(key, key))
    try: return text_template.format(**kwargs)
    except: return text_template

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

# --- FORENSIC ALGORITHMS ---

def _check_benfords_law(amounts: List[Decimal]) -> Optional[float]:
    """
    Calculates deviation from Benford's Law for first digits (1-9).
    Returns Mean Absolute Deviation (MAD) percentage if significant.
    """
    if len(amounts) < 30: return None # Need sample size
    
    first_digits = [int(str(abs(a)).lstrip('0.')[:1]) for a in amounts if abs(a) >= 1]
    if not first_digits: return None
    
    counts = {d: 0 for d in range(1, 10)}
    for d in first_digits: 
        if 1 <= d <= 9: counts[d] += 1
        
    total = len(first_digits)
    observed = {d: c/total for d, c in counts.items()}
    expected = {d: math.log10(1 + 1/d) for d in range(1, 10)}
    
    mad = sum(abs(observed[d] - expected[d]) for d in range(1, 10)) / 9
    return mad * 100 # Return as percentage

def _is_weekend(date_str: str) -> bool:
    try:
        # Try generic formats
        for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.weekday() >= 5 # 5=Saturday, 6=Sunday
            except: continue
    except: pass
    return False

# --- CORE LOGIC ---

async def _forensic_detect_anomalies(records: List[Dict], lang: str) -> List[AnomalyEvidence]:
    anomalies = []
    amounts = [r['amount'] for r in records]
    
    # 1. Benford's Law (The "Fraud Fingerprint")
    benford_score = _check_benfords_law(amounts)
    if benford_score and benford_score > 5.0: # >5% deviation is suspicious
        anomalies.append(AnomalyEvidence(
            anomaly_id=str(uuid.uuid4()),
            type=AnomalyType.BENFORDS_LAW_VIOLATION,
            risk_level=RiskLevel.CRITICAL if benford_score > 10.0 else RiskLevel.HIGH,
            transaction_date="N/A",
            amount=Decimal('0.00'),
            description=get_text('desc_benford', lang),
            legal_hook=get_text('hook_benford', lang, score=f"{benford_score:.1f}")
        ))

    # 2. Round Number Analysis
    round_counts = sum(1 for a in amounts if a % 1 == 0 or a % 10 == 0)
    if len(amounts) > 10:
        pct_round = (round_counts / len(amounts)) * 100
        if pct_round > 25.0: # If >25% of transactions are round numbers
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.ROUND_NUMBER_ANOMALY,
                risk_level=RiskLevel.MEDIUM,
                transaction_date="N/A",
                amount=Decimal('0.00'),
                description=get_text('desc_round', lang),
                legal_hook=get_text('hook_round', lang, pct=f"{pct_round:.1f}")
            ))

    # 3. Duplicate Detection
    seen = {}
    for r in records:
        key = f"{r['amount']}_{r['date']}" # Same amount, same date
        if key in seen:
            seen[key].append(r)
        else:
            seen[key] = [r]
            
    for key, group in seen.items():
        if len(group) > 1 and abs(group[0]['amount']) > 50: # Only significant amounts
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.POTENTIAL_DUPLICATE,
                risk_level=RiskLevel.HIGH,
                transaction_date=group[0]['date'],
                amount=group[0]['amount'],
                description=get_text('desc_duplicate', lang),
                legal_hook=get_text('hook_duplicate', lang, count=len(group), amount=group[0]['amount'], date=group[0]['date'])
            ))

    # 4. Specific Transaction Checks
    for record in records:
        amt = abs(record['amount'])
        
        # Structuring
        if THRESHOLD_STRUCTURING_MIN <= amt <= THRESHOLD_STRUCTURING_MAX:
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()), type=AnomalyType.STRUCTURING, risk_level=RiskLevel.HIGH,
                transaction_date=record['date'], amount=record['amount'], description=record['description'],
                legal_hook=get_text('hook_structuring', lang, amount=f"{amt:,.2f}")
            ))
            
        # Weekend High Value
        if amt > 500 and _is_weekend(record['date']):
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.SUSPICIOUS_WEEKEND_ACTIVITY,
                risk_level=RiskLevel.MEDIUM,
                transaction_date=record['date'],
                amount=record['amount'],
                description=get_text('desc_weekend', lang),
                legal_hook=get_text('hook_weekend', lang, amount=f"{amt:,.2f}")
            ))

    # 5. Cash Flow Deficit
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = abs(sum(r['amount'] for r in records if r['amount'] < 0))
    deficit = total_out - total_in
    if deficit > 5000 and total_out > total_in * Decimal('1.2'):
         anomalies.append(AnomalyEvidence(
            anomaly_id=str(uuid.uuid4()), type=AnomalyType.SIGNIFICANT_CASHFLOW_DEFICIT, risk_level=RiskLevel.CRITICAL,
            transaction_date="Periudha", amount=Decimal(f"-{deficit:.2f}"), description=get_text('desc_deficit', lang),
            legal_hook=get_text('hook_deficit', lang, amount=f"{deficit:,.2f}")
        ))

    return anomalies

async def _generate_unified_strategic_memo(case_id: str, stats: Dict, top_anomalies: List[Dict], lang: str) -> str:
    system_prompt = get_text('prompt_persona', lang)
    user_content = get_text('prompt_user_input', lang, 
                           stats=json.dumps(stats, ensure_ascii=False), 
                           anomalies=json.dumps(top_anomalies, ensure_ascii=False))
    
    response = await asyncio.to_thread(getattr(llm_service, "_call_llm"), system_prompt, user_content, False, 0.1)
    return response or get_text('err_fail', lang)

async def _run_unified_analysis(content: bytes, filename: str, case_id: str, db: Database, lang: str = 'sq') -> Dict[str, Any]:
    try:
        df = pd.read_csv(io.BytesIO(content)) if filename.lower().endswith('.csv') else pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"{get_text('err_format', lang)}: {e}")
    
    df.columns = [str(c).lower().strip() for c in df.columns]
    col_amount = next((c for c in df.columns if 'amount' in c or 'shuma' in c), None)
    if not col_amount: raise ValueError(get_text('err_column', lang))
    
    records = []
    no_desc_txt = get_text('txt_no_desc', lang)
    
    for idx, row in df.fillna('').iterrows():
        try: amount = Decimal(str(row[col_amount]).replace('€', '').replace(',', '').strip())
        except: amount = Decimal('0.00')
        records.append({ 
            "row_id": idx, 
            "date": str(row.get('date', 'N/A')), 
            "description": str(row.get('description', no_desc_txt)), 
            "amount": amount 
        })
    
    anomalies_found = await _forensic_detect_anomalies(records, lang)
    
    stats_for_llm = {
        "Hyrjet": f"€{sum(r['amount'] for r in records if r['amount'] > 0):,.2f}",
        "Daljet": f"€{abs(sum(r['amount'] for r in records if r['amount'] < 0)):,.2f}",
        "Nr. Transaksioneve": len(records)
    }
    
    top_anomalies_for_llm = [
        {
            "Lloji": a.type.name, 
            "Data": a.transaction_date, 
            "Pershkrimi": a.description, 
            "Shuma": f"€{a.amount:,.2f}", 
            "Implikimi": a.legal_hook
        }
        for a in sorted(anomalies_found, key=lambda x: x.risk_level.value, reverse=True)[:5]
    ]
    
    executive_summary = await _generate_unified_strategic_memo(case_id, stats_for_llm, top_anomalies_for_llm, lang)
    await _vectorize_and_store(records, case_id, db)
    
    return {
        "executive_summary": executive_summary, 
        "anomalies": json_friendly_encoder([asdict(a) for a in anomalies_found]),
    }

# --- PUBLIC FUNCTIONS ---
async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database, lang: str = 'sq') -> Dict[str, Any]:
    return await _run_unified_analysis(content, filename, case_id, db, lang)

async def forensic_analyze_spreadsheet(content: bytes, filename: str, case_id: str, db: Database, analyst_id: Optional[str] = None, lang: str = 'sq') -> Dict[str, Any]:
    report = await _run_unified_analysis(content, filename, case_id, db, lang)
    report["forensic_metadata"] = { 
        "evidence_hash": generate_evidence_hash(content),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "record_count": len(report.get("anomalies", []))
    }
    return report

async def ask_financial_question(case_id: str, question: str, db: Database, lang: str = 'sq') -> Dict[str, Any]:
    q_vector = await asyncio.to_thread(llm_service.get_embedding, question)
    rows = await asyncio.to_thread(list, db.financial_vectors.find({"case_id": ObjectId(case_id)}))
    scored_rows = sorted([(np.dot(q_vector, row.get("embedding", [])), row) for row in rows if row.get("embedding")], key=lambda x: x[0], reverse=True)
    context_lines = [row["content"] for _, row in scored_rows[:15]]
    
    if not context_lines: 
        return {"answer": get_text('msg_no_data', lang)}
    
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

async def forensic_interrogate_evidence(case_id: str, question: str, db: Database, lang: str = 'sq') -> Dict[str, Any]:
    return await ask_financial_question(case_id, question, db, lang)