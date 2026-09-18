# FILE: backend/scripts/optimize_laws_indexes.py
# PHOENIX PROTOCOL - PHASE 2: MONGO INDEX OPTIMIZATION V1.0
# Krijon 6 indekse për koleksionin legal_knowledge_base.
# I sigurt për t'u ekzekutuar disa herë (idempotent — kontrollon para krijimit).
#
# Përdorimi:
#   cd backend
#   python scripts/optimize_laws_indexes.py
#
# Për të fshirë një indeks specifik:
#   db.legal_knowledge_base.dropIndex("idx_emri")

import sys
import os
from pathlib import Path
from datetime import datetime

# Shto backend/ në sys.path që të importohet app.*
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import get_db_instance

COLLECTION_NAME = "legal_knowledge_base"

# ═══════════════════════════════════════════════════════════════════════════
# INDEKSET E REJA
# ═══════════════════════════════════════════════════════════════════════════
NEW_INDEXES = [
    {
        "name": "idx_chunk_id_unique",
        "keys": [("chunk_id", 1)],
        "options": {"unique": True, "sparse": True, "name": "idx_chunk_id_unique"},
        "reason": "get_law_chunk — lookup direkt sipas chunk_id",
    },
    {
        "name": "idx_article_is_article",
        "keys": [("article_number", 1), ("is_article", 1)],
        "options": {"name": "idx_article_is_article", "sparse": True},
        "reason": "get_law_article, get_law_articles, ai_semantic_law_search",
    },
    {
        "name": "idx_case_number",
        "keys": [("case_number", 1)],
        "options": {"name": "idx_case_number", "sparse": True},
        "reason": "get_case_starting_page, caselaw lookups",
    },
    {
        "name": "idx_law_title",
        "keys": [("law_title", 1)],
        "options": {"name": "idx_law_title", "sparse": True},
        "reason": "Exact matches, distinct() në get_law_titles",
    },
    {
        "name": "idx_page",
        "keys": [("page", 1)],
        "options": {"name": "idx_page", "sparse": True},
        "reason": "get_case_starting_page sort + filter page > 20",
    },
    {
        "name": "idx_source",
        "keys": [("source", 1)],
        "options": {"name": "idx_source", "sparse": True},
        "reason": "distinct('source') në get_law_titles",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _line(char: str = "─", length: int = 70) -> None:
    print(char * length)


def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def _err(msg: str) -> None:
    print(f"  ❌ {msg}")


def _info(msg: str) -> None:
    print(f"  ℹ️  {msg}")


# ═══════════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════════

def show_collection_stats(coll) -> None:
    _section("1. STATISTIKAT E KOLEKSIONIT")

    try:
        total = coll.estimated_document_count()
        _info(f"Koleksioni: {COLLECTION_NAME}")
        _info(f"Numri i dokumenteve (approx): {total:,}")
    except Exception as e:
        _warn(f"estimated_document_count dështoi: {e}")

    try:
        stats = coll.database.command("collstats", COLLECTION_NAME)
        size_mb = stats.get("size", 0) / (1024 * 1024)
        storage_mb = stats.get("storageSize", 0) / (1024 * 1024)
        avg_obj = stats.get("avgObjSize", 0)
        _info(f"Madhësia logjike: {size_mb:.2f} MB")
        _info(f"Madhësia në disk: {storage_mb:.2f} MB")
        _info(f"Mesatarja e dokumentit: {avg_obj} bytes")
    except Exception as e:
        _warn(f"collstats dështoi: {e}")


def show_existing_indexes(coll) -> set:
    _section("2. INDEKSET EKZISTUESE")

    existing_names = set()
    try:
        indexes = list(coll.list_indexes())
        for idx in indexes:
            name = idx.get("name", "?")
            keys = dict(idx.get("key", {}))
            existing_names.add(name)

            # Formato key
            key_str = ", ".join(f"{k}: {v}" for k, v in keys.items())
            extras = []
            if idx.get("unique"):
                extras.append("unique")
            if idx.get("sparse"):
                extras.append("sparse")

            tag = f" [{', '.join(extras)}]" if extras else ""
            print(f"  📌 {name}{tag}")
            print(f"      keys: {key_str}")

        _info(f"Total: {len(existing_names)} indekse ekzistuese")
    except Exception as e:
        _err(f"list_indexes dështoi: {e}")

    return existing_names


# ═══════════════════════════════════════════════════════════════════════════
# CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_missing_indexes(coll, existing_names: set) -> dict:
    _section("3. KRIJIMI I INDEKSEVE TË REJA")

    results = {"created": [], "skipped": [], "failed": []}

    for idx_spec in NEW_INDEXES:
        idx_name = idx_spec["name"]

        if idx_name in existing_names:
            _warn(f"Skip: {idx_name} (ekziston tashmë)")
            results["skipped"].append(idx_name)
            continue

        try:
            start = datetime.now()
            coll.create_index(idx_spec["keys"], **idx_spec["options"])
            elapsed_ms = (datetime.now() - start).total_seconds() * 1000

            _ok(f"Krijuar: {idx_name} ({elapsed_ms:.0f} ms) — {idx_spec['reason']}")
            results["created"].append(idx_name)

        except Exception as e:
            _err(f"Dështoi: {idx_name} — {e}")
            results["failed"].append({"name": idx_name, "error": str(e)})

    return results


def verify_new_indexes(coll) -> None:
    _section("4. VERIFIKIMI I INDEKSEVE")

    try:
        current = {idx.get("name") for idx in coll.list_indexes()}

        for idx_spec in NEW_INDEXES:
            name = idx_spec["name"]
            if name in current:
                _ok(f"Verifikuar: {name}")
            else:
                _err(f"Mungon: {name}")

    except Exception as e:
        _err(f"Verifikimi dështoi: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# EXPLAIN (OPTIONAL — MATJE)
# ═══════════════════════════════════════════════════════════════════════════

def show_sample_explain(coll) -> None:
    _section("5. TEST (EXPLAIN) PËR NJË QUERY REAL")

    samples = [
        ("Lookup sipas chunk_id", {"chunk_id": "test-chunk-id"}),
        ("Lookup sipas article + is_article", {"article_number": "1", "is_article": True}),
        ("Lookup sipas case_number", {"case_number": {"$regex": "^PML", "$options": "i"}}),
    ]

    for label, query in samples:
        try:
            explain = coll.find(query).limit(1).explain()
            plan = explain.get("queryPlanner", {}).get("winningPlan", {})
            stage = _extract_stage(plan)
            print(f"  🔍 {label}")
            print(f"      Stage: {stage}")
        except Exception as e:
            _warn(f"Explain dështoi për '{label}': {e}")


def _extract_stage(plan: dict) -> str:
    """Nxjerr emrin e fazës së planit (rekursiv)."""
    if not isinstance(plan, dict):
        return "?"
    stage = plan.get("stage", "?")
    if "inputStage" in plan:
        return f"{stage} → {_extract_stage(plan['inputStage'])}"
    if "inputStages" in plan:
        subs = " | ".join(_extract_stage(s) for s in plan["inputStages"])
        return f"{stage} → [{subs}]"
    return stage


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    print("\n" + "█" * 70)
    print("  PHOENIX PROTOCOL — FAZA 2: MONGO INDEX OPTIMIZATION")
    print("  Koleksioni: " + COLLECTION_NAME)
    print("█" * 70)

    try:
        db = get_db_instance()
    except Exception as e:
        _err(f"Nuk mund të lidhem me MongoDB: {e}")
        return 1

    coll = db[COLLECTION_NAME]

    # 1. Stats
    show_collection_stats(coll)

    # 2. Indexes ekzistuese
    existing = show_existing_indexes(coll)

    # 3. Krijo indekset e reja
    results = create_missing_indexes(coll, existing)

    # 4. Verifiko
    verify_new_indexes(coll)

    # 5. Explain sample (opsionale, për matje)
    show_sample_explain(coll)

    # ═══ RAPORT FINAL ═══
    _section("6. RAPORT FINAL")

    _ok(f"Krijuar: {len(results['created'])} indekse")
    for name in results["created"]:
        print(f"      • {name}")

    if results["skipped"]:
        _warn(f"Skip (ekzistues): {len(results['skipped'])}")
        for name in results["skipped"]:
            print(f"      • {name}")

    if results["failed"]:
        _err(f"Dështuan: {len(results['failed'])}")
        for item in results["failed"]:
            print(f"      • {item['name']}: {item['error']}")
        return 1

    print("\n" + "█" * 70)
    print("  ✅ FAZA 2 PËRFUNDOI ME SUKSES")
    print("  Indekset e reja janë aktive menjëherë.")
    print("  Kërkimet në /laws/* duhet të përmirësohen ndjeshëm.")
    print("█" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())