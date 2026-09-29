# FILE: backend/scripts/recreate_text_index.py
# PHOENIX PROTOCOL - RECREATE TEXT INDEX V1.0
#
# ZGJIDHJA E KONFLIKTIT TË TEXT INDEX:
#   - MongoDB lejon vetëm NJË text index për collection
#   - Ekzistuesi: 'text_text_title_text_law_title_text' me:
#       * default_language: "english"   ← problem për shqip (stemming anglez)
#       * weights: {text:1, title:1, law_title:1}
#   - I riu (shqip-friendly):
#       * default_language: "none"      ← pa stemming/stopwords
#       * weights: {law_title:10, source:5, text:1}
#
# Ky skript:
#   1. Kontrollon indekset ekzistuese
#   2. DROP text index ekzistues (backup i emrit)
#   3. CREATE text index i ri me opsione për shqip
#   4. Verifikon rezultatin
#
# ⚠️ PARALAJMËRIM:
#   - Skripti DROP-on text index ekzistues (vetëm text, jo të tjerët)
#   - Nëse kodi përdor $text query në fushën 'text' me stemming anglez,
#     sjellja mund të ndryshojë (ndryshe — pa stemming — më e mira për shqip)
#   - Nëse përdoret vetëm $regex (si V23.0), nuk ka impakt në funksionalitet
#
# Përdorimi:
#   cd backend
#   python -m scripts.recreate_text_index
#
# Për dry-run (vetëm kontroll, pa ndryshim):
#   python -m scripts.recreate_text_index --dry-run

import os
import sys
import argparse
import logging
from typing import Optional, Dict, Any

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("recreate_text_index")

COLLECTION_NAME = "legal_knowledge_base"

# Opsionet e text index-it të re
NEW_TEXT_INDEX_NAME = "idx_text_law_title_source"
NEW_TEXT_INDEX_KEYS = [("law_title", "text"), ("source", "text"), ("text", "text")]
NEW_TEXT_INDEX_OPTIONS: Dict[str, Any] = {
    "name": NEW_TEXT_INDEX_NAME,
    "weights": {"law_title": 10, "source": 5, "text": 1},
    "default_language": "none",
    "background": True,
}


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
# DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def _find_text_indexes(collection) -> Dict[str, Dict[str, Any]]:
    """
    Kthen vetëm text indexes (key përmban '_fts' ose type='text').
    """
    text_indexes: Dict[str, Dict[str, Any]] = {}
    try:
        all_indexes = collection.index_information()
    except Exception as e:
        logger.error(f"index_information dështoi: {e}")
        return text_indexes

    for name, info in all_indexes.items():
        key = info.get("key", [])
        if not isinstance(key, list):
            continue
        # Kontrollo nëse është text index (ka _fts ose _ftsx)
        is_text = any(
            (isinstance(k, tuple) and len(k) >= 1 and k[0] in ("_fts", "_ftsx"))
            or k in ("_fts", "_ftsx")
            for k in key
        )
        if is_text:
            text_indexes[name] = info
    return text_indexes


def _describe_text_index(info: Dict[str, Any]) -> str:
    """Përshkrim njerëzor i një text index."""
    weights = info.get("weights", {})
    default_lang = info.get("default_language", "?")
    return (
        f"language={default_lang}, "
        f"weights={weights}, "
        f"key={info.get('key')}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# ACTION
# ═══════════════════════════════════════════════════════════════════════════

def recreate_text_index(dry_run: bool = False) -> int:
    """
    Returns: 0 = OK, 1 = error, 2 = no action needed
    """
    logger.info("═" * 75)
    logger.info("RECREATE TEXT INDEX — legal_knowledge_base")
    logger.info(f"Mode: {'DRY-RUN (pa ndryshim)' if dry_run else 'EXECUTE'}")
    logger.info("═" * 75)

    try:
        db = _get_db()
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return 1

    collection = db[COLLECTION_NAME]

    # ─── HAPI 1: Discovery ─────────────────────────────────────────────
    logger.info("\n[1/4] Zbulimi i text indexes ekzistues...")
    text_indexes = _find_text_indexes(collection)

    if not text_indexes:
        logger.info("     Asnjë text index ekzistues. Do krijohet i ri.")
    else:
        logger.info(f"     Gjetur {len(text_indexes)} text index(es):")
        for name, info in text_indexes.items():
            logger.info(f"       • {name}")
            logger.info(f"         {_describe_text_index(info)}")

    # ─── HAPI 2: Kontroll nëse i riu ekziston tashmë ────────────────────
    logger.info(f"\n[2/4] Kontroll nëse '{NEW_TEXT_INDEX_NAME}' ekziston...")
    if NEW_TEXT_INDEX_NAME in text_indexes:
        existing = text_indexes[NEW_TEXT_INDEX_NAME]
        if existing.get("default_language") == NEW_TEXT_INDEX_OPTIONS["default_language"]:
            logger.info(f"     ✅ Ekziston tashmë me opsione korrekte. Asnjë veprim.")
            logger.info(f"     {_describe_text_index(existing)}")
            return 2
        else:
            logger.warning(f"     ⚠️  Ekziston me opsione TË NDRYSHME — do rindërtohet.")
            logger.warning(f"     {_describe_text_index(existing)}")

    # ─── HAPI 3: DROP text indexes ekzistues ────────────────────────────
    logger.info("\n[3/4] Drop text indexes ekzistues...")
    if not text_indexes:
        logger.info("     Asnjë për të drop-uar.")
    else:
        for name in text_indexes.keys():
            if dry_run:
                logger.info(f"     [DRY-RUN] Do DROP: '{name}'")
            else:
                try:
                    collection.drop_index(name)
                    logger.info(f"     ✅ DROP: '{name}'")
                except Exception as e:
                    logger.error(f"     ❌ DROP dështoi për '{name}': {e}")
                    return 1

    # ─── HAPI 4: CREATE text index i ri ─────────────────────────────────
    logger.info("\n[4/4] CREATE text index i ri...")
    logger.info(f"     Name: {NEW_TEXT_INDEX_NAME}")
    logger.info(f"     Keys: {NEW_TEXT_INDEX_KEYS}")
    logger.info(f"     Opsione: {NEW_TEXT_INDEX_OPTIONS}")

    if dry_run:
        logger.info("     [DRY-RUN] Do krijohej text index i ri.")
        logger.info("\n✅ DRY-RUN përfundoi — asnjë ndryshim nuk u bë.")
        return 0

    try:
        result_name = collection.create_index(
            NEW_TEXT_INDEX_KEYS,
            **NEW_TEXT_INDEX_OPTIONS,
        )
        logger.info(f"     ✅ KRIJUAR: '{result_name}'")
    except Exception as e:
        logger.error(f"     ❌ CREATE dështoi: {e}")
        return 1

    # ─── VERIFIKIM FINAL ────────────────────────────────────────────────
    logger.info("\n" + "═" * 75)
    logger.info("VERIFIKIM FINAL")
    logger.info("═" * 75)
    final_text_indexes = _find_text_indexes(collection)
    if len(final_text_indexes) == 1 and NEW_TEXT_INDEX_NAME in final_text_indexes:
        logger.info(f"✅ Text index i vetëm dhe i saktë: '{NEW_TEXT_INDEX_NAME}'")
        logger.info(f"   {_describe_text_index(final_text_indexes[NEW_TEXT_INDEX_NAME])}")
        return 0
    else:
        logger.warning(f"⚠️  Gjendje e papritur — {len(final_text_indexes)} text index(es):")
        for name, info in final_text_indexes.items():
            logger.warning(f"   • {name}: {_describe_text_index(info)}")
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Recreate MongoDB text index për shqip (default_language=none)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Vetëm kontroll, pa ndryshime.",
    )
    args = parser.parse_args()

    try:
        code = recreate_text_index(dry_run=args.dry_run)
        sys.exit(code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Anuluar nga user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Gabim fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()