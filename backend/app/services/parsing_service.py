# FILE: backend/app/services/parsing_service.py
import pandas as pd
import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

class PosParsingService:
    ALL_FIELDS = {
        'date': ['date', 'data', 'koha', 'time', 'datë'],
        'product': ['product', 'item', 'artikulli', 'pershkrimi', 'emertimi'],
        'quantity': ['qty', 'quantity', 'sasia', 'cope'],
        'price': ['price', 'cmimi', 'unit price', 'çmimi'],
        'total': ['total', 'amount', 'vlera', 'shuma'],
        'ref': ['receipt', 'fatura', 'ref', 'nr']
    }

    @staticmethod
    def get_headers_from_file(file_content: bytes, filename: str) -> List[str]:
        try:
            df = pd.read_csv(io.BytesIO(file_content), nrows=0) if filename.lower().endswith('.csv') else pd.read_excel(io.BytesIO(file_content), nrows=0)
            return [str(c).strip().lower() for c in df.columns]
        except Exception as e:
            raise ValueError(f"Could not read file headers. Error: {e}")

    @staticmethod
    def map_columns_with_keywords(columns: List[str]) -> Dict[str, str]:
        mapping = {}
        for system_field, keywords in PosParsingService.ALL_FIELDS.items():
            found_col = next((col for col in columns if any(kw in col for kw in keywords)), None)
            if found_col:
                mapping[found_col] = system_field
        return mapping

    @staticmethod
    def _clean_number(value: Any) -> float:
        if isinstance(value, (int, float)): return float(value)
        if value is None: return 0.0
        val_str = str(value).replace("€", "").strip()
        if not val_str: return 0.0
        if "," in val_str and "." in val_str:
            val_str = val_str.replace(".", "").replace(",", ".") if val_str.rfind(",") > val_str.rfind(".") else val_str.replace(",", "")
        elif "," in val_str:
            val_str = val_str.replace(",", ".")
        try: return float(val_str)
        except (ValueError, TypeError): return 0.0

    @staticmethod
    def _parse_safe_date(date_input: Any) -> datetime:
        if date_input is None: return datetime.utcnow()
        try:
            dt = pd.to_datetime(date_input, dayfirst=True, errors='coerce')
            return dt.to_pydatetime() if not pd.isna(dt) else datetime.utcnow()
        except Exception: return datetime.utcnow()

    @staticmethod
    def process_dataframe(df: pd.DataFrame, mapping: Dict[str, str]) -> Tuple[List[Dict[str, Any]], float]:
        df.rename(columns=mapping, inplace=True)
        
        transactions_to_insert: List[Dict[str, Any]] = []
        batch_total_volume = 0.0

        for _, row in df.iterrows():
            try:
                total = PosParsingService._clean_number(row.get('total'))
                if total == 0.0: continue

                tx_data = {
                    "transaction_ref": str(row.get('ref', '')) if 'ref' in df.columns else None,
                    "date_time": PosParsingService._parse_safe_date(row.get('date')),
                    "product_name": str(row.get('product')),
                    "quantity": PosParsingService._clean_number(row.get('quantity', 1.0)) or 1.0,
                    "unit_price": PosParsingService._clean_number(row.get('price', 0.0)),
                    "total_amount": total,
                    "source_raw_data": row.to_dict()
                }
                transactions_to_insert.append(tx_data)
                batch_total_volume += total # PHOENIX FIX: Corrected typo from "batch_total_volumev"
            except Exception:
                continue
        
        return transactions_to_insert, batch_total_volume