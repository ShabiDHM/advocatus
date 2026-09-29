# FILE: backend/tests/test_laws_library.py
# PHOENIX PROTOCOL - LAWS LIBRARY TESTS V1.1
#
# V1.1: SUPPRESS i log-eve të pritura.
#   - Log i post_processor-ës (FAIL) është i qëllimshëm gjatë testit T1
#     (teston detektimin e halluzinimit). Tani nuk shfaqet në output.
#
# V1.0: Teste sipas Rregullit 14:
#   T1: False-positive (input i gabuar → NUK shpik)
#   T2: Real (input i saktë → kthen të vërtetën)
#   T3: Morfologji (case, diakritika, formate)
#
# ZERO KOSTO LLM — vetëm Python + MongoDB (read-only).
#
# Përdorimi:
#   cd backend
#   python -m tests.test_laws_library

import os
import sys
import logging
import traceback
from typing import List, Tuple

# ═══════════════════════════════════════════════════════════════════════════
# LOG SUPPRESSION (V1.1)
# ═══════════════════════════════════════════════════════════════════════════
# Suppress log-et e pritura gjatë testit (post_processor FAIL, etj.)
logging.basicConfig(level=logging.CRITICAL)
logging.disable(logging.CRITICAL)

# Shto backend/ në path
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# TEST FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
        self.tests: List[Tuple[str, str, bool, str]] = []

    def add(self, group: str, name: str, ok: bool, msg: str = ""):
        self.tests.append((group, name, ok, msg))
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"[{group}] {name}: {msg}")

    def summary(self) -> str:
        total = self.passed + self.failed
        lines = [
            "═" * 75,
            f"REZULTATI: {self.passed}/{total} PASS",
            "═" * 75,
        ]
        for group, name, ok, msg in self.tests:
            icon = "✅" if ok else "❌"
            lines.append(f"{icon} [{group}] {name}")
            if not ok and msg:
                lines.append(f"      → {msg}")
        if self.errors:
            lines.append("")
            lines.append("═" * 75)
            lines.append(f"GABIME ({len(self.errors)}):")
            lines.append("═" * 75)
            for e in self.errors:
                lines.append(f"  • {e}")
        return "\n".join(lines)


RESULT = TestResult()


def check(group: str, name: str, condition: bool, msg: str = ""):
    RESULT.add(group, name, condition, msg)


def check_eq(group: str, name: str, actual, expected, msg: str = ""):
    ok = actual == expected
    detail = msg or f"actual={actual!r}, expected={expected!r}"
    check(group, name, ok, detail if not ok else "")


# ═══════════════════════════════════════════════════════════════════════════
# SETUP — importet e target
# ═══════════════════════════════════════════════════════════════════════════

try:
    from app.api.endpoints.laws_pkg.laws_dictionary import (
        _normalize_hallucinated_title,
        _is_case_law,
        _natural_sort_key,
        _normalize_diacritics,
        _strip_alpha,
        clear_canonical_title_cache,
    )
    from app.api.endpoints.laws_pkg.laws_search_service import (
        _score_candidate,
        _compute_confidence,
        _build_art_variants,
        _tokenize_title,
    )
    from app.services.law_library.post_processor import (
        verify_explanation_output,
        _normalize_law_number,
        _extract_articles,
        _extract_law_numbers,
    )
    from app.services.law_library.article_fetcher import (
        _normalize_article,
        _build_title_patterns,
    )
    IMPORTS_OK = True
    IMPORT_ERROR = ""
except Exception as e:
    IMPORTS_OK = False
    IMPORT_ERROR = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


# ═══════════════════════════════════════════════════════════════════════════
# T1 — FALSE-POSITIVE
# ═══════════════════════════════════════════════════════════════════════════

def run_t1_false_positive():
    group = "T1-false-positive"

    result = _normalize_hallucinated_title("Ligji XYZ Kuantik", "42", db=None)
    check_eq(group, "titull i panjohur pa DB → passthrough",
             result, "Ligji XYZ Kuantik")

    result = _normalize_hallucinated_title("Ligji përkatës", "297", db=None)
    check_eq(group, "ligji përkatës pa DB → NUK shpik",
             result, "Ligji përkatës",
             msg="V5.0 do kthente LIGJI NR. 03/L-006 (hardcoded) — bug")

    check_eq(group, "titull bosh → bosh",
             _normalize_hallucinated_title("", "5", db=None), "")
    check_eq(group, "titull None → bosh",
             _normalize_hallucinated_title(None, "5", db=None), "")

    result = verify_explanation_output(
        output_text="Sipas nenit 999, vepra dënohet me burg.",
        source_text="Neni 5. Vjedhja dënohet me gjobë.",
        source_article="5",
        source_law_title="Kodi Penal Nr. 06/L-074",
    )
    check(group, "LLM shpik nen 999 → flag i saktë",
          "999" in result.get("extra_articles", []),
          msg=f"extra_articles={result.get('extra_articles')}")
    check(group, "LLM shpik nen → is_clean=False",
          result.get("is_clean") is False,
          msg=f"is_clean={result.get('is_clean')}")

    result = verify_explanation_output(
        output_text="Sipas ligjit 99/L-999, dispozita zbatohet.",
        source_text="Neni 5 i Kodit Penal.",
        source_article="5",
        source_law_title="Kodi Penal Nr. 06/L-074",
    )
    check(group, "LLM shpik numër ligji → flag",
          len(result.get("extra_law_numbers", [])) > 0,
          msg=f"extra_law_numbers={result.get('extra_law_numbers')}")

    check_eq(group, "_normalize_article('') → ''", _normalize_article(""), "")
    check_eq(group, "_normalize_article(None) → ''", _normalize_article(None), "")
    check_eq(group, "_build_art_variants('') → []", _build_art_variants(""), [])

    words, digits = _tokenize_title("")
    check_eq(group, "_tokenize_title('') words → []", words, [])
    check_eq(group, "_tokenize_title('') digits → []", digits, [])

    check_eq(group, "_build_title_patterns('') → []", _build_title_patterns(""), [])


# ═══════════════════════════════════════════════════════════════════════════
# T2 — REAL
# ═══════════════════════════════════════════════════════════════════════════

def run_t2_real():
    group = "T2-real"

    check(group, "PRAKTIKË → case_law", _is_case_law("PRAKTIKA GJYQËSORE 2020"))
    check(group, "AKTGJYKIM → case_law", _is_case_law("AKTGJYKMET E GJYKATËS SUPREME") is True)
    check(group, "Kodi Penal → NUK case_law", _is_case_law("Kodi Penal Nr. 06/L-074") is False)
    check(group, "Case_Law → case_law", _is_case_law("Case_Law 2023"))

    check_eq(group, "_natural_sort_key('5')", _natural_sort_key("5"), [5])
    check_eq(group, "_natural_sort_key('5/1') → sub-article",
             _natural_sort_key("5/1"), [5, 1])
    check_eq(group, "_natural_sort_key('5.2') → sub-article dot",
             _natural_sort_key("5.2"), [5, 2])
    check_eq(group, "_natural_sort_key('10')", _natural_sort_key("10"), [10])
    check(group, "sort natural: 5, 10, 2 → 2, 5, 10",
          sorted([5, 10, 2], key=_natural_sort_key) == [2, 5, 10])

    check_eq(group, "_normalize_article('Neni 5')",
             _normalize_article("Neni 5"), "5")
    check_eq(group, "_normalize_article('5/1') → sub-article",
             _normalize_article("5/1"), "5/1")
    check_eq(group, "_normalize_article('Neni 5.2') → dot sub-article",
             _normalize_article("Neni 5.2"), "5.2")

    variants = _build_art_variants("5")
    check(group, "_build_art_variants('5') përmban '5'", "5" in variants)
    check(group, "_build_art_variants('5') përmban '5.'", "5." in variants)
    check(group, "_build_art_variants('5') përmban int 5", 5 in variants)
    check(group, "_build_art_variants('5') përmban 'Neni 5'", "Neni 5" in variants)

    patterns = _build_title_patterns("Kodi Penal Nr. 06/L-074")
    check(group, "_build_title_patterns gjeneron pattern për '06/L-074'",
          any("06" in p and "074" in p for p in patterns))

    score_exact = _score_candidate("Kodi Penal", "Kodi Penal")
    check(group, "_score_candidate exact match → maksimal",
          score_exact >= 10000, msg=f"score={score_exact}")

    score_sub = _score_candidate("Kodi Penal", "Kodi Penal i Kosovës")
    check(group, "_score_candidate substring → i lartë por jo maksimal",
          5000 <= score_sub < 10000, msg=f"score={score_sub}")

    score_none = _score_candidate("Kodi Penal", "Ligji i Punës")
    check(group, "_score_candidate pa match → i ulët",
          score_none < 5000, msg=f"score={score_none}")

    level, score, desc = _compute_confidence({}, {}, False)
    check_eq(group, "_compute_confidence({}) level", level, "NONE")
    check_eq(group, "_compute_confidence({}) score", score, 0.0)

    level, score, desc = _compute_confidence(
        {"law_title": "Kodi Penal", "source": "kodi_penal.pdf"},
        {"title_match_type": "exact", "article_matches": 3, "candidate_count": 5},
        page_available=True,
    )
    check(group, "_compute_confidence exact → HIGH",
          level == "HIGH", msg=f"level={level}, score={score}")
    check(group, "_compute_confidence exact → score >= 0.9",
          score >= 0.9, msg=f"score={score}")

    level2, score2, _ = _compute_confidence(
        {"law_title": "Kodi Penal", "source": "kodi_penal.pdf"},
        {"title_match_type": "exact", "article_matches": 1, "candidate_count": 5},
        page_available=False,
    )
    check(group, "_compute_confidence pa faqe → score < me faqe",
          score2 < score, msg=f"with_page={score}, without_page={score2}")

    result = verify_explanation_output(
        output_text="Sipas nenit 5, vepra dënohet me gjobë.",
        source_text="Neni 5. Vjedhja dënohet me gjobë.",
        source_article="5",
        source_law_title="Kodi Penal",
    )
    check(group, "post_processor output i pastër → is_clean=True",
          result.get("is_clean") is True,
          msg=f"extra_articles={result.get('extra_articles')}")

    check_eq(group, "_normalize_law_number('06/L-074')",
             _normalize_law_number("06/L-074"), "06L074")
    check_eq(group, "_normalize_law_number('06 L 074')",
             _normalize_law_number("06 L 074"), "06L074")
    check_eq(group, "_normalize_law_number('2004/32')",
             _normalize_law_number("2004/32"), "200432")

    articles = _extract_articles("Sipas nenit 5 dhe nenit 10, dispozita...")
    check(group, "_extract_articles gjen 5 dhe 10",
          "5" in articles and "10" in articles,
          msg=f"articles={articles}")

    nums = _extract_law_numbers("Sipas ligjit 06/L-074 dhe ligjit 2004/32")
    check(group, "_extract_law_numbers gjen 06L074 dhe 200432",
          "06L074" in nums and "200432" in nums,
          msg=f"nums={nums}")


# ═══════════════════════════════════════════════════════════════════════════
# T3 — MORFOLOGJI
# ═══════════════════════════════════════════════════════════════════════════

def run_t3_morphology():
    group = "T3-morphology"

    check_eq(group, "_normalize_diacritics('Kosovë')",
             _normalize_diacritics("Kosovë"), "Kosove")
    check_eq(group, "_normalize_diacritics('Çështje')",
             _normalize_diacritics("Çështje"), "Ceshtje")
    check_eq(group, "_normalize_diacritics('Kosovë') == _normalize_diacritics('Kosove')",
             _normalize_diacritics("Kosovë") == _normalize_diacritics("Kosove"), True)

    check(group, "'praktikë' lowercase → case_law", _is_case_law("praktikë gjyqësore"))
    check(group, "'PRAKTIKË' uppercase → case_law", _is_case_law("PRAKTIKË GJYQËSORE"))
    check(group, "'Praktike' pa diakritikë → case_law", _is_case_law("Praktike Gjyqesore"))

    check_eq(group, "_strip_alpha('Kodi_Penal.PDF')",
             _strip_alpha("Kodi_Penal.PDF"), "kodipenal")
    check_eq(group, "_strip_alpha('03/L-074.pdf')",
             _strip_alpha("03/L-074.pdf"), "03l074")
    check_eq(group, "_strip_alpha('Ligji i Punës.pdf')",
             _strip_alpha("Ligji i Punës.pdf"), "ligjiipunes")

    s1 = _score_candidate("Kodi Penal", "KODI PENAL")
    s2 = _score_candidate("KODI PENAL", "kodi penal")
    s3 = _score_candidate("kodi penal", "Kodi Penal")
    check(group, "_score_candidate case-insensitive (3 variante)",
          s1 >= 10000 and s2 >= 10000 and s3 >= 10000,
          msg=f"s1={s1}, s2={s2}, s3={s3}")

    s = _score_candidate("Kodi Penal i Kosovës", "Kodi Penal i Kosoves")
    check(group, "_score_candidate diakritika normalized (ë=e)",
          s >= 10000, msg=f"score={s}")

    r1 = _normalize_hallucinated_title("KODI PENAL", "5", db=None)
    r2 = _normalize_hallucinated_title("Kodi Penal", "5", db=None)
    r3 = _normalize_hallucinated_title("  Kodi Penal  ", "5", db=None)
    check_eq(group, "normalize uppercase→orig", r1, "KODI PENAL")
    check_eq(group, "normalize mixed→orig", r2, "Kodi Penal")
    check_eq(group, "normalize me hapësira→strip", r3, "Kodi Penal")

    for text in ["Neni 5", "neni 5", "NENI 5", "Nenit 5", "Nenin 5", "Neniet 5"]:
        arts = _extract_articles(text)
        check(group, f"_extract_articles('{text}')",
              "5" in arts, msg=f"gjeti {arts}")

    forms = ["06/L-074", "06 L 074", "06_l_074", "06-L-074"]
    normalized = [_normalize_law_number(f) for f in forms]
    check(group, "formatet e 06/L-074 → të gjitha identike",
          len(set(normalized)) == 1,
          msg=f"normalized={normalized}")

    variants = _build_art_variants("5/1")
    check(group, "_build_art_variants('5/1') përmban '5/1'", "5/1" in variants)
    check(group, "_build_art_variants('5/1') përmban '5' (base)", "5" in variants)

    arts = ["10", "5", "2", "1", "5/1", "5/2", "100"]
    sorted_arts = sorted(arts, key=_natural_sort_key)
    expected_order = ["1", "2", "5", "5/1", "5/2", "10", "100"]
    check_eq(group, "sort natural i artikujve me sub-article",
             sorted_arts, expected_order)


# ═══════════════════════════════════════════════════════════════════════════
# T4 — DB INTEGRATION (read-only)
# ═══════════════════════════════════════════════════════════════════════════

def run_t4_db_integration():
    group = "T4-db-integration"

    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        if db is None:
            check(group, "DB connection", False, msg="get_db_instance() → None")
            return
    except Exception as e:
        check(group, "DB connection", False, msg=f"{type(e).__name__}: {e}")
        return

    check(group, "DB connection OK", True)

    try:
        collection = db["legal_knowledge_base"]
        count = collection.estimated_document_count()
        check(group, f"DB ka dokumente (count={count})",
              count > 0, msg=f"count={count}")

        clear_canonical_title_cache()
        result = _normalize_hallucinated_title("Kodi Penal", "", db=db)
        check(group, "DB normalization 'Kodi Penal' → titull kanonik",
              bool(result) and "penal" in result.lower(),
              msg=f"result={result!r}")

        clear_canonical_title_cache()
        r1 = _normalize_hallucinated_title("KODI PENAL", "", db=db)
        clear_canonical_title_cache()
        r2 = _normalize_hallucinated_title("kodi penal", "", db=db)
        check(group, "DB normalization case-insensitive → të njëjtin",
              r1 == r2 and bool(r1), msg=f"r1={r1!r}, r2={r2!r}")

        clear_canonical_title_cache()
        r3 = _normalize_hallucinated_title("Ligj Absurd 9999", "", db=db)
        check_eq(group, "DB normalization ligj absurd → passthrough",
                 r3, "Ligj Absurd 9999")
    except Exception as e:
        check(group, "DB integration", False, msg=f"{type(e).__name__}: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 75)
    print("LAWS LIBRARY — TEST SUITE V1.1")
    print("═" * 75)
    print()

    if not IMPORTS_OK:
        print("❌ IMPORT FAILED — testet nuk mund të ekzekutohen:")
        print(IMPORT_ERROR)
        sys.exit(1)

    print("✅ Importet OK (log-et e pritura të suppress-uara)\n")

    print("─" * 75)
    print("T1 — FALSE-POSITIVE")
    print("─" * 75)
    run_t1_false_positive()

    print("\n" + "─" * 75)
    print("T2 — REAL")
    print("─" * 75)
    run_t2_real()

    print("\n" + "─" * 75)
    print("T3 — MORFOLOGJI")
    print("─" * 75)
    run_t3_morphology()

    print("\n" + "─" * 75)
    print("T4 — DB INTEGRATION (read-only)")
    print("─" * 75)
    run_t4_db_integration()

    print()
    print(RESULT.summary())

    sys.exit(0 if RESULT.failed == 0 else 1)


if __name__ == "__main__":
    main()