# FILE: backend/scripts/create_indexes.py
# PHOENIX PROTOCOL - MONGODB INDEXES V1.1
#
# V1.1: FIX G4 (auditim i testeve).
#   - _create_index kap IndexOptionsConflict (code 85) si WARNING, jo ERROR
#   - MongoDB lejon vetëm NJË text index për collection — raportohet qartë
#
# V1.0: Krijon indekset e nevojshme për Bibliotekën Ligjore.
#
# Sigurt: IDEMPOTENT (mund të ekzekutohet shumë herë pa dëm).
# NUK FSHIN asnjë indeks ekzistues.
#
# Përdorimi:
#   cd backend
#   python -m scripts.create_indexes

import os
import sys
import logging
from typing import List, Tuple, Dict, Any

# Shto backend/ në path për të importuar app.core.db
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("create_indexes")


COLLECTION_NAME = "legal_knowledge_base"


# ═══════════════════════════════════════════════════════════════════════════
# INDEKSET E PLANIFIKUARA
# ═══════════════════════════════════════════════════════════════════════════

INDEXES: List[Tuple[Any, Dict[str, Any], str]] = [
    # ═══ 1. TEXT SEARCH (P2 i laws_search_service V23.0) ═══
    (
        [("law_title", "text"), ("source", "text")],
        {
            "name": "idx_text_law_title_source",
            "weights": {"law_title": 10, "source": 5},
            "default_language": "none",
            "background": True,
        },
        "Text search mbi titullin e ligjit + source",
    ),

    # ═══ 2. ARTICLE LOOKUP ═══
    (
        [("is_article", 1), ("article_number", 1), ("law_title", 1)],
        {
            "name": "idx_article_lookup",
            "background": True,
        },
        "Kërkim i nenit specifik në një ligj",
    ),

    # ═══ 3. LAW TITLE + CHUNK INDEX ═══
    (
        [("law_title", 1), ("chunk_index", 1)],
        {
            "name": "idx_law_title_chunk",
            "background": True,
        },
        "Sort i chunks sipas rendit për një ligj",
    ),

    # ═══ 4. IS_ARTICLE + LAW_TITLE ═══
    (
        [("is_article", 1), ("law_title", 1)],
        {
            "name": "idx_is_article_law_title",
            "background": True,
        },
        "Listim statutuesh (distinct law_title)",
    ),

    # ═══ 5. SOURCE ═══
    (
        [("source", 1)],
        {
            "name": "idx_source",
            "background": True,
        },
        "Mapim filename → source (PDF router)",
    ),

    # ═══ 6. CASE_NUMBER ═══
    (
        [("case_number", 1)],
        {
            "name": "idx_case_number",
            "background": True,
            "sparse": True,
        },
        "Kërkim aktgjykimesh sipas numrit",
    ),

    # ═══ 7. IS_CASE_LAW + CATEGORY ═══
    (
        [("is_case_law", 1), ("category", 1)],
        {
            "name": "idx_is_case_law_category",
            "background": True,
            "sparse": True,
        },
        "Filtër i shpejtë caselaw vs statutes",
    ),

    # ═══ 8. PAGE ═══
    (
        [("page", 1)],
        {
            "name": "idx_page",
            "background": True,
            "sparse": True,
        },
        "Gjetja e faqes fillestare (skip TOC 1-20)",
    ),

    # ═══ 9. CHUNK_ID ═══
    (
        [("chunk_id", 1)],
        {
            "name": "idx_chunk_id",
            "background": True,
            "unique": False,
            "sparse": True,
        },
        "Lookup i chunk-ut sipas ID",
    ),

    # ═══ 10. ACTUAL_PAGE ═══
    (
        [("article_number", 1), ("actual_page", 1)],
        {
            "name": "idx_article_actual_page",
            "background": True,
            "sparse": True,
        },
        "Gjetja e faqes reale për një nen",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# EKZEKUTIMI
# ═══════════════════════════════════════════════════════════════════════════

def _get_db():
    """Merr database instance nga app.core.db."""
    try:
        from app.core.db import get_db_instance
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        logger.error(
            "Sigurohu që ekzekutohet nga backend/ dhe që .env ka MONGODB_URI."
        )
        raise

    db = get_db_instance()
    if db is None:
        raise RuntimeError("get_db_instance() ktheu None — kontrollo config")
    return db


def _existing_index_names(collection) -> set:
    """Kthen setin e emrave të indekseve ekzistues."""
    try:
        existing = collection.index_information()
        return set(existing.keys())
    except Exception as e:
        logger.warning(f"Kontroll indeksesh ekzistues dështoi: {e}")
        return set()


def _create_index(collection, keys, options: Dict[str, Any], description: str) -> bool:
    """
    V1.1 (G4 fix): Krijon një indeks. IDEMPOTENT:
    - Nëse ekziston me të njëjtin emër → skip
    - Nëse konflikt (code 85 IndexOptionsConflict) → WARN, jo ERROR
    - Tjetër → error
    """
    name = options.get("name", "unnamed")
    try:
        existing = collection.index_information()
        if name in existing:
            logger.info(f"⏭️  SKIP: '{name}' ekziston tashmë — {description}")
            return True

        result_name = collection.create_index(keys, **options)
        logger.info(f"✅ KRIJUAR: '{result_name}' — {description}")
        return True
    except Exception as e:
        err_code = getattr(e, "code", None)
        # G4: Text index conflict — MongoDB lejon vetëm NJË text index
        if err_code == 85:
            logger.warning(
                f"⚠️  KONFLIKT: '{name}' — ekziston text index tjetër me opsione të ndryshme."
            )
            logger.warning(
                f"        MongoDB lejon vetëm NJË text index për collection."
            )
            logger.warning(
                f"        Nëse dëshiron indeksin e ri, duhet DROP i atij ekzistues."
            )
            logger.warning(
                f"        Aktualisht, search-i përdor $regex (jo $text) → nuk ka impakt."
            )
            return True   # Nuk është fatal
        logger.error(f"❌ DËSHTOI: '{name}' — {e}")
        return False


def create_all_indexes() -> int:
    """
    Krijon të gjitha indekset e planifikuara.
    Returns: numri i indekseve të krijuar me sukses (jo skip).
    """
    logger.info("═" * 75)
    logger.info("MONGODB INDEX CREATION — legal_knowledge_base")
    logger.info("═" * 75)

    try:
        db = _get_db()
    except Exception as e:
        logger.error(f"Nuk mund të lidhem me DB: {e}")
        return -1

    collection = db[COLLECTION_NAME]

    try:
        doc_count = collection.estimated_document_count()
        logger.info(f"Koleksioni '{COLLECTION_NAME}': ~{doc_count} dokumente")
    except Exception as e:
        logger.warning(f"estimated_document_count dështoi: {e}")

    existing = _existing_index_names(collection)
    logger.info(f"Indekse ekzistues: {len(existing)}")
    for idx_name in sorted(existing):
        logger.info(f"   • {idx_name}")
    logger.info("")

    success = 0
    skipped = 0

    for i, (keys, options, description) in enumerate(INDEXES, start=1):
        name = options.get("name", f"unnamed_{i}")
        logger.info(f"[{i}/{len(INDEXES)}] {name}")
        logger.info(f"        Fusha: {keys}")
        logger.info(f"        Qëllimi: {description}")

        if name in existing:
            logger.info(f"        → SKIP (ekziston)\n")
            skipped += 1
            continue

        if _create_index(collection, keys, options, description):
            success += 1
            existing.add(name)
        logger.info("")

    logger.info("═" * 75)
    logger.info(f"PËRMBLEDHJE: {success} të krijuar, {skipped} të skip-uar")
    logger.info("═" * 75)

    logger.info("\nIndekse finale:")
    try:
        final = collection.index_information()
        for idx_name, idx_info in sorted(final.items()):
            keys_str = ", ".join(
                f"{k}:{v}" if isinstance(v, int) else f"{k}:{v}"
                for k, v in idx_info.get("key", [])
            )
            logger.info(f"   • {idx_name}  ({keys_str})")
    except Exception as e:
        logger.warning(f"Listim final dështoi: {e}")

    return success


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    try:
        result = create_all_indexes()
        if result < 0:
            sys.exit(1)
        logger.info(f"\n✅ Përfunduar. ({result} indekse të reja)")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Anuluar nga user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Gabim fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()