# FILE: backend/scripts/audit_db.py
# PHOENIX PROTOCOL - DB AUDIT V1.0
#
# Audit i plotë i collection 'legal_knowledge_base':
#   - Numri total i dokumenteve
#   - Shpërndarja sipas law_title, source, is_article, category
#   - Detektim dublikatësh (chunk_id, kombinime)
#   - Fushat e mangut (null/empty)
#   - Statistikat e chunks (min/max/avg për dokument)
#   - Shembull dokument (struktura)
#
# NUK modifikon asgjë. Vetëm lexon dhe raporton.
#
# Përdorimi:
#   cd backend
#   python -m scripts.audit_db
#
# Për raport të detajuar (më shumë law_titles):
#   python -m scripts.audit_db --top 50

import os
import sys
import argparse
import logging
from collections import Counter
from typing import Dict, Any, List, Tuple

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("audit_db")

COLLECTION_NAME = "legal_knowledge_base"


# ═══════════════════════════════════════════════════════════════════════════
# DB
# ═══════════════════════════════════════════════════════════════════════════

def _get_db():
    try:
        from app.core.db import get_db_instance
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        raise
    db = get_db_instance()
    if db is None:
        raise RuntimeError("get_db_instance() ktheu None")
    return db


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT
# ═══════════════════════════════════════════════════════════════════════════

def _section(title: str):
    logger.info("")
    logger.info("─" * 75)
    logger.info(title)
    logger.info("─" * 75)


def audit(top_n: int = 30) -> None:
    db = _get_db()
    coll = db[COLLECTION_NAME]

    # ═══ 1. TOTALS ═══
    _section("1. TOTALET")
    total = coll.estimated_document_count()
    logger.info(f"Total dokumente (estimated): {total}")

    try:
        exact = coll.count_documents({})
        logger.info(f"Total dokumente (exact):     {exact}")
    except Exception as e:
        logger.warning(f"count_documents dështoi: {e}")

    # ═══ 2. FUSHAT E DISTINCT ═══
    _section("2. VLERA TË DISTINCT")

    for field in ["law_title", "source", "category", "is_article", "is_case_law"]:
        try:
            values = coll.distinct(field)
            # Filtro None dhe bosh për numërimin
            non_null = [v for v in values if v is not None and v != ""]
            n_total = len(values)
            n_non_null = len(non_null)
            logger.info(f"{field:15s}: {n_non_null} vlera të vlefshme (nga {n_total} gjithsej)")
        except Exception as e:
            logger.warning(f"{field:15s}: FAIL — {e}")

    # ═══ 3. SHPËRNDARJA SIPAS law_title (top N) ═══
    _section(f"3. TOP {top_n} LAW_TITLE (sipas numrit të dokumenteve)")

    try:
        pipeline = [
            {"$match": {"law_title": {"$exists": True, "$nin": [None, ""]}}},
            {"$group": {"_id": "$law_title", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n},
        ]
        results = list(coll.aggregate(pipeline, allowDiskUse=True))
        logger.info(f"Gjetur {len(results)} law_titles të ndryshme (top):")
        for r in results:
            name = str(r["_id"])[:70]
            logger.info(f"  {r['count']:5d}  {name}")
    except Exception as e:
        logger.warning(f"Aggregation dështoi: {e}")

    # ═══ 4. SHPËRNDARJA SIPAS source (top N) ═══
    _section(f"4. TOP {top_n} SOURCE")

    try:
        pipeline = [
            {"$match": {"source": {"$exists": True, "$nin": [None, ""]}}},
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n},
        ]
        results = list(coll.aggregate(pipeline, allowDiskUse=True))
        logger.info(f"Gjetur {len(results)} source të ndryshme (top):")
        for r in results:
            name = str(r["_id"])[:70]
            logger.info(f"  {r['count']:5d}  {name}")
    except Exception as e:
        logger.warning(f"Aggregation dështoi: {e}")

    # ═══ 5. DUBLIKATË — chunk_id ═══
    _section("5. KONTROLL DUBLIKATËSH — chunk_id")

    try:
        pipeline = [
            {"$match": {"chunk_id": {"$exists": True, "$nin": [None, ""]}}},
            {"$group": {"_id": "$chunk_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        duplicates = list(coll.aggregate(pipeline, allowDiskUse=True))
        if not duplicates:
            logger.info("  ✅ Zero dublikatë chunk_id")
        else:
            logger.warning(f"  ⚠️  {len(duplicates)} chunk_id të dublikuar (top 20):")
            for d in duplicates:
                logger.warning(f"     {d['count']}x  chunk_id={str(d['_id'])[:60]}")
    except Exception as e:
        logger.warning(f"Aggregation dështoi: {e}")

    # ═══ 6. DUBLIKATË — kombinim (law_title, article_number, chunk_index) ═══
    _section("6. KONTROLL DUBLIKATËSH — (law_title, article_number, chunk_index)")

    try:
        pipeline = [
            {"$match": {
                "law_title": {"$exists": True, "$nin": [None, ""]},
                "article_number": {"$exists": True, "$nin": [None, ""]},
                "chunk_index": {"$exists": True},
            }},
            {"$group": {
                "_id": {
                    "law": "$law_title",
                    "art": "$article_number",
                    "chunk": "$chunk_index",
                },
                "count": {"$sum": 1},
            }},
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        duplicates = list(coll.aggregate(pipeline, allowDiskUse=True))
        if not duplicates:
            logger.info("  ✅ Zero dublikatë në kombinim")
        else:
            logger.warning(f"  ⚠️  {len(duplicates)} kombinime të dublikuara (top 20):")
            for d in duplicates:
                id_ = d["_id"]
                logger.warning(
                    f"     {d['count']}x  law={str(id_['law'])[:40]} "
                    f"art={id_['art']} chunk={id_['chunk']}"
                )
    except Exception as e:
        logger.warning(f"Aggregation dështoi: {e}")

    # ═══ 7. FUSHAT E MANGUT ═══
    _section("7. FUSHAT E MANGUT (null/empty)")

    checks = [
        ("law_title", {"$or": [{"law_title": None}, {"law_title": ""}, {"law_title": {"$exists": False}}]}),
        ("source", {"$or": [{"source": None}, {"source": ""}, {"source": {"$exists": False}}]}),
        ("article_number", {"$or": [{"article_number": None}, {"article_number": ""}, {"article_number": {"$exists": False}}]}),
        ("text", {"$or": [{"text": None}, {"text": ""}, {"text": {"$exists": False}}]}),
        ("chunk_index", {"chunk_index": {"$exists": False}}),
        ("page", {"$and": [{"page": {"$exists": False}}, {"page_number": {"$exists": False}}]}),
    ]

    for field, query in checks:
        try:
            n = coll.count_documents(query, limit=1_000_000)
            logger.info(f"{field:18s}: {n} dokumente të mangut")
        except Exception as e:
            logger.warning(f"{field:18s}: FAIL — {e}")

    # ═══ 8. SHPËRNDARJA is_article ═══
    _section("8. SHPËRNDARJA is_article / is_case_law / category")

    for field in ["is_article", "is_case_law", "category"]:
        try:
            pipeline = [
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            results = list(coll.aggregate(pipeline, allowDiskUse=True))
            logger.info(f"{field}:")
            for r in results:
                logger.info(f"  {r['count']:6d}  {r['_id']!r}")
        except Exception as e:
            logger.warning(f"{field}: FAIL — {e}")

    # ═══ 9. SAMPLE DOKUMENT ═══
    _section("9. SAMPLE DOKUMENT (statute)")

    try:
        doc = coll.find_one({"is_article": True})
        if doc:
            for key, val in doc.items():
                if key == "_id":
                    logger.info(f"  {key}: {val}")
                    continue
                val_str = str(val)
                if len(val_str) > 120:
                    val_str = val_str[:120] + "..."
                logger.info(f"  {key}: {val_str}")
        else:
            logger.warning("Asnjë dokument me is_article=True")
    except Exception as e:
        logger.warning(f"find_one dështoi: {e}")

    # ═══ 10. STATISTIKA CHUNKS ═══
    _section("10. STATISTIKA CHUNKS (për law_title)")

    try:
        pipeline = [
            {"$match": {"law_title": {"$exists": True, "$nin": [None, ""]}}},
            {"$group": {
                "_id": "$law_title",
                "chunks": {"$sum": 1},
                "avg_chunk_idx": {"$avg": "$chunk_index"},
                "max_chunk_idx": {"$max": "$chunk_index"},
            }},
            {"$sort": {"chunks": -1}},
            {"$limit": 15},
        ]
        results = list(coll.aggregate(pipeline, allowDiskUse=True))
        logger.info(f"{'chunks':>7s} {'avg_idx':>9s} {'max_idx':>9s}  law_title")
        for r in results:
            avg = r.get("avg_chunk_idx") or 0
            mx = r.get("max_chunk_idx") or 0
            name = str(r["_id"])[:50]
            logger.info(f"{r['chunks']:7d} {avg:9.1f} {mx:9.0f}  {name}")
    except Exception as e:
        logger.warning(f"Aggregation dështoi: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Audit i DB legal_knowledge_base.")
    parser.add_argument("--top", type=int, default=30, help="Sa law_titles të listohen (default 30)")
    args = parser.parse_args()

    logger.info("═" * 75)
    logger.info("DB AUDIT — legal_knowledge_base")
    logger.info("═" * 75)

    try:
        audit(top_n=args.top)
        logger.info("")
        logger.info("═" * 75)
        logger.info("✅ Audit përfundoi")
        logger.info("═" * 75)
        sys.exit(0)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Anuluar")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Gabim fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()