# backend/scripts/test_section_order.py
"""V282.34: Verifikon që SECTION_ORDER përputhet me DOCUMENT_REVIEW_PROMPTS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_review.report_builder import SECTION_ORDER
from app.services.document_review.prompts import DOCUMENT_REVIEW_PROMPTS

prompt_keys = list(DOCUMENT_REVIEW_PROMPTS.keys())
order_keys = list(SECTION_ORDER)

print(f"\n📌 DOCUMENT_REVIEW_PROMPTS ({len(prompt_keys)} seksione):")
for k in prompt_keys:
    marker = "✅" if k in order_keys else "🔴 MUNGON në SECTION_ORDER"
    print(f"   {marker} {k}")

print(f"\n📌 SECTION_ORDER ({len(order_keys)} seksione):")
for k in order_keys:
    marker = "✅" if k in prompt_keys else "🔴 NUK ekziston në PROMPTS"
    print(f"   {marker} {k}")

# Kontroll: të njëjtat sete
missing = set(prompt_keys) - set(order_keys)
extra = set(order_keys) - set(prompt_keys)

assert not missing, f"🔴 Seksione që LLM gjeneron por nuk shfaqen: {missing}"
assert not extra, f"🔴 Seksione në SECTION_ORDER por pa prompt: {extra}"

# Kontroll: rendi identik
assert prompt_keys == order_keys, (
    f"🔴 Rendi nuk përputhet:\n"
    f"   prompts: {prompt_keys}\n"
    f"   order:   {order_keys}"
)

print(f"\n{'=' * 60}\n✅ SECTION_ORDER = DOCUMENT_REVIEW_PROMPTS ({len(order_keys)} seksione)\n{'=' * 60}")