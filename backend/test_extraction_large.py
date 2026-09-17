# FILE: backend/test_extraction_large.py
# PHOENIX PROTOCOL - EXTRACTION LARGE DOCUMENT TEST (V1)
# Verifikon chunk-aware processing për dokumente të mëdha (>40K chars).
# Prova kryesore: ZERO SILENT TRUNCATION.

import asyncio
import sys
import json
import time
from collections import Counter

from app.core.db import get_db_instance
from app.services.extraction_pipeline import get_extraction_pipeline


async def main():
    print("=" * 70)
    print("🔬 EXTRACTION LARGE DOCUMENT TEST")
    print("=" * 70)

    db = get_db_instance()
    print(f"✅ DB connected: {db.name}\n")

    # 1. Gjej dokumentin më të madh
    print("🔎 Kërkoj dokumentin më të madh me tekst...\n")

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

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, doc, text = candidates[0]

    doc_id = str(doc["_id"])
    case_id = str(doc.get("case_id", ""))
    user_id = str(doc.get("owner_id", ""))
    file_name = doc.get("file_name", "unknown")
    pages = doc.get("page_count", "?")

    expected_chunks = max(1, (len(text) + 8000 - 1) // 8000)

    print(f"   ✅ U zgjodh dokumenti MË I MADH:")
    print(f"      - document_id:     {doc_id}")
    print(f"      - case_id:         {case_id}")
    print(f"      - file_name:       {file_name}")
    print(f"      - page_count:      {pages}")
    print(f"      - text_length:     {len(text):,} chars")
    print(f"      - chunks (vlerësuar): ~{expected_chunks}")

    print(f"\n   ⏱️  Koha e pritur: ~{expected_chunks * 10}-{expected_chunks * 20} sekonda")
    print(f"   💰 Shpenzimi i pritur: ~{expected_chunks * 2} calls LLM\n")

    input("   Shtypni ENTER për të filluar (ose Ctrl+C për të anuluar)...")

    # 2. Pipeline
    print("\n" + "=" * 70)
    print("🚀 Nisja e pipeline (LARGE DOCUMENT)...")
    print("=" * 70)

    pipeline = get_extraction_pipeline(db)
    t_start = time.time()

    async for event in pipeline.run(
        user_id=user_id,
        case_id=case_id,
        document_ids=[doc_id],
        force_reprocess=True,
    ):
        evt = event.get("event", "?")

        if evt == "start":
            print(f"\n📋 START: {event['total_documents']} dokument(e)")

        elif evt == "document_started":
            print(f"▶️  Duke procesuar: {event['file_name']}")
            print(f"   ⏳ NER + Metadata po ekzekutohen në chunks...")

        elif evt == "document_completed":
            stats = event.get("stats", {})
            print(f"\n✅ PËRFUNDOI: {event['file_name']}")
            print(f"   - text_length:       {stats.get('text_length'):,}")
            print(f"   - total_entities:    {stats.get('total_entities')}")
            print(f"   - metadata_fields:   {stats.get('metadata_fields_found')}")
            print(f"   - duration_sec:      {stats.get('duration_sec')}")

        elif evt == "document_failed":
            print(f"❌ DËSHTOI: {event['file_name']} — {event.get('error')}")

        elif evt == "complete":
            summary = event.get("summary", {})
            print(f"\n🎉 COMPLETE:")
            print(json.dumps(summary, indent=2, default=str))

        elif evt == "error":
            print(f"\n🚨 ERROR: {event.get('message')}")

    total_wall = round(time.time() - t_start, 2)

    # 3. Verifikim i plotë
    print("\n" + "=" * 70)
    print("🔍 VERIFIKIM I THELLË")
    print("=" * 70)

    stored = db["case_extractions"].find_one({
        "case_id": case_id,
        "document_id": doc_id,
    })

    if not stored:
        print("❌ Nuk u gjet në case_extractions.")
        return

    # 3a. Zero truncation check
    print("\n📏 KONTROLLI #1 — ZERO SILENT TRUNCATION:")
    print(f"   Original text_length:  {len(text):,}")
    print(f"   Stored text_length:    {stored.get('text_length'):,}")
    if stored.get("text_length") == len(text):
        print(f"   ✅ KALOI — asnjë karakter nuk humbi")
    else:
        diff = len(text) - stored.get("text_length", 0)
        print(f"   ❌ DËSHTOI — humbën {diff:,} karaktere!")

    # 3b. Chunk count check
    ner_stats = stored.get("ner_stats", {})
    meta_stats = stored.get("metadata_stats", {})
    actual_chunks = ner_stats.get("total_chunks", 0)

    print(f"\n📦 KONTROLLI #2 — CHUNK COUNT:")
    print(f"   Original chars:       {len(text):,}")
    print(f"   Chunk size:           8,000")
    print(f"   Expected chunks:      ~{expected_chunks}")
    print(f"   NER actual chunks:    {actual_chunks}")
    print(f"   META actual chunks:   {meta_stats.get('total_chunks', 0)}")
    if actual_chunks >= expected_chunks - 1:
        print(f"   ✅ KALOI — chunks përputhen")
    else:
        print(f"   ⚠️  DIFERENCË — kontrollo")

    # 3c. Entities by type
    entities = stored.get("entities_flat", [])
    print(f"\n🏷️  KONTROLLI #3 — ENTITETET:")
    print(f"   Total entities (deduped):  {len(entities)}")
    print(f"   Total raw (para dedup):    {ner_stats.get('total_raw_entities', '?')}")

    if entities:
        type_counts = Counter(e.get("label", "UNKNOWN") for e in entities)
        print(f"\n   Shpërndarja sipas tipit:")
        for label, count in type_counts.most_common():
            print(f"      {label:20s} {count}")

    # 3d. Metadata completeness
    meta = stored.get("metadata", {})
    print(f"\n📋 KONTROLLI #4 — METADATA:")
    fields_filled = 0
    for k in ["court", "judge", "case_number", "document_type",
              "date", "amount", "subject", "deadline_mentioned"]:
        v = meta.get(k)
        filled = v not in (None, "", [], {})
        marker = "✅" if filled else "⚪"
        if filled:
            fields_filled += 1
        preview = str(v)[:60] if filled else "—"
        print(f"   {marker} {k:22s} {preview}")

    # Lists
    for k in ["statute", "articles", "parties"]:
        v = meta.get(k) or []
        print(f"   ✅ {k:22s} {len(v)} element(e)")

    # 3e. Warnings
    warnings = (stored.get("ner_warnings") or []) + (stored.get("metadata_warnings") or [])
    print(f"\n⚠️  KONTROLLI #5 — WARNINGS:")
    if warnings:
        for w in warnings:
            print(f"   ⚠️  {w}")
    else:
        print(f"   ✅ Asnjë warning")

    # 3f. Timing
    print(f"\n⏱️  KONTROLLI #6 — TIMING:")
    print(f"   Wall time:         {total_wall}s")
    print(f"   Pipeline duration: {stored.get('stats', {}).get('duration_sec')}s")
    print(f"   Avg per chunk:     "
          f"{round(stored.get('stats', {}).get('duration_sec', 0) / max(1, actual_chunks), 2)}s")

    # 3g. Sample entities
    if entities:
        print(f"\n📝 SHEMBULL — 10 entitetet e para:")
        for e in entities[:10]:
            print(f"   [{e.get('label'):15s}] "
                  f"{e.get('text')[:50]:50s} "
                  f"(conf={e.get('confidence')})")

    # 4. Përfundim
    print("\n" + "=" * 70)
    print("🏁 PËRFUNDIMI")
    print("=" * 70)

    truncation_ok = stored.get("text_length") == len(text)
    chunks_ok = actual_chunks >= expected_chunks - 1
    entities_ok = len(entities) > 0
    metadata_ok = fields_filled >= 4

    verdict = all([truncation_ok, chunks_ok, entities_ok, metadata_ok])
    if verdict:
        print("✅ MODULI 2 — KALOI PLOTËSISHT")
        print("   - Zero silent truncation")
        print("   - Chunk-aware processing")
        print("   - Entitete të ekstraktuara")
        print("   - Metadata e plotë")
        print("\n   ➡️  Gati për Modulin 3 (Cross-Reference)")
    else:
        print("⚠️  MODULI 2 — KA PROBLEME:")
        if not truncation_ok:
            print("   ❌ Silent truncation u zbulua")
        if not chunks_ok:
            print("   ❌ Chunk count nuk përputhet")
        if not entities_ok:
            print("   ❌ Zero entitete")
        if not metadata_ok:
            print("   ❌ Metadata e mangët")

    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Ndërprerë nga përdoruesi.")
        sys.exit(1)