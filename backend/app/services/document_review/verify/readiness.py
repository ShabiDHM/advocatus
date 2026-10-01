# FILE: backend/app/services/document_review/verify/readiness.py
# PHOENIX PROTOCOL - VERIFY READINESS V1.2
# V1.2: WORD BOUNDARY FIX —
#       - `_OLD_VERDICT_PATTERN` nuk kishte `\b`, pavarësisht se docstring-u
#         pretendonte kontroll me word boundaries. Rezultati: "Gatishmëria"
#         (shumë e zakonshme në raport gatishmërie) match-ohej nga "Gati"
#         dhe korruptohej në "~~Gati~~ **KËRKON PUNË** (KORRIGJUAR NGA
#         SISTEMI)shmëria". Tani `\b` para dhe pas alternativës.
# V1.1: BODY VERDICT REPLACEMENT.
# V1.0: Ekstraktuar nga draft_verifier.py V1.17.

import logging
import re
from typing import Any, Dict

from .config import (
    KRITIKE_MARKER_REGEX,
    CONCRETE_RECOMMENDATIONS_KEY,
    READINESS_LABELS_SQ,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PARSE
# ═══════════════════════════════════════════════════════════════════════════

def parse_readiness(sections: Dict[str, Dict[str, Any]]) -> str:
    sec = sections.get("readiness")
    if not sec or not sec.get("content"):
        return "UNKNOWN"

    content_upper = sec["content"].upper()

    if (
        re.search(r'\bINCOMPLETE\b', content_upper)
        or re.search(r'\bI PËRPLOTË\b', content_upper)
        or re.search(r'\bI PERPLOTE\b', content_upper)
    ):
        return "INCOMPLETE"

    if (
        re.search(r'\bNEEDS WORK\b', content_upper)
        or re.search(r'\bNEEDS_WORK\b', content_upper)
        or re.search(r'\bKËRKON PUNË\b', content_upper)
        or re.search(r'\bKERKON PUNE\b', content_upper)
    ):
        return "NEEDS WORK"

    if (
        re.search(r'\bREADY\b', content_upper)
        or re.search(r'\bGATI\b', content_upper)
    ):
        return "READY"

    return "UNKNOWN"


# ═══════════════════════════════════════════════════════════════════════════
# COUNT CRITICAL RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════

def count_critical_recommendations(
    sections: Dict[str, Dict[str, Any]],
) -> int:
    sec = sections.get(CONCRETE_RECOMMENDATIONS_KEY)
    if not sec:
        return 0
    content = sec.get("content") or ""
    if not content:
        return 0
    return len(KRITIKE_MARKER_REGEX.findall(content))


# ═══════════════════════════════════════════════════════════════════════════
# V1.1: BODY VERDICT REPLACEMENT
# V1.2: `\b` para/pas alternativës — parandalon match brenda "Gatishmëria".
# ═══════════════════════════════════════════════════════════════════════════

_OLD_VERDICT_PATTERN = re.compile(
    r'(\*{0,2})\b(GATI|Gati|READY|Ready)\b(\*{0,2})',
    re.UNICODE,
)


def _replace_body_verdict(content: str, new_label: str) -> str:
    """
    V1.2: Zëvendëson verdiktin e vjetër (GATI/READY) në body me verdiktin e ri.

    `\\b` para/pas alternativës garanton që nuk match-ohet "Gati" brenda
    "Gatishmëria", "Gatishmërinë", "Gati-shmëria", etj.

    Count=1: zëvendëso VETËM ndodhjen e parë (verdikti kryesor).
    """
    def _sub(match: re.Match) -> str:
        old = match.group(2)
        return f'~~{old}~~ **{new_label}** (KORRIGJUAR NGA SISTEMI)'

    return _OLD_VERDICT_PATTERN.sub(_sub, content, count=1)


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL BANNER BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _prepend_readiness_override_banner(
    sec: Dict[str, Any],
    new_label: str,
    reason_block: str,
) -> None:
    # ── 1. Zëvendësim i verdiktit në body ──
    if sec.get("content"):
        original_content = sec["content"]
        replaced_content = _replace_body_verdict(original_content, new_label)

        if replaced_content != original_content:
            logger.info(
                f"🔄 [VERIFY V1.2] Body verdict u zëvendësua: "
                f"GATI/READY → {new_label}"
            )
        else:
            logger.info(
                f"ℹ️ [VERIFY V1.2] Body verdict nuk u gjet për zëvendësim "
                f"(ndoshta LLM shkroi formë tjetër). Banner prepend-ohet."
            )

        sec["content"] = replaced_content

    # ── 2. Sinkronizim titulli ──
    original_title = sec.get("title") or "6. GATISHMËRIA"
    if "KËRKON PUNË" not in original_title:
        sec["title"] = f"{original_title} — ⚠️ {new_label}"

    # ── 3. Prepend banner ──
    if sec.get("content"):
        override_block = (
            f"> 🛑 **VËREJTJE E SISTEMIT — GATISHMËRIA U KORRIGJUA: {new_label}**\n"
            f">\n"
            f"{reason_block}"
            f"> **Vlerësimi përfundimtar dhe i vlefshëm: {new_label}.**\n"
            f"\n---\n\n"
        )
        sec["content"] = override_block + sec["content"]
    else:
        logger.warning(
            "⚠️ [VERIFY V1.2] Seksioni 'readiness' ka content bosh."
        )


# ═══════════════════════════════════════════════════════════════════════════
# OVERRIDE — HALLUCINATION
# ═══════════════════════════════════════════════════════════════════════════

def maybe_override_readiness(
    readiness: str,
    hallucination_report: Dict[str, Any],
    sections: Dict[str, Dict[str, Any]],
) -> str:
    if readiness != "READY":
        return readiness

    sev = (hallucination_report or {}).get("severity_totals", {}) or {}
    high = int(sev.get("high", 0) or 0)
    medium = int(sev.get("medium", 0) or 0)

    if high == 0 and medium == 0:
        return readiness

    reasons = []
    if high > 0:
        reasons.append(f"{high} dyshime me **rrezik të lartë**")
    if medium > 0:
        reasons.append(f"{medium} dyshime me **rrezik të mesëm**")
    reason_text = " dhe ".join(reasons)

    new_readiness = "NEEDS WORK"
    new_label = READINESS_LABELS_SQ.get(new_readiness, new_readiness)

    logger.info(
        f"🔄 [VERIFY V1.2] Readiness override: READY → NEEDS WORK "
        f"(arsyeja: {reason_text})"
    )

    sec = sections.get("readiness")
    if not sec:
        logger.warning(
            "⚠️ [VERIFY V1.2] Seksioni 'readiness' mungon — "
            "override u aplikua vetëm në header."
        )
        return new_readiness

    reason_block = (
        f"> ⚠️ **MOS e lexoni vlerësimin \"GATI\" më poshtë si "
        f"vlerësim aktual.** Teksti më poshtë u gjenerua nga LLM-ja "
        f"para kontrollit anti-hallucination. Sistemi identifikoi "
        f"{reason_text} dhe e ka rishkallëzuar gatishmërinë në "
        f"**{new_label}**.\n"
        f">\n"
        f"> Verifikoni manualisht seksionet e shënuara më sipër "
        f"përpara dorëzimit.\n"
        f">\n"
    )
    _prepend_readiness_override_banner(sec, new_label, reason_block)

    return new_readiness


# ═══════════════════════════════════════════════════════════════════════════
# OVERRIDE — CRITICAL RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════

def maybe_override_readiness_for_critical(
    readiness: str,
    sections: Dict[str, Dict[str, Any]],
) -> str:
    if readiness != "READY":
        return readiness

    critical_count = count_critical_recommendations(sections)
    if critical_count == 0:
        return readiness

    new_readiness = "NEEDS WORK"
    new_label = READINESS_LABELS_SQ.get(new_readiness, new_readiness)

    logger.info(
        f"🔄 [VERIFY V1.2] Readiness override (KRITIKE): READY → NEEDS WORK "
        f"(arsyeja: {critical_count} rekomandime KRITIKE [#K] në Section 5)"
    )

    sec = sections.get("readiness")
    if not sec:
        logger.warning(
            "⚠️ [VERIFY V1.2] Seksioni 'readiness' mungon — "
            "override u aplikua vetëm në header."
        )
        return new_readiness

    reason_block = (
        f"> ⚠️ **MOS e lexoni vlerësimin \"GATI\" më poshtë si "
        f"vlerësim aktual.** Teksti më poshtë u gjenerua nga LLM-ja "
        f"para kontrollit të konsistencës. Sistemi identifikoi "
        f"**{critical_count} rekomandime KRITIKE** ([#K] në Seksionin 5 "
        f"\"Rekomandime Konkrete\") që duhet të adresohen para dorëzimit, "
        f"dhe e ka rishkallëzuar gatishmërinë në **{new_label}**.\n"
        f">\n"
        f"> Adresoni të gjitha rekomandimet KRITIKE (K1, K2, ...) "
        f"para dorëzimit.\n"
        f">\n"
    )
    _prepend_readiness_override_banner(sec, new_label, reason_block)

    return new_readiness