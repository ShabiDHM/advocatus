# FILE: backend/test_synthesis.py
# Teston SynthesisService me ekstraktimet + cross-references ekzistuese.

import time
from app.core.db import get_db_instance
from app.services.synthesis_service import get_synthesis_service


def main():
    db = get_db_instance()
    print(f"✅ DB: {db.name}\n")

    # Gjej një case_id me ekstraktime
    latest = db["case_extractions"].find_one(sort=[("completed_at", -1)])
    if not latest:
        print("❌ Nuk ka ekstraktime.")
        return

    case_id = latest["case_id"]
    print(f"📋 Case ID: {case_id}\n")

    service = get_synthesis_service(db)

    print("=" * 70)
    print("🚀 Nisja e sintetizimit (6 sections × ~20s = ~2 min)...")
    print("=" * 70)

    t_start = time.time()

    result = service.synthesize(
        case_id=case_id,
        user_id=str(latest.get("user_id", "")),
    )

    wall = round(time.time() - t_start, 2)

    print(f"\n✅ PËRFUNDOI në {wall}s\n")

    print("=" * 70)
    print("📊 STATS:")
    print("=" * 70)
    for k, v in result["stats"].items():
        print(f"   {k}: {v}")

    print("\n" + "=" * 70)
    print("📄 SECIONET E GJENERUARA:")
    print("=" * 70)
    for section_key, section in result.get("sections", {}).items():
        title = section.get("title", section_key)
        content = section.get("content", "")
        stats = result.get("section_stats", {}).get(section_key, {})
        print(f"\n{'─' * 70}")
        print(f"📌 {title}")
        print(f"   ({len(content)} chars, {stats.get('duration_sec', '?')}s)")
        print(f"{'─' * 70}")
        if content:
            # Shfaq 500 karakteret e parë
            preview = content[:500].replace("\n", " ")
            print(preview + ("..." if len(content) > 500 else ""))
        else:
            print(f"   ⚠️  BOSH")

    print("\n" + "=" * 70)
    print("🏁 FUNDI")
    print("=" * 70)


if __name__ == "__main__":
    main()