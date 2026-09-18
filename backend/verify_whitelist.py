# verify_whitelist.py (i përkohshëm — fshije pas testit)
import sys
sys.path.insert(0, '.')
from app.core.db import get_db_instance
from bson import ObjectId
import re

db = get_db_instance()
case_id = '6aac1f79ef09232ccbe1ba13'

regex_08 = re.compile(r'08/L-185', re.IGNORECASE)
regex_03 = re.compile(r'03/L-182', re.IGNORECASE)

query = {
    "$or": [{"case_id": case_id}, {"case_id": ObjectId(case_id)}],
    "status": {"$ne": "DELETED"}
}

docs = list(db.documents.find(query, {"file_name": 1, "content": 1, "extracted_text": 1, "text": 1}))

print(f"\nTotal dokumente: {len(docs)}\n")
print("=" * 70)
print("Dokumentet që përmbajnë 08/L-185:")
print("=" * 70)
for d in docs:
    text = d.get("content") or d.get("extracted_text") or d.get("text") or ""
    if regex_08.search(text):
        print(f"  - {d.get('file_name', 'N/A')}")

print("\n" + "=" * 70)
print("Dokumentet që përmbajnë 03/L-182:")
print("=" * 70)
for d in docs:
    text = d.get("content") or d.get("extracted_text") or d.get("text") or ""
    if regex_03.search(text):
        print(f"  - {d.get('file_name', 'N/A')}")

print("\n" + "=" * 70)
print("Dokumentet me emra gjykatore (aktvendim/aktgjykim/vendim/urdhër):")
print("=" * 70)
for d in docs:
    name = (d.get("file_name") or "").lower()
    if any(k in name for k in ["aktvendim", "aktgjykim", "vendim", "urdhër", "urdher"]):
        print(f"  - {d.get('file_name', 'N/A')}")

print("\n" + "=" * 70)