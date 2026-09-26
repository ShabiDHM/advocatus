# check_db_suspects.py
from bson import ObjectId
from app.core.db import get_db
from app.services.document_review.fact_extractor import extract_suspects

db = get_db()

print("=" * 70)
print("1) TË GJITHA CASE-t")
print("=" * 70)
cases = list(db.cases.find({}, {"_id": 1, "title": 1, "client_name": 1}))
for c in cases[:20]:
    print(f"  _id={c['_id']}  title={c.get('title', '?')}  client={c.get('client_name', '?')}")

print()
print("=" * 70)
print("2) TË GJITHA DOKUMENTET (pa filter case)")
print("=" * 70)
docs = list(db.documents.find({}).limit(50))
print(f"Total docs në DB: {db.documents.count_documents({})}")
print()

for d in docs:
    fname = d.get("file_name") or d.get("title") or "?"
    case_id = d.get("case_id")
    status = d.get("status", "?")
    content = d.get("content") or ""
    extracted = d.get("extracted_text") or ""
    text = d.get("text") or ""
    best = max([content, extracted, text], key=len)

    print(f"=== {fname} ===")
    print(f"  case_id: {case_id} (type={type(case_id).__name__})")
    print(f"  status: {status}")
    print(f"  content={len(content)}, extracted={len(extracted)}, text={len(text)}")
    print(f"  keys: {list(d.keys())[:15]}")

    if best:
        suspects = extract_suspects(best)
        print(f"  Suspects: {len(suspects)}")
        for s in suspects[:20]:
            print(f"    • {s['name']}")
    else:
        print("  ⚠️ ASNJË TEKST — kontrollo fusha tjera")

        # Provo ekstraktimet
        ext_doc = db.case_extractions.find_one({
            "$or": [
                {"document_id": str(d["_id"])},
                {"document_id": d["_id"]},
            ]
        })
        if ext_doc:
            ext_text = ext_doc.get("text") or ""
            print(f"  case_extractions.text len: {len(ext_text)}")
            if ext_text:
                suspects = extract_suspects(ext_text)
                print(f"  Suspects nga extraction: {len(suspects)}")
                for s in suspects[:20]:
                    print(f"    • {s['name']}")
        else:
            print("  ⚠️ Nuk u gjet case_extractions për këtë doc")

    print()

print("=" * 70)
print("3) CASE_EXTRACTIONS (sample)")
print("=" * 70)
exts = list(db.case_extractions.find({}).limit(10))
for e in exts:
    doc_id = e.get("document_id")
    text = e.get("text") or ""
    print(f"  doc={doc_id}, case={e.get('case_id')}, text_len={len(text)}, status={e.get('status')}")