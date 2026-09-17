# FILE: backend/test_orchestrator.py
# Teston CaseAnalysisOrchestrator me një case real.

import asyncio
import sys
import time

from app.core.db import get_db_instance
from app.services.case_analysis_orchestrator import get_case_analysis_orchestrator


async def main():
    db = get_db_instance()
    print(f"✅ DB: {db.name}\n")

    # Gjej një case me ekstraktime
    latest = db["case_extractions"].find_one(sort=[("completed_at", -1)])
    if not latest:
        print("❌ Nuk ka ekstraktime. Fillimisht ekzekutoni test_extraction_large.py")
        return

    case_id = latest["case_id"]
    user_id = str(latest.get("user_id", ""))

    print(f"📋 Case ID: {case_id}")
    print(f"📋 User ID: {user_id}\n")

    orchestrator = get_case_analysis_orchestrator(db)

    print("=" * 70)
    print("🚀 Nisja e orkestratorit...")
    print("=" * 70)

    t_start = time.time()
    last_phase = None

    async for evt in orchestrator.run(
        case_id=case_id,
        user_id=user_id,
        force_reprocess=False,  # përdor cache
    ):
        evt_type = evt.get("event", "?")
        phase = evt.get("phase", "")

        # Printo vetëm event-et kryesore (jo per-document, për të shmangur spam)
        if evt_type == "start":
            print(f"\n▶️  START: {evt.get('case_title')}")

        elif evt_type == "phase_started":
            print(f"\n{'═' * 70}")
            print(f"📦 FAZA: {phase.upper()}")
            print(f"{'═' * 70}")

        elif evt_type == "phase_skipped":
            print(f"\n⏭️  SKIP: {phase} — {evt.get('reason')}")

        elif evt_type == "phase_completed":
            print(f"\n✅ FAZA PËRFUNDOI: {phase}")
            stats = evt.get("stats") or evt.get("summary") or {}
            for k, v in stats.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    print(f"   {k}: {v}")

        elif evt_type == "document_started":
            print(f"   ▶️  {evt.get('file_name')} [{evt.get('index')+1}/{evt.get('total_documents')}]")

        elif evt_type == "document_completed":
            stats = evt.get("stats", {})
            print(f"      ✅ {stats.get('total_entities')} entitete, "
                  f"{stats.get('duration_sec')}s")

        elif evt_type == "document_skipped":
            print(f"   ⏭️  SKIP: {evt.get('file_name')}")

        elif evt_type == "document_failed":
            print(f"   ❌ {evt.get('file_name')}: {evt.get('error')}")

        elif evt_type == "section_started":
            print(f"   📝 Section: {evt.get('section_title')}")

        elif evt_type == "section_completed":
            print(f"      ✅ {evt.get('content_length')} chars")

        elif evt_type == "error":
            print(f"\n🚨 ERROR në fazën {phase}: {evt.get('message')}")

        elif evt_type == "complete":
            print(f"\n{'═' * 70}")
            print(f"🎉 PËRFUNDOI")
            print(f"{'═' * 70}")
            import json
            print(json.dumps(evt.get("summary", {}), indent=2, default=str))

    wall = round(time.time() - t_start, 2)
    print(f"\n⏱️  Wall time: {wall}s")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Ndërprerë nga përdoruesi.")
        sys.exit(1)