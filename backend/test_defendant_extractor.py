# FILE: backend/test_defendant_extractor.py
# Teston DefendantGroupExtractor me lëndën reale.

import json
from app.core.db import get_db_instance
from app.services.defendant_group_extractor import get_defendant_group_extractor


def main():
    db = get_db_instance()
    print(f"✅ DB: {db.name}\n")

    case_id = "6aa9aee5bbdf3ff0b2edcc46"
    print(f"📋 Case: {case_id}\n")

    extractor = get_defendant_group_extractor(db)

    # Force re-extraction për test
    groups = extractor.extract_for_case(case_id, force=True)

    print("=" * 70)
    print(f"📊 REZULTATI: {len(groups)} grupe")
    print("=" * 70)

    total = 0
    for g in groups:
        print(f"\n{'─' * 70}")
        print(f"GRUPI {g['group']}: {g['title']}")
        if g.get('subtitle'):
            print(f"   ({g['subtitle'][:80]}...)")
        print(f"{'─' * 70}")

        for d in g.get('defendants', []):
            total += 1
            print(f"   {d['number']}. {d['name']}")
            print(f"      Roli: {d['role'][:100]}")

    print(f"\n{'═' * 70}")
    print(f"TOTAL: {len(groups)} grupe, {total} të pandehur")
    print(f"{'═' * 70}")

    # Verifiko DB
    from bson import ObjectId
    case = db.cases.find_one({"_id": ObjectId(case_id)})
    meta = case.get("defendants_groups_meta", {})
    print(f"\n✅ Ruajtur në DB:")
    print(json.dumps(meta, indent=2, default=str))


if __name__ == "__main__":
    main()