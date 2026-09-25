# FILE: backend/app/services/document_review/rewrite_prompts.py
# PHOENIX PROTOCOL - DOCUMENT REWRITE PROMPTS V2.1
# V2.1: NO CONTEXT — hequr PREV_TAIL/NEXT_HEAD nga chunk prompt (shkaktonte duplikim).
#       LLM tani rishkruan chunk-un në izolim total.
# V2.0: FAZA 2 — CHUNKED REWRITE.

from typing import Dict, Any

from .verify_prompts import VERIFY_DOC_TYPES, DOC_TYPE_CHECKLISTS


# ═══════════════════════════════════════════════════════════════════════════
# SISTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════

REWRITE_SYSTEM_PROMPT = (
    "Ti je partner i lartë në një zyrë ligjore prestigjioze në Prishtinë. "
    "Detyra jote është të rishkruash PJESË të një dokumenti ligjor duke "
    "përmirësuar strukturën, argumentimin dhe citimet, por PA HEQUR ASNJË FAKT. "
    "NUK PËRMBLEDH. NUK KONDENSOJ. NUK SHKURTOJ. "
    "Rishkruaj të plotën e asaj pjese që të jepet. "
    "NUK ndryshon faktet, emrat, datat, shumat, adresat, numrat personalë. "
    "Kthe vetëm tekstin e rishkruar në markdown, pa komente shtesë."
)


# ═══════════════════════════════════════════════════════════════════════════
# CHUNK REWRITE PROMPT (V2.1: pa kontekst fqinjësh)
# ═══════════════════════════════════════════════════════════════════════════

CHUNK_REWRITE_PROMPT_TEMPLATE = (
    "Detyra: Rishkruaj PJESËN {{CHUNK_INDEX}}/{{TOTAL_CHUNKS}} të një "
    "dokumenti ligjor ({{DOC_TYPE}}).\n"
    "\n"
    "🛑 RREGULLI MË I RËNDËSISHËM: MOS PËRMBLEDH — RISHKRUAJ TË PLOTË\n"
    "\n"
    "RISHKRUAJ DO TË THOTË:\n"
    "  ✅ Mbaj 100% të fakteve, ngjarjeve, personave, datave, shumave TË KËSAJ PJESE.\n"
    "  ✅ Mbaj të gjitha seksionet e kësaj pjese.\n"
    "  ✅ Mbaj të gjitha provat, dëshmitë, referencat e kësaj pjese.\n"
    "  ✅ Përmirëso strukturën.\n"
    "  ✅ Shto citimet ligjore që rekomandon raporti i verifikimit.\n"
    "  ✅ Forco argumentimin juridik.\n"
    "\n"
    "RISHKRUAJ NUK DO TË THOTË:\n"
    "  ❌ NUK heq detaje.\n"
    "  ❌ NUK përmbledh.\n"
    "  ❌ NUK shkruaj 'etj.' ose '...'.\n"
    "  ❌ NUK shkruaj 'vazhdon në pjesën tjetër'.\n"
    "  ❌ NUK shto përmbledhje të pjesëve të tjera.\n"
    "  ❌ NUK përsërit seksione që nuk janë në këtë pjesë.\n"
    "\n"
    "🛑 RREGULL ABSOLUT PËR KUFIJTË (V2.1):\n"
    "  - Rishkruaj VETËM përmbajtjen e kësaj pjese.\n"
    "  - NUK shto asgjë nga jashtë kësaj pjese.\n"
    "  - NUK përfshij seksione që nuk gjenden në tekstin e dhënë.\n"
    "  - NUK përsërit titujt e seksioneve që shfaqen më shumë se një herë.\n"
    "  - Nëse teksti i dhënë përmban një seksion të pjesshëm, "
    "rishkruaje vetëm atë pjesë — mos plotëso me pjesë të tjera.\n"
    "\n"
    "KONTROLLI I GJATËSISË:\n"
    "  📏 Kjo pjesë origjinale: {{CHUNK_LENGTH}} karaktere.\n"
    "  📏 Pjesa e RI duhet: TË PAKTËN {{CHUNK_LENGTH}} karaktere ose MË SHUMË.\n"
    "\n"
    "UDHËZIME SPECIFIKE:\n"
    "  - Nëse ky është pjesa e PARË: fillo me titullin e gjykatës "
    "(kapitale) + titullin e dokumentit (PADI CIVILE / KALLËZIM PENAL / etj.).\n"
    "  - Nëse ky është pjesa e FUNDIT: mbaro me vendin, datën, nënshkrimin "
    "(siç janë në pjesën origjinale).\n"
    "  - Nëse ky është pjesa e MESME: vazhdo direkt me përmbajtjen — "
    "pa titull kryesor, pa nënshkrim.\n"
    "  - NUK shpik fakte ose referenca që nuk shfaqen në pjesën origjinale.\n"
    "\n"
    "═══════════════════════════════════════════════════════════════════════════\n"
    "KJO PJESË ORIGJINALE ({{CHUNK_LENGTH}} karaktere — RISHKRUAJ TË PLOTË):\n"
    "═══════════════════════════════════════════════════════════════════════════\n"
    "\n"
    "{{CHUNK_CONTENT}}\n"
    "\n"
    "═══════════════════════════════════════════════════════════════════════════\n"
    "REKOMANDIMET E VERIFIKIMIT (zbatoji kur të përshtaten):\n"
    "═══════════════════════════════════════════════════════════════════════════\n"
    "\n"
    "{{VERIFICATION_FINDINGS}}\n"
    "\n"
    "═══════════════════════════════════════════════════════════════════════════\n"
    "\n"
    "Rishkruaj PJESËN E PLOTË {{CHUNK_INDEX}}/{{TOTAL_CHUNKS}}. "
    "Kthe VETËM tekstin e rishkruar në markdown, pa komente rreth tij."
)


# ═══════════════════════════════════════════════════════════════════════════
# BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_CHUNK_SIZE = 7000
DEFAULT_MAX_DRAFT_CHARS = 300000


def build_chunk_rewrite_prompt(
    chunk_content: str,
    chunk_index: int,
    total_chunks: int,
    doc_type: str,
    verification_findings: str,
) -> str:
    """
    Ndërton promptin për një pjesë (chunk) të dokumentit.
    V2.1: NUK ka kontekst nga fqinjët — izolim total për të shmangur duplikim.
    """
    doc_type_label = VERIFY_DOC_TYPES.get(doc_type, doc_type)

    prompt = CHUNK_REWRITE_PROMPT_TEMPLATE
    prompt = prompt.replace("{{CHUNK_INDEX}}", str(chunk_index))
    prompt = prompt.replace("{{TOTAL_CHUNKS}}", str(total_chunks))
    prompt = prompt.replace("{{DOC_TYPE}}", doc_type_label)
    prompt = prompt.replace("{{CHUNK_LENGTH}}", str(len(chunk_content)))
    prompt = prompt.replace("{{CHUNK_CONTENT}}", chunk_content)
    prompt = prompt.replace("{{VERIFICATION_FINDINGS}}", verification_findings)

    return prompt


def get_rewrite_doc_types() -> Dict[str, str]:
    return dict(VERIFY_DOC_TYPES)