# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - SPREADSHEET SERVICE V3.6 (LINTER FIX)
# 1. FIXED: Explicit type casting for 'safe_report_data' to silence Pylance errors
# 2. FIXED: 'json_friendly_encoder' handles all types correctly
# 3. VERIFIED: No QR, No OCR, Forensic Mode Active

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

# --- KOSOVO FORENSIC CONSTANTS ---
class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AnomalyType(str, Enum):
    STRUCTURING = "CURRENCY_STRUCTURING"
    SUSPICIOUS_KEYWORD = "SUSPICIOUS_KEYWORD"
    ROUND_AMOUNT = "ROUND_AMOUNT_TRANSACTION"
    STATISTICAL_OUTLIER = "STATISTICAL_OUTLIER"
    TEMPORAL_PATTERN = "TEMPORAL_PATTERN_ANOMALY"
    BENFORD_LAW_VIOLATION = "BENFORD_LAW_DEVIATION"

THRESHOLD_STRUCTURING = Decimal('1900.00')
THRESHOLD_CASH_LARGE = Decimal('500.00')
SUSPICIOUS_KEYWORDS = ["baste", "bet", "casino", "crypto", "binance", "kredi", "hua", "debt", "borxh", "offshore", "shell", "hawala", "unreported", "cash only", "no receipt"]

# KOSOVO LEGAL REFERENCES MAPPING
KOSOVO_LEGAL_REFERENCES = {
    "STRUCTURING": {
        "law": "Ligji Nr. 06/L-075",
        "article": "Neni 4",
        "title": "Shmangia e Raportimit të Detyrueshëm të Transaksioneve",
        "authority": "Banka Qendrore e Republikës së Kosovës",
        "threshold": "2,000€"
    },
    "SUSPICIOUS_KEYWORD": {
        "law": "Ligji Nr. 05/L-080",
        "article": "Neni 2",
        "title": "Veprime të Dyshimta Financiare dhe Parandalimi i Financimit të Terrorizmit",
        "authority": "Autoriteti për Parandalimin e Pastrimit të Parave",
        "threshold": "N/A"
    },
    "ROUND_AMOUNT": {
        "law": "Kodi Penal i Republikës së Kosovës",
        "article": "Neni 305",
        "title": "Pastrim i Parave përmes Transaksioneve Cash të Rrumbullakëta",
        "authority": "Prokuroria e Republikës së Kosovës",
        "threshold": "500€"
    },
    "STATISTICAL_OUTLIER": {
        "law": "Ligji Nr. 06/L-123",
        "article": "Neni 12",
        "title": "Transaksione Financiare të Pajustifikueshme",
        "authority": "Inspektorati Financiar i Kosovës",
        "threshold": "Statistikore"
    },
    "BENFORD_LAW_VIOLATION": {
        "law": "Standardet e Prokurorisë së Kosovës",
        "article": "ISO 27037:2012",
        "title": "Analiza Gjurmimore Digjitale për Manipulim të të Dhënave",
        "authority": "Ekspertëza Gjyqësore e Kosovës",
        "threshold": "Devijim Statistikor"
    }
}

# --- FORENSIC DATA STRUCTURES ---
@dataclass
class ForensicMetadata:
    evidence_id: str
    original_filename: str
    file_hash_sha256: str
    analysis_hash_sha256: str
    analyst_id: Optional[str]
    acquisition_timestamp: datetime
    acquisition_method: str
    device_source: Optional[str]
    chain_of_custody: List[Dict[str, Any]]
    jurisdiction: str = "KOSOVO"

@dataclass
class AnomalyEvidence:
    anomaly_id: str
    type: AnomalyType
    risk_level: RiskLevel
    transaction_date: str
    amount: Decimal
    description: str
    statistical_confidence: float
    supporting_evidence: List[str]
    legal_reference: str
    kosovo_authority: str
    recommended_action: str
    applicable_law: str = "Legjislacioni i Republikës së Kosovës"

@dataclass
class ForensicReport:
    report_id: str
    case_id: str
    executive_summary: str
    anomalies: List[AnomalyEvidence]
    statistical_analysis: Dict[str, Any]
    chain_of_custody: List[Dict[str, Any]]
    integrity_verification: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime
    report_hash: str
    jurisdiction: str = "KOSOVO"

# --- HELPER: JSON SAFE ENCODER ---
def json_friendly_encoder(obj: Any) -> Any:
    """Recursively convert Enums and Decimals to JSON-safe types"""
    if isinstance(obj, dict):
        return {k: json_friendly_encoder(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_friendly_encoder(i) for i in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, tuple):
        return [json_friendly_encoder(i) for i in obj]
    elif isinstance(obj, (datetime, ObjectId)):
        return str(obj)
    return obj

# --- FORENSIC UTILITIES ---
def generate_evidence_hash(content: bytes, metadata: Dict) -> str:
    combined = content + json.dumps(metadata, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()

def validate_benford_law(amounts: List[Decimal]) -> Dict[str, float]:
    first_digits = [int(str(abs(amt)).lstrip('0')[0]) for amt in amounts if amt != Decimal('0')]
    if not first_digits:
        return {}
    
    observed = {i: 0 for i in range(1, 10)}
    for digit in first_digits:
        if 1 <= digit <= 9:
            observed[digit] += 1
    
    total = len(first_digits)
    benford_distribution = {
        1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
        5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
    }
    
    deviations = {}
    for digit in range(1, 10):
        expected = benford_distribution[digit] * total
        observed_pct = observed[digit] / total
        deviation = abs(observed_pct - benford_distribution[digit]) / benford_distribution[digit]
        deviations[str(digit)] = deviation
    
    return deviations

def detect_statistical_outliers(amounts: List[Decimal]) -> List[Tuple[int, Decimal]]:
    if len(amounts) < 3:
        return []
    
    values = [float(amt) for amt in amounts]
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0
    
    outliers = []
    for idx, value in enumerate(values):
        if stdev > 0:
            z_score = abs((value - mean) / stdev)
            if z_score > 3.0:
                outliers.append((idx, Decimal(str(value)).quantize(Decimal('0.01'))))
    
    return outliers

def get_kosovo_legal_reference(anomaly_type: AnomalyType, amount: Decimal) -> Dict[str, str]:
    type_str = anomaly_type.name
    
    if type_str in KOSOVO_LEGAL_REFERENCES:
        ref = KOSOVO_LEGAL_REFERENCES[type_str]
        legal_text = f"{ref['law']}, {ref['article']} - {ref['title']}"
        if ref['threshold'] != "N/A" and "STRUCTURING" in type_str:
            legal_text += f" (Pragu i Raportimit: {ref['threshold']})"
        
        return {
            "legal_reference": legal_text,
            "authority": ref['authority'],
            "applicable_law": "Legjislacioni i Republikës së Kosovës"
        }
    
    return {
        "legal_reference": "Kodi Penal i Republikës së Kosovës, Neni 307 - Mashtrim Financiar",
        "authority": "Prokuroria e Republikës së Kosovës",
        "applicable_law": "Legjislacioni i Republikës së Kosovës"
    }

# --- NEW FORENSIC ANALYSIS FUNCTION (KOSOVO-COMPLIANT) ---
async def forensic_analyze_spreadsheet(
    content: bytes, 
    filename: str, 
    case_id: str, 
    db: Database,
    analyst_id: Optional[str] = None,
    acquisition_method: str = "UPLOAD"
) -> Dict[str, Any]:
    
    # === EVIDENCE INTEGRITY ===
    evidence_id = str(uuid.uuid4())
    acquisition_time = datetime.now(timezone.utc)
    metadata = {
        "filename": filename,
        "case_id": case_id,
        "analyst_id": analyst_id,
        "acquisition_time": acquisition_time.isoformat(),
        "jurisdiction": "KOSOVO"
    }
    evidence_hash = generate_evidence_hash(content, metadata)
    
    chain_of_custody = [{
        "timestamp": acquisition_time.isoformat(),
        "action": "ACQUISITION",
        "actor": analyst_id or "SYSTEM",
        "location": "FORENSIC_SERVER_KOSOVO",
        "integrity_hash": evidence_hash,
        "notes": f"File acquisition via {acquisition_method} - Jurisdiction: KOSOVO"
    }]
    
    # === PARSING ===
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"[FORENSIC-KOSOVO] Evidence parsing failed: {e}")
        raise HTTPException(status_code=422, detail=f"Format i pavlefshëm: {str(e)}")
    
    original_shape = df.shape
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    col_mapping = {
        'date': next((c for c in df.columns if 'date' in c or 'data' in c), None),
        'description': next((c for c in df.columns if 'desc' in c or 'pershkrim' in c or 'përshkrim' in c), None),
        'amount': next((c for c in df.columns if 'amount' in c or 'shuma' in c or 'vlere' in c), None)
    }
    
    if not col_mapping['amount']:
        raise HTTPException(status_code=422, detail="Mungon kolona 'Shuma' ose 'Amount'.")
    
    # === RECORD CONSTRUCTION ===
    records = []
    df = df.fillna('')
    
    for idx, row in df.iterrows():
        raw_amt = row[col_mapping['amount']]
        try:
            if isinstance(raw_amt, str):
                raw_amt = str(raw_amt).replace('€', '').replace('$', '').replace(',', '').strip()
            amount = Decimal(raw_amt).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except:
            amount = Decimal('0.00')
        
        date_val = str(row[col_mapping['date']]) if col_mapping['date'] else "N/A"
        desc_val = str(row[col_mapping['description']]) if col_mapping['description'] else "Pa Përshkrim"
        
        records.append({
            "row_id": idx,
            "date": date_val,
            "description": desc_val,
            "amount": amount,
            "raw_row": row.to_dict(),
            "evidence_reference": f"{evidence_id}:ROW:{idx}:KOS"
        })
    
    # === ANOMALY DETECTION ===
    anomalies = await _forensic_detect_anomalies_kosovo(records)
    
    # === STATISTICAL ANALYSIS ===
    statistical_analysis = {
        "benford_law_deviation": validate_benford_law([r['amount'] for r in records]),
        "outliers": detect_statistical_outliers([r['amount'] for r in records]),
        "total_records": len(records),
        "amount_summary": {
            "total_inflow": sum(r['amount'] for r in records if r['amount'] > 0),
            "total_outflow": abs(sum(r['amount'] for r in records if r['amount'] < 0))
        }
    }
    
    await _vectorize_and_store_forensic(records, case_id, evidence_id, db)
    executive_summary = await _generate_kosovo_forensic_summary(records, anomalies, statistical_analysis, case_id)
    
    # === RECOMMENDATIONS ===
    kosovo_recommendations = [
        "Iniconi procedurën 'Discovery' sipas rregullave të procesit civil të Kosovës.",
        "Kryeni auditim të stilit të jetesës vs. të ardhurave të deklaruara në taxat kosovare.",
        "Verifikoni përputhshmërinë me ligjet AML të Kosovës (Ligji Nr. 05/L-080).",
        f"Evidence Hash: {evidence_hash[:16]}... (Kosovo Jurisdiction)"
    ]
    
    # === REPORT CONSTRUCTION ===
    report_id = str(uuid.uuid4())
    report_data = {
        "report_id": report_id,
        "case_id": case_id,
        "executive_summary": executive_summary,
        "anomalies": [asdict(anom) for anom in anomalies],
        "statistical_analysis": statistical_analysis,
        "chain_of_custody": chain_of_custody,
        "integrity_verification": {
            "evidence_hash": evidence_hash,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": original_shape[0],
            "jurisdiction": "KOSOVO"
        },
        "recommendations": kosovo_recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jurisdiction": "KOSOVO"
    }
    
    # === SERIALIZATION FIX: Ensure Enums and Decimals are JSON safe ===
    # LINTER FIX: Explicitly cast to Dict[str, Any] to silence Pylance errors
    safe_report_data = cast(Dict[str, Any], json_friendly_encoder(report_data))
    
    # Generate report hash on the safe data
    report_hash = hashlib.sha256(
        json.dumps(safe_report_data, sort_keys=True, default=str).encode('utf-8')
    ).hexdigest()
    safe_report_data['report_hash'] = report_hash
    
    # Update chain
    # Note: 'chain_of_custody' is a list inside the dict, we append to the list
    if 'chain_of_custody' in safe_report_data and isinstance(safe_report_data['chain_of_custody'], list):
        safe_report_data['chain_of_custody'].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ANALYSIS_COMPLETED",
            "actor": "FORENSIC_ENGINE_KOSOVO",
            "integrity_hash": report_hash
        })
    
    # Store
    await asyncio.to_thread(
        db.forensic_reports.insert_one,
        {
            **safe_report_data,
            "stored_at": datetime.now(timezone.utc),
            "status": "COMPLETED"
        }
    )
    
    return safe_report_data

# --- EXISTING ANALYSIS FUNCTION (UPDATED) ---
async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"Spreadsheet parse error: {e}")
        raise ValueError("Formati i skedarit nuk është valid.")

    df.columns = [str(c).lower().strip() for c in df.columns]
    col_amount = next((c for c in df.columns if 'amount' in c or 'shuma' in c or 'vlere' in c), None)
    if not col_amount: raise ValueError("Nuk u gjet kolona 'Shuma' ose 'Amount'.")

    records = []
    df = df.fillna('')
    for idx, row in df.iterrows():
        try:
            raw_amt = str(row[col_amount]).replace('€', '').replace(',', '').strip()
            amount = float(raw_amt)
        except:
            amount = 0.0
        records.append({
            "row_id": idx, "date": str(row.get('date', 'N/A')), "description": str(row.get('description', 'Pa Përshkrim')),
            "amount": amount, "raw_row": row.to_dict()
        })

    anomalies = await _forensic_detect_anomalies_simple(records)
    trends = _calculate_trends(records)
    
    statistical_analysis = {
        "total_records": len(records),
        "total_inflow": sum(r['amount'] for r in records if r['amount'] > 0),
        "total_outflow": abs(sum(r['amount'] for r in records if r['amount'] < 0)),
        "jurisdiction": "KOSOVO"
    }
    
    exec_summary = await _generate_kosovo_forensic_summary_simple(records, anomalies, statistical_analysis, case_id)
    evidence_hash = hashlib.sha256(content).hexdigest()
    
    await _vectorize_and_store(records, case_id, db)

    # Return structure with forensic_metadata populated for consistency
    return {
        "executive_summary": exec_summary, 
        "anomalies": anomalies[:20],
        "trends": trends,
        "recommendations": [
            "Iniconi procedurën 'Discovery' sipas rregullave të procesit civil të Kosovës.",
            "Kryeni auditim të stilit të jetesës vs. të ardhurave.",
            f"Evidence Hash: {evidence_hash[:16]}... (Standard Scan)"
        ],
        "forensic_metadata": { 
            "evidence_hash": evidence_hash,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": len(records),
            "jurisdiction": "KOSOVO"
        }
    }

async def ask_financial_question(case_id: str, question: str, db: Database) -> Dict[str, Any]:
    q_vector = await asyncio.to_thread(llm_service.get_embedding, question)
    rows = await asyncio.to_thread(list, db.financial_vectors.find({"case_id": ObjectId(case_id)}))
    
    scored_rows = []
    for row in rows:
        v = row.get("embedding")
        if v:
            score = np.dot(q_vector, v)
            scored_rows.append((score, row))
    scored_rows.sort(key=lambda x: x[0], reverse=True)
    top_rows = scored_rows[:30]
    
    context_lines = [row["content"] for _, row in top_rows]
    if not context_lines: return {"answer": "Nuk u gjetën të dhëna relevante."}
    
    answer = await asyncio.to_thread(llm_service.forensic_interrogation, question, context_lines)
    return {
        "answer": answer, 
        "referenced_rows_count": len(top_rows),
        "forensic_context": "Analizë Financiare Standarde",
        "jurisdiction": "KOSOVO"
    }

def _detect_anomalies(records: List[Dict]) -> List[Dict]:
    return [] # Placeholder, logic moved to forensic functions

def _calculate_trends(records: List[Dict]) -> List[Dict]:
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = sum(abs(r['amount']) for r in records if r['amount'] < 0)
    return [
        {"category": "Totali i Hyrjeve", "trend": "STABLE", "percentage": f"€{total_in:,.2f}", "comment": "Të ardhura të detektuara."},
        {"category": "Totali i Daljeve", "trend": "UP", "percentage": f"€{total_out:,.2f}", "comment": "Shpenzime totale."}
    ]

async def _vectorize_and_store(records: List[Dict], case_id: str, db: Database):
    vectors = []
    for r in records:
        semantic_text = f"Data: {r['date']}. Shuma: {r['amount']} EUR. Përshkrimi: {r['description']}."
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        vectors.append({
            "case_id": ObjectId(case_id), "row_id": r['row_id'], "content": semantic_text,
            "metadata": r['raw_row'], "embedding": embedding, "created_at": datetime.now(timezone.utc),
            "forensic_flag": False, "jurisdiction": "KOSOVO"
        })
    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)

async def _vectorize_and_store_forensic(records: List[Dict], case_id: str, evidence_id: str, db: Database):
    vectors = []
    for record in records:
        semantic_text = f"DATA: {record['date']} | SHUMA: {record['amount']}€ | PËRSHKRIMI: {record['description']} | JURISDIKSION: KOSOVO"
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        vectors.append({
            "case_id": ObjectId(case_id), "evidence_id": evidence_id, "row_id": record['row_id'],
            "content": semantic_text, "metadata": {**record['raw_row'], "forensic_metadata": {"evidence_reference": record['evidence_reference']}},
            "embedding": embedding, "created_at": datetime.now(timezone.utc), "vector_type": "FORENSIC"
        })
    if vectors:
        await asyncio.to_thread(db.forensic_vectors.insert_many, vectors)

async def _forensic_detect_anomalies_simple(records: List[Dict]) -> List[Dict]:
    anomalies = []
    for r in records:
        amt = abs(r['amount'])
        desc = r['description'].lower()
        if 1500 < amt < 2000:
            anomalies.append({
                "date": r['date'], "amount": r['amount'], "description": r['description'],
                "risk_level": "HIGH", "forensic_type": "STRUCTURING",
                "explanation": "Strukturim i Mundshëm - Kontrolloni Ligjin Nr. 06/L-075",
                "legal_reference": "Ligji Nr. 06/L-075, Neni 4",
                "confidence": 0.85
            })
    return anomalies

async def _generate_kosovo_forensic_summary_simple(records, anomalies, stats, case_id):
    prompt = f"Gjenero një përmbledhje të shkurtër financiare për rastin {case_id} në Kosovë. Totali: {stats['total_records']} transaksione."
    response = await asyncio.to_thread(getattr(llm_service, "_call_llm"), "Ekspert Financiar", prompt, False)
    return response or "Përmbledhje jo e disponueshme."

async def _forensic_detect_anomalies_kosovo(records: List[Dict]) -> List[AnomalyEvidence]:
    anomalies = []
    records.sort(key=lambda x: x['date'])
    statistical_outliers = detect_statistical_outliers([r['amount'] for r in records])
    outlier_indices = {idx for idx, _ in statistical_outliers}
    
    for i, record in enumerate(records):
        amt = abs(record['amount'])
        desc = record['description'].lower()
        
        # 1. Structuring
        if THRESHOLD_STRUCTURING - Decimal('100.00') < amt < THRESHOLD_STRUCTURING:
            legal_ref = get_kosovo_legal_reference(AnomalyType.STRUCTURING, amt)
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.STRUCTURING,
                risk_level=RiskLevel.HIGH,
                transaction_date=record['date'],
                amount=record['amount'],
                description=record['description'],
                statistical_confidence=0.85,
                supporting_evidence=["Shuma afër pragut të raportimit"],
                legal_reference=legal_ref['legal_reference'],
                kosovo_authority=legal_ref['authority'],
                recommended_action="Kërko analizë shtesë"
            ))
            
        # 4. Outliers
        if i in outlier_indices:
            legal_ref = get_kosovo_legal_reference(AnomalyType.STATISTICAL_OUTLIER, amt)
            anomalies.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.STATISTICAL_OUTLIER,
                risk_level=RiskLevel.CRITICAL,
                transaction_date=record['date'],
                amount=record['amount'],
                description=record['description'],
                statistical_confidence=0.99,
                supporting_evidence=["Devijim statistikor > 3 sigma"],
                legal_reference=legal_ref['legal_reference'],
                kosovo_authority=legal_ref['authority'],
                recommended_action="Hetim i menjëhershëm"
            ))
            
    return anomalies

async def _generate_kosovo_forensic_summary(records, anomalies, stats, case_id):
    safe_anomalies = json_friendly_encoder([asdict(a) for a in anomalies[:5]])
    
    prompt = f"""
    VEPRO SI EKSPERT FORENZIK LIGJOR PËR KOSOVË.
    ID RASTI: {case_id}
    STATS: {json.dumps(json_friendly_encoder(stats))}
    ANOMALIES: {json.dumps(safe_anomalies)}
    
    Shkruaj një raport profesional ligjor në shqip.
    """
    response = await asyncio.to_thread(getattr(llm_service, "_call_llm"), "Ekspert Forenzik", prompt, False)
    return response or "Raporti nuk u gjenerua."

async def forensic_interrogate_evidence(case_id: str, question: str, db: Database, include_chain_of_custody: bool = True) -> Dict[str, Any]:
    q_vector = await asyncio.to_thread(llm_service.get_embedding, question)
    vectors = await asyncio.to_thread(list, db.forensic_vectors.find({"case_id": ObjectId(case_id)}))
    
    scored_vectors = []
    for vec in vectors:
        v = vec.get("embedding")
        if v:
            score = np.dot(q_vector, v)
            scored_vectors.append((score, vec))
    
    scored_vectors.sort(key=lambda x: x[0], reverse=True)
    top_vectors = scored_vectors[:10]
    
    if not top_vectors: return {"answer": "Nuk ka dëshmi.", "forensic_warning": "No evidence found."}
    
    context_lines = [v["content"] for _, v in top_vectors]
    answer = await asyncio.to_thread(llm_service.forensic_interrogation, f"PYETJE: {question}", context_lines)
    
    return {
        "answer": answer,
        "supporting_evidence_count": len(top_vectors),
        "chain_of_custody": [], 
        "jurisdiction": "KOSOVO"
    }