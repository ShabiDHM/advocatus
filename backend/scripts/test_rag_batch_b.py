# backend/scripts/test_rag_batch_b.py
"""V282.34: Verifikon fix-et e batch B të RAG."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.cross_doc_comparator import (
    _ARTICLE_RE as COMPARE_ARTICLE_RE,
    extract_articles_per_document,
)
from app.services.rag.timeline_builder import _find_all_dates

fails = 0

# ─── T1: cross_doc_comparator regex (diaeresis) ───
print("\n=== T1: Cross-doc regex ===")
cases = ["Neni 5", "Nenit 5", "Nenin 5", "Nenët 5", "Nenet 5", "Nene 5"]
for t in cases:
    m = COMPARE_ARTICLE_RE.search(t)
    ok = m and m.group(1) == "5"
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {t!r} → {m.group(1) if m else None}")

# ─── T2: extract_articles_per_document ───
# Design: regex match-on çdo "Nen X" veç e veç (jo lista me presje).
# Kjo është sjellja origjinale — fix V1.3 ishte VETËM për diaeresis.
print("\n=== T2: extract_articles_per_document ===")
docs = [
    {"file_name": "doc1.pdf", "content": "Nenet 5 dhe Neni 6 dhe Neni 7 të Ligjit Nr. 06/L-074."},
    {"file_name": "doc2.pdf", "content": "Neni 5 dhe Nenet 8 të Ligjit Nr. 06/L-074."},
]
res = extract_articles_per_document(docs)
doc1_articles = res.get("doc1.pdf", {}).get("articles", [])
doc2_articles = res.get("doc2.pdf", {}).get("articles", [])

# doc1 ka Nenet 5, Neni 6, Neni 7 → të tre duhet të nxirren
ok_doc1 = set(doc1_articles) == {"5", "6", "7"}
# doc2 ka Neni 5, Nenet 8 → {5, 8}
ok_doc2 = set(doc2_articles) == {"5", "8"}
fails += 0 if ok_doc1 else 1
fails += 0 if ok_doc2 else 1
print(f"{'OK  ' if ok_doc1 else 'FAIL'} doc1 (Nenet 5, Neni 6, Neni 7) → {doc1_articles}")
print(f"{'OK  ' if ok_doc2 else 'FAIL'} doc2 (Neni 5, Nenet 8) → {doc2_articles}")

# ─── T3: timeline validim dite ───
print("\n=== T3: Timeline date validation ===")
cases = [
    ("Data 15 Janar 2024",     True,  "2024-01-15"),
    ("Data 31 Shkurt 2024",    False, None),   # 31 Shkurt invalid (Shkurt=02)
    ("Data 29 Shkurt 2024",    True,  "2024-02-29"),  # vit i brishtë
    ("Data 29 Shkurt 2023",    False, None),   # 2023 jo i brishtë
    ("Data 31 Prill 2024",     False, None),   # Prill=04 max 30
    ("Data 15.02.2024",        True,  "2024-02-15"),
    ("Data 31.02.2024",        False, None),   # numeric Feb 31
    ("Data 40 Janar 2024",     False, None),
    ("Data 15 Janar 1800",     False, None),
]
for text, should_exist, expected_iso in cases:
    results = _find_all_dates(text)
    if expected_iso:
        ok = any(r["iso"] == expected_iso for r in results)
    else:
        ok = len(results) == 0
    fails += 0 if ok else 1
    display = [r["iso"] for r in results] if results else "(asnjë)"
    print(f"{'OK  ' if ok else 'FAIL'} {text!r:30} → {display}")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)