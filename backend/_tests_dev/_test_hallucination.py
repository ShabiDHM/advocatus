# FILE: backend/_tests_dev/_test_hallucination.py
"""Verifikon hallucination_checker: rast i paster + rast i dyshimte."""
from app.services.document_review.hallucination_checker import (
    HallucinationChecker,
    check_all_sections,
)

# Profilet "e verteta" te dokumentit
citation_profile = {
    "articles": [
        {"number": "1", "paragraph": "2", "law_hint": "03/L-182"},
        {"number": "5", "paragraph": None, "law_hint": "03/L-182"},
    ],
    "laws_by_number": [{"number": "03/L-182", "name": ""}],
    "abbreviations": ["LPK"],
    "case_numbers": [{"case_number": "P.nr.123/2024"}],
}
fact_profile = {
    "dates": [
        {"display": "15.03.2024", "iso": "2024-03-15"},
        {"display": "10.01.2024", "iso": "2024-01-10"},
    ],
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

checker = HallucinationChecker(citation_profile, fact_profile, verification_report)

# TEST 1: output i paster
clean_content = """
Sipas Nenit 1 par. 2 te Ligjit Nr. 03/L-182, i pandehuri u denua.
Vendimi u mor me 15.03.2024 dhe ka numer lende P.nr.123/2024.
"""

r1 = checker.check_section("document_summary", clean_content)
print("=" * 60)
print("TEST 1 — OUTPUT I PASTER")
print(f"  status: {r1['status']}")
print(f"  issues: {len(r1['issues'])}")
print(f"  counts: {r1['counts']}")
assert r1["status"] == "clean", f"Pritet clean, mori {r1['status']}"

# TEST 2: output me hallucinations
dirty_content = """
Sipas Nenit 42 par. 3 te Ligjit Nr. 08/L-999, i pandehuri u denua.
Vendimi u mor me 25.12.2025 dhe ka numer lende P.nr.999/2099.
"""

r2 = checker.check_section("document_summary", dirty_content)
print("=" * 60)
print("TEST 2 — OUTPUT ME HALLUCINATIONS")
print(f"  status: {r2['status']}")
print(f"  severity_counts: {r2['severity_counts']}")
for i in r2["issues"]:
    print(f"    [{i['severity']:6s}] {i['type']:12s} {i['value']}")
assert r2["status"] == "suspect", f"Pritet suspect, mori {r2['status']}"
assert r2["severity_counts"]["high"] >= 2, "Priten >=2 high (date + case)"
assert r2["severity_counts"]["medium"] >= 2, "Priten >=2 medium (law + article)"

# TEST 3: check_all_sections
sections = {
    "document_summary": {"title": "X", "content": clean_content},
    "article_verification": {"title": "Y", "content": dirty_content},
    "empty_section": {"title": "Z", "content": ""},
}
r3 = check_all_sections(
    sections, citation_profile, fact_profile, verification_report
)
print("=" * 60)
print("TEST 3 — ALL SECTIONS")
print(f"  status: {r3['status']}")
print(f"  total_issues: {r3['total_issues']}")
print(f"  severity_totals: {r3['severity_totals']}")
print(f"  suspicious_sections: {r3['suspicious_sections']}")
assert r3["status"] == "suspect"
assert "article_verification" in r3["suspicious_sections"]

print("=" * 60)
print("[OK] Te gjitha testet kaluan.")