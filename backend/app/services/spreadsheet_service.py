# FILE: backend/app/services/spreadsheet_service.py
# PHOENIX PROTOCOL - CORRECTION V1.2 (STRICT TYPE FIX)
# 1. FIX: Explicitly annotated 'key_statistics' as Dict[str, Any] to allow floats.
# 2. STATUS: Verified against strict Pylance inference rules.

import pandas as pd
import numpy as np
import io
import logging
from typing import Dict, Any, List, Optional, cast
from datetime import datetime
from . import llm_service

logger = logging.getLogger(__name__)

def _detect_anomalies(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detects numerical anomalies using Z-Score (Standard Deviation).
    """
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        # Skip columns with too few unique values (likely categories encoded as numbers)
        if df[col].nunique() < 3: continue
        
        # Calculate Z-Score
        mean = df[col].mean()
        std = df[col].std()
        
        if std == 0: continue
        
        # Identify outliers (> 3 std devs)
        outliers = df[np.abs((df[col] - mean) / std) > 3]
        
        for idx, row in outliers.iterrows():
            # PHOENIX FIX: Ensure index is treated as int for row calculation
            # Pylance sees idx as 'Hashable', so we explicitly cast or ignore type check
            try:
                row_idx = int(idx) + 2  # type: ignore # +2 for Excel 1-based indexing + header
            except (ValueError, TypeError):
                row_idx = 0 # Fallback if index is somehow non-numeric

            severity = "HIGH" if np.abs((row[col] - mean) / std) > 5 else "MEDIUM"
            anomalies.append({
                "row_index": row_idx,
                "column": col,
                "value": float(row[col]),
                "reason": f"Value is {np.round((row[col] - mean) / std, 1)} standard deviations from mean.",
                "severity": severity
            })
            
    # Limit to top 20 anomalies to prevent flooding
    return sorted(anomalies, key=lambda x: x['value'], reverse=True)[:20]

def _generate_chart_config(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generates chart configurations for the frontend.
    """
    charts = []
    
    # 1. Categorical Distribution (Pie/Bar candidate)
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        if df[col].nunique() < 15: # Only chart if reasonable number of categories
            counts = df[col].value_counts().head(8).to_dict()
            chart_data = [{"name": str(k), "value": int(v)} for k, v in counts.items()]
            charts.append({
                "id": f"dist_{col}",
                "title": f"Distribution by {col}",
                "type": "bar",
                "description": f"Frequency of top categories in {col}",
                "data": chart_data
            })
            if len(charts) >= 2: break # Limit number of automatic charts

    # 2. Numerical Trends (if 'date' or 'year' column exists) or Top Values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        # Histogram-like data (bins)
        if df[col].nunique() > 5:
            top_vals = df.nlargest(8, col)
            chart_data = []
            for idx, row in top_vals.iterrows():
                # Try to find a label column
                label = f"Row {idx}"
                for cat in categorical_cols:
                    if df[cat].nunique() == len(df): # Unique ID
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
        # 1. Parse File
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError("Unsupported file format")

        # 2. Basic Stats
        record_count = len(df)
        columns = df.columns.tolist()
        
        # Calculate Stats for Narrative
        stats_summary = df.describe(include='all').to_string()
        null_counts = df.isnull().sum().to_string()
        
        # 3. Anomaly Detection
        anomalies = _detect_anomalies(df)
        
        # 4. Generate Charts
        charts = _generate_chart_config(df)
        
        # 5. Key Statistics Dictionary (for UI Grid)
        # FIX: Explicit type annotation to prevent Pylance inferring Dict[str, int]
        key_statistics: Dict[str, Any] = {
            "Total Records": record_count,
            "Total Columns": len(columns),
            "Empty Cells": int(df.isnull().sum().sum())
        }
        
        # Add sum/mean for numeric cols
        for col in df.select_dtypes(include=[np.number]).columns[:3]:
            # This assignment is now valid because we defined the dict as Dict[str, Any]
            key_statistics[f"Avg {col}"] = round(float(df[col].mean()), 2)

        # 6. LLM Narrative Generation
        data_context = f"""
        FILENAME: {filename}
        SHAPE: {df.shape}
        COLUMNS: {columns}
        
        SAMPLE DATA (First 5 rows):
        {df.head(5).to_string()}
        
        STATISTICAL SUMMARY:
        {stats_summary}
        
        MISSING VALUES:
        {null_counts}
        
        DETECTED ANOMALIES (Top 5):
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
        logger.error(f"Spreadsheet analysis failed: {e}")
        raise e