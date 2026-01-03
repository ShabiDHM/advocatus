# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - ROBUSTNESS PATCH V1.3
# 1. FIX: Added Case-Insensitive extension checking.
# 2. FIX: Explicit engine definition for read_excel.
# 3. LOGGING: Added detailed error logging for debugging.

import pandas as pd
import numpy as np
import io
import logging
from typing import Dict, Any, List, Optional, cast
from datetime import datetime
from . import llm_service

logger = logging.getLogger(__name__)

# --- Dependency Check ---
try:
    import openpyxl
except ImportError:
    logger.critical("❌ OPENPYXL IS MISSING. Excel upload will fail. Please pip install openpyxl.")

def _detect_anomalies(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detects numerical anomalies using Z-Score (Standard Deviation).
    """
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        if df[col].nunique() < 3: continue
        
        mean = df[col].mean()
        std = df[col].std()
        
        if std == 0: continue
        
        outliers = df[np.abs((df[col] - mean) / std) > 3]
        
        for idx, row in outliers.iterrows():
            try:
                row_idx = int(idx) + 2  # type: ignore 
            except (ValueError, TypeError):
                row_idx = 0 

            severity = "HIGH" if np.abs((row[col] - mean) / std) > 5 else "MEDIUM"
            anomalies.append({
                "row_index": row_idx,
                "column": col,
                "value": float(row[col]),
                "reason": f"Value is {np.round((row[col] - mean) / std, 1)} standard deviations from mean.",
                "severity": severity
            })
            
    return sorted(anomalies, key=lambda x: x['value'], reverse=True)[:20]

def _generate_chart_config(df: pd.DataFrame) -> List[Dict[str, Any]]:
    charts = []
    
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        if df[col].nunique() < 15: 
            counts = df[col].value_counts().head(8).to_dict()
            chart_data = [{"name": str(k), "value": int(v)} for k, v in counts.items()]
            charts.append({
                "id": f"dist_{col}",
                "title": f"Distribution by {col}",
                "type": "bar",
                "description": f"Frequency of top categories in {col}",
                "data": chart_data
            })
            if len(charts) >= 2: break 

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].nunique() > 5:
            top_vals = df.nlargest(8, col)
            chart_data = []
            for idx, row in top_vals.iterrows():
                label = f"Row {idx}"
                for cat in categorical_cols:
                    if df[cat].nunique() == len(df): 
                        label = str(row[cat])
                        break
                
                chart_data.append({"name": label, "value": float(row[col])})
            
            charts.append({
                "id": f"top_{col}",
                "title": f"Top Values in {col}",
                "type": "bar",
                "description": f"Highest recorded values for {col}",
                "data": chart_data
            })
            if len(charts) >= 4: break

    return charts

async def analyze_spreadsheet_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    try:
        # 1. Normalize Extension
        filename_clean = filename.lower().strip()
        
        # 2. Parse File with Explicit Engine
        df = None
        if filename_clean.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(file_content))
            except Exception as e:
                logger.error(f"CSV Parsing Failed: {e}")
                raise ValueError("Could not parse CSV file. Check delimiter/encoding.")
                
        elif filename_clean.endswith(('.xls', '.xlsx')):
            try:
                # Explicitly use openpyxl for xlsx to avoid ambiguity
                engine = 'openpyxl' if filename_clean.endswith('.xlsx') else None
                df = pd.read_excel(io.BytesIO(file_content), engine=engine)
            except ImportError:
                logger.error("Pandas Engine Missing: openpyxl is likely not installed.")
                raise ValueError("Server missing Excel support (openpyxl).")
            except Exception as e:
                logger.error(f"Excel Parsing Failed: {e}")
                raise ValueError("Could not parse Excel file. Is it corrupted?")
        else:
            raise ValueError(f"Unsupported format: {filename}")

        if df is None or df.empty:
            raise ValueError("File is empty or could not be read.")

        # 3. Processing
        record_count = len(df)
        columns = df.columns.tolist()
        
        stats_summary = df.describe(include='all').to_string()
        null_counts = df.isnull().sum().to_string()
        
        anomalies = _detect_anomalies(df)
        charts = _generate_chart_config(df)
        
        key_statistics: Dict[str, Any] = {
            "Total Records": record_count,
            "Total Columns": len(columns),
            "Empty Cells": int(df.isnull().sum().sum())
        }
        
        for col in df.select_dtypes(include=[np.number]).columns[:3]:
            key_statistics[f"Avg {col}"] = round(float(df[col].mean()), 2)

        data_context = f"""
        FILENAME: {filename}
        SHAPE: {df.shape}
        COLUMNS: {columns}
        SAMPLE DATA:
        {df.head(5).to_string()}
        STATISTICAL SUMMARY:
        {stats_summary}
        ANOMALIES:
        {anomalies[:5]}
        """
        
        narrative = llm_service.analyze_financial_summary(data_context)

        return {
            "filename": filename,
            "record_count": record_count,
            "columns": columns,
            "narrative_report": narrative,
            "charts": charts,
            "anomalies": anomalies,
            "key_statistics": key_statistics,
            "processed_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception("Spreadsheet Service Critical Failure") # This prints stack trace to logs
        raise e