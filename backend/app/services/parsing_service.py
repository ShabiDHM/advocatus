# FILE: backend/app/services/parsing_service.py
import pandas as pd
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId

from app.models.finance import TransactionInDB, ImportBatchInDB
from app.models.common import PyObjectId # PHOENIX FIX: Import PyObjectId for casting

class PosParsingService:
    COLUMN_MAP = {
        'date': ['date', 'data', 'koha', 'time', 'datë'],
        'product': ['product', 'item', 'artikulli', 'pershkrimi', 'emertimi'],
        'quantity': ['qty', 'quantity', 'sasia', 'cope'],
        'price': ['price', 'cmimi', 'unit price', 'çmimi'],
        'total': ['total', 'amount', 'vlera', 'shuma'],
        'ref': ['receipt', 'fatura', 'ref', 'nr']
    }

    def __init__(self, db: Any):
        self.db = db
        self.transactions_collection = db["transactions"]
        self.batches_collection = db["import_batches"]

    def _map_columns(self, columns: list) -> Dict[str, Optional[str]]:
        mapping: Dict[str, Optional[str]] = {k: None for k in self.COLUMN_MAP.keys()}
        for col in columns:
            for key, keywords in self.COLUMN_MAP.items():
                if mapping[key] is None and any(kw in col for kw in keywords):
                    mapping[key] = col
        return mapping

    def _clean_number(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if value is None:
            return 0.0
            
        val_str = str(value).replace("€", "").strip()
        if not val_str:
            return 0.0

        if "," in val_str and "." in val_str:
            if val_str.rfind(",") > val_str.rfind("."): # European format: 1.200,50
                val_str = val_str.replace(".", "").replace(",", ".")
            else: # US format: 1,200.50
                val_str = val_str.replace(",", "")
        elif "," in val_str:
            val_str = val_str.replace(",", ".")
        
        try:
            return float(val_str)
        except (ValueError, TypeError):
            return 0.0

    def _parse_date(self, value: Any) -> datetime:
        if value is None:
            return datetime.utcnow()
        try:
            dt = pd.to_datetime(value, dayfirst=True, errors='coerce')
            if pd.isna(dt):
                return datetime.utcnow()
            return dt.to_pydatetime()
        except Exception:
            return datetime.utcnow()

    async def process_file(self, user_id: str, file_content: bytes, filename: str) -> dict:
        try:
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Could not read the file. Ensure it is a valid CSV or Excel file. Error: {e}")

        df.columns = [str(c).strip().lower() for c in df.columns]
        mapped_cols = self._map_columns(list(df.columns))

        if not mapped_cols.get('product') or not mapped_cols.get('total'):
            raise ValueError("Could not identify 'Product' or 'Total' columns. Please check file headers.")

        transactions_to_insert: List[Dict] = []
        batch_total_volume = 0.0
        user_oid = ObjectId(user_id)

        for _, row in df.iterrows():
            try:
                total = self._clean_number(row.get(mapped_cols['total']))
                if total == 0.0: continue

                qty = self._clean_number(row.get(mapped_cols['quantity'], 1.0))
                price = self._clean_number(row.get(mapped_cols['price'], 0.0))

                tx = TransactionInDB(
                    # PHOENIX FIX: Cast ObjectId to PyObjectId
                    user_id=PyObjectId(user_oid),
                    batch_id=PyObjectId(ObjectId()), # Placeholder, will be updated
                    transaction_ref=str(row.get(mapped_cols['ref'], '')) if mapped_cols['ref'] else None,
                    date_time=self._parse_date(row.get(mapped_cols['date'])),
                    product_name=str(row.get(mapped_cols['product'])),
                    quantity=qty if qty > 0 else 1.0,
                    unit_price=price,
                    total_amount=total,
                    source_raw_data=row.to_dict()
                )
                transactions_to_insert.append(tx.model_dump(by_alias=True))
                batch_total_volume += total
            except Exception:
                continue 

        if not transactions_to_insert:
            raise ValueError("No valid transactions found in the file.")

        batch_record = ImportBatchInDB(
            # PHOENIX FIX: Cast ObjectId to PyObjectId
            user_id=PyObjectId(user_oid),
            filename=filename,
            status="PROCESSED",
            row_count=len(transactions_to_insert),
            total_volume=batch_total_volume
        )
        new_batch = await self.batches_collection.insert_one(batch_record.model_dump(by_alias=True))
        batch_id = new_batch.inserted_id

        for tx in transactions_to_insert:
            tx['batch_id'] = batch_id
        
        await self.transactions_collection.insert_many(transactions_to_insert)

        return {
            "id": batch_id,
            "filename": filename,
            "status": "PROCESSED",
            "row_count": len(transactions_to_insert),
            "total_volume": batch_total_volume,
            "created_at": datetime.utcnow()
        }