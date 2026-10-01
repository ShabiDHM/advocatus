# FILE: backend/scripts/verify_orphans.py
"""
V282.34: Verifikim i drejtpërdrejtë për file-at 'e padorëzuar'.
Grep tekstual në app/ për çdo term specifik.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"

# Emrat specifikë për t'u verifikuar
TARGETS = [
    # (module_emri_per_grep, shpjegim)
    ("hallucination.checker", "checker.py brenda hallucination/"),
    ("hallucination import", "importi i paketës hallucination"),
    ("from .checker", "relative import brenda hallucination/"),
    ("from . import checker", "relative import brenda hallucination/"),
    ("mongo_verifier.orchestrator", "orchestrator.py"),
    ("mongo_verifier import", "importi i paketës mongo_verifier"),
    ("from .orchestrator", "relative import brenda mongo_verifier/"),
    ("from . import orchestrator", "relative import brenda mongo_verifier/"),
    ("precedent_search.query_builder", "query_builder.py"),
    ("precedent_search import", "importi i paketës precedent_search"),
    ("from .query_builder", "relative import brenda precedent_search/"),
    ("from . import query_builder", "relative import brenda precedent_search/"),
    ("from .verifier", "relative import brenda verify/"),
    ("from . import verifier", "relative import brenda verify/"),
    ("from .report_builder", "relative import brenda verify/"),
]

print(f"\n{'=' * 78}")
print("VERIFIKIM DIREKT PËR ORPHANS")
print(f"{'=' * 78}")

for term, desc in TARGETS:
    hits = []
    for f in APP.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if term in txt:
            rel = str(f.relative_to(BACKEND)).replace("\\", "/")
            # Numëro occurrences
            cnt = txt.count(term)
            hits.append((rel, cnt))

    print(f"\n▶ '{term}'  ({desc})")
    if hits:
        for rel, cnt in hits[:10]:
            print(f"    {rel}  ×{cnt}")
    else:
        print(f"    (asnjë hit)")