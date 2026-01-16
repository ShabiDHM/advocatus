# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - SPREADSHEET FORENSICS V3.0 (SMART MERGE)
# 1. INTEGRATION: Consumes 'Smart JSON' from LLM Service.
# 2. HYBRID INTEL: Merges Statistical Anomalies (Z-Score) with Semantic Anomalies (AI).
# 3. OUTPUT: Returns structure fully compatible with 'SmartFinancialReport' frontend interface.

import pandas as pd
import numpy as np
import io
import logging
import re
import csv
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Safe Import
import app.services.llm_service as llm_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
MAX_PREVIEW_ROWS = 5
MAX_ANOMALIES = 20

# --- HELPER: CLEAN CURRENCY ---
def _clean_currency_column(df: pd.DataFrame, col: str) -> pd.Series:
    """Forces a column to be numeric, stripping 'EUR', '$', ',' etc."""
    try:
        series = df[col].astype(str).str.strip()
        series = series.str.replace(r'[€$£EUR\s,]', '', regex=True)
        return pd.to_numeric(series, errors='coerce')
    except Exception:
        return df[col]

def _detect_delimiter(file_content: bytes) -> str:
    """Sniffs the CSV delimiter."""
    try:
        sample = file_content[:2048].decode('utf-8', errors='ignore')
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except:
        return ','

def _detect_statistical_anomalies(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Forensic Z-Score Analysis (The 'Math' part of the brain).
    Detects mathematical outliers irrespective of context.
    """
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        if df[col].nunique() < 3: continue
        
        mean = df[col].mean()
        std = df[col].std()
        
        if std == 0: continue
        
        # Z-Score > 3 (3 Sigma Rule)
        outliers = df[np.abs((df[col] - mean) / std) > 3]
        
        for idx, row in outliers.iterrows():
            val = float(row[col])
            z_score = round((val - mean) / std, 1)
            
            anomalies.append({
                "date": str(idx), # Fallback if no date col
                "amount": val,
                "description": f"Row {idx} in {col}",
                "risk_level": "HIGH" if abs(z_score) > 5 else "MEDIUM",
                "explanation": f"Statistical Outlier ({z_score}x Sigma). Average: {mean:.2f}"
            })
            
    return sorted(anomalies, key=lambda x: abs(x['amount']), reverse=True)[:10]

def _generate_chart_config(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generates chart configs for the UI."""
    charts = []
    
    # 1. Distribution of Categorical Data
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        if df[col].nunique() < 20: 
            counts = df[col].value_counts().head(10).to_dict()
            chart_data = [{"name": str(k), "value": int(v)} for k, v in counts.items()]
            charts.append({
                "id": f"dist_{col}",
                "title": f"Shpërndarja sipas {col}",
                "type": "bar",
                "description": f"Frekuenca e kategorive në kolonën {col}",
                "data": chart_data
            })
            if len(charts) >= 3: break 

    return charts

async def analyze_spreadsheet_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    try:
        filename_clean = filename.lower().strip()
        df = None
        
        # 1. LOAD
        if filename_clean.endswith('.csv'):
            delimiter = _detect_delimiter(file_content)
            try:
                df = pd.read_csv(io.BytesIO(file_content), delimiter=delimiter)
            except:
                df = pd.read_csv(io.BytesIO(file_content), on_bad_lines='skip')
        elif filename_clean.endswith(('.xls', '.xlsx')):
            try:
                df = pd.read_excel(io.BytesIO(file_content))
            except ImportError:
                raise ValueError("Mungon libraria 'openpyxl'.")
        else:
            raise ValueError("Format i panjohur.")

        if df is None or df.empty:
            raise ValueError("Skedari është bosh.")

        # 2. CLEAN
        for col in df.columns:
            if df[col].dtype == 'object':
                is_money = any(x in col.lower() for x in ['eur', 'usd', 'amount', 'shuma', 'total', 'cmimi', 'price'])
                if is_money:
                    df[col] = _clean_currency_column(df, col)

        # 3. STATISTICAL ANALYSIS (Local Math)
        math_anomalies = _detect_statistical_anomalies(df)
        charts = _generate_chart_config(df)
        
        stats = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            total_val = float(df[col].sum())
            stats[f"Total {col}"] = total_val
        
        # 4. AI ANALYSIS (Semantic Intelligence)
        # Prepare context for AI
        sample_rows = df.head(10).replace({np.nan: None}).to_dict(orient='records')
        
        ai_context = {
            "file_name": filename,
            "columns": df.columns.tolist(),
            "key_stats": stats,
            "sample_data": sample_rows, # AI sees real rows to understand context
            "math_flags": math_anomalies[:3] # AI sees what math flagged
        }
        
        json_context = json.dumps(ai_context, default=str)
        
        # Call LLM (Returns Dict)
        ai_result = llm_service.analyze_financial_portfolio(json_context)
        
        # 5. MERGE RESULTS (Hybrid Intelligence)
        # We prioritize AI anomalies as they have context, but keep math anomalies if unique
        final_anomalies = ai_result.get("anomalies", [])
        
        # If AI failed to return anomalies, fallback to math ones
        if not final_anomalies:
            final_anomalies = math_anomalies
            
        # Ensure proper structure
        final_response = {
            "filename": filename,
            "record_count": len(df),
            "key_statistics": stats,
            "charts": charts,
            
            # Map AI fields to Frontend Interface
            "executive_summary": ai_result.get("executive_summary", "Analiza përfundoi, por mungon përmbledhja."),
            "anomalies": final_anomalies,
            "trends": ai_result.get("trends", []),
            "recommendations": ai_result.get("recommendations", []),
            
            "processed_at": datetime.now().isoformat()
        }

        return final_response

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.exception("Spreadsheet Service Critical Failure")
        raise ValueError(f"Gabim kritik gjatë analizës: {str(e)}")