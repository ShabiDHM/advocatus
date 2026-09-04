import sys, os
sys.path.insert(0, os.path.abspath("backend"))
from app.core.db import get_db_instance

db = get_db_instance()
docs = list(db.documents.find({"status": {"$ne": "DELETED"}}).sort("created_at", -1))

print("\n" + "="*80)
print(f"{'EMRI I DOKUMENTIT':<38} | {'STATUSI':<10} | {'FAQET':<6} | {'KARAKTERE':<10}")
print("="*80)
for d in docs:
    fname = str(d.get("file_name") or "Pa emër")[:38]
    stat = str(d.get("status") or "N/A")
    pages = d.get("page_count") or d.get("pages") or 0
    txt = d.get("extracted_text") or d.get("content") or ""
    txt_len = len(txt.strip())
    print(f"{fname:<38} | {stat:<10} | {pages:<6} | {txt_len:<10}")
print("="*80 + "\n")