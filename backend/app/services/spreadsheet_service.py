# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - FINANCIAL INTERROGATION ENGINE V1.2 (VECTOR QUERY)
# 1. ADDED: ask_financial_question() - Performs vector search on financial rows.
# 2. LOGIC: Retrieves top 20 relevant rows -> Sends to LLM for forensic answer.

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
SUSPICIOUS_KEYWORDS = ["baste", "bet", "casino", "crypto", "binance", "kredi", "hua", "debt"]

async def analyze_spreadsheet_file(content: bytes, filename: str, case_id: str, db: Database) -> Dict[str, Any]:
    # ... (Same as previous version, see V1.1) ...
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"Spreadsheet parse error: {e}")
        raise ValueError("Invalid file format. Please upload .xlsx or .csv")

    df.columns = [str(c).lower().strip() for c in df.columns]
    col_date = next((c for c in df.columns if 'date' in c or 'data' in c), None)
    col_desc = next((c for c in df.columns if 'desc' in c or 'pershkrim' in c or 'details' in c), None)
    col_amount = next((c for c in df.columns if 'amount' in c or 'shuma' in c or 'vlere' in c), None)

    if not col_amount: raise ValueError("Could not identify 'Amount/Shuma' column.")

    records = []
    df = df.fillna('')
    for idx, row in df.iterrows():
        raw_amt = row[col_amount]
        try:
            if isinstance(raw_amt, str): raw_amt = raw_amt.replace('€', '').replace(',', '')
            amount = float(raw_amt)
        except: amount = 0.0
            
        date_val = str(row[col_date]) if col_date else "N/A"
        desc_val = str(row[col_desc]) if col_desc else "No Description"
        records.append({"row_id": idx, "date": date_val, "description": desc_val, "amount": amount, "raw_row": row.to_dict()})

    anomalies = _detect_anomalies(records)
    trends = _calculate_trends(records)
    await _vectorize_and_store(records, case_id, db)
    
    summary_prompt = f"Analyze these top anomalies: {str(anomalies[:5])} and trends: {str(trends[:3])}. Write a short Forensic Executive Summary for a lawyer."
    exec_summary = llm_service._call_llm("Ti je Ekspert Financiar.", summary_prompt, False)

    return {"executive_summary": exec_summary, "anomalies": anomalies, "trends": trends, "recommendations": ["Request bank statements.", "Cross-examine withdrawals."]}

async def ask_financial_question(case_id: str, question: str, db: Database) -> Dict[str, Any]:
    """
    Performs the Interrogation:
    1. Embeds the user's question.
    2. Searches MongoDB Vector Search for relevant rows.
    3. Uses LLM to formulate an evidence-backed answer.
    """
    # 1. Embed Question
    q_vector = llm_service.get_embedding(question)
    
    # 2. Vector Search (Using Atlas Vector Search Syntax - Standard)
    # Note: Requires an Atlas Vector Search Index on 'embedding' field.
    # Fallback to simple Cosine Similarity if index not set (InMemory approach for dev)
    
    rows = await asyncio.to_thread(list, db.financial_vectors.find({"case_id": ObjectId(case_id)}))
    
    # Calculate Similarity (InMemory for reliability without Atlas triggers)
    scored_rows = []
    for row in rows:
        v = row.get("embedding")
        if v:
            # Simple Dot Product for normalized vectors (Cosine Similarity)
            score = np.dot(q_vector, v)
            scored_rows.append((score, row))
            
    # Sort by score desc, take top 30
    scored_rows.sort(key=lambda x: x[0], reverse=True)
    top_rows = scored_rows[:30]
    
    # 3. Formulate Context
    context_lines = []
    for _, row in top_rows:
        context_lines.append(row["content"])
        
    if not context_lines:
        return {"answer": "Nuk u gjetën të dhëna relevante në spreadsheet."}
        
    # 4. Ask Agent
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
            anomalies.append({"date": r['date'], "amount": r['amount'], "description": r['description'], "risk_level": "HIGH", "explanation": "Potential Structuring < €2000."})
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in desc:
                anomalies.append({"date": r['date'], "amount": r['amount'], "description": r['description'], "risk_level": "HIGH", "explanation": f"Suspicious Activity: {kw}"})
        if amt >= 500 and amt % 50 == 0 and ("atm" in desc or "cash" in desc):
             anomalies.append({"date": r['date'], "amount": r['amount'], "description": r['description'], "risk_level": "MEDIUM", "explanation": "Large Cash Withdrawal."})
    return anomalies

def _calculate_trends(records: List[Dict]) -> List[Dict]:
    total_in = sum(r['amount'] for r in records if r['amount'] > 0)
    total_out = sum(abs(r['amount']) for r in records if r['amount'] < 0)
    return [{"category": "Total Inflow", "trend": "STABLE", "percentage": f"€{total_in:,.2f}", "comment": "Total deposits."}, {"category": "Total Outflow", "trend": "UP", "percentage": f"€{total_out:,.2f}", "comment": "Total spending."}]

async def _vectorize_and_store(records: List[Dict], case_id: str, db: Database):
    vectors = []
    for r in records:
        semantic_text = f"Date: {r['date']}. Amount: {r['amount']} EUR. Desc: {r['description']}."
        embedding = llm_service.get_embedding(semantic_text)
        vectors.append({"case_id": ObjectId(case_id), "row_id": r['row_id'], "content": semantic_text, "metadata": r['raw_row'], "embedding": embedding, "created_at": datetime.now(timezone.utc)})
    if vectors:
        await asyncio.to_thread(db.financial_vectors.delete_many, {"case_id": ObjectId(case_id)})
        await asyncio.to_thread(db.financial_vectors.insert_many, vectors)
        logger.info(f"Vectorized {len(vectors)} rows for {case_id}")