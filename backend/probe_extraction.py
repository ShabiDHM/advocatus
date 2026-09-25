# FILE: backend/probe_extraction.py
# Zbulon strukturën e case_extractions.
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.db import get_db
from bson import ObjectId

db = get_db()
case_id = "6ab42c76b6e7f311be56c2ae"
doc_ids = [
    "6ab42cb6b6e7f311be56c2af",   # deep_seek_kallxim.docx
    "6ab4e2b75124df1bbc8c639d",   # Vendimi_per_urdher_mbrojtje.pdf
]

print("=" * 78)
print("PROBE — struktura e case_extractions")
print("=" * 78)

# 1. Sa dokumente në koleksion?
total = db["case_extractions"].count_documents({})
print(f"\n📊 Total në case_extractions: {total}")

# 2. Gjej të gjitha për këtë case (string)
found = list(db["case_extractions"].find({"case_id": case_id}))
print(f"📊 Me case_id='{case_id}' (string): {len(found)}")

# 3. Gjej me ObjectId
try:
    c_oid = ObjectId(case_id)
    found_oid = list(db["case_extractions"].find({"case_id": c_oid}))
    print(f"📊 Me case_id=ObjectId(...): {len(found_oid)}")
except Exception as e:
    print(f"⚠️ ObjectId: {e}")

# 4. Shfaq strukturën e një dokumenti
print("\n" + "=" * 78)
print("STRUKTURA E DOKUMENTIT (keys + types)")
print("=" * 78)

if found:
    d = found[0]
    for k, v in d.items():
        if isinstance(v, dict):
            print(f"  {k}: dict  keys={list(v.keys())[:10]}")
        elif isinstance(v, list):
            print(f"  {k}: list  len={len(v)}")
            if v and isinstance(v[0], dict):
                print(f"      [0] keys={list(v[0].keys())[:10]}")
        elif isinstance(v, str):
            preview = v[:80].replace("\n", " ")
            print(f"  {k}: str  len={len(v)}  preview='{preview}...'")
        else:
            print(f"  {k}: {type(v).__name__}  value={v}")

# 5. Shfaq të gjitha dokumentet
print("\n" + "=" * 78)
print(f"DOKUMENTET ({len(found)})")
print("=" * 78)
for i, d in enumerate(found, 1):
    print(f"\n--- {i}. _id={d.get('_id')} ---")
    for k, v in d.items():
        if k == "_id":
            continue
        if isinstance(v, str):
            preview = v[:120].replace("\n", " ")
            print(f"  {k}: str(len={len(v)}) = '{preview}'")
        elif isinstance(v, dict):
            print(f"  {k}: dict  keys={list(v.keys())[:15]}")
            # Thello nëse ka documents dict
            for sk, sv in list(v.items())[:5]:
                if isinstance(sv, dict):
                    print(f"      .{sk}: dict keys={list(sv.keys())[:10]}")
                    for ssk, ssv in list(sv.items())[:5]:
                        if isinstance(ssv, str):
                            prev = ssv[:100].replace("\n", " ")
                            print(f"          .{ssk}: str(len={len(ssv)}) = '{prev}'")
                        elif isinstance(ssv, dict):
                            print(f"          .{ssk}: dict keys={list(ssv.keys())[:8]}")
                elif isinstance(sv, str):
                    prev = sv[:100].replace("\n", " ")
                    print(f"      .{sk}: str(len={len(sv)}) = '{prev}'")
        elif isinstance(v, list):
            print(f"  {k}: list(len={len(v)})")
            if v and isinstance(v[0], dict):
                print(f"      [0] keys={list(v[0].keys())[:10]}")
                for kk, vv in list(v[0].items())[:8]:
                    if isinstance(vv, str):
                        prev = vv[:80].replace("\n", " ")
                        print(f"          .{kk}: str(len={len(vv)}) = '{prev}'")
        else:
            print(f"  {k}: {type(v).__name__} = {v}")

# 6. Kontrollo edhe për dokumentet individualisht
print("\n" + "=" * 78)
print("KONTROLL INDIVIDUAL PËR ÇDO DOC_ID")
print("=" * 78)
for did in doc_ids:
    print(f"\n🔎 doc_id={did}")
    for key in ("document_id", "doc_id", "id"):
        matches = list(db["case_extractions"].find({key: did}))
        if matches:
            print(f"   ✓ gjetur me '{key}': {len(matches)}")
            break
        try:
            oid = ObjectId(did)
            matches = list(db["case_extractions"].find({key: oid}))
            if matches:
                print(f"   ✓ gjetur me '{key}' (ObjectId): {len(matches)}")
                break
        except Exception:
            pass
    else:
        print(f"   ✗ nuk u gjet me document_id/doc_id/id")