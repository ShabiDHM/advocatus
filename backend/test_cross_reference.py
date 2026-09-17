# FILE: backend/test_cross_reference.py
# Teston CrossReferenceService me ekstraktimet ekzistuese.

from app.core.db import get_db_instance
from app.services.pillars.cross_reference_service import get_cross_reference_service


def main():
    db = get_db_instance()
    print(f"✅ DB: {db.name}\n")

    # Gjej një case_id që ka ekstraktime
    latest = db["case_extractions"].find_one(sort=[("completed_at", -1)])
    if not latest:
        print("❌ Nuk ka ekstraktime.")
        return

    case_id = latest["case_id"]
    print(f"📋 Case ID: {case_id}\n")

    service = get_cross_reference_service(db)
    result = service.build(case_id)

    print("=" * 70)
    print("📊 STATS:")
    print("=" * 70)
    for k, v in result["stats"].items():
        print(f"   {k}: {v}")

    print("\n" + "=" * 70)
    print("🔗 DOCUMENT REFERENCES:")
    print("=" * 70)
    for ref in result.get("document_references", []):
        print(f"   '{ref['source_file_name']}' → '{ref['target_file_name']}' "
              f"(via {ref['via_case_number']})")

    print("\n" + "=" * 70)
    print("📁 CASE NUMBER CHAIN (top 10):")
    print("=" * 70)
    items = sorted(
        result.get("case_number_chain", {}).items(),
        key=lambda x: -len(x[1])
    )[:10]
    for cn, docs in items:
        print(f"   '{cn}' → {len(docs)} dokument(e)")

    print("\n" + "=" * 70)
    print("👥 PARTY APPEARANCES (top 10):")
    print("=" * 70)
    items = sorted(
        result.get("party_appearances", {}).items(),
        key=lambda x: -len(x[1])
    )[:10]
    for name, docs in items:
        print(f"   '{name}' → {len(docs)} dokument(e)")

    print("\n" + "=" * 70)
    print("📜 STATUTE CITATIONS (top 10):")
    print("=" * 70)
    items = sorted(
        result.get("statute_citations", {}).items(),
        key=lambda x: -len(x[1])
    )[:10]
    for stat, docs in items:
        print(f"   '{stat}' → {len(docs)} dokument(e)")

    print("\n" + "=" * 70)
    print("📅 CHRONOLOGICAL CHAIN:")
    print("=" * 70)
    for item in result.get("chronological_chain", [])[:10]:
        print(f"   {item.get('date') or '?':15s} | {item.get('file_name')}")

    print("\n" + "=" * 70)
    print("🏁 FUNDI")
    print("=" * 70)


if __name__ == "__main__":
    main()