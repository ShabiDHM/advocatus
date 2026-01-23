# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - FINANCIAL ENGINE V2.3 (OCR INTEGRATION)
# 1. FEATURE: Added 'analyze_text_to_spreadsheet' to process raw text from OCR.
# 2. AI: Implements a "Data Entry Specialist" LLM prompt to convert text to a clean CSV.
# 3. INTEGRATION: Seamlessly connects the new OCR workflow to the existing analysis pipeline.

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
THRESHOLD_STRUCTURING = 1900.0
THRESHOLD_CASH_LARGE = 500.0
SUSPICIOUS_KEYWORDS = ["baste", "bet", "casino", "crypto", "binance", "kredi", "hua", "debt", "borxh"]

# --- PHOENIX: NEW OCR-TO-CSV FUNCTION ---

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


async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    """
    Primary Entry Point: Parses Excel/CSV, runs heuristics, and generates a report.
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

    anomalies = _detect_anomalies(records)
    trends = _calculate_trends(records)
    
    await _vectorize_and_store(records, case_id, db)

    summary_prompt = f"""
    Vepro si një "Asistent Ligjor AI" i specializuar në forenzikë financiare.
    
    TË DHËNAT E ANALIZËS:
    - Anomalitë Kryesore: {str(anomalies[:5])}
    - Trendet Financiare: {str(trends[:3])}
    
    DETYRA: Shkruaj një "RAPORT FORENZIK PARAPRAK: ANALIZA E QËNDRUESHMËRISË FINANCIARE" me estetikë të lartë dhe gjuhë juridike autoritare.
    
    STRUKTURA E DETYRUESHME (Përdor Markdown):
    
    #### 1. KONKLUZION EKZEKUTIV
    (Jep një gjykim të prerë: A ka rrezik? Cili është disproporcioni hyrje/dalje? Përdor terma si "Diskrepancë Materiale", "Deficit i Pajustifikuar", "Indikatorë të Lartë Risku".)
    
    #### 2. EVIDENCA KRITIKE (FLAMUJT E KUQ)
    (Listo anomalitë me bullet points. Për çdo anomali, shpjego *Pse* është e rrezikshme ligjërisht.)
    
    #### 3. STRATEGJIA LIGJORE & VEPRIMET E REKOMANDUARA
    (Jep hapa taktikë: "Kërkesë për Zbulim (Discovery)", "Kryqëzim Asetesh", "Auditimi i Stilit të Jetesës", "Verifikim i Burimit të Fondeve".)

    RREGULL I RËNDËSISHËM:
    - MOS SHTO ASNJË LLOJ NËNSHKRIMI, EMRI, APO INFORMACION TË FIRMËS NË FUND. Fokusi është vetëm tek analiza.
    
    TONI: Përdor fjalor elitar. GJUHA: SHQIP LETRAR (PA GABIME).
    """
    
    exec_summary = await asyncio.to_thread(llm_service._call_llm, "Ti je Ekspert Forenzik i Nivelit të Lartë që flet vetëm Shqip.", summary_prompt, False)

    return {
        "executive_summary": exec_summary, "anomalies": anomalies, "trends": trends,
        "recommendations": [
            "Iniconi procedurën 'Discovery' për faturat e dyshimta.",
            "Kryeni auditim të stilit të jetesës vs. të ardhurave të deklaruara.",
            "Verifikoni përputhshmërinë me ligjet AML (Neni 288 KPRK)."
        ]
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
        
    if not context_lines:
        return {"answer": "Nuk u gjetën të dhëna relevante në spreadsheet."}
        
    answer = await asyncio.to_thread(llm_service.forensic_interrogation, question, context_lines)
    
    return {"answer": answer, "referenced_rows_count": len(top_rows)}

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
        embedding = await asyncio.to_thread(llm_service.get_embedding, semantic_text)
        
        vectors.append({
            "case_id": ObjectId(case_id), "row_id": r['row_id'], "content": semantic_text,
            "metadata": r['raw_row'], "embedding": embedding, "created_at": datetime.now(timezone.utc)
        })

    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)
        logger.info(f"Vectorized and stored {len(vectors)} financial rows for case {case_id}")