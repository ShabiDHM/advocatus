# FILE: backend/diagnose_documents.py
# Diagnostikon strukturën e koleksionit 'documents'.

from app.core.db import get_db_instance

db = get_db_instance()
print(f"✅ DB: {db.name}")
print(f"✅ Koleksioni: documents\n")

# 1. Totali
total = db.documents.count_documents({})
print(f"📊 TOTALI i dokumenteve: {total}\n")

if total == 0:
    print("❌ Koleksioni 'documents' është bosh.")
    raise SystemExit(0)

# 2. Nje dokument sample — shfaq të gjitha fushat
print("=" * 70)
print("🔍 SAMPLE i një dokumenti (fushat + tipet):")
print("=" * 70)
sample = db.documents.find_one({})
for k, v in sample.items():
    tipo = type(v).__name__
    if isinstance(v, str):
        preview = v[:60].replace("\n", " ")
        print(f"   {k:25s} ({tipo:10s}): {preview!r}")
    elif isinstance(v, (int, float, bool)):
        print(f"   {k:25s} ({tipo:10s}): {v}")
    elif v is None:
        print(f"   {k:25s} ({tipo:10s}): None")
    else:
        print(f"   {k:25s} ({tipo:10s}): <...>")

# 3. Analiza e fushave të mundshme të tekstit
print("\n" + "=" * 70)
print("📝 Analiza e fushave të tekstit (length):")
print("=" * 70)

text_fields = ["content", "extracted_text", "text", "summary", "raw_text"]
field_counts = {f: 0 for f in text_fields}
field_lengths = {f: [] for f in text_fields}

for doc in db.documents.find({}):
    for f in text_fields:
        v = doc.get(f)
        if isinstance(v, str) and v.strip():
            field_counts[f] += 1
            field_lengths[f].append(len(v))

for f in text_fields:
    count = field_counts[f]
    if count > 0:
        lengths = field_lengths[f]
        print(
            f"   {f:20s}: {count:4d} dokumente kanë këtë fushë | "
            f"min={min(lengths):6d} max={max(lengths):7d} "
            f"avg={sum(lengths)//len(lengths):6d}"
        )
    else:
        print(f"   {f:20s}: 0 dokumente")

# 4. Shpërndarja e madhësive (bazuar në fushën më të plotë)
print("\n" + "=" * 70)
print("📊 Shpërndarja e madhësive (duke përdorur 'content' ose 'extracted_text'):")
print("=" * 70)

buckets = {
    "0 (bosh)": 0,
    "1-500": 0,
    "501-5000": 0,
    "5001-50000": 0,
    "50001+": 0,
}

for doc in db.documents.find({}):
    text = (
        doc.get("content")
        or doc.get("extracted_text")
        or doc.get("text")
        or doc.get("summary")
        or ""
    )
    n = len(text)
    if n == 0:
        buckets["0 (bosh)"] += 1
    elif n <= 500:
        buckets["1-500"] += 1
    elif n <= 5000:
        buckets["501-5000"] += 1
    elif n <= 50000:
        buckets["5001-50000"] += 1
    else:
        buckets["50001+"] += 1

for k, v in buckets.items():
    print(f"   {k:15s}: {v:4d} dokumente")

# 5. A ka case_id?
print("\n" + "=" * 70)
print("🔗 Kontrolli i lidhjeve:")
print("=" * 70)

with_case = db.documents.count_documents({"case_id": {"$exists": True, "$ne": None}})
with_owner = db.documents.count_documents({"owner_id": {"$exists": True, "$ne": None}})
with_status = db.documents.count_documents({"status": {"$exists": True}})
print(f"   Me case_id:  {with_case}")
print(f"   Me owner_id: {with_owner}")
print(f"   Me status:   {with_status}")

# 6. Nje lende e plote si shembull
print("\n" + "=" * 70)
print("📁 Një lëndë me shumë dokumente (kandidate për test):")
print("=" * 70)

pipeline = [
    {"$group": {"_id": "$case_id", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 5},
]
for row in db.documents.aggregate(pipeline):
    print(f"   case_id={row['_id']} → {row['count']} dokumente")