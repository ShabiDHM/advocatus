# FILE: backend/test_extraction.py
# PHOENIX PROTOCOL - EXTRACTION PIPELINE SMOKE TEST (V2)
# Zgjedh dokumentin më të vogël në DB për test të shpejtë.

import asyncio
import sys
import json

from app.core.db import get_db_instance
from app.services.extraction_pipeline import get_extraction_pipeline


async def main():
    print("=" * 70)
    print("🔍 EXTRACTION PIPELINE SMOKE TEST (V2)")
    print("=" * 70)

    db = get_db_instance()
    print(f"✅ DB connected: {db.name}\n")

    # 1. Gjej dokumentin më të vogël në DB
    print("🔎 Kërkoj dokumentin më të vogël me tekst...\n")

    candidates = []
    for doc in db.documents.find(
        {"status": {"$ne": "DELETED"}},
        {"_id": 1, "case_id": 1, "owner_id": 1, "file_name": 1,
         "content": 1, "extracted_text": 1, "text": 1, "page_count": 1}
    ):
        text = (
            doc.get("content")
            or doc.get("extracted_text")
            or doc.get("text")
            or ""
        )
        if text.strip():
            candidates.append((len(text), doc, text))

    if not candidates:
        print("❌ Nuk u gjet asnjë dokument me tekst.")
        return

    candidates.sort(key=lambda x: x[0])
    _, doc, text = candidates[0]

    doc_id = str(doc["_id"])
    case_id = str(doc.get("case_id", ""))
    user_id = str(doc.get("owner_id", ""))
    file_name = doc.get("file_name", "unknown")
    pages = doc.get("page_count", "?")

    print(f"   ✅ U zgjodh dokumenti MË I VOGËL:")
    print(f"      - document_id: {doc_id}")
    print(f"      - case_id:     {case_id}")
    print(f"      - user_id:     {user_id}")
    print(f"      - file_name:   {file_name}")
    print(f"      - page_count:  {pages}")
    print(f"      - text_length: {len(text)} chars")
    print(f"      - chunks ~    {max(1, len(text) // 8000)} (me chunk_size=8000)")

    # 2. Ekzekuto pipeline
    print("\n" + "=" * 70)
    print("🚀 Nisja e pipeline (chunk-aware)...")
    print("=" * 70)

    pipeline = get_extraction_pipeline(db)

    async for event in pipeline.run(
        user_id=user_id,
        case_id=case_id,
        document_ids=[doc_id],
        force_reprocess=True,
    ):
        evt_type = event.get("event", "?")

        if evt_type == "start":
            print(f"\n📋 START: {event['total_documents']} dokument(e)")

        elif evt_type == "document_started":
            print(f"▶️  Duke procesuar: {event['file_name']}")

        elif evt_type == "document_completed":
            stats = event.get("stats", {})
            print(f"✅ PËRFUNDOI: {event['file_name']}")
            print(f"   - text_length:       {stats.get('text_length')}")
            print(f"   - total_entities:    {stats.get('total_entities')}")
            print(f"   - metadata_fields:   {stats.get('metadata_fields_found')}")
            print(f"   - duration_sec:      {stats.get('duration_sec')}")

        elif evt_type == "document_failed":
            print(f"❌ DËSHTOI: {event['file_name']} — {event.get('error')}")

        elif evt_type == "document_skipped":
            print(f"⏭️  SKIP: {event['file_name']} — {event.get('reason')}")

        elif evt_type == "complete":
            summary = event.get("summary", {})
            print(f"\n🎉 COMPLETE: {json.dumps(summary, indent=2, default=str)}")

        elif evt_type == "error":
            print(f"\n🚨 ERROR: {event.get('message')}")

    # 3. Verifiko ruajtjen në DB
    print("\n" + "=" * 70)
    print("🔍 Verifikim në DB (case_extractions)...")
    print("=" * 70)

    stored = db["case_extractions"].find_one({
        "case_id": case_id,
        "document_id": doc_id,
    })

    if stored:
        print(f"✅ U ruajt në DB:")
        print(f"   - _id:           {stored.get('_id')}")
        print(f"   - status:        {stored.get('status')}")
        print(f"   - text_length:   {stored.get('text_length')}")
        print(f"   - entities_flat: {len(stored.get('entities_flat', []))}")

        ner_stats = stored.get("ner_stats", {})
        print(f"   - ner_stats:")
        print(f"       total_chunks:      {ner_stats.get('total_chunks')}")
        print(f"       total_entities:    {ner_stats.get('total_entities')}")
        print(f"       chunks_failed:     {ner_stats.get('chunks_failed')}")

        meta_stats = stored.get("metadata_stats", {})
        print(f"   - metadata_stats:")
        print(f"       total_chunks:        {meta_stats.get('total_chunks')}")
        print(f"       llm_success:         {meta_stats.get('chunks_with_llm_success')}")

        meta = stored.get("metadata", {})
        print(f"   - metadata (sample):")
        print(f"       court:               {meta.get('court')}")
        print(f"       judge:               {meta.get('judge')}")
        print(f"       case_number:         {meta.get('case_number')}")
        print(f"       document_type:       {meta.get('document_type')}")
        print(f"       date:                {meta.get('date')}")
        print(f"       amount:              {meta.get('amount')}")
        print(f"       statute:             {meta.get('statute')}")
        print(f"       articles:            {meta.get('articles')}")
        print(f"       parties:             {len(meta.get('parties', []))} palë")
        if meta.get("parties"):
            for p in meta["parties"][:3]:
                print(f"         - {p.get('role')}: {p.get('name')}")

        # Shfaq 5 entitetet e para
        entities = stored.get("entities_flat", [])
        if entities:
            print(f"   - entities (5 të parat):")
            for e in entities[:5]:
                print(f"       [{e.get('label')}] {e.get('text')} "
                      f"(conf={e.get('confidence')})")
    else:
        print("❌ Nuk u gjet dokument në case_extractions.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Ndërprerë nga përdoruesi.")
        sys.exit(1)