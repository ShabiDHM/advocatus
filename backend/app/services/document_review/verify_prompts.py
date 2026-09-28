# FILE: backend/app/services/document_review/verify_prompts.py
# PHOENIX PROTOCOL - VERIFY PROMPTS SHIM V2.0
# V2.0: SHIM — Logjika u zhvendos në paketën `verify/`:
#       - verify.prompt_rules       (DEDUP_RULE, PRECEDENT_SOURCE_RULE, CROSS_SECTION_*)
#       - verify.prompt_constants   (VERIFY_SECTION_KEYS + konstantet)
#       - verify.prompt_doc_types   (VERIFY_DOC_TYPES)
#       - verify.prompt_checklists  (DOC_TYPE_CHECKLISTS)
#       - verify.prompt_sections    (VERIFY_SECTION_PROMPTS + sub-prompts)
#       - verify.context_builders   (build_verify_context)
#       Ky file ruan API-n publike për backward-compatibility.

from .verify.prompt_constants import (
    VERIFY_SECTION_KEYS,
    DEFAULT_VERIFY_MAX_TOKENS,
    DEFAULT_MAX_DRAFT_CHARS,
    DRAFT_HEAD_CHARS,
    DRAFT_TAIL_CHARS,
    MIN_PRECEDENT_SIMILARITY,
    PRECEDENT_LLM_EXCERPT_CHARS,
)
from .verify.prompt_rules import (
    DEDUP_RULE,
    PRECEDENT_SOURCE_RULE,
    CROSS_SECTION_CONSISTENCY_RULE,
)
from .verify.prompt_doc_types import VERIFY_DOC_TYPES
from .verify.prompt_checklists import DOC_TYPE_CHECKLISTS
from .verify.prompt_sections import VERIFY_SECTION_PROMPTS
from .verify.context_builders import (
    build_verify_context,
    get_verify_section_keys,
    get_verify_doc_types,
    get_checklist,
)


__all__ = [
    "VERIFY_SECTION_KEYS",
    "DEFAULT_VERIFY_MAX_TOKENS",
    "DEFAULT_MAX_DRAFT_CHARS",
    "DRAFT_HEAD_CHARS",
    "DRAFT_TAIL_CHARS",
    "MIN_PRECEDENT_SIMILARITY",
    "PRECEDENT_LLM_EXCERPT_CHARS",
    "DEDUP_RULE",
    "PRECEDENT_SOURCE_RULE",
    "CROSS_SECTION_CONSISTENCY_RULE",
    "VERIFY_DOC_TYPES",
    "DOC_TYPE_CHECKLISTS",
    "VERIFY_SECTION_PROMPTS",
    "build_verify_context",
    "get_verify_section_keys",
    "get_verify_doc_types",
    "get_checklist",
]


def _cli_test():
    print("=" * 70)
    print("VERIFY PROMPTS V2.0 (SHIM) — DIAGNOSTIKË")
    print("=" * 70)

    print(f"\nLlojet e dokumenteve ({len(VERIFY_DOC_TYPES)}):")
    for k, v in VERIFY_DOC_TYPES.items():
        n = len(DOC_TYPE_CHECKLISTS.get(k, {}).get("required_parts", []))
        print(f"  - {k:22s} → {v} ({n} pika)")

    print(f"\nSeksionet ({len(VERIFY_SECTION_KEYS)}):")
    for k in VERIFY_SECTION_KEYS:
        cfg = VERIFY_SECTION_PROMPTS[k]
        needs = cfg.get("needs", [])
        subs = cfg.get("sub_prompts")
        sub_str = f" sub_prompts={subs}" if subs else ""
        print(f"  - {k:25s} max_tokens={cfg.get('max_tokens')} needs={needs}{sub_str}")

    print(f"\nKonstante:")
    print(f"  - MIN_PRECEDENT_SIMILARITY: {MIN_PRECEDENT_SIMILARITY}")
    print(f"  - PRECEDENT_LLM_EXCERPT_CHARS: {PRECEDENT_LLM_EXCERPT_CHARS}")
    print(f"  - weaknesses_risks split: {'AKTIV' if VERIFY_SECTION_PROMPTS['weaknesses_risks'].get('sub_prompts') else 'JOAKTIV'}")


if __name__ == "__main__":
    _cli_test()