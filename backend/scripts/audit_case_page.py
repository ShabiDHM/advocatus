# FILE: backend/scripts/audit_case_page.py
# PHOENIX PROTOCOL - CASE-PAGE DIAGNOSTIC V1.0
#
# Diagnostikon si sillet /laws/case-page realisht mbi DB.
# NUK modifikon asgjë. Vetëm lexon dhe raporton.
#
# Zbulon:
#   1. Sa dokumente kanë case_number (vendime reale)
#   2. Sa case_number shfaqen VETËM në 'text' (referenca fantazmë)
#   3. Sa kërkesa tipike gjejnë vendim real vs referencë
#   4. Precedentë ku `text_reference` fallback mund të japë false positive
#
# Përdorimi:
#   cd backend
#   python -m scripts.audit_case_page

import os
import sys
import re
import logging
from collections import Counter
from typing import List, Dict, Set, Tuple

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("audit_case_page")

COLLECTION_NAME = "legal_knowledge_base"

# Regex për case number (njësoj si në backend)
CASE_NO_REGEX = re.compile(
    r'\b(?:PA1|PKR|PML|REV|KMLP|ANR|A\.NR|PZR)\.?\s*(?:nr|Nr|NR)?\.?\s*(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)


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


def _section(title: str):
    logger.info("")
    logger.info("─" * 75)
    logger.info(title)
    logger.info("─" * 75)


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT
# ═══════════════════════════════════════════════════════════════════════════

def audit() -> None:
    db = _get_db()
    coll = db[COLLECTION_NAME]

    # ═══ 1. TOTALS ═══
    _section("1. TOTALS")
    total = coll.estimated_document_count()
    logger.info(f"Total dokumente: ~{total}")

    # ═══ 2. Dokumente me case_number ═══
    _section("2. DOKUMENTE ME case_number")

    try:
        with_case_number = coll.count_documents({
            "case_number": {"$exists": True, "$nin": [None, ""]},
        }, limit=1_000_000)
        logger.info(f"Dokumente me case_number: {with_case_number}")
    except Exception as e:
        logger.warning(f"Count failed: {e}")
        with_case_number = 0

    try:
        without_case_number = coll.count_documents({
            "$or": [
                {"case_number": {"$exists": False}},
                {"case_number": None},
                {"case_number": ""},
            ]
        }, limit=1_000_000)
        logger.info(f"Dokumente pa case_number: {without_case_number}")
    except Exception as e:
        logger.warning(f"Count failed: {e}")

    # ═══ 3. CASE NUMBERS UNIKE (vendime reale) ═══
    _section("3. CASE NUMBERS UNIKE")

    try:
        distinct_case_numbers = coll.distinct("case_number")
        clean_cn = [c.strip() for c in distinct_case_numbers if c and c.strip()]
        logger.info(f"Case numbers unike (distinct): {len(clean_cn)}")

        # Sa prej tyre janë vetëm 1 dokument?
        single_docs = 0
        multi_docs = 0
        for cn in clean_cn[:200]:  # shiko top 200
            cnt = coll.count_documents({"case_number": cn}, limit=10)
            if cnt == 1:
                single_docs += 1
            elif cnt > 1:
                multi_docs += 1

        logger.info(f"  Nga top 200: {single_docs} me 1 doc, {multi_docs} me shumë docs")
    except Exception as e:
        logger.warning(f"Distinct failed: {e}")
        clean_cn = []

    # ═══ 4. CASE NUMBERS QË SHFAQEN VETËM NË TEXT ═══
    _section("4. CASE NUMBERS VETËM NË TEXT (referenca fantazmë)")

    # Merr të gjitha case numbers që janë në fushën case_number (reale)
    real_cn_set: Set[str] = set()
    for cn in clean_cn:
        normalized = re.sub(r'\s+', '', cn.upper())
        real_cn_set.add(normalized)

    logger.info(f"Case numbers reale (normalized): {len(real_cn_set)}")

    # Gjej të gjitha case numbers që shfaqen në TEXT
    try:
        # Marrim vetëm dokumentet që kanë tekst dhe nuk kanë case_number (përmbledhje, lista, analiza)
        cursor = coll.find(
            {
                "text": {"$exists": True, "$nin": [None, ""]},
                "case_number": {"$in": [None, ""]},
                "is_article": False,  # jo statute
            },
            {"text": 1, "law_title": 1, "source": 1},
        ).limit(500)

        phantom_refs: Dict[str, int] = Counter()
        docs_scanned = 0

        for doc in cursor:
            docs_scanned += 1
            text = doc.get("text", "")[:5000]  # kap 5KB fillim
            for m in CASE_NO_REGEX.finditer(text):
                cn_found = m.group(0).strip()
                cn_norm = re.sub(r'\s+', '', cn_found.upper())
                if cn_norm not in real_cn_set:
                    phantom_refs[cn_found] += 1

        logger.info(f"Dokumente të skanuar (jo-statute pa case_number): {docs_scanned}")
        logger.info(f"Case numbers 'fantazmë' të gjetura në text: {len(phantom_refs)}")

        if phantom_refs:
            logger.info(f"Top 15 case numbers që shfaqen vetëm në text:")
            for cn, cnt in phantom_refs.most_common(15):
                logger.info(f"  {cnt:3d}x  {cn}")
        else:
            logger.info("  ✅ Asnjë case number fantazmë — të gjitha kanë dokument real")

    except Exception as e:
        logger.warning(f"Phantom scan failed: {e}")

    # ═══ 5. TEST ME KËRKESA TIPIKE ═══
    _section("5. TEST ME KËRKESA TIPIKE (si sillet /case-page)")

    # Marr mostër case numbers nga DB për të testuar
    test_queries: List[str] = []
    if clean_cn:
        # 5 mostër të rastësishme
        import random
        test_queries = random.sample(clean_cn, min(5, len(clean_cn)))

    # Shto disa kërkime të rreme (nuk ekzistojnë)
    test_queries.extend([
        "PML 999999/9999",
        "REV 00000/0000",
    ])

    logger.info(f"Test {len(test_queries)} kërkime:")

    for query in test_queries:
        clean_title = query.strip()

        # Simulo logjikën e /laws/case-page
        strategies = []

        # 1. law_title exact
        doc = coll.find_one(
            {"law_title": clean_title},
            {"law_title": 1, "source": 1, "page": 1, "case_number": 1},
        )
        if doc:
            strategies.append(("law_title_exact", doc))
        else:
            # 2. law_title regex
            doc = coll.find_one(
                {"law_title": {"$regex": re.escape(clean_title), "$options": "i"}},
                {"law_title": 1, "source": 1, "page": 1, "case_number": 1},
            )
            if doc:
                strategies.append(("law_title_regex", doc))

        if not strategies:
            # 3. case_number exact
            doc = coll.find_one(
                {"case_number": clean_title},
                {"law_title": 1, "source": 1, "page": 1, "case_number": 1},
            )
            if doc:
                strategies.append(("case_number_exact", doc))
            else:
                # 4. case_number regex
                doc = coll.find_one(
                    {"case_number": {"$regex": re.escape(clean_title), "$options": "i"}},
                    {"law_title": 1, "source": 1, "page": 1, "case_number": 1},
                )
                if doc:
                    strategies.append(("case_number_regex", doc))

        if not strategies:
            # 5. text contains (RREZIKSHËM)
            doc = coll.find_one(
                {"text": {"$regex": re.escape(clean_title), "$options": "i"}},
                {"law_title": 1, "source": 1, "page": 1, "case_number": 1},
            )
            if doc:
                strategies.append(("text_reference", doc))

        if strategies:
            strat, doc = strategies[0]
            title = (doc.get("law_title") or "")[:60]
            source = (doc.get("source") or "")[:50]
            cn = doc.get("case_number") or "—"

            marker = "⚠️" if strat == "text_reference" else "✅"
            logger.info(f"  {marker} '{clean_title[:40]}'")
            logger.info(f"      strategy: {strat}")
            logger.info(f"      matched_title: {title}")
            logger.info(f"      case_number i dokumentit: {cn}")
            logger.info(f"      source: {source}")
        else:
            logger.info(f"  ❌ '{clean_title[:40]}' → nuk u gjet")


def main():
    logger.info("═" * 75)
    logger.info("CASE-PAGE AUDIT — legal_knowledge_base")
    logger.info("═" * 75)

    try:
        audit()
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