# FILE: backend/scripts/audit_lpk_kednj.py
# PHOENIX PROTOCOL - AUDIT LPK + KEDNJ V1.0
#
# Diagnostikon pse disa artikuj shfaqen si "unverified" në document review:
#   - LPK Neni 360, 319, 367, 327 (duhet të ekzistojnë)
#   - KEDNJ Neni 6, 8, 13 (nuk ka ligj të tillë në DB)
#
# NUK modifikon asgjë. Vetëm lexon dhe raporton.

import os
import sys
import re

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.core.db import get_db_instance


def main():
    db = get_db_instance()
    coll = db["legal_knowledge_base"]

    print("═" * 75)
    print("AUDIT — LPK + KEDNJ VERIFIKIM")
    print("═" * 75)

    # ═══ 1. LPK ekziston? ═══
    print("\n[1] LPK — a ekziston në DB?")
    lpk_title = "LIGJI NR. 03 L 006 PËR PROCEDURËN KONTESTIMORE"

    doc = coll.find_one(
        {"law_title": {"$regex": re.escape("03 L 006"), "$options": "i"}},
        {"law_title": 1, "source": 1},
    )
    if doc:
        print(f"    ✓ LPK: {doc.get('law_title')}")
        print(f"    source: {doc.get('source')}")
        lpk_canonical = doc.get("law_title", "")
    else:
        print(f"    ✗ LPK NUK U GJET në DB")
        lpk_canonical = lpk_title

    # ═══ 2. A ekzistojnë nenet 360, 319, 367, 327? ═══
    print(f"\n[2] LPK — a ekzistojnë nenet e kërkuara?")
    test_articles = ["360", "319", "367", "327"]

    for art in test_articles:
        art_variants = [art, f"{art}.", f"Neni {art}"]
        if art.isdigit():
            art_variants.append(int(art))

        doc = coll.find_one(
            {
                "article_number": {"$in": art_variants},
                "is_article": True,
                "law_title": {"$regex": "03 L 006|KONTESTIMORE", "$options": "i"},
            },
            {"law_title": 1, "article_number": 1, "chunk_index": 1, "page": 1},
        )
        if doc:
            print(f"    ✓ Neni {art}: chunk={doc.get('chunk_index')}, page={doc.get('page')}")
        else:
            print(f"    ✗ Neni {art}: NUK EKZISTON")

    # ═══ 3. Sa nene ka LPK totalisht? ═══
    print(f"\n[3] LPK — statistika totale")
    lpk_count = coll.count_documents(
        {"law_title": {"$regex": "03 L 006|KONTESTIMORE", "$options": "i"},
         "is_article": True}
    )
    print(f"    Total chunks me is_article=True: {lpk_count}")

    # Nenet unike
    distinct_articles = coll.distinct(
        "article_number",
        {"law_title": {"$regex": "03 L 006|KONTESTIMORE", "$options": "i"},
         "is_article": True},
    )
    print(f"    Total nene unike: {len(distinct_articles)}")

    # Nenet max
    sorted_arts = sorted(
        [a for a in distinct_articles if str(a).replace('.', '').isdigit()],
        key=lambda x: int(str(x).replace('.', '')) if str(x).replace('.', '').isdigit() else 0,
    )
    if sorted_arts:
        print(f"    Neni min: {sorted_arts[0]}")
        print(f"    Neni max: {sorted_arts[-1]}")

    # ═══ 4. KEDNJ — a ekziston? ═══
    print(f"\n[4] KEDNJ — a ekziston në DB?")
    kednj_patterns = [
        "KEDNJ", "KONVENTA EVROPIANE", "EUROPEAN CONVENTION",
        "DREJTAT E NJERIUT", "DREJTAT E NJERIUT DHE LIRITË THEMELORE",
    ]
    found_kednj = False
    for pattern in kednj_patterns:
        doc = coll.find_one(
            {"law_title": {"$regex": pattern, "$options": "i"}},
            {"law_title": 1},
        )
        if doc:
            print(f"    ✓ U gjet me '{pattern}': {doc.get('law_title')[:70]}")
            found_kednj = True

    if not found_kednj:
        print(f"    ✗ KEDNJ NUK ekziston në DB (sipas të gjitha patterns)")
        print(f"      Kjo është E PRITUR — KEDNJ është konventë ndërkombëtare,")
        print(f"      jo ligj i Kosovës, ndaj nuk gjendet në legal_knowledge_base.")

    # ═══ 5. Të gjitha ligjet në DB ═══
    print(f"\n[5] TË GJITHA ligjet në DB (distinct law_title me is_article)")
    all_titles = coll.distinct(
        "law_title",
        {"is_article": True},
    )
    clean = sorted([t for t in all_titles if t and t.strip()])
    print(f"    Total: {len(clean)}")
    for t in clean:
        print(f"      • {t[:75]}")

    print()
    print("═" * 75)
    print("✅ Audit përfundoi")
    print("═" * 75)


if __name__ == "__main__":
    main()