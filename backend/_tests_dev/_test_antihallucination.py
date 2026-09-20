# FILE: backend/_tests_dev/_test_antihallucination.py
"""Verifikon qe _block_antihallucination shfaqet ne çdo seksion."""
from app.services.document_review.prompts import (
    build_verified_context,
    DOCUMENT_REVIEW_PROMPTS,
)

citation_profile = {
    "articles": [{"number": "1", "paragraph": "2", "law_hint": "03/L-182"}],
    "laws_by_number": [{"number": "03/L-182", "name": ""}],
    "laws_by_name": [],
    "abbreviations": ["LPK", "LMDHF"],
    "case_numbers": [{"case_number": "P.nr.123/2024"}],
}
fact_profile = {
    "dates": [{"display": "15.03.2024", "iso": "2024-03-15"}],
    "legal_deadlines": [],
    "parties": [],
    "contradictions": [],
    "dispositive_points": [],
    "medical_findings": [],
    "medical_tests": [],
    "prior_convictions": [],
    "judge_and_court": {},
    "stats": {},
}
verification_report = {
    "articles": [],
    "laws_by_number": [],
    "case_numbers": [],
}

print(f"Testoj {len(DOCUMENT_REVIEW_PROMPTS)} seksione...")
for key in DOCUMENT_REVIEW_PROMPTS:
    ctx = build_verified_context(
        citation_profile, fact_profile, verification_report,
        document_type="Vendim", file_name="test.pdf", section_key=key,
    )
    has_anti = "ANTI-HALLUCINATION" in ctx
    has_law = "03/L-182" in ctx
    has_date = "15.03.2024" in ctx
    print(f"  {key:30s} anti={has_anti} law={has_law} date={has_date}")
    assert has_anti, f"Section {key} mungon anti-hallucination!"
    assert has_law, f"Section {key} mungon ligjin!"
    assert has_date, f"Section {key} mungon daten!"

print("\n[OK] Te gjitha seksionet kane anti-hallucination block.")