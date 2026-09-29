# FILE: backend/scripts/mark_repealed_laws.py
# PHOENIX PROTOCOL - MARK REPEALED LAWS V1.0
#
# Migration script: Lexon `data/repealed_laws.json` dhe shënon në DB
# fushat `is_repealed`, `repealed_by`, `repealed_date`, `repealed_source`
# për dokumentet përkatëse.
#
# IDEMPOTENT: mund të ekzekutohet shumë herë. Edhe për të bërë revert
# (nëse regjistri ndryshon, docs përditësohen).
#
# Përdorimi:
#   cd backend
#   python -m scripts.mark_repealed_laws
#
# Për dry-run (vetëm kontroll, pa shkrim):
#   python -m scripts.mark_repealed_laws --dry-run

import os
import sys
import re
import argparse
import logging
from typing import List, Dict, Any

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mark_repealed_laws")

COLLECTION_NAME = "legal_knowledge_base"


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


def _normalize_diacritics(s: str) -> str:
    if not s:
        return ""
    mp = {
        'ë': 'e', 'ç': 'c', 'â': 'a', 'î': 'i', 'û': 'u',
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
    }
    result = s
    for k, v in mp.items():
        result = result.replace(k, v)
    return result


def _normalize(s: str) -> str:
    if not s:
        return ""
    n = _normalize_diacritics(s.lower())
    return re.sub(r'\s+', ' ', n).strip()


def _find_matching_docs(collection, patterns: List[str]) -> List[Dict[str, Any]]:
    """
    Gjen docs që përputhen me një nga patterns (case + diakritika normalized).
    """
    # Kërkim në DB me regex fleksibel
    or_conditions = []
    for pattern in patterns:
        # Escape regex + lejo fleksibilitet për hapësira
        flexible = re.escape(pattern)
        flexible = flexible.replace(r'\ ', r'[\s\.\-_]*')  # hapësira → çdo separator
        or_conditions.append({"law_title": {"$regex": flexible, "$options": "i"}})

    if not or_conditions:
        return []

    query = {"$or": or_conditions}
    projection = {"law_title": 1, "source": 1, "_id": 1}

    return list(collection.find(query, projection))


def _verify_match(doc_title: str, patterns: List[str]) -> bool:
    """
    Double-check në Python që doc_title përputhet realisht.
    Kjo shmang false-positive nga regex.
    """
    norm_doc = _normalize(doc_title)
    for pattern in patterns:
        norm_pattern = _normalize(pattern)
        if norm_pattern and norm_pattern in norm_doc:
            return True
    return False


def mark_repealed(dry_run: bool = False) -> int:
    """
    Returns: 0 = OK, 1 = error
    """
    logger.info("═" * 75)
    logger.info("MARK REPEALED LAWS")
    logger.info(f"Mode: {'DRY-RUN (pa shkrim)' if dry_run else 'EXECUTE'}")
    logger.info("═" * 75)

    # 1. Ngarko regjistrin
    try:
        from app.api.endpoints.laws_pkg.repealed_registry import load_repealed_registry
        registry = load_repealed_registry(force_reload=True)
    except Exception as e:
        logger.error(f"Regjistri load failed: {e}")
        return 1

    repealed_entries = registry.get("repealed", [])
    if not repealed_entries:
        logger.warning("Regjistri është bosh — asnjë veprim")
        return 0

    logger.info(f"\nRegjistri: {len(repealed_entries)} ligje të shfuqizuara")

    # 2. Lidhu me DB
    try:
        db = _get_db()
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return 1

    collection = db[COLLECTION_NAME]

    total_docs_matched = 0
    total_docs_updated = 0

    # 3. Për çdo ligj të shfuqizuar
    for idx, entry in enumerate(repealed_entries, start=1):
        entry_id = entry.get("id", f"entry-{idx}")
        patterns = entry.get("title_patterns", [])
        repealed_by = entry.get("repealed_by", "")
        repealed_date = entry.get("repealed_date", "")
        source = entry.get("source", "")

        logger.info(f"\n[{idx}/{len(repealed_entries)}] {entry_id}")
        logger.info(f"     Patterns: {len(patterns)}")

        # Gjej docs
        try:
            docs = _find_matching_docs(collection, patterns)
        except Exception as e:
            logger.error(f"     Query failed: {e}")
            continue

        # Double-check në Python
        verified_docs = [
            d for d in docs
            if _verify_match(d.get("law_title", ""), patterns)
        ]

        logger.info(f"     Matched: {len(verified_docs)} docs (nga {len(docs)} kandidatë)")

        if not verified_docs:
            continue

        total_docs_matched += len(verified_docs)

        # Përditëso
        if dry_run:
            logger.info(f"     [DRY-RUN] Do përditësoheshin {len(verified_docs)} docs")
            # Shembull
            for d in verified_docs[:3]:
                logger.info(f"       • {d.get('law_title', '')[:70]}")
            continue

        ids = [d["_id"] for d in verified_docs if "_id" in d]
        try:
            result = collection.update_many(
                {"_id": {"$in": ids}},
                {"$set": {
                    "is_repealed": True,
                    "repealed_by": repealed_by,
                    "repealed_date": repealed_date,
                    "repealed_source": source,
                    "repealed_id": entry_id,
                }},
            )
            total_docs_updated += result.modified_count
            logger.info(f"     ✅ Updated: {result.modified_count} docs")
        except Exception as e:
            logger.error(f"     Update failed: {e}")

    logger.info("")
    logger.info("═" * 75)
    if dry_run:
        logger.info(f"DRY-RUN: {total_docs_matched} docs do përditësoheshin")
    else:
        logger.info(f"PËRFUNDUAR: {total_docs_updated} docs të përditësuar (nga {total_docs_matched} matched)")
    logger.info("═" * 75)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Shënon ligjet e shfuqizuara në DB."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Vetëm kontroll, pa shkrim.")
    args = parser.parse_args()

    try:
        code = mark_repealed(dry_run=args.dry_run)
        sys.exit(code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Anuluar")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Gabim fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()