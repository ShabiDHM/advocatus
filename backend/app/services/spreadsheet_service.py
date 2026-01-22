# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - FINANCIAL ENGINE V2.2 (PROMPT FIX)
# 1. FIXED: Modified the LLM prompt to remove the generated signature.
# 2. PROMPT ENGINEERING: Changed persona to "AI Legal Assistant" and added a negative constraint forbidding signatures.
# 3. STATUS: Output is now clean and focused solely on the analysis.

import pandas as pd
import io
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
import numpy as np
from pymongo.database import Database
import asyncio

# Internal Services
from . import llm_service

logger = logging.getLogger(__name__)

# --- HEURISTICS CONSTANTS ---
THRESHOLD_STRUCTURING = 1900.0  # Just below 2000 EUR reporting limit
THRESHOLD_CASH_LARGE = 500.0
SUSPICIOUS_KEYWORDS = ["baste", "bet", "casino", "crypto", "binance", "kredi", "hua", "debt", "borxh"]

async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    """
    Primary Entry Point:
    1. Parses Excel/CSV.
    2. Runs Forensic Heuristics (Evidence Board).
    3. Vectorizes Rows (Interrogation Room).
    4. Stores Data in DB (using passed DB session).
    """
    try:
        if filename.endswith('.csv'):
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
        raise ValueError("Nuk u gjet kolona 'Shuma' ose 'Amount'.")

    records = []
    df = df.fillna('')
    
    for idx, row in df.iterrows():
        raw_amt = row[col_amount]
        try:
            if isinstance(raw_amt, str):
                raw_amt = raw_amt.replace('€', '').replace(',', '')
            amount = float(raw_amt)
        except:
            amount = 0.0
            
        date_val = str(row[col_date]) if col_date else "N/A"
        desc_val = str(row[col_desc]) if col_desc else "Pa Përshkrim"
        
        records.append({
            "row_id": idx,
            "date": date_val,
            "description": desc_val,
            "amount": amount,
            "raw_row": row.to_dict()
        })

    anomalies = _detect_anomalies(records)
    trends = _calculate_trends(records)
    
    await _vectorize_and_store(records, case_id, db)

    # PHOENIX FIX: Updated prompt to prevent signature generation.
    summary_prompt = f"""
    Vepro si një "Asistent Ligjor AI" i specializuar në forenzikë financiare.
    
    TË DHËNAT E ANALIZËS:
    - Anomalitë Kryesore: {str(anomalies[:5])}
    - Trendet Financiare: {str(trends[:3])}
    
    DETYRA:
    Shkruaj një "RAPORT FORENZIK PARAPRAK: ANALIZA E QËNDRUESHMËRISË FINANCIARE" me estetikë të lartë dhe gjuhë juridike autoritare.
    
    STRUKTURA E DETYRUESHME (Përdor Markdown):
    
    #### 1. KONKLUZION EKZEKUTIV
    (Jep një gjykim të prerë: A ka rrezik? Cili është disproporcioni hyrje/dalje? Përdor terma si "Diskrepancë Materiale", "Deficit i Pajustifikuar", "Indikatorë të Lartë Risku".)
    
    #### 2. EVIDENCA KRITIKE (FLAMUJT E KUQ)
    (Listo anomalitë me bullet points. Për çdo anomali, shpjego *Pse* është e rrezikshme ligjërisht. Psh: Përmend "Tentativë për shmangie të raportimit" për shumat afër 2000€, ose "Mungesë Transparence".)
    
    #### 3. STRATEGJIA LIGJORE & VEPRIMET E REKOMANDUARA
    (Jep hapa taktikë: "Kërkesë për Zbulim (Discovery)", "Kryqëzim Asetesh", "Auditimi i Stilit të Jetesës", "Verifikim i Burimit të Fondeve".)

    RREGULL I RËNDËSISHËM:
    - MOS SHTO ASNJË LLOJ NËNSHKRIMI, EMRI, APO INFORMACION TË FIRMËS NË FUND. Fokusi është vetëm tek analiza.
    
    TONI:
    - Përdor fjalor elitar (psh: jo "ngre dyshime", por "indikatorë të evazionit").
    - GJUHA: SHQIP LETRAR (PA GABIME).
    """
    
    exec_summary = llm_service._call_llm("Ti je Ekspert Forenzik i Nivelit të Lartë që flet vetëm Shqip.", summary_prompt, False)

    return {
        "executive_summary": exec_summary,
        "anomalies": anomalies,
        "trends": trends,
        "recommendations": [
            "Iniconi procedurën 'Discovery' për faturat e dyshimta.",
            "Kryeni auditim të stilit të jetesës vs. të ardhurave të deklaruara.",
            "Verifikoni përputhshmërinë me ligjet AML (Neni 288 KPRK)."
        ]
    }

async def ask_financial_question(case_id: str, question: str, db: Database) -> Dict[str, Any]:
    """
    Performs the Interrogation:
    1. Embeds the user's question.
    2. Searches MongoDB Vector Search for relevant rows.
    3. Uses LLM to formulate an evidence-backed answer.
    """
    q_vector = llm_service.get_embedding(question)
    
    rows = await asyncio.to_thread(list, db.financial_vectors.find({"case_id": ObjectId(case_id)}))
    
    scored_rows = []
    for row in rows:
        v = row.get("embedding")
        if v:
            score = np.dot(q_vector, v)
            scored_rows.append((score, row))
            
    scored_rows.sort(key=lambda x: x[0], reverse=True)
    top_rows = scored_rows[:30]
    
    context_lines = []
    for _, row in top_rows:
        context_lines.append(row["content"])
        
    if not context_lines:
        return {"answer": "Nuk u gjetën të dhëna relevante në spreadsheet."}
        
    answer = llm_service.forensic_interrogation(question, context_lines)
    
    return {
        "answer": answer,
        "referenced_rows_count": len(top_rows)
    }

def _detect_anomalies(records: List[Dict]) -> List[Dict]:
    anomalies = []
    records.sort(key=lambda x: x['date']) 
    
    for i, r in enumerate(records):
        amt = abs(r['amount'])
        desc = r['description'].lower()
        
        if 1500 < amt < 2000:
            anomalies.append({
                "date": r['date'], "amount": r['amount'], "description": r['description'],
                "risk_level": "HIGH", "explanation": "Strukturim i Mundshëm (Smurfing): Shuma është pak nën pragun e raportimit prej 2,000€. Indikator i shmangies së gjurmëve bankare."
            })
            
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in desc:
                anomalies.append({
                    "date": r['date'], "amount": r['amount'], "description": r['description'],
                    "risk_level": "HIGH", "explanation": f"Aktivitet me Risk të Lartë: Transaksion i lidhur me '{kw}' (Potencialisht Bixhoz/Kripto/Borxhe joformale)."
                })
                
        if amt >= 500 and amt % 50 == 0 and ("atm" in desc or "cash" in desc):
             anomalies.append({
                "date": r['date'], "amount": r['amount'], "description": r['description'],
                "risk_level": "MEDIUM", "explanation": "Tërheqje Cash Signifikante: Tërheqje e likuiditetit pa gjurmë destinacioni përfundimtar."
            })

    return anomalies

def _calculate_trends(records: List[Dict]) -> List[Dict]:
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = sum(abs(r['amount']) for r in records if r['amount'] < 0)
    
    return [
        {"category": "Totali i Hyrjeve", "trend": "STABLE", "percentage": f"€{total_in:,.2f}", "comment": "Totali i depozitave/të ardhurave të detektuara."},
        {"category": "Totali i Daljeve", "trend": "UP", "percentage": f"€{total_out:,.2f}", "comment": "Totali i shpenzimeve operative dhe personale."}
    ]

async def _vectorize_and_store(records: List[Dict], case_id: str, db: Database):
    vectors = []
    
    for r in records:
        semantic_text = f"Data: {r['date']}. Shuma: {r['amount']} EUR. Përshkrimi: {r['description']}."
        embedding = llm_service.get_embedding(semantic_text)
        
        vectors.append({
            "case_id": ObjectId(case_id), "row_id": r['row_id'], "content": semantic_text,
            "metadata": r['raw_row'], "embedding": embedding, "created_at": datetime.now(timezone.utc)
        })

    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)
        logger.info(f"Vectorized and stored {len(vectors)} financial rows for case {case_id}")