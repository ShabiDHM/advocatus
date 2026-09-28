# FILE: backend/scripts/run_golden.py
# PHOENIX PROTOCOL - GOLDEN DATASET RUNNER V2.0
# V2.0: DY KATEGORI — analizo/ dhe verifiko/. Struktura e re e folderave
#       me nën-folderë për secilin pipeline. Raport i veçantë.
# V1.0: Versioni fillestar.

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_review.citation_extractor import build_citation_profile
from app.services.document_review.fact_extractor import build_fact_profile
from app.services.document_review.forensic_engine import (
    run_forensic_detectors,
    load_forensic_config,
)
from app.services.document_review.forensic_extractor import extract_forensic_data


GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_text(file_path: Path) -> str:
    try:
        from app.services.text_extraction_service import extract_text
        return extract_text(str(file_path), "")
    except Exception as e:
        print(f"   ⚠️ Text extraction failed: {e}")
        return ""


def _compare_min_thresholds(
    actual: Dict[str, int],
    expected: Dict[str, int],
) -> List[str]:
    failures: List[str] = []
    for key, min_val in expected.items():
        actual_val = actual.get(key, 0)
        if actual_val < min_val:
            failures.append(
                f"{key}: {actual_val} < {min_val} (i pritur ≥ {min_val})"
            )
    return failures


def _extract_actual_counts(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
) -> Dict[str, int]:
    cs = citation_profile.get("stats", {}) or {}
    fs = fact_profile.get("stats", {}) or {}
    return {
        "articles": int(cs.get("total_articles", 0) or 0),
        "laws_by_number": int(cs.get("total_laws_by_number", 0) or 0),
        "case_numbers": int(cs.get("total_case_numbers", 0) or 0),
        "dates": int(fs.get("total_dates", 0) or 0),
        "deadlines": int(fs.get("legal_deadlines", 0) or 0),
        "parties": int(fs.get("total_parties", 0) or 0),
        "dispositive_points": len(fact_profile.get("dispositive_points", []) or []),
    }


def _check_forensic_rules(
    text: str,
    file_name: str,
    document_type: str,
    expected_any: List[str],
    min_count: int,
) -> Tuple[List[str], List[str], int]:
    failures: List[str] = []
    matched: List[str] = []

    if not text:
        failures.append("Nuk mund të ekzekutohet forensiku — tekst bosh")
        return failures, matched, 0

    try:
        config = load_forensic_config()
    except Exception as e:
        failures.append(f"Forensic config load dështoi: {e}")
        return failures, matched, 0

    profile = None
    mapping = config.get("document_type_to_profile", {})
    if document_type and document_type in mapping:
        profile = mapping[document_type]

    struct = extract_forensic_data(text, file_name)
    flags = run_forensic_detectors([struct], profile=profile)

    flag_ids = {f.rule_id for f in flags}

    for rule_id in expected_any:
        if rule_id in flag_ids:
            matched.append(rule_id)

    if min_count > 0 and len(matched) < min_count:
        missing = set(expected_any) - set(matched)
        failures.append(
            f"Forensik: u gjetën {len(matched)}/{min_count}. Mungojnë: {sorted(missing)}"
        )

    return failures, matched, len(flags)


def _run_category(category: str) -> Tuple[int, int]:
    """
    Ekzekuton të gjitha testet për një kategori (analizo/ ose verifiko/).
    Kthen: (passed, failed)
    """
    docs_dir = GOLDEN_DIR / "documents" / category
    expected_dir = GOLDEN_DIR / "expected" / category

    print(f"\n{'═' * 70}")
    print(f"📂 KATEGORIA: {category.upper()}")
    print(f"{'═' * 70}\n")

    if not docs_dir.exists():
        print(f"⚠️ Folderi {docs_dir} nuk ekziston — skip.")
        return 0, 0

    if not expected_dir.exists():
        print(f"⚠️ Folderi {expected_dir} nuk ekziston — skip.")
        return 0, 0

    expected_files = sorted(expected_dir.glob("*.json"))
    if not expected_files:
        print(f"⚠️ Nuk ka file expected/*.json në {expected_dir}")
        return 0, 0

    passed = 0
    failed = 0

    for exp_file in expected_files:
        try:
            with exp_file.open("r", encoding="utf-8") as f:
                expected = json.load(f)
        except Exception as e:
            print(f"❌ {exp_file.name}: JSON i pavlefshëm — {e}")
            failed += 1
            continue

        file_name = expected.get("file_name")
        document_type = expected.get("document_type", "Dokument")

        if not file_name:
            print(f"❌ {exp_file.name}: 'file_name' mungon")
            failed += 1
            continue

        doc_path = docs_dir / file_name
        if not doc_path.exists():
            print(f"❌ {file_name}: nuk gjendet në documents/{category}/")
            failed += 1
            continue

        print(f"🔍 {file_name}")

        text = _extract_text(doc_path)
        if not text or len(text.strip()) < 100:
            print(f"   ❌ Teksti bosh ose shumë i shkurtër ({len(text)} chars)")
            failed += 1
            print()
            continue

        print(f"   📄 Text: {len(text)} chars")

        try:
            citation_profile = build_citation_profile(text)
            fact_profile = build_fact_profile(text, source_document=file_name)
        except Exception as e:
            print(f"   ❌ Ekstraktimi dështoi: {e}")
            failed += 1
            print()
            continue

        actual_counts = _extract_actual_counts(citation_profile, fact_profile)
        print(
            f"   🔬 Actual: articles={actual_counts['articles']}, "
            f"laws={actual_counts['laws_by_number']}, "
            f"cases={actual_counts['case_numbers']}, "
            f"dates={actual_counts['dates']}, "
            f"deadlines={actual_counts['deadlines']}, "
            f"parties={actual_counts['parties']}, "
            f"dispositive={actual_counts['dispositive_points']}"
        )

        failures: List[str] = []
        min_thresholds = expected.get("min_thresholds", {})
        failures.extend(_compare_min_thresholds(actual_counts, min_thresholds))

        exp_rules = expected.get("expected_forensic_rules_any", [])
        min_rules = int(expected.get("expected_forensic_rules_min_count", 0) or 0)
        if exp_rules:
            f_fails, f_matched, f_total = _check_forensic_rules(
                text=text,
                file_name=file_name,
                document_type=document_type,
                expected_any=exp_rules,
                min_count=min_rules,
            )
            failures.extend(f_fails)
            print(f"   🔴 Forensik: {f_total} konstatime, matched={f_matched}")

        if failures:
            print(f"   ❌ FAIL ({len(failures)} arsye):")
            for f in failures:
                print(f"      - {f}")
            failed += 1
        else:
            print(f"   ✅ PASS")
            passed += 1

        print()

    return passed, failed


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 70)
    print("🧪 GOLDEN DATASET RUNNER — Juristi AI (V2.0)")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    for category in ("analizo", "verifiko"):
        p, f = _run_category(category)
        total_passed += p
        total_failed += f

    print("=" * 70)
    print(
        f"📊 REZULTATI TOTAL: {total_passed} PASS, {total_failed} FAIL, "
        f"gjithsej {total_passed + total_failed}"
    )
    print("=" * 70)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())