# FILE: backend/_tests_dev/_test_service_integration.py
"""Verifikon qe service.review() integron hallucination_checker (pa Mongo/LLM)."""
import sys
from unittest.mock import patch, MagicMock
from app.services.document_review import service


# ═══ Mock varesite ═══
FAKE_DOC_TEXT = """
REPUBLIKA E KOSOVES
GJYKATA THEMELORE NE PRISHTINE
Nr. 123/2024, Date: 15.03.2024

FAKTET:
Me 10.01.2024, i pandehuri ka shkaktuar lendime.

ARSYETIMI:
Gjykata konstaton se vepra eshte provuar.

VENDOSI:
I. I pandehuri denohet me 6 muaj burg sipas Nenit 1.2 te Ligjit Nr. 03/L-182.
"""

# Fake doc
fake_doc = {
    "file_name": "test.pdf",
    "document_type": "Vendim",
    "content": FAKE_DOC_TEXT,
}

# Fake LLM output: permban hallucination (date te rreme, ligj te rreme)
fake_llm_output = {
    "document_summary": "Me 25.12.2025, gjykata vendosi sipas Ligjit Nr. 08/L-999.",
    "article_verification": "Neni 1 par. 2 i Ligjit 03/L-182 EKZISTON.",
    "supreme_court_precedents": "Nuk ka precedente.",
    "drafting_quality": "Cilesi e mire.",
    "errors_corrections": "[OK] Nuk u identifikuan gabime.",
    "action_steps": "Hapi 1: kontakto klientin.",
}


def fake_synthesize(section_key, section_cfg, verified_context, **kwargs):
    return fake_llm_output.get(section_key, "")


with patch.object(service, "load_document", return_value=fake_doc), \
     patch.object(service, "load_extraction", return_value={"text": FAKE_DOC_TEXT}), \
     patch.object(service, "verify_all", return_value={
         "articles": [], "laws_by_number": [], "case_numbers": [],
         "stats": {"articles_verified": 0, "articles_total": 0,
                   "laws_verified": 0, "laws_total": 0,
                   "precedents_verified": 0, "case_numbers_cited": 0},
     }), \
     patch.object(service, "synthesize_section_streaming", side_effect=fake_synthesize), \
     patch.object(service, "persist", return_value=None):

    svc = service.DocumentReviewService(db=MagicMock())
    result = svc.review(case_id="c1", user_id="u1", document_id="d1")

# Verifiko
assert "hallucination_report" in result, "Mungon hallucination_report!"
hr = result["hallucination_report"]

print("=" * 60)
print(f"Status global: {hr['status']}")
print(f"Total issues: {hr['total_issues']}")
print(f"Severity totals: {hr['severity_totals']}")
print(f"Suspicious sections: {hr['suspicious_sections']}")
print("=" * 60)
print("Stats:")
print(f"  hallucination_status: {result['stats']['hallucination_status']}")
print(f"  hallucination_issues: {result['stats']['hallucination_issues']}")
print(f"  execution_mode: {result['stats']['execution_mode']}")
print(f"  timing_breakdown: {result['stats']['timing_breakdown']}")
print("=" * 60)

# Pritet: halluci_status = suspect (ka 25.12.2025 dhe 08/L-999 te rreme)
assert hr["status"] == "suspect", f"Pritet suspect, mori {hr['status']}"
assert "document_summary" in hr["suspicious_sections"]

# Verifiko qe article_verification (i paster) nuk eshte ne suspicious
assert "article_verification" not in hr["suspicious_sections"], \
    "article_verification eshte i paster, nuk duhet te jete suspicious!"

print("[OK] Integrimi V5.6 funksionon.")