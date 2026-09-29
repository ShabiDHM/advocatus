# FILE: backend/scripts/test_external_sources.py
# PHOENIX PROTOCOL - EXTERNAL SOURCES TEST V1.1 (SHQIP)
#
# Verifikon që KEDNJ/OKB/Hagë klasifikohen si "external" (jo "unverified").
# V1.1: Etiketat në shqip për lexueshmëri më të mirë.

import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.core.db import get_db_instance
from app.services.document_review.mongo_verifier import verify_all


def _status_label(r: dict) -> str:
    """Kthen etiketën e statusit në shqip."""
    if r.get("is_external"):
        ext_id = r.get("external_source_id", "")
        return f"🌐 BURIM NDËRKOMBËTAR [{ext_id}]"
    if r.get("exists"):
        return "✅ VERIFIKUAR"
    return "❌ NUK U GJT"


def _reason_label(reason: str) -> str:
    """Përkthen match_reason në shqip për lexueshmëri."""
    mapping = {
        "international_treaty_constitutional": "Traktat ndërkombëtar (Neni 22 i Kushtetutës)",
        "article_not_in_db": "Neni nuk ekziston në bazë",
        "no_db": "Baza e të dhënave e padisponueshme",
        "law_hint_no_match": "Ligji nuk u gjet",
        "law_hint_no_match_but_exists_elsewhere": "Ekziston në ligj tjetër (gabim citimi)",
        "single_law_in_db": "Vetëm një ligj në bazë",
    }
    if reason in mapping:
        return mapping[reason]
    if reason.startswith("abbrev_known:"):
        return f"Akronim i njohur ({reason.split(':', 1)[1]})"
    if reason.startswith("abbrev_alias:"):
        return f"Alias akronimi ({reason.split(':', 1)[1]})"
    if reason.startswith("abbrev_match_alias:"):
        return f"Alias akronimi ({reason.split(':', 1)[1]})"
    if reason.startswith("found_in_successor_law"):
        return "Gjetur në ligj pasardhës"
    if reason.startswith("compound_abbrev"):
        return "Akronim i përbërë"
    if reason.startswith("law_replaced_by"):
        return "Ligj i zëvendësuar"
    if reason.startswith("error:"):
        return f"Gabim: {reason.split(':', 1)[1]}"
    if reason.startswith("multiple_laws_no_hint"):
        return f"Shumë ligje pa kontekst ({reason.split(':', 1)[1]})"
    return reason or "—"


def main():
    print("═" * 75)
    print("TEST — BURIME NDËRKOMBËTARE (KEDNJ / OKB / Hagë)")
    print("═" * 75)

    citation_profile = {
        "articles": [
            # KEDNJ
            {"number": "6", "paragraph": None, "law_hint": "KEDNJ", "context": "", "sentence": ""},
            {"number": "8", "paragraph": None, "law_hint": "KEDNJ", "context": "", "sentence": ""},
            {"number": "13", "paragraph": None, "law_hint": "KEDNJ", "context": "", "sentence": ""},
            # OKB
            {"number": "3", "paragraph": None, "law_hint": "Konventa e OKB-së për të Drejtat e Fëmijës", "context": "", "sentence": ""},
            {"number": "12", "paragraph": None, "law_hint": "OKB për të drejtat e fëmijës", "context": "", "sentence": ""},
            # Hagë
            {"number": "3", "paragraph": None, "law_hint": "Konventa e Hagës", "context": "", "sentence": ""},
            # LPK (kontroll pozitiv — duhet të verifikohet në DB)
            {"number": "360", "paragraph": None, "law_hint": "LPK", "context": "", "sentence": ""},
            {"number": "319", "paragraph": None, "law_hint": "LPK", "context": "", "sentence": ""},
            # Nen inekzistent (test negativ)
            {"number": "99999", "paragraph": None, "law_hint": "LPK", "context": "", "sentence": ""},
        ],
        "laws_by_number": [],
        "case_numbers": [],
    }

    db = get_db_instance()
    report = verify_all(db, citation_profile)

    print("\n" + "─" * 75)
    print("REZULTATET")
    print("─" * 75)

    for r in report["articles"]:
        art = r.get("article_number")
        hint = r.get("law_hint", "")
        status = _status_label(r)
        reason = _reason_label(r.get("match_reason", ""))

        hint_display = hint if len(hint) <= 40 else hint[:37] + "..."
        print(f"  {status}")
        print(f"     Neni {art} i '{hint_display}'")
        print(f"     Arsyeja: {reason}")
        print()

    print("─" * 75)
    print("STATISTIKA")
    print("─" * 75)
    stats = report["stats"]

    labels = {
        "articles_total": "Nene gjithsej",
        "articles_verified": "Nene të verifikuar (në DB)",
        "articles_not_found": "Nene që nuk u gjetën (të vërtetë)",
        "articles_external": "Nene në burime ndërkombëtare",
        "articles_external_kednj": "  • KEDNJ",
        "articles_external_okb": "  • OKB për Fëmijët",
        "articles_external_haga": "  • Konventa e Hagës",
        "articles_in_successor_laws": "Nene në ligje pasardhëse",
        "articles_via_alias": "Nene përmes aliasit të akronimit",
    }

    for key, label in labels.items():
        value = stats.get(key, 0)
        print(f"  {label}: {value}")

    print()
    print("═" * 75)
    print("✅ Test përfundoi")
    print("═" * 75)


if __name__ == "__main__":
    main()