# FILE: backend/scripts/test_rag_redaction.py
"""Test redaction helper për RAG chat (pa LLM call)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.WARNING)

from app.services.rag.response_generator import _redact_messages_for_llm


def main():
    messages = [
        {"role": "system", "content": "Konteksti: Email i palës arben@test.com, IBAN AL35202111090000000001234567."},
        {"role": "user", "content": "Pyetje e vjetër nga Arben Krasniqi."},
        {"role": "assistant", "content": "Përgjigje e vjetër."},
        {"role": "user", "content": "Kush është Gjyqtari Arben Krasniqi? Email: arben@test.com"},
    ]

    print("=" * 70)
    print("TEST: RAG redaction helper")
    print("=" * 70)

    result = _redact_messages_for_llm(messages)

    for i, (orig, new) in enumerate(zip(messages, result)):
        role = orig.get("role")
        changed = "CHANGED" if orig["content"] != new["content"] else "same"
        print(f"\n[{i}] {role} ({changed}):")
        print(f"    IN:  {orig['content'][:80]}")
        print(f"    OUT: {new['content'][:80]}")

    # Kontrolle
    sys_content = result[0]["content"]
    old_user = result[1]["content"]
    new_user = result[3]["content"]

    print("\nKontroll:")
    print(f"  System: email redaktuar?   {'[EMAIL' in sys_content}")
    print(f"  System: IBAN redaktuar?    {'[IBAN' in sys_content}")
    print(f"  Historik user: i pandryshuar? {old_user == messages[1]['content']}")
    print(f"  User i fundit: emri redaktuar? {'[EMRI' in new_user or '[ENTITY' in new_user}")
    print(f"  User i fundit: email redaktuar? {'[EMAIL' in new_user}")


if __name__ == "__main__":
    main()