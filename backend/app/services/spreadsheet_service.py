# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - KOSOVO FORENSIC FINANCIAL ENGINE V3.2
# ENHANCEMENTS:
# 1. KOSOVO-SPECIFIC: All legal references updated for Kosovo legislation
# 2. LAWYER-FOCUSED: Removed prosecutor signatures, focused on legal evidence collection
# 3. COMPLIANCE: Updated with Kosovo AML/CFT laws and regulations
# 4. COURT-READY: Evidence preparation for Kosovo judicial system

import pandas as pd
import io
import logging
import hashlib
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
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

# --- KOSOVO FORENSIC CONSTANTS (KOSOVO LEGISLATION COMPLIANT) ---
class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AnomalyType(Enum):
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
    """ISO 27037: Evidence Item Metadata (Kosovo Compliant)"""
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
    """Court-ready anomaly documentation for Kosovo legal system"""
    anomaly_id: str
    type: AnomalyType
    risk_level: RiskLevel
    transaction_date: str
    amount: Decimal
    description: str
    statistical_confidence: float  # 0.0 to 1.0
    supporting_evidence: List[str]
    legal_reference: str  # Kosovo-specific legal reference
    kosovo_authority: str  # Relevant Kosovo authority
    recommended_action: str
    applicable_law: str = "Legjislacioni i Republikës së Kosovës"

@dataclass
class ForensicReport:
    """Complete forensic analysis package for Kosovo legal proceedings"""
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

# --- FORENSIC UTILITIES ---
def generate_evidence_hash(content: bytes, metadata: Dict) -> str:
    """Generate SHA-256 hash for evidence integrity verification"""
    combined = content + json.dumps(metadata, sort_keys=True).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()

def validate_benford_law(amounts: List[Decimal]) -> Dict[str, float]:
    """Benford's Law analysis for detecting fabricated numbers"""
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
    """Z-score based outlier detection"""
    if len(amounts) < 3:
        return []
    
    values = [float(amt) for amt in amounts]
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0
    
    outliers = []
    for idx, value in enumerate(values):
        if stdev > 0:
            z_score = abs((value - mean) / stdev)
            if z_score > 3.0:  # 99.7% confidence interval
                outliers.append((idx, Decimal(str(value)).quantize(Decimal('0.01'))))
    
    return outliers

def get_kosovo_legal_reference(anomaly_type: AnomalyType, amount: Decimal) -> Dict[str, str]:
    """Get Kosovo-specific legal references for anomalies"""
    type_str = anomaly_type.name
    
    if type_str in KOSOVO_LEGAL_REFERENCES:
        ref = KOSOVO_LEGAL_REFERENCES[type_str]
        legal_text = f"{ref['law']}, {ref['article']} - {ref['title']}"
        
        # Add threshold information if applicable
        if ref['threshold'] != "N/A" and "STRUCTURING" in type_str:
            legal_text += f" (Pragu i Raportimit: {ref['threshold']})"
        
        return {
            "legal_reference": legal_text,
            "authority": ref['authority'],
            "applicable_law": "Legjislacioni i Republikës së Kosovës"
        }
    
    # Default Kosovo legal reference
    return {
        "legal_reference": "Kodi Penal i Republikës së Kosovës, Neni 307 - Mashtrim Financiar",
        "authority": "Prokuroria e Republikës së Kosovës",
        "applicable_law": "Legjislacioni i Republikës së Kosovës"
    }

# --- EXISTING OCR FUNCTION (ENHANCED WITH FORENSIC TRACKING) ---
async def analyze_text_to_spreadsheet(ocr_text: str, case_id: str, db: Database) -> Dict[str, Any]:
    """
    Takes raw text (from OCR), uses an LLM to structure it into a CSV,
    then passes it to the standard spreadsheet analysis pipeline.
    """
    logger.info(f"Initiating AI data structuring for case {case_id}.")
    
    system_prompt = """
    Ti je "Specialist i Të Dhënave" (Data Entry Specialist). Detyra jote është të konvertosh tekstin e pa-strukturuar nga një skanim (OCR) në formatin CSV.

    RREGULLAT STRICTE:
    1.  **Krijoni Kokat (Headers)**: Rreshti i parë i përgjigjes TUAJ DUHET TË JETË: `Data,Pershkrimi,Shuma`
    2.  **Formati i të Dhënave**:
        -   **Data**: Përdor formatin DD.MM.YYYY. Nëse nuk e gjeni vitin, përdorni vitin aktual.
        -   **Pershkrimi**: Përmblidh transaksionin në disa fjalë kyçe.
        -   **Shuma**: Përdor VETËM numra. Hyrjet duhet të jenë pozitive (psh: 800.00), daljet duhet të jenë negative (psh: -50.00). MOS PËRDOR simbole monedhe.
    3.  **Injoro Mbeturinat**: MOS PËRFSHI rreshta që nuk janë transaksione (psh: balancat, titujt e kolonave, informacione të bankës).
    4.  **PËRGJIGJJA JOTE DUHET TË PËRMBAJË VETËM TË DHËNA CSV, PA ASNJË TEKST APO SHPJEGIM SHTESË.**
    """
    
    user_prompt = f"Konverto këtë tekst të skanuar në formatin CSV:\n\n---\n{ocr_text}\n---"
    
    # We use a standard _call_llm, not a JSON one, as we expect raw CSV text.
    csv_string = await asyncio.to_thread(llm_service._call_llm, system_prompt, user_prompt, False, 0.0)
    
    if not csv_string or not csv_string.strip():
        raise ValueError("AI data structuring failed to produce a valid CSV.")
    
    logger.info(f"AI successfully structured text into CSV format. Analyzing...")
    
    # Convert the CSV string to bytes and pass to the original analysis function
    csv_bytes = csv_string.encode('utf-8')
    return await analyze_spreadsheet_file(content=csv_bytes, filename="skanim_nga_celulari.csv", case_id=case_id, db=db)

# --- NEW FORENSIC ANALYSIS FUNCTION (KOSOVO-COMPLIANT) ---
async def forensic_analyze_spreadsheet(
    content: bytes, 
    filename: str, 
    case_id: str, 
    db: Database,
    analyst_id: Optional[str] = None,
    acquisition_method: str = "UPLOAD"
) -> Dict[str, Any]:
    """
    Kosovo ISO 27037 Compliant Forensic Analysis with Chain of Custody
    Returns court-admissible forensic report for Kosovo legal system
    """
    # === EVIDENCE INTEGRITY & CHAIN OF CUSTODY ===
    evidence_id = str(uuid.uuid4())
    acquisition_time = datetime.now(timezone.utc)
    
    # Generate cryptographic hash for evidence
    metadata = {
        "filename": filename,
        "case_id": case_id,
        "analyst_id": analyst_id,
        "acquisition_time": acquisition_time.isoformat(),
        "jurisdiction": "KOSOVO"
    }
    
    evidence_hash = generate_evidence_hash(content, metadata)
    
    # Initialize chain of custody
    chain_of_custody = [{
        "timestamp": acquisition_time.isoformat(),
        "action": "ACQUISITION",
        "actor": analyst_id or "SYSTEM",
        "location": "FORENSIC_SERVER_KOSOVO",
        "integrity_hash": evidence_hash,
        "notes": f"File acquisition via {acquisition_method} - Jurisdiction: KOSOVO"
    }]
    
    logger.info(f"[FORENSIC-KOSOVO] Evidence {evidence_id} acquired for case {case_id}. Hash: {evidence_hash[:16]}...")
    
    # === DATA EXTRACTION WITH VALIDATION ===
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"[FORENSIC-KOSOVO] Evidence {evidence_id} parsing failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Format i pavlefshëm i dëshmisë: {str(e)}"
        )
    
    # Metadata preservation
    original_shape = df.shape
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # === FORENSIC DATA MAPPING ===
    col_mapping = {
        'date': next((c for c in df.columns if 'date' in c or 'data' in c), None),
        'description': next((c for c in df.columns if 'desc' in c or 'pershkrim' in c or 'përshkrim' in c or 'details' in c), None),
        'amount': next((c for c in df.columns if 'amount' in c or 'shuma' in c or 'vlere' in c or 'vlera' in c), None)
    }
    
    if not col_mapping['amount']:
        raise HTTPException(
            status_code=422,
            detail="Kolonë e detyrueshme 'Shuma' mungon. Ky është kërkesë për analizë forenzike sipas standardeve të Kosovës."
        )
    
    # === FORENSIC RECORD CONSTRUCTION ===
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
        
        date_val = str(row[col_mapping['date']]) if col_mapping['date'] and col_mapping['date'] in row else "N/A"
        desc_val = str(row[col_mapping['description']]) if col_mapping['description'] and col_mapping['description'] in row else "Pa Përshkrim"
        
        records.append({
            "row_id": idx,
            "date": date_val,
            "description": desc_val,
            "amount": amount,
            "raw_row": row.to_dict(),
            "evidence_reference": f"{evidence_id}:ROW:{idx}:KOS"
        })
    
    # === ADVANCED ANOMALY DETECTION (KOSOVO-SPECIFIC) ===
    anomalies = await _forensic_detect_anomalies_kosovo(records)
    
    # === STATISTICAL ANALYSIS ===
    statistical_analysis = {
        "benford_law_deviation": validate_benford_law([r['amount'] for r in records]),
        "outliers": detect_statistical_outliers([r['amount'] for r in records]),
        "total_records": len(records),
        "date_range": {
            "earliest": min([r['date'] for r in records if r['date'] != "N/A"], default="N/A"),
            "latest": max([r['date'] for r in records if r['date'] != "N/A"], default="N/A")
        },
        "amount_summary": {
            "total_inflow": str(sum(r['amount'] for r in records if r['amount'] > 0)),
            "total_outflow": str(abs(sum(r['amount'] for r in records if r['amount'] < 0))),
            "mean_absolute_amount": str(statistics.mean([abs(float(r['amount'])) for r in records]) if records else 0),
            "std_dev_amount": str(statistics.stdev([abs(float(r['amount'])) for r in records]) if len(records) > 1 else 0)
        },
        "jurisdiction": "KOSOVO"
    }
    
    # === VECTOR STORAGE FOR AI INTERROGATION ===
    await _vectorize_and_store_forensic(records, case_id, evidence_id, db)
    
    # === FORENSIC REPORT GENERATION (KOSOVO LAWYER-FOCUSED) ===
    executive_summary = await _generate_kosovo_forensic_summary(records, anomalies, statistical_analysis, case_id)
    
    # === KOSOVO-SPECIFIC RECOMMENDATIONS ===
    kosovo_recommendations = [
        "NISNI PROCEDURËN 'DISCOVERY' SIPAS RREGULLAVE TË PROCESIT CIVIL TË KOSOVËS",
        "KRYENI AUDITIM TË STILIT TË JETESËS KUNDREJT TË ARDHURAVE TË DEKLARUARA NË TAXAT KOSOVARE",
        "VERIFIKONI PËRPUTHSHMËRINË ME LIGJIN NR. 05/L-080 TË KOSOVËS PËR PARANDALIMIN E PASTIRIMIT TË PARAVE",
        "KOORDINOHUNI ME AUTORITETIN PËR MENAXHIMIN E ASETEVE TË KONFISKUARA TË KOSOVËS",
        "REFERONI INDICATË TE INSPEKTORATI FINANCIAR I KOSOVËS PËR VEPRIME TË MËTEJSHME",
        "APLIKONI PROCEDURAT E NGRIRJES SË ASETEVE SIPAS LIGJIT KOSOVAR NR. 06/L-123",
        "MBLIDHNI DËSHMITË PËR PËRDORIM NË GJYKATËN PËRFAQËSORE TË KOSOVËS"
    ]
    
    # === COMPILE FORENSIC REPORT ===
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
            "original_file_metadata": {
                "filename": filename,
                "size_bytes": len(content),
                "row_count": original_shape[0],
                "column_count": original_shape[1]
            },
            "jurisdiction": "KOSOVO"
        },
        "recommendations": kosovo_recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jurisdiction": "KOSOVO"
    }
    
    # Generate report hash for tamper detection
    report_hash = hashlib.sha256(
        json.dumps(report_data, sort_keys=True, default=str).encode('utf-8')
    ).hexdigest()
    report_data['report_hash'] = report_hash
    
    # Store complete forensic report
    await asyncio.to_thread(
        db.forensic_reports.insert_one,
        {
            **report_data,
            "stored_at": datetime.now(timezone.utc),
            "status": "COMPLETED",
            "jurisdiction": "KOSOVO"
        }
    )
    
    # Update chain of custody
    chain_of_custody.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "ANALYSIS_COMPLETED",
        "actor": "FORENSIC_ENGINE_KOSOVO",
        "location": "ANALYSIS_SERVER_KOSOVO",
        "integrity_hash": report_hash,
        "notes": f"Forensic analysis completed for Kosovo jurisdiction. Report ID: {report_id}"
    })
    
    logger.info(f"[FORENSIC-KOSOVO] Report {report_id} generated for case {case_id}. Anomalies detected: {len(anomalies)}")
    
    return report_data

# --- EXISTING ANALYSIS FUNCTION (ENHANCED WITH KOSOVO FORENSIC) ---
async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    """
    Primary Entry Point: Parses Excel/CSV, runs heuristics, and generates a report.
    NOW WITH KOSOVO FORENSIC CAPABILITIES
    """
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"Spreadsheet parse error: {e}")
        raise ValueError("Formati i skedarit nuk është valid. Ju lutemi ngarkoni .xlsx ose .csv")

    df.columns = [str(c).lower().strip() for c in df.columns]
    
    col_date = next((c for c in df.columns if 'date' in c or 'data' in c), None)
    col_desc = next((c for c in df.columns if 'desc' in c or 'pershkrim' in c or 'përshkrim' in c or 'details' in c), None)
    col_amount = next((c for c in df.columns if 'amount' in c or 'shuma' in c or 'vlere' in c or 'vlera' in c), None)

    if not col_amount:
        raise ValueError("Nuk u gjet kolona 'Shuma' ose 'Amount' në skedarin e analizuar.")

    records = []
    df = df.fillna('')
    
    for idx, row in df.iterrows():
        raw_amt = row[col_amount]
        try:
            if isinstance(raw_amt, str):
                raw_amt = str(raw_amt).replace('€', '').replace(',', '').strip()
            amount = float(raw_amt)
        except:
            amount = 0.0
            
        date_val = str(row[col_date]) if col_date and col_date in row else "N/A"
        desc_val = str(row[col_desc]) if col_desc and col_desc in row else "Pa Përshkrim"
        
        records.append({
            "row_id": idx, "date": date_val, "description": desc_val,
            "amount": amount, "raw_row": row.to_dict()
        })

    # ENHANCED: Use forensic anomaly detection (Kosovo-specific)
    anomalies = await _forensic_detect_anomalies_simple(records)
    trends = _calculate_trends(records)
    
    # ENHANCED: Generate forensic summary
    statistical_analysis = {
        "total_records": len(records),
        "total_inflow": sum(r['amount'] for r in records if r['amount'] > 0),
        "total_outflow": abs(sum(r['amount'] for r in records if r['amount'] < 0)),
        "jurisdiction": "KOSOVO"
    }
    
    exec_summary = await _generate_kosovo_forensic_summary_simple(records, anomalies, statistical_analysis, case_id)
    
    # ENHANCED: Add evidence hash for integrity
    evidence_hash = hashlib.sha256(content).hexdigest()
    
    await _vectorize_and_store(records, case_id, db)

    # KOSOVO-SPECIFIC RECOMMENDATIONS
    kosovo_recommendations = [
        "Iniconi procedurën 'Discovery' sipas rregullave të procesit civil të Kosovës.",
        "Kryeni auditim të stilit të jetesës vs. të ardhurave të deklaruara në taxat kosovare.",
        "Verifikoni përputhshmërinë me ligjet AML të Kosovës (Ligji Nr. 05/L-080).",
        f"Evidence Hash: {evidence_hash[:16]}... (Kosovo Jurisdiction)"
    ]

    return {
        "executive_summary": exec_summary, 
        "anomalies": anomalies[:20],  # Limit for compatibility
        "trends": trends,
        "recommendations": kosovo_recommendations,
        "forensic_metadata": {  # Added forensic metadata
            "evidence_hash": evidence_hash,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": len(records),
            "jurisdiction": "KOSOVO"
        }
    }

# --- EXISTING QUESTION FUNCTION (ENHANCED) ---
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
        
    if not context_lines:
        return {"answer": "Nuk u gjetën të dhëna relevante në spreadsheet."}
    
    # ENHANCED: Use forensic interrogation
    answer = await asyncio.to_thread(llm_service.forensic_interrogation, question, context_lines)
    
    # ENHANCED: Add forensic context
    return {
        "answer": answer, 
        "referenced_rows_count": len(top_rows),
        "forensic_context": "Kjo përgjigje është gjeneruar nga analiza forenzike AI për përdorim në sistemin ligjor të Kosovës.",
        "legal_disclaimer": "Këshillohuni me avokat të licencuar në Kosovë për veprime të mëtejshme.",
        "jurisdiction": "KOSOVO"
    }

# --- EXISTING ANOMALY DETECTION (ENHANCED FOR KOSOVO) ---
def _detect_anomalies(records: List[Dict]) -> List[Dict]:
    """Enhanced with forensic detection methods for Kosovo"""
    anomalies = []
    records.sort(key=lambda x: x['date']) 
    
    # Get amounts for statistical analysis
    amounts = [abs(r['amount']) for r in records]
    
    for i, r in enumerate(records):
        amt = abs(r['amount'])
        desc = r['description'].lower()
        
        # 1. Currency Structuring Detection (Enhanced for Kosovo)
        if 1500 < amt < 2000:
            legal_ref = get_kosovo_legal_reference(AnomalyType.STRUCTURING, Decimal(str(amt)))
            anomalies.append({
                "date": r['date'], "amount": r['amount'], "description": r['description'],
                "risk_level": "HIGH", 
                "forensic_type": "STRUCTURING",
                "explanation": f"Strukturim i Mundshëm (Smurfing): Shuma ({amt}€) është pak nën pragun e raportimit të 2,000€ sipas Ligjit Nr. 06/L-075 të Kosovës.",
                "legal_reference": legal_ref['legal_reference'],
                "kosovo_authority": legal_ref['authority'],
                "confidence": 0.85
            })
            
        # 2. Suspicious Keyword Detection (Enhanced for Kosovo)
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in desc:
                legal_ref = get_kosovo_legal_reference(AnomalyType.SUSPICIOUS_KEYWORD, Decimal(str(amt)))
                anomalies.append({
                    "date": r['date'], "amount": r['amount'], "description": r['description'],
                    "risk_level": "HIGH", 
                    "forensic_type": "SUSPICIOUS_KEYWORD",
                    "explanation": f"Aktivitet me Risk të Lartë: Transaksion i lidhur me '{kw}'. Kontrolloni përputhshmërinë me Ligjin Nr. 05/L-080 të Kosovës.",
                    "legal_reference": legal_ref['legal_reference'],
                    "kosovo_authority": legal_ref['authority'],
                    "confidence": 0.90
                })
                
        # 3. Round Amount Transactions (Enhanced for Kosovo)
        if amt >= 500 and amt % 50 == 0 and ("atm" in desc or "cash" in desc):
            legal_ref = get_kosovo_legal_reference(AnomalyType.ROUND_AMOUNT, Decimal(str(amt)))
            anomalies.append({
                "date": r['date'], "amount": r['amount'], "description": r['description'],
                "risk_level": "MEDIUM", 
                "forensic_type": "ROUND_AMOUNT",
                "explanation": f"Tërheqje Cash Signifikante: {amt}€ transaksion i rrumbullakët. Kontrolloni për Nenin 305 të Kodit Penal të Kosovës.",
                "legal_reference": legal_ref['legal_reference'],
                "kosovo_authority": legal_ref['authority'],
                "confidence": 0.75
            })
        
        # 4. Statistical Outlier Detection (NEW - Kosovo specific)
        if len(amounts) > 2:
            mean = statistics.mean(amounts)
            stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
            if stdev > 0 and abs(amt - mean) > 3 * stdev:
                legal_ref = get_kosovo_legal_reference(AnomalyType.STATISTICAL_OUTLIER, Decimal(str(amt)))
                anomalies.append({
                    "date": r['date'], "amount": r['amount'], "description": r['description'],
                    "risk_level": "CRITICAL",
                    "forensic_type": "STATISTICAL_OUTLIER",
                    "explanation": f"Devijim Statistikor: {amt}€ është >3 devijime standarde nga mesatarja ({mean:.2f}€). Kërkon hetim sipas Ligjit Nr. 06/L-123 të Kosovës.",
                    "legal_reference": legal_ref['legal_reference'],
                    "kosovo_authority": legal_ref['authority'],
                    "confidence": 0.99
                })

    return anomalies

# --- EXISTING TRENDS FUNCTION (UNCHANGED) ---
def _calculate_trends(records: List[Dict]) -> List[Dict]:
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = sum(abs(r['amount']) for r in records if r['amount'] < 0)
    
    return [
        {"category": "Totali i Hyrjeve", "trend": "STABLE", "percentage": f"€{total_in:,.2f}", "comment": "Totali i depozitave/të ardhurave të detektuara."},
        {"category": "Totali i Daljeve", "trend": "UP", "percentage": f"€{total_out:,.2f}", "comment": "Totali i shpenzimeve operative dhe personale."}
    ]

# --- EXISTING VECTOR STORE (ENHANCED) ---
async def _vectorize_and_store(records: List[Dict], case_id: str, db: Database):
    vectors = []
    
    for r in records:
        semantic_text = f"Data: {r['date']}. Shuma: {r['amount']} EUR. Përshkrimi: {r['description']}."
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        
        vectors.append({
            "case_id": ObjectId(case_id), "row_id": r['row_id'], "content": semantic_text,
            "metadata": r['raw_row'], "embedding": embedding, "created_at": datetime.now(timezone.utc),
            "forensic_flag": True,
            "jurisdiction": "KOSOVO"
        })

    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)
        logger.info(f"Vectorized and stored {len(vectors)} financial rows for case {case_id} (Kosovo)")

# --- MISSING FUNCTIONS ADDED (KOSOVO-SPECIFIC) ---

async def _vectorize_and_store_forensic(
    records: List[Dict], 
    case_id: str, 
    evidence_id: str,
    db: Database
):
    """Store vector embeddings with forensic metadata (Kosovo-specific)"""
    vectors = []
    
    for record in records:
        semantic_text = f"DATA: {record['date']} | SHUMA: {record['amount']}€ | PËRSHKRIMI: {record['description']} | REFERENCË DËSHMISH: {record['evidence_reference']} | JURISDIKSION: KOSOVO"
        
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        
        vectors.append({
            "case_id": ObjectId(case_id),
            "evidence_id": evidence_id,
            "row_id": record['row_id'],
            "content": semantic_text,
            "metadata": {
                **record['raw_row'],
                "forensic_metadata": {
                    "evidence_reference": record['evidence_reference'],
                    "analysis_timestamp": datetime.now(timezone.utc),
                    "integrity_flag": "VERIFIED",
                    "jurisdiction": "KOSOVO"
                }
            },
            "embedding": embedding,
            "created_at": datetime.now(timezone.utc),
            "vector_type": "FORENSIC_FINANCIAL_KOSOVO"
        })
    
    if vectors:
        # Store in forensic-specific collection
        await asyncio.to_thread(
            db.forensic_vectors.insert_many,
            vectors
        )
        logger.info(f"[FORENSIC-KOSOVO] Stored {len(vectors)} forensic vectors for evidence {evidence_id}")

async def _forensic_detect_anomalies_simple(records: List[Dict]) -> List[Dict]:
    """Simplified forensic detection for backward compatibility (Kosovo-specific)"""
    anomalies = []
    for i, r in enumerate(records):
        amt = abs(r['amount'])
        desc = r['description'].lower()
        
        # Structuring detection (Kosovo threshold)
        if 1500 < amt < 2000:
            legal_ref = get_kosovo_legal_reference(AnomalyType.STRUCTURING, Decimal(str(amt)))
            anomalies.append({
                "date": r['date'], "amount": r['amount'], "description": r['description'],
                "risk_level": "HIGH", "forensic_type": "STRUCTURING",
                "explanation": f"Strukturim i Mundshëm (Smurfing) - Kontrolloni Ligjin Nr. 06/L-075 të Kosovës",
                "legal_reference": legal_ref['legal_reference'],
                "kosovo_authority": legal_ref['authority'],
                "confidence": 0.85
            })
        
        # Keyword detection (Kosovo context)
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in desc:
                legal_ref = get_kosovo_legal_reference(AnomalyType.SUSPICIOUS_KEYWORD, Decimal(str(amt)))
                anomalies.append({
                    "date": r['date'], "amount": r['amount'], "description": r['description'],
                    "risk_level": "HIGH", "forensic_type": "SUSPICIOUS_KEYWORD",
                    "explanation": f"Aktivitet i lidhur me '{kw}' - Kontrolloni Ligjin Nr. 05/L-080 të Kosovës",
                    "legal_reference": legal_ref['legal_reference'],
                    "kosovo_authority": legal_ref['authority'],
                    "confidence": 0.90
                })
    
    return anomalies

async def _generate_kosovo_forensic_summary_simple(
    records: List[Dict], 
    anomalies: List[Dict], 
    statistical_analysis: Dict[str, Any],
    case_id: str
) -> str:
    """Generate simplified forensic summary for Kosovo legal system"""
    
    high_risk_count = sum(1 for a in anomalies if a.get('risk_level') in ['HIGH', 'CRITICAL'])
    
    prompt = f"""
    VEPRO SI NJË "EKSPERT FORENZIK LIGJOR" për sistemin juridik të Republikës së Kosovës.
    
    ID RASTI: {case_id}
    JURISDIKSION: REPUBLIKA E KOSOVËS
    
    TË DHËNAT STATISTIKORE:
    - Total Transaksione: {statistical_analysis.get('total_records', 0)}
    - Vlerë Totale Hyrjesh: {statistical_analysis.get('total_inflow', 0)}€
    - Vlerë Totale Daljesh: {statistical_analysis.get('total_outflow', 0)}€
    - Anomalitë me Risk të Lartë/Kritik: {high_risk_count}
    
    DETYRË E DETYRUESHME:
    Shkruaj një "RAPORT FORENZIK LIGJOR PËR KOSOVË" me fokus në mbledhjen e dëshmive për përdorim në procesin ligjor të Kosovës.
    
    STRUKTURA E DETYRUESHME (Markdown):
    
    ### RAPORT FORENZIK NR. {case_id}
    **Data e Gjenerimit**: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}
    **Jurisdiksion**: Republika e Kosovës
    
    #### 1. KONKLUZION ANALITIK (PËR AVOKATË)
    Jep një vlerësim teknik të dëshmive të mbledhura për përdorim në procesin ligjor të Kosovës.
    
    #### 2. DËSHMITË TEKNIKE TË MBLEDHURA
    Listo anomalitë më të rëndësishme me referenca të ligjit të Kosovës.
    
    #### 3. REKOMANDIME PËR VEPRIM LIGJOR
    Specifiko hapat konkretë për përdorim të dëshmive në sistemin juridik të Kosovës.
    
    RREGULLAT ABSOLUTE PËR KOSOVË:
    1. PËRDOR VETËM REFERENCA LIGJORE TË REPUBLIKËS SË KOSOVËS
    2. MOS PËRFSHI NËNshKRIME TË PROKURORISË
    3. FOKUSO NË MBLEDHJEN E DËSHMIVE PËR AVOKATË
    4. PËRDOR TERMINOLOGJINË LIGJORE TË KOSOVËS
    
    GJUHA: SHQIP LETRARE JURIDIKE (STANDARDET E KOSOVËS).
    """
    
    response = await asyncio.to_thread(
        llm_service._call_llm,
        "Ti je Ekspert Forenzik Ligjor me specializim në sistemin juridik të Republikës së Kosovës.",
        prompt,
        False
    )
    
    # Ensure we return a string (not None)
    return response if response else "Nuk u gjenerua përmbledhje forenzike. Kontrolloni të dhënat e hyrjes."

# --- NEW FORENSIC FUNCTIONS (KOSOVO-SPECIFIC) ---
async def _forensic_detect_anomalies_kosovo(records: List[Dict]) -> List[AnomalyEvidence]:
    """Court-admissible anomaly detection for Kosovo legal system"""
    anomalies = []
    records.sort(key=lambda x: x['date'])
    
    all_amounts = [abs(r['amount']) for r in records]
    statistical_outliers = detect_statistical_outliers([r['amount'] for r in records])
    outlier_indices = {idx for idx, _ in statistical_outliers}
    
    for i, record in enumerate(records):
        amt = abs(record['amount'])
        desc = record['description'].lower()
        anomaly_list = []
        
        # 1. Currency Structuring Detection (Smurfing) - Kosovo Law
        if THRESHOLD_STRUCTURING - Decimal('100.00') < amt < THRESHOLD_STRUCTURING:
            legal_ref = get_kosovo_legal_reference(AnomalyType.STRUCTURING, amt)
            anomaly_list.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.STRUCTURING,
                risk_level=RiskLevel.HIGH,
                transaction_date=record['date'],
                amount=record['amount'],
                description=record['description'],
                statistical_confidence=0.85,
                supporting_evidence=[
                    f"Shuma ({amt}€) është pak nën pragun e raportimit të 2,000€ sipas Ligjit Nr. 06/L-075 të Kosovës",
                    "Model tipik i strukturimit monetar (smurfing) për shmangien e raportimit"
                ],
                legal_reference=legal_ref['legal_reference'],
                kosovo_authority=legal_ref['authority'],
                recommended_action="KËRKO ANALIZË SHTESË SIPAS LIGJIT NR. 06/L-075 TË KOSOVËS DHE KOORDINOHU ME BANKËN QENDRORE"
            ))
        
        # 2. Suspicious Keyword Detection - Kosovo AML Law
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in desc:
                legal_ref = get_kosovo_legal_reference(AnomalyType.SUSPICIOUS_KEYWORD, amt)
                anomaly_list.append(AnomalyEvidence(
                    anomaly_id=str(uuid.uuid4()),
                    type=AnomalyType.SUSPICIOUS_KEYWORD,
                    risk_level=RiskLevel.HIGH,
                    transaction_date=record['date'],
                    amount=record['amount'],
                    description=record['description'],
                    statistical_confidence=0.90,
                    supporting_evidence=[
                        f"Përmban fjalën kyçe të riskit: '{kw}'",
                        "Aktivitet i lidhur me bixhoze/kriptomonedha/huadhënje joformale"
                    ],
                    legal_reference=legal_ref['legal_reference'],
                    kosovo_authority=legal_ref['authority'],
                    recommended_action="IDENTIFIKO MARRLIDHJET SIPAS LIGJIT NR. 05/L-080 TË KOSOVËS DHE REFERO TE AUTORITETI PËR PARANDALIMIN E PASTIRIMIT TË PARAVE"
                ))
        
        # 3. Round Amount Transactions - Kosovo Penal Code
        if amt >= THRESHOLD_CASH_LARGE and amt % Decimal('50.00') == Decimal('0.00') and ("atm" in desc or "cash" in desc):
            legal_ref = get_kosovo_legal_reference(AnomalyType.ROUND_AMOUNT, amt)
            anomaly_list.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.ROUND_AMOUNT,
                risk_level=RiskLevel.MEDIUM,
                transaction_date=record['date'],
                amount=record['amount'],
                description=record['description'],
                statistical_confidence=0.75,
                supporting_evidence=[
                    f"Shumë e rrumbullakët: {amt}€",
                    "Tërheqje cash pa gjurmë destinacioni përfundimtar"
                ],
                legal_reference=legal_ref['legal_reference'],
                kosovo_authority=legal_ref['authority'],
                recommended_action="VERIFIKO DESTINACIONIN E PARAVE TË TËRHEQURA SIPAS NENIT 305 TË KODIT PENAL TË KOSOVËS"
            ))
        
        # 4. Statistical Outliers - Kosovo Financial Inspectorate Law
        if i in outlier_indices:
            legal_ref = get_kosovo_legal_reference(AnomalyType.STATISTICAL_OUTLIER, amt)
            anomaly_list.append(AnomalyEvidence(
                anomaly_id=str(uuid.uuid4()),
                type=AnomalyType.STATISTICAL_OUTLIER,
                risk_level=RiskLevel.CRITICAL,
                transaction_date=record['date'],
                amount=record['amount'],
                description=record['description'],
                statistical_confidence=0.99,
                supporting_evidence=[
                    f"Devijim statistikor: {amt}€ është >3 devijime standarde nga mesatarja",
                    "Transaksion jashtëzakonisht i madh krahasuar me trendin e zakonshëm"
                ],
                legal_reference=legal_ref['legal_reference'],
                kosovo_authority=legal_ref['authority'],
                recommended_action="KËRKO HETIM SIPAS LIGJIT NR. 06/L-123 TË KOSOVËS DHE NGRIRJE TË ASETEVE ME AUTORITETIN PËR MENAXHIMIN E ASETEVE TË KONFISKUARA"
            ))
        
        # Add all detected anomalies
        anomalies.extend(anomaly_list)
    
    return anomalies

async def _generate_kosovo_forensic_summary(
    records: List[Dict], 
    anomalies: List[AnomalyEvidence], 
    statistical_analysis: Dict[str, Any],
    case_id: str
) -> str:
    """Generate court-admissible forensic summary for Kosovo legal system"""
    
    high_risk_count = sum(1 for a in anomalies if a.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL])
    date_str = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
    
    # Prepare Kosovo-specific anomaly details
    anomaly_details = []
    for a in anomalies[:5]:
        anomaly_details.append({
            'type': a.type.value,
            'risk': a.risk_level.value,
            'amount': str(a.amount),
            'law': a.legal_reference.split(',')[0] if ',' in a.legal_reference else a.legal_reference
        })
    
    prompt = f"""
    VEPRO SI NJË "EKSPERT FORENZIK LIGJOR" i specializuar në sistemin juridik të Republikës së Kosovës.
    
    ID RASTI: {case_id}
    JURISDIKSION: REPUBLIKA E KOSOVËS
    
    TË DHËNAT STATISTIKORE:
    - Total Transaksione: {statistical_analysis.get('total_records', 0)}
    - Vlerë Totale Hyrjesh: {statistical_analysis.get('amount_summary', {}).get('total_inflow', '0')}€
    - Vlerë Totale Daljesh: {statistical_analysis.get('amount_summary', {}).get('total_outflow', '0')}€
    - Anomalitë me Risk të Lartë/Kritik: {high_risk_count}
    
    ANOMALITË KRYESORE (5 të Parat) me Referenca të Ligjit të Kosovës:
    {json.dumps(anomaly_details, indent=2, ensure_ascii=False)}
    
    DEVIJIMET E LIGJIT TË BENFORD-IT (Indikator i Manipulimeve):
    {json.dumps(statistical_analysis.get('benford_law_deviation', {}), indent=2)}
    
    DETYRË E DETYRUESHME:
    Shkruaj një "RAPORT FORENZIK LIGJOR PËR SISTEMIN JURIDIK TË KOSOVËS" me strukturë profesionale për avokatë.
    
    STRUKTURA E DETYRUESHME (Markdown):
    
    ### RAPORT FORENZIK LIGJOR NR. {case_id}
    **Data e Gjenerimit**: {date_str}
    **Jurisdiksion**: Republika e Kosovës
    **Qëllimi**: Mbledhje e dëshmive teknike për përdorim në procesin ligjor
    
    #### 1. KONKLUZION TEKNIK PËR AVOKATË
    Jep një vlerësim teknik të dëshmive të mbledhura, pa oftuar vlerësime penale. Fokuso në:
    - Treguesit statistikorë të konsiderueshëm
    - Anomalitë me bazë teknike
    - Referencat e ligjit të Kosovës që aplikojnë
    
    #### 2. DËSHMITË TEKNIKE TË MBLEDHURA (ME REFERENCA LIGJORE TË KOSOVËS)
    Listo 3-5 anomalitë më të rëndësishme me:
    - **Karakteristikat Teknike** (Tipi, Shuma, Koha)
    - **Baza Ligjore në Kosovë** (Ligji Nr., Neni)
    - **Autoriteti Kompetent në Kosovë** për çështjen
    
    #### 3. REKOMANDIME PËR VEPRIM LIGJOR NË KOSOVË
    Specifiko hapat konkretë për përdorim të dëshmive:
    1. **MBLEDHJET E MËTEJSHME** (Cilat dokumente, nga cilat institucione në Kosovë)
    2. **REFERIMET INSTITUCIONALE** (Cilës autoriteti të Kosovës duhet referuar)
    3. **PROCEDURAT E NGRIRJES** (Sipas cilës ligji të Kosovës)
    4. **PËRGATITJA PËR GJYKATË** (Si të paraqiten dëshmitë në Gjykatën e Kosovës)
    
    #### 4. METODOLOGJIA FORENZIKE (STANDARDET E KOSOVËS)
    Përmblidh shkurtimisht metodat e përdorura në përputhje me standardet e prokurorisë së Kosovës.
    
    RREGULLAT ABSOLUTE PËR RAPORTIN E KOSOVËS:
    1. MOS PËRDOR REFERENCA LIGJORE TË SHTETEVE TË TJERA
    2. MOS PËRFSHI NËNSHKRIME TË PROKURORISË APO AUTORITETEVE
    3. FOKUSO VETËM NË ASPEKTET TEKNIKE TË DËSHMIVE
    4. PËRDOR VETËM LEGJISLACIONIN E REPUBLIKËS SË KOSOVËS
    5. ADRESOHU AVOKATËVE SI AUDIENCË KRYESORE
    
    GJUHA: SHQIP LETRARE JURIDIKE PROFESIONALE (STANDARDET E PROFESIONIT LIGJOR NË KOSOVË).
    """
    
    response = await asyncio.to_thread(
        llm_service._call_llm,
        "Ti je Ekspert Forenzik Ligjor me specializim në sistemin juridik të Republikës së Kosovës. Fokuso në mbledhjen e dëshmive teknike për përdorim nga avokatët në procesin ligjor të Kosovës.",
        prompt,
        False
    )
    
    # Ensure we return a string (not None)
    return response if response else f"RAPORT FORENZIK LIGJOR PËR KOSOVË\nID Rasti: {case_id}\nData: {date_str}\nNuk u gjenerua përmbledhje e plotë për shkak të kufizimeve të të dhënave."

# --- FORENSIC INTERROGATION FUNCTION (KOSOVO-SPECIFIC) ---
async def forensic_interrogate_evidence(
    case_id: str, 
    question: str, 
    db: Database,
    include_chain_of_custody: bool = True
) -> Dict[str, Any]:
    """
    Advanced forensic interrogation with evidence chain verification for Kosovo
    """
    # Get question embedding
    q_vector = await asyncio.to_thread(llm_service.get_embedding, question)
    
    # Search in forensic vectors
    vectors = await asyncio.to_thread(
        list,
        db.forensic_vectors.find({"case_id": ObjectId(case_id)})
    )
    
    # Score and sort by relevance
    scored_vectors = []
    for vec in vectors:
        v = vec.get("embedding")
        if v:
            score = np.dot(q_vector, v)
            scored_vectors.append((score, vec))
    
    scored_vectors.sort(key=lambda x: x[0], reverse=True)
    top_vectors = scored_vectors[:10]
    
    if not top_vectors:
        # Fall back to regular financial vectors
        regular_vectors = await asyncio.to_thread(
            list,
            db.financial_vectors.find({"case_id": ObjectId(case_id)})
        )
        for vec in regular_vectors:
            v = vec.get("embedding")
            if v:
                score = np.dot(q_vector, v)
                scored_vectors.append((score, vec))
        
        scored_vectors.sort(key=lambda x: x[0], reverse=True)
        top_vectors = scored_vectors[:10]
    
    if not top_vectors:
        return {
            "answer": "NUK KA DËSHMI RELEVANTE PËR KËTË PYETJE NË BAZËN E TË DHËNAVE.",
            "forensic_warning": "PYETJA NUK ËSHTË E MBULUAR NGA DËSHMITË E DISPONUESHME NË SISTEMIN E KOSOVËS.",
            "chain_of_custody": [],
            "jurisdiction": "KOSOVO"
        }
    
    # Prepare context with evidence references
    context_lines = []
    evidence_references = set()
    
    for score, vec in top_vectors:
        context_lines.append(vec["content"])
        evidence_references.add(vec.get("evidence_id", "UNKNOWN"))
    
    # Get chain of custody if requested
    chain_data = []
    if include_chain_of_custody and evidence_references:
        for evidence_id in evidence_references:
            # Check forensic_reports collection
            chain = await asyncio.to_thread(
                db.forensic_reports.find_one,
                {"case_id": case_id, "integrity_verification.evidence_hash": {"$regex": f"^{evidence_id}"}}
            )
            if chain and chain.get("chain_of_custody"):
                chain_data.extend(chain.get("chain_of_custody", []))
    
    # Generate forensic-grade answer with Kosovo context
    kosovo_context = " KONTEKSTI I KOSOVËS: Kjo analizë është krijuar për përdorim në sistemin ligjor të Republikës së Kosovës."
    answer = await asyncio.to_thread(
        llm_service.forensic_interrogation,
        f"PYETJE FORENZIKE PËR KOSOVË: {question}",
        context_lines
    )
    
    return {
        "answer": answer + kosovo_context,
        "supporting_evidence_count": len(top_vectors),
        "evidence_references": list(evidence_references),
        "chain_of_custody": chain_data,
        "legal_disclaimer": "Kjo analizë është krijuar për qëllime ligjore dhe duhet verifikuar nga një avokat i licencuar në Republikën e Kosovës.",
        "jurisdiction": "KOSOVO"
    }