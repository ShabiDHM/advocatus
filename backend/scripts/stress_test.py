# FILE: backend/scripts/stress_test.py
# PHOENIX PROTOCOL - STRESS TEST V1.0
# Ekzekuton pjesët deterministe mbi një folder dokumentesh dhe raporton
# statistika. Zero varësi LLM (falas). Përdoret për të verifikuar
# sjelljen e sistemit përpara testimit me LLM.
#
# Përdorimi:
#   cd backend
#   python scripts/stress_test.py [folder_path]
#
# Default folder: scripts/golden/documents/
#
# Exit code: 0 gjithmonë (raport, jo test PASS/FAIL).

import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_review.citation_extractor import build_citation_profile
from app.services.document_review.fact_extractor import build_fact_profile
from app.services.document_review.forensic_engine import (
    run_forensic_detectors,
    load_forensic_config,
)
from app.services.document_review.forensic_extractor import extract_forensic_data


logging.basicConfig(level=logging.WARNING)


# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTE
# ═══════════════════════════════════════════════════════════════════════════

# Pragje për "suspicious" — heuristika të buta
SUSPICIOUS_ARTICLES_MAX = 200
SUSPICIOUS_LAWS_MAX = 50
SUSPICIOUS_CASES_MAX = 50
SUSPICIOUS_DATES_MAX = 100
SUSPICIOUS_CONTRADICTIONS_MAX = 20


# ═══════════════════════════════════════════════════════════════════════════
# TEXT EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════

def _extract_text(file_path: Path) -> str:
    try:
        from app.services.text_extraction_service import extract_text
        return extract_text(str(file_path), "")
    except Exception as e:
        print(f"   ⚠️ Text extraction failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# DETEKTOR ANOMALISH
# ═══════════════════════════════════════════════════════════════════════════

def _detect_anomalies(
    counts: Dict[str, int],
    forensic_count: int,
    text_length: int,
) -> List[str]:
    """Kthen listë me anomali të mundshme (për t'u kontrolluar manualisht)."""
    anomalies: List[str] = []

    if counts["articles"] > SUSPICIOUS_ARTICLES_MAX:
        anomalies.append(
            f"Shumë nene ({counts['articles']} > {SUSPICIOUS_ARTICLES_MAX}) — "
            f"kontrollo për false-positive"
        )
    if counts["laws_by_number"] > SUSPICIOUS_LAWS_MAX:
        anomalies.append(
            f"Shumë ligje ({counts['laws_by_number']} > {SUSPICIOUS_LAWS_MAX})"
        )
    if counts["case_numbers"] > SUSPICIOUS_CASES_MAX:
        anomalies.append(
            f"Shumë numra lënde ({counts['case_numbers']} > {SUSPICIOUS_CASES_MAX})"
        )
    if counts["dates"] > SUSPICIOUS_DATES_MAX:
        anomalies.append(
            f"Shumë data ({counts['dates']} > {SUSPICIOUS_DATES_MAX})"
        )
    if counts["contradictions"] > SUSPICIOUS_CONTRADICTIONS_MAX:
        anomalies.append(
            f"Shumë kontradikta ({counts['contradictions']} > "
            f"{SUSPICIOUS_CONTRADICTIONS_MAX})"
        )

    if text_length > 0 and text_length < 500:
        anomalies.append(
            f"Tekst shumë i shkurtër ({text_length} chars) — "
            f"ndoshta nuk u ekstraktua saktë"
        )

    return anomalies


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def _process_doc(doc_path: Path) -> Dict[str, Any]:
    """Proceson një dokument dhe kthen stats + anomalies."""
    result: Dict[str, Any] = {
        "file_name": doc_path.name,
        "path": str(doc_path),
        "text_length": 0,
        "counts": {},
        "forensic_total": 0,
        "forensic_rules": [],
        "anomalies": [],
        "error": None,
    }

    try:
        text = _extract_text(doc_path)
    except Exception as e:
        result["error"] = f"extract failed: {e}"
        return result

    if not text or len(text.strip()) < 50:
        result["error"] = f"text too short ({len(text)} chars)"
        return result

    result["text_length"] = len(text)

    try:
        citation = build_citation_profile(text)
        facts = build_fact_profile(text, source_document=doc_path.name)
    except Exception as e:
        result["error"] = f"extraction pipeline failed: {e}"
        return result

    cs = citation.get("stats", {}) or {}
    fs = facts.get("stats", {}) or {}

    result["counts"] = {
        "articles": int(cs.get("total_articles", 0) or 0),
        "laws_by_number": int(cs.get("total_laws_by_number", 0) or 0),
        "laws_by_name": int(cs.get("total_laws_by_name", 0) or 0),
        "abbreviations": int(cs.get("total_abbreviations", 0) or 0),
        "case_numbers": int(cs.get("total_case_numbers", 0) or 0),
        "dates": int(fs.get("total_dates", 0) or 0),
        "deadlines": int(fs.get("legal_deadlines", 0) or 0),
        "parties": int(fs.get("total_parties", 0) or 0),
        "suspects": int(fs.get("total_suspects", 0) or 0),
        "contradictions": len(facts.get("contradictions", []) or []),
    }

    # Forensic
    try:
        config = load_forensic_config()
        struct = extract_forensic_data(text, doc_path.name)
        flags = run_forensic_detectors([struct])
        result["forensic_total"] = len(flags)
        result["forensic_rules"] = sorted({f.rule_id for f in flags})
    except Exception as e:
        result["error"] = f"forensic failed: {e}"

    # Anomalies
    result["anomalies"] = _detect_anomalies(
        counts=result["counts"],
        forensic_count=result["forensic_total"],
        text_length=result["text_length"],
    )

    return result


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent / "golden" / "documents"
    )

    if not folder.exists():
        print(f"❌ Folderi {folder} nuk ekziston.")
        return 1

    # Mblidh të gjitha dokumentet (rekursivisht)
    docs: List[Path] = []
    for ext in ("*.pdf", "*.docx", "*.doc", "*.txt"):
        docs.extend(folder.rglob(ext))

    docs = sorted(docs)
    if not docs:
        print(f"⚠️ Nuk u gjetën dokumente në {folder}")
        return 1

    print("=" * 78)
    print(f"🔬 STRESS TEST — {len(docs)} dokumente në {folder}")
    print("=" * 78)
    print()

    results: List[Dict[str, Any]] = []
    with_anomalies = 0
    with_errors = 0

    for i, doc_path in enumerate(docs, 1):
        print(f"[{i}/{len(docs)}] 📄 {doc_path.name}")
        r = _process_doc(doc_path)
        results.append(r)

        if r["error"]:
            print(f"   ❌ {r['error']}")
            with_errors += 1
            print()
            continue

        c = r["counts"]
        print(f"   📊 Text: {r['text_length']} chars")
        print(
            f"   🔬 art={c['articles']}, law#={c['laws_by_number']}, "
            f"abbr={c['abbreviations']}, case#={c['case_numbers']}, "
            f"dates={c['dates']}, parties={c['parties']}, "
            f"suspects={c['suspects']}, contr={c['contradictions']}"
        )
        print(f"   🔴 forensic: {r['forensic_total']} flags "
              f"({len(r['forensic_rules'])} unique rules)")

        if r["anomalies"]:
            print(f"   ⚠️ ANOMALI ({len(r['anomalies'])}):")
            for a in r["anomalies"]:
                print(f"      - {a}")
            with_anomalies += 1
        else:
            print(f"   ✅ OK")

        print()

    print("=" * 78)
    print(f"📊 REZULTATI: {len(results)} dokumente "
          f"({with_anomalies} me anomali, {with_errors} gabime)")
    print("=" * 78)

    # Raport JSON (opsionale)
    report_path = folder / "stress_test_report.json"
    try:
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"📝 Raport JSON: {report_path}")
    except Exception as e:
        print(f"⚠️ Raporti JSON nuk u ruajt: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())