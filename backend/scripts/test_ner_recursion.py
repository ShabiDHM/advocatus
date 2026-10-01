# FILE: backend/scripts/test_ner_recursion.py
"""Test që NER vazhdon të nxjerrë entitete pas FIX 11d (redact_pii=False)."""
import sys
import os
from pathlib import Path

# Shto backend/ në sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.WARNING)

from app.services.albanian_ner_service import ALBANIAN_NER_SERVICE


def main():
    text = (
        "Gjyqtari Arben Krasniqi ka shqyrtuar lëndën. "
        "Prokurorja Fikrije Sylejmani ka paraqitur aktakuzën. "
        "Email kontakti: arben@test.com, Tel: +383 44 123 456."
    )

    print("=" * 70)
    print("TEST: NER pas FIX 11d (redact_pii=False)")
    print("=" * 70)

    result = ALBANIAN_NER_SERVICE.extract_legal_entities(
        text=text,
        document_id="test_recursion",
    )

    stats = result["stats"]
    print(f"\nStats:")
    print(f"  Total entities:  {stats['total_entities']}")
    print(f"  Raw entities:    {stats['total_raw_entities']}")
    print(f"  Chunks failed:   {stats['chunks_failed']}")
    print(f"  Duration:        {stats['duration_sec']}s")

    print(f"\nEntities ({len(result['entities_flat'])}):")
    for e in result["entities_flat"][:10]:
        print(f"  - [{e['label']:12}] {e['text']}  (conf={e['confidence']:.2f})")

    joined = " ".join(e["text"] for e in result["entities_flat"])
    if "Arben Krasniqi" in joined or "Fikrije Sylejmani" in joined:
        print("\nOK: NER sheh emrat origjinale (pa redaktim).")
    else:
        print("\nWARN: NER nuk gjeti emrat — verifiko redact_pii=False.")

    print("OK: Pa RecursionError.")


if __name__ == "__main__":
    main()