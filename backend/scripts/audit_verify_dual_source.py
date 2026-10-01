# FILE: backend/scripts/audit_verify_dual_source.py
"""
V282.34: Zbulon divergjenca mes modulit legacy verify_prompts.py dhe
moduleve modulare verify/prompt_*.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Moduli legacy (monolit)
import app.services.document_review.verify_prompts as legacy

# Modulet modulare
from app.services.document_review.verify.prompt_constants import (
    VERIFY_SECTION_KEYS as MOD_KEYS,
    MIN_PRECEDENT_SIMILARITY as MOD_MIN_SIM,
)
from app.services.document_review.verify.prompt_doc_types import (
    VERIFY_DOC_TYPES as MOD_DOC_TYPES,
)
from app.services.document_review.verify.prompt_sections import (
    VERIFY_SECTION_PROMPTS as MOD_SECTION_PROMPTS,
)

fails = 0

# ─── 1. VERIFY_SECTION_KEYS ───
legacy_keys = tuple(getattr(legacy, "VERIFY_SECTION_KEYS", ()))
mod_keys = tuple(MOD_KEYS)
print(f"\n▶ VERIFY_SECTION_KEYS")
print(f"   legacy: {legacy_keys}")
print(f"   modular:{mod_keys}")
if legacy_keys == mod_keys:
    print(f"   ✅ Identikë")
else:
    print(f"   🔴 DIVERGJENCA!")
    fails += 1

# ─── 2. MIN_PRECEDENT_SIMILARITY ───
legacy_min = getattr(legacy, "MIN_PRECEDENT_SIMILARITY", None)
print(f"\n▶ MIN_PRECEDENT_SIMILARITY")
print(f"   legacy: {legacy_min}")
print(f"   modular:{MOD_MIN_SIM}")
if legacy_min == MOD_MIN_SIM:
    print(f"   ✅ Identikë")
else:
    print(f"   🔴 DIVERGJENCA!")
    fails += 1

# ─── 3. VERIFY_DOC_TYPES ───
legacy_dt = getattr(legacy, "VERIFY_DOC_TYPES", {})
print(f"\n▶ VERIFY_DOC_TYPES")
print(f"   legacy: {len(legacy_dt)} tipe")
print(f"   modular:{len(MOD_DOC_TYPES)} tipe")
if legacy_dt == MOD_DOC_TYPES:
    print(f"   ✅ Identikë")
else:
    print(f"   🔴 DIVERGJENCA!")
    for k in set(legacy_dt) | set(MOD_DOC_TYPES):
        lv = legacy_dt.get(k)
        mv = MOD_DOC_TYPES.get(k)
        if lv != mv:
            print(f"      {k}: legacy={lv!r}, modular={mv!r}")
    fails += 1

# ─── 4. VERIFY_SECTION_PROMPTS — vetëm titles ───
legacy_sp = getattr(legacy, "VERIFY_SECTION_PROMPTS", {})
print(f"\n▶ VERIFY_SECTION_PROMPTS")
print(f"   legacy: {len(legacy_sp)} sections")
print(f"   modular:{len(MOD_SECTION_PROMPTS)} sections")

if set(legacy_sp.keys()) != set(MOD_SECTION_PROMPTS.keys()):
    print(f"   🔴 Key set i ndryshëm!")
    print(f"      legacy: {sorted(legacy_sp.keys())}")
    print(f"      modular:{sorted(MOD_SECTION_PROMPTS.keys())}")
    fails += 1
else:
    for k in sorted(MOD_SECTION_PROMPTS.keys()):
        l_title = legacy_sp.get(k, {}).get("title")
        m_title = MOD_SECTION_PROMPTS[k].get("title")
        l_max = legacy_sp.get(k, {}).get("max_tokens")
        m_max = MOD_SECTION_PROMPTS[k].get("max_tokens")
        l_needs = tuple(legacy_sp.get(k, {}).get("needs", []))
        m_needs = tuple(MOD_SECTION_PROMPTS[k].get("needs", []))
        l_subs = tuple(legacy_sp.get(k, {}).get("sub_prompts", []) or [])
        m_subs = tuple(MOD_SECTION_PROMPTS[k].get("sub_prompts", []) or [])

        if (l_title, l_max, l_needs, l_subs) != (m_title, m_max, m_needs, m_subs):
            print(f"   🔴 {k} ndryshon:")
            if l_title != m_title:
                print(f"      title: legacy={l_title!r}, modular={m_title!r}")
            if l_max != m_max:
                print(f"      max_tokens: legacy={l_max}, modular={m_max}")
            if l_needs != m_needs:
                print(f"      needs: legacy={l_needs}, modular={m_needs}")
            if l_subs != m_subs:
                print(f"      sub_prompts: legacy={l_subs}, modular={m_subs}")
            fails += 1

if fails == 0:
    print(f"\n{'=' * 60}\n✅ Zero divergjenca — konstantet janë sinkron.\n{'=' * 60}")
else:
    print(f"\n{'=' * 60}\n🔴 {fails} divergjenca u gjetën.\n{'=' * 60}")

sys.exit(1 if fails else 0)