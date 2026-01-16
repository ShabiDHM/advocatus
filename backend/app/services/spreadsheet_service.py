# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - SPREADSHEET FORENSICS V2.1 (TYPE SAFETY FIX)
# 1. FIX: Replaced .dt.strftime with .apply() to satisfy Pylance strict typing.
# 2. CORE: Retains all delimiter detection, currency cleaning, and Forensic AI connection.

import pandas as pd
import numpy as np
import io
import logging
import re
import csv
from typing import Dict, Any, List, Optional
from datetime import datetime
from . import llm_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
MAX_PREVIEW_ROWS = 5
MAX_ANOMALIES = 20

# --- HELPER: CLEAN CURRENCY ---
def _clean_currency_column(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Forces a column to be numeric, stripping 'EUR', '$', ',' etc.
    """
    try:
        # Convert to string, strip whitespace
        series = df[col].astype(str).str.strip()
        # Remove currency symbols and thousand separators (assuming '.' is decimal)
        series = series.str.replace(r'[€$£EUR\s,]', '', regex=True)
        # Convert to numeric, turning errors to NaN
        return pd.to_numeric(series, errors='coerce')
    except Exception:
        return df[col]

def _detect_delimiter(file_content: bytes) -> str:
    """Sniffs the CSV delimiter (comma, semicolon, pipe)."""
    try:
        sample = file_content[:2048].decode('utf-8', errors='ignore')
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except:
        return ',' # Fallback to standard comma

def _detect_anomalies(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Forensic Z-Score Analysis.
    """
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        # Skip ID columns or boring columns
        if df[col].nunique() < 3: continue
        
        mean = df[col].mean()
        std = df[col].std()
        
        if std == 0: continue
        
        # Z-Score > 3 (3 Sigma Rule)
        outliers = df[np.abs((df[col] - mean) / std) > 3]
        
        for idx, row in outliers.iterrows():
            row_idx = int(idx) + 2 if isinstance(idx, int) else 0
            val = float(row[col])
            z_score = round((val - mean) / std, 1)
            
            # Severity Logic
            severity = "HIGH" if abs(z_score) > 5 else "MEDIUM"
            reason = f"Devijim ekstrem ({z_score}x sigma). Mesatarja: {mean:.2f}"
            
            anomalies.append({
                "row_index": row_idx,
                "column": col,
                "value": val,
                "reason": reason,
                "severity": severity
            })
            
    # Return top severe anomalies
    return sorted(anomalies, key=lambda x: abs(x['value']), reverse=True)[:MAX_ANOMALIES]

def _generate_chart_config(df: pd.DataFrame) -> List[Dict[str, Any]]:
    charts = []
    
    # 1. Distribution of Categorical Data (e.g., "Category", "Vendor")
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

    # 2. Time Series Estimate (if Date exists)
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'data' in c.lower()]
    amount_cols = [c for c in df.select_dtypes(include=[np.number]).columns if 'amount' in c.lower() or 'shuma' in c.lower() or 'total' in c.lower()]
    
    if date_cols and amount_cols:
        d_col = date_cols[0]
        a_col = amount_cols[0]
        try:
            # Create a lightweight copy to not mess up main DF
            temp_df = df[[d_col, a_col]].copy()
            temp_df[d_col] = pd.to_datetime(temp_df[d_col], errors='coerce')
            temp_df = temp_df.dropna(subset=[d_col]).sort_values(by=d_col)
            
            if not temp_df.empty:
                # Group by Month if spans > 60 days
                time_span = (temp_df[d_col].max() - temp_df[d_col].min()).days
                if time_span > 60:
                    # FIX: Use lambda apply instead of .dt accessor to satisfy Pylance
                    temp_df['Month'] = temp_df[d_col].apply(lambda x: x.strftime('%Y-%m'))
                    trend = temp_df.groupby('Month')[a_col].sum().reset_index()
                    
                    charts.append({
                        "id": "financial_trend",
                        "title": "Trendi Financiar (Mujor)",
                        "type": "line",
                        "description": f"Lëvizja e {a_col} përgjatë kohës",
                        "data": [{"name": r['Month'], "value": float(r[a_col])} for _, r in trend.iterrows()]
                    })
        except Exception as e:
            logger.warning(f"Failed to generate time chart: {e}")

    return charts

async def analyze_spreadsheet_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    try:
        filename_clean = filename.lower().strip()
        df = None
        
        # 1. LOAD & PARSE
        if filename_clean.endswith('.csv'):
            delimiter = _detect_delimiter(file_content)
            try:
                # Try reading with detected delimiter
                df = pd.read_csv(io.BytesIO(file_content), delimiter=delimiter)
            except:
                # Fallback to standard
                df = pd.read_csv(io.BytesIO(file_content), on_bad_lines='skip')
                
        elif filename_clean.endswith(('.xls', '.xlsx')):
            try:
                df = pd.read_excel(io.BytesIO(file_content))
            except ImportError:
                raise ValueError("Mungon libraria 'openpyxl'.")
        else:
            raise ValueError("Format i panjohur. Përdorni CSV ose Excel.")

        if df is None or df.empty:
            raise ValueError("Skedari është bosh.")

        # 2. DATA CLEANING (The Forensic Wash)
        # Attempt to convert "Amount (EUR)" etc. to numbers
        for col in df.columns:
            if df[col].dtype == 'object':
                # Heuristic: If column name contains currency keywords or looks numeric
                is_money = any(x in col.lower() for x in ['eur', 'usd', 'amount', 'shuma', 'total', 'cmimi', 'price'])
                if is_money:
                    df[col] = _clean_currency_column(df, col)

        # 3. ANALYSIS
        record_count = len(df)
        columns = df.columns.tolist()
        anomalies = _detect_anomalies(df)
        charts = _generate_chart_config(df)
        
        # Generate Statistics safe for JSON (no NaN/Inf)
        stats = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            total_val = float(df[col].sum())
            avg_val = float(df[col].mean())
            stats[f"Total {col}"] = total_val if not pd.isna(total_val) else 0.0
            stats[f"Avg {col}"] = avg_val if not pd.isna(avg_val) else 0.0

        # 4. PREPARE FOR AI (The Forensic Accountant Persona)
        # Convert DataFrame to a JSON structure the AI can read
        
        # Smart Sampling: Take head, tail, and anomaly rows
        sample_rows = df.head(5).to_dict(orient='records')
        
        ai_context = {
            "file_name": filename,
            "columns": columns,
            "total_rows": record_count,
            "key_stats": stats,
            "sample_data": sample_rows,
            "detected_anomalies": anomalies[:5] # Feed the top anomalies to the AI
        }
        
        # Call the new "Forensic Accountant" logic
        import json
        json_context = json.dumps(ai_context, default=str)
        narrative = llm_service.analyze_financial_portfolio(json_context)

        # 5. PREVIEW ROWS (Replace NaN with null for JSON safety)
        preview_rows = df.head(10).replace({np.nan: None}).to_dict(orient='records')

        return {
            "filename": filename,
            "record_count": record_count,
            "columns": columns,
            "narrative_report": narrative,
            "charts": charts,
            "anomalies": anomalies,
            "key_statistics": stats,
            "preview_rows": preview_rows,
            "processed_at": datetime.now().isoformat()
        }

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.exception("Spreadsheet Service Critical Failure")
        raise ValueError(f"Gabim kritik gjatë analizës: {str(e)}")