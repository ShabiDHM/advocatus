# FILE: backend/scripts/check_precedent.py
# PHOENIX PROTOCOL - CHECK PRECEDENT V1.0
# Verifikon nëse një precedent (PML.Nr.X/YYYY, Rev.Nr.X/YYYY, etj.)
# ekziston në bazën e të dhënave (MongoDB + Atlas Vector Search).
#
# Përdorimi:
#   python -m scripts.check_precedent "PML.Nr.185/2025"
#   python -m scripts.check_precedent "Rev.Nr.252/2025"
#   python -m scripts.check_precedent  # test me të gjithë 13 numrat e njohur

import os
import re
import sys
import logging
from typing import List, Dict, Any

# Setup Django/Python path (nga backend/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURIMI
# ═══════════════════════════════════════════════════════════════════════════

# Koleksionet e mundshme ku mund të ruhen precedentët
PRECEDENT_COLLECTIONS = [
    "supreme_court_decisions",
    "case_numbers",
    "precedents",
    "legal_knowledge_base",
    "global_knowledge_base",
]

# Fushat e mundshme ku mund të ruhet numri i lëndës
CASE_NUMBER_FIELDS = [
    "case_number",
    "case_no",
    "case_id",
    "title",
    "raw_text",
    "content",
    "text",
]


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZIM
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_case_number(cn: str) -> str:
    """PML.Nr.185/2025 → PMLNR1852025"""
    if not cn:
        return ""
    return re.sub(r'[\s\.\-_/]+', '', cn.upper())


def _build_tolerant_regex(cn: str) -> str:
    """
    PML.Nr.185/2025 → PML[\.\s]*Nr[\.\s]*185[\.\s]*/[\.\s]*2025
    Kap variante si PML nr 185/2025, PML.Nr.185/2025, PMLNR185/2025
    """
    tokens = re.findall(r'[A-Za-z]+|\d+', cn)
    if not tokens:
        return re.escape(cn)
    parts = r'[\.\s\-_/]*'.join(re.escape(t) for t in tokens)
    return parts


# ═══════════════════════════════════════════════════════════════════════════
# VERIFIKIMI
# ═══════════════════════════════════════════════════════════════════════════

def check_in_mongo(db, case_number: str) -> List[Dict[str, Any]]:
    """Kërkon numrin në të gjitha koleksionet e mundshme."""
    pattern = _build_tolerant_regex(case_number)
    regex_ci = re.compile(pattern, re.IGNORECASE)

    found: List[Dict[str, Any]] = []

    # Listo të gjitha koleksionet në DB (për debug)
    all_collections = db.list_collection_names()
    print(f"\n  📚 Koleksionet në DB ({len(all_collections)}):")
    for c in sorted(all_collections):
        try:
            count = db[c].estimated_document_count()
            print(f"     • {c} (~{count} docs)")
        except Exception:
            print(f"     • {c} (n/a)")

    # Kërko në koleksionet e njohura + çdo koleksion me fjalë 'precedent'/'case'/'decision'
    target_collections = set(PRECEDENT_COLLECTIONS)
    for c in all_collections:
        if any(kw in c.lower() for kw in ("precedent", "case", "decision", "court", "supreme")):
            target_collections.add(c)

    print(f"\n  🎯 Duke kërkuar në {len(target_collections)} koleksione...")

    for coll_name in sorted(target_collections):
        try:
            coll = db[coll_name]
        except Exception as e:
            print(f"     ⚠️ {coll_name}: nuk hapet ({e})")
            continue

        # Kërko në të gjitha fushat e mundshme
        for field in CASE_NUMBER_FIELDS:
            try:
                docs = list(coll.find(
                    {field: {"$regex": regex_ci.pattern, "$options": "i"}},
                    {"_id": 0, field: 1, "source": 1, "page": 1, "topic_label": 1, "law_title": 1},
                ).limit(3))
                if docs:
                    found.append({
                        "collection": coll_name,
                        "field": field,
                        "count": len(docs),
                        "samples": docs,
                    })
            except Exception:
                continue

    return found


def check_in_atlas_vector(db, case_number: str) -> List[Dict[str, Any]]:
    """
    Kërkon në Atlas Vector Search nëse ka indeks.
    Nuk bën embedding — thjesht kontrollon nëse numri është i ruajtur si tekst.
    """
    found: List[Dict[str, Any]] = []
    pattern = _build_tolerant_regex(case_number)
    regex_ci = re.compile(pattern, re.IGNORECASE)

    # Provon koleksionin kryesor të vector search
    for coll_name in ["legal_knowledge_base", "supreme_court_decisions"]:
        try:
            coll = db[coll_name]
            docs = list(coll.find(
                {"$or": [
                    {"text": {"$regex": regex_ci.pattern, "$options": "i"}},
                    {"content": {"$regex": regex_ci.pattern, "$options": "i"}},
                    {"case_number": {"$regex": regex_ci.pattern, "$options": "i"}},
                ]},
                {"_id": 0, "case_number": 1, "source": 1, "page": 1, "topic_label": 1},
            ).limit(5))
            if docs:
                found.append({
                    "collection": coll_name,
                    "count": len(docs),
                    "samples": docs,
                })
        except Exception:
            continue

    return found


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    from app.core.db import get_db

    db = get_db()

    # Argumentet
    if len(sys.argv) > 1:
        case_numbers = [sys.argv[1]]
    else:
        # Default: 13 numrat e njohur nga kallëzimi
        case_numbers = [
            "PML.Nr.185/2025",
            "PML.Nr.122/2025",
            "PML.Nr.352/2025",
            "PML.Nr.272/2025",
            "PML.Nr.752/2024",
            "Rev.Nr.252/2025",
            "Rev.Nr.570/2021",
            "P.nr.869/18",
            "C.nr.385/2024",
            "C.nr.160/21",
            "C.nr.5906/2025",
            "CA.nr.3120/2024",
            "PP.II.nr.122/24F",
        ]
        print("=" * 75)
        print("  TEST BATCH — 13 numrat e njohur nga kallëzimi penal")
        print("=" * 75)

    results_summary = {}

    for cn in case_numbers:
        print(f"\n{'═' * 75}")
        print(f"  🔎 Duke verifikuar: {cn}")
        print(f"{'═' * 75}")

        mongo_found = check_in_mongo(db, cn)
        vector_found = check_in_atlas_vector(db, cn)

        all_found = mongo_found + vector_found

        if all_found:
            print(f"\n  ✅ GJEТ NË {len(all_found)} VENDE:")
            for hit in all_found:
                print(f"     📁 {hit['collection']} (field={hit.get('field', 'text')}, count={hit['count']})")
                for s in hit.get("samples", [])[:2]:
                    print(f"        → {s}")
            results_summary[cn] = "FOUND"
        else:
            print(f"\n  ❌ NUK U GJET në asnjë koleksion.")
            results_summary[cn] = "NOT_FOUND"

    # Përmbledhje
    print(f"\n\n{'═' * 75}")
    print(f"  📊 PËRMBLEDHJE")
    print(f"{'═' * 75}\n")

    found_count = sum(1 for v in results_summary.values() if v == "FOUND")
    not_found_count = sum(1 for v in results_summary.values() if v == "NOT_FOUND")

    for cn, status in results_summary.items():
        icon = "✅" if status == "FOUND" else "❌"
        print(f"  {icon}  {cn:35s}  {status}")

    print(f"\n  Gjithsej: {len(results_summary)}")
    print(f"  ✅ U gjetën: {found_count}")
    print(f"  ❌ Nuk u gjetën: {not_found_count}")

    print()


if __name__ == "__main__":
    main()