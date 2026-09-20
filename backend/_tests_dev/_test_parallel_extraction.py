# FILE: backend/_tests_dev/_test_parallel_extraction.py
"""Verifikon paralelizmin e extraction_pipeline."""
import asyncio
import time
from unittest.mock import patch, MagicMock
from app.services import extraction_pipeline as ep


async def main():
    # Mock dependencies
    fake_docs = [
        {"_id": f"doc{i}", "file_name": f"f{i}.pdf", "content": f"Text {i}" * 100,
         "case_id": "c1", "owner_id": "u1"}
        for i in range(6)
    ]

    def fake_categorize(text):
        time.sleep(0.2)  # simulo work
        return {"primary_category": "Vendim", "confidence": 0.9}

    def fake_ner(text, document_id, document_type):
        time.sleep(0.3)
        return {"entities_by_type": {}, "entities_flat": [], "stats": {"total_entities": 5, "role_conflicts_resolved": 0}}

    def fake_meta(text, document_id):
        time.sleep(0.1)
        return {"parties": [], "stats": {}}

    with patch.object(ep.ExtractionPipeline, "_fetch_documents", return_value=fake_docs), \
         patch.object(ep.ExtractionPipeline, "_fetch_existing_extractions", return_value={}), \
         patch.object(ep.ExtractionPipeline, "_persist_extraction", return_value=None), \
         patch.object(ep.CATEGORIZATION_SERVICE, "categorize_document_detailed", side_effect=fake_categorize), \
         patch.object(ep.ALBANIAN_NER_SERVICE, "extract_legal_entities", side_effect=fake_ner), \
         patch.object(ep.albanian_metadata_extractor, "extract", side_effect=fake_meta):

        db = MagicMock()
        pipeline = ep.ExtractionPipeline(db=db)

        events = []
        start = time.time()
        async for evt in pipeline.run(user_id="u1", case_id="c1"):
            events.append(evt)
        elapsed = time.time() - start

        summary = next(e for e in events if e["event"] == "complete")["summary"]
        print(f"Elapsed: {elapsed:.2f}s")
        print(f"Mode: {summary['max_concurrent_docs']}")
        print(f"Successful: {summary['documents_successful']}/{summary['documents_total']}")

        # 6 docs, ~0.6s secili, sekuencial = 3.6s, paralel x3 = ~1.3s
        assert elapsed < 2.5, f"Duhet <2.5s (paralel), mori {elapsed:.2f}s"
        assert summary["documents_successful"] == 6
        print("[OK] Extraction paralel funksionon.")


asyncio.run(main())