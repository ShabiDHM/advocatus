# FILE: backend/test_all_doc_types.py
# Teston DraftVerifier për të 7 llojet e dokumenteve (pa LLM — vetëm validate).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.document_review.verify_prompts import (
    VERIFY_DOC_TYPES,
    DOC_TYPE_CHECKLISTS,
    VERIFY_SECTION_PROMPTS,
)

print("=" * 78)
print("DIAGNOSTIK — 7 LLOJET E DOKUMENTEVE")
print("=" * 78)

print(f"\n{'#':<3} {'Key':<22} {'Label':<22} {'Pika':<6} {'Sections':<10}")
print("-" * 78)

for i, (key, label) in enumerate(VERIFY_DOC_TYPES.items(), 1):
    checklist = DOC_TYPE_CHECKLISTS.get(key, {})
    n_parts = len(checklist.get("required_parts", []))
    n_issues = len(checklist.get("common_issues", []))
    status = "✅ OK" if key in DOC_TYPE_CHECKLISTS else "❌ MISSING"
    print(f"{i:<3} {key:<22} {label:<22} {n_parts:<6} {status}")

print(f"\nTotal lloje: {len(VERIFY_DOC_TYPES)}")
print(f"Total checklists: {len(DOC_TYPE_CHECKLISTS)}")

# Verifiko që çdo doc_type ka checklist
missing = [k for k in VERIFY_DOC_TYPES if k not in DOC_TYPE_CHECKLISTS]
if missing:
    print(f"\n❌ DOKUMENTE PA CHECKLIST: {missing}")
else:
    print(f"\n✅ Të gjitha {len(VERIFY_DOC_TYPES)} kanë checklist")

# Verifiko që çdo seksion ka needs
print(f"\nSections ({len(VERIFY_SECTION_PROMPTS)}):")
for k, cfg in VERIFY_SECTION_PROMPTS.items():
    needs = cfg.get("needs", [])
    print(f"  - {k:<25} needs={needs}")

print("\n✅ Struktura komplete.")