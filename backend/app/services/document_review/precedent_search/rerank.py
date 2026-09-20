# FILE: backend/app/services/document_review/precedent_search/rerank.py
# PHOENIX PROTOCOL - PRECEDENT RERANK V2.2
# V2.2: User prompt shton "[tema: X]" para fragmentit (nga topic_label).

import re
import logging
from typing import List, Dict, Any

from .config import (
    PRECEDENT_RERANK_TOP_N,
    PRECEDENT_RERANK_INPUT_N,
    PRECEDENT_RERANK_MIN_CANDIDATES,
)

logger = logging.getLogger(__name__)


_RERANK_SYS_PROMPT = """Ti je gjyqtar i relevancës për precedentët e Gjykatave të Kosovës.

DETYRA: Vlerëso SA I PËRSHTATSHËM është secili precedent për lëndën e dhënë.

Kthe VETËM JSON të vlefshëm me këtë formë:
{"scores": [{"idx": 0, "score": 8.5}, {"idx": 1, "score": 3.0}, ...]}

SHKALLA E VLERESIMIT (0-10):
  9-10 = TEMË IDENTIKE: precedent mbi të njëjtën çështje (dhunë familjare,
         urdhër mbrojtjeje, kontakt me fëmijë, kujdestari, alimentacion).
  7-8  = TEMË E NGJASHME: parim juridik direkt i aplikueshëm.
  5-6  = LIDHJE INDIREKTE: procedurë, e drejta për gjykim të drejtë.
  3-4  = LIDHJE E DOBËT: temë e ndryshme por kontekst i njëjtë.
  0-2  = I PALIDHUR: temë komplet tjetër (ndarje pasurie, kompensim,
         kontrata civile, trafikim, vjedhje).

SHEMBUJ KONKRETË (për lëndë: dhunë familjare + urdhër mbrojtjeje + kontakt fëmijë):
  + Fragment "vendimi për besim të fëmijës" → 9.0
  + Fragment "ndryshimi i urdhrit kufizues" → 8.5
  + Fragment "alimentacioni për fëmijën e mitur" → 8.0
  + Fragment "kufizimi i vizitave familjare" → 7.5
  + Fragment "kontakt me fëmijën" → 8.5
  + Fragment "qasja në drejtësi" → 5.5
  + Fragment "ndarje pasurie familjare" → 2.0
  + Fragment "kompensim dëmi nga aksidenti" → 1.5
  + Fragment "kërkesë për mbrojtje të ligjshmërisë" → 3.0

RREGULLA:
- Mos shpik. Vlerëso VETËM fragmentin e dhënë.
- Vlerëso ÇDO index (0 deri në numrin e fundit).
- Mos shto fusha të tjera përveç idx dhe score.
- Ji i guximshëm: nëse fragmenti ka terma identikë me lëndën (fëmijë,
  kontakt, urdhër, dhunë, mbrojtje, familjare), jep 7-10.
"""


def rerank_deepseek(
    query_text: str,
    candidates: List[Dict[str, Any]],
    top_n: int = PRECEDENT_RERANK_TOP_N,
) -> List[Dict[str, Any]]:
    """Rerank candidates me DeepSeek-as-judge."""
    if not candidates:
        return []

    if len(candidates) < PRECEDENT_RERANK_MIN_CANDIDATES:
        logger.info(
            f"ℹ️ [RERANK] {len(candidates)} kandidate < "
            f"{PRECEDENT_RERANK_MIN_CANDIDATES} -> skip rerank"
        )
        return candidates[:top_n]

    try:
        from app.services.llm.llm_client import (
            _call_llm,
            clean_and_parse_json,
            DEEP_ANALYSIS_MODEL,
        )
    except Exception as e:
        logger.warning(f"⚠️ [RERANK] Import DeepSeek deshtoi: {e}")
        return candidates[:top_n]

    to_rerank = candidates[:PRECEDENT_RERANK_INPUT_N]

    # Ndërto user prompt
    user_lines = [f"LËNDA: {query_text[:500]}", "", "PRECEDENTËT:"]
    for i, c in enumerate(to_rerank):
        cn = c.get("case_number") or c.get("title") or "?"
        excerpt = (c.get("text") or "")[:400]
        excerpt = re.sub(r'\s+', ' ', excerpt).strip()

        user_lines.append(f"\n[{i}] {cn}")

        # V2.2: Shto topic_label nese ekziston
        topic = c.get("topic_label")
        if topic:
            user_lines.append(f"    [tema: {topic}]")

        user_lines.append(f"    {excerpt}")

    user_p = "\n".join(user_lines)

    try:
        raw = _call_llm(
            _RERANK_SYS_PROMPT,
            user_p,
            json_mode=True,
            model=DEEP_ANALYSIS_MODEL,
        )
        if not raw:
            logger.warning("⚠️ [RERANK] DeepSeek ktheu bosh")
            return candidates[:top_n]

        parsed = clean_and_parse_json(raw)
        scores_list = parsed.get("scores", [])

        if not scores_list:
            logger.warning(
                f"⚠️ [RERANK] JSON pa 'scores': {str(raw)[:200]}"
            )
            return candidates[:top_n]

        applied = 0
        for item in scores_list:
            idx = item.get("idx")
            score = item.get("score", 0.0)
            try:
                idx_int = int(idx)
                score_f = float(score)
            except (ValueError, TypeError):
                continue
            if 0 <= idx_int < len(to_rerank):
                to_rerank[idx_int]["rerank_score"] = score_f
                applied += 1

        to_rerank.sort(
            key=lambda x: (
                -x.get("rerank_score", -1.0),
                -x.get("rrf_score", 0.0),
            )
        )

        if to_rerank:
            scores = [c.get("rerank_score", 0) for c in to_rerank]
            logger.info(
                f"✅ [RERANK] DeepSeek vleresoi {applied}/{len(to_rerank)} kandidate | "
                f"max={max(scores):.1f} min={min(scores):.1f} "
                f"avg={sum(scores)/len(scores):.1f}"
            )
        return to_rerank[:top_n]

    except Exception as e:
        logger.error(f"❌ [RERANK] DeepSeek deshtoi: {e}")
        return candidates[:top_n]