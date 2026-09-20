# FILE: backend/_tests_dev/_diagnose_roles.py
"""Diagnostikon pse rolet e palëve janë të përmbysura."""
import sys
from bson import ObjectId
from app.core.db import get_db_instance
from app.services.synthesis.case_types import detect_case_type
from app.services.synthesis.digest import build_digest


CASE_ID = "6aaf15fcbb7612ffc88db1ab"

db = get_db_instance()

# ═══ 1. CASE INFO ═══
case = db.cases.find_one({"_id": ObjectId(CASE_ID)}) or {}
print("=" * 72)
print("CASE INFO")
print("=" * 72)
for k in ["title", "case_name", "client_name", "client_position",
          "client_role", "client", "opposing_party", "defendants_groups"]:
    v = case.get(k)
    if isinstance(v, list) and len(v) > 3:
        v = f"{len(v)} items (truncated)"
    print(f"  {k}: {v}")
print()

# ═══ 2. EXTRACTIONS ═══
extractions = list(db.case_extractions.find({"case_id": CASE_ID}))
print(f"Extractions: {len(extractions)}")
print("=" * 72)
for ext in extractions:
    print(f"\nDoc: {ext.get('file_name')}")
    meta = ext.get("metadata", {}) or {}
    print(f"  metadata.parties: {meta.get('parties')}")
    print(f"  metadata.court: {meta.get('court')}")
    print(f"  metadata.judge: {meta.get('judge')}")
    ebt = ext.get("entities_by_type", {}) or {}
    print(f"  entities PARTY: {[(i.get('text'), i.get('role')) for i in ebt.get('PARTY', [])]}")
    print(f"  entities ORGANIZATION: {[i.get('text') for i in ebt.get('ORGANIZATION', [])]}")

# ═══ 3. DIGEST ═══
xrefs = db.case_cross_references.find_one({"case_id": CASE_ID}) or {}
defendants_groups = case.get("defendants_groups", []) or []

articles_by_law = {}  # Skip
verified_citations = None

case_type = detect_case_type(db, CASE_ID, extractions)
digest = build_digest(
    case, extractions, xrefs, defendants_groups,
    articles_by_law, case_type, verified_citations
)

print()
print("=" * 72)
print(f"DIGEST ({len(digest)} chars)")
print("=" * 72)
print(digest)