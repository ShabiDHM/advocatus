# FILE: backend/_tests_dev/_test_parallel_synthesis.py
"""Verifikon qe synthesis.service ekzekutohet paralel."""
import time
from unittest.mock import patch, MagicMock
from app.services.synthesis import service as synthesis_service


# Mock all dependencies
FAKE_SECTIONS = {k: {"title": f"T-{k}", "prompt": "test", "max_tokens": 100}
                 for k in ["a", "b", "c", "d", "e", "f"]}


def fake_synthesize(section_key, section_cfg, digest, case, stream_callback):
    time.sleep(0.5)  # Simulo LLM
    return f"Content for {section_key}"


with patch.object(synthesis_service, "SECTION_PROMPTS", FAKE_SECTIONS), \
     patch.object(synthesis_service, "load_case", return_value={"title": "Test"}), \
     patch.object(synthesis_service, "load_extractions", return_value=[{"_id": "e1"}]), \
     patch.object(synthesis_service, "load_cross_refs", return_value=[]), \
     patch.object(synthesis_service, "detect_case_type", return_value="civil"), \
     patch.object(synthesis_service, "extract_articles_by_law", return_value={}), \
     patch.object(synthesis_service, "extract_verified_citations_from_documents",
                  return_value={"total_laws": 0, "total_articles": 0, "total_pairs": 0, "articles": []}), \
     patch.object(synthesis_service, "build_digest", return_value="fake digest"), \
     patch.object(synthesis_service, "synthesize_section_streaming", side_effect=fake_synthesize), \
     patch.object(synthesis_service, "persist", return_value=None), \
     patch.object(synthesis_service, "post_process_output",
                  return_value=("processed", {"hallucinations_fixed": 0, "institutions_fixed": 0, "prefix_fixes": 0})):

    svc = synthesis_service.SynthesisService(db=MagicMock())
    svc.defendant_extractor = MagicMock()
    svc.defendant_extractor.extract_for_case.return_value = []

    start = time.time()
    result = svc.synthesize(case_id="c1", user_id="u1")
    elapsed = time.time() - start

    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Mode: {result['stats']['execution_mode']}")
    print(f"Sections: {result['stats']['sections_generated']}/{result['stats']['sections_total']}")

    # Me 6 seksione * 0.5s, sekuencial = 3s, paralel x3 = ~1s
    assert elapsed < 2.0, f"Duhet te jete <2s (paralel), mori {elapsed:.2f}s"
    assert result['stats']['sections_generated'] == 6
    assert "parallel_x" in result['stats']['execution_mode']

    print("[OK] Synthesis paralel funksionon.")