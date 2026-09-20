# FILE: backend/app/services/document_review/precedent_search/rerank.py
# PHOENIX PROTOCOL - PRECEDENT RERANK V2.3
# V2.3: Shtuar Cohere Reranker + dispatcher:
#       - rerank_deepseek(): i paprekur nga V2.2
#       - rerank_cohere(): Cohere Rerank API (multilingual v3.0)
#       - rerank(): dispatcher sipas PRECEDENT_RERANKER
#       - Cohere score 0-1 skalohet ne 0-10 per konsistence me DeepSeek
# V2.2: User prompt shton "[tema: X]" para fragmentit.
# V2.1: Prompt me shembuj + kalibrim.

import re
import logging
from typing import List, Dict, Any

from .config import (
    PRECEDENT_RERANK_TOP_N,
    PRECEDENT_RERANK_INPUT_N,
    PRECEDENT_RERANK_MIN_CANDIDATES,
    PRECEDENT_RERANKER,
    COHERE_API_KEY,
    COHERE_RERANK_MODEL,
    COHERE_RERANK_TIMEOUT,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# PROMPT PER DEEPSEEK
# ===========================================================================

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


# ===========================================================================
# DEEPSEEK RERANK
# ===========================================================================

def rerank_deepseek(
    query_text: str,
    candidates: List[Dict[str, Any]],
    top_n: int = PRECEDENT_RERANK_TOP_N,
) -> List[Dict[str, Any]]:
    """
    Rerank me DeepSeek-as-judge. Kthen rerank_score 0-10.
    """
    if not candidates:
        return []

    if len(candidates) < PRECEDENT_RERANK_MIN_CANDIDATES:
        logger.info(
            f"ℹ️ [RERANK-DS] {len(candidates)} kandidate < "
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
        logger.warning(f"⚠️ [RERANK-DS] Import deshtoi: {e}")
        return candidates[:top_n]

    to_rerank = candidates[:PRECEDENT_RERANK_INPUT_N]

    user_lines = [f"LËNDA: {query_text[:500]}", "", "PRECEDENTËT:"]
    for i, c in enumerate(to_rerank):
        cn = c.get("case_number") or c.get("title") or "?"
        excerpt = (c.get("text") or "")[:400]
        excerpt = re.sub(r'\s+', ' ', excerpt).strip()

        user_lines.append(f"\n[{i}] {cn}")

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
            logger.warning("⚠️ [RERANK-DS] DeepSeek ktheu bosh")
            return candidates[:top_n]

        parsed = clean_and_parse_json(raw)
        scores_list = parsed.get("scores", [])

        if not scores_list:
            logger.warning(
                f"⚠️ [RERANK-DS] JSON pa 'scores': {str(raw)[:200]}"
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
                f"✅ [RERANK-DS] DeepSeek vleresoi {applied}/{len(to_rerank)} kandidate | "
                f"max={max(scores):.1f} min={min(scores):.1f} "
                f"avg={sum(scores)/len(scores):.1f}"
            )
        return to_rerank[:top_n]

    except Exception as e:
        logger.error(f"❌ [RERANK-DS] Deshtoi: {e}")
        return candidates[:top_n]


# ===========================================================================
# COHERE RERANK (V2.3)
# ===========================================================================

def _get_cohere_client():
    """Kthen Cohere client (ose None nese mungon key / paketa)."""
    if not COHERE_API_KEY:
        logger.warning("⚠️ [RERANK-COHERE] COHERE_API_KEY mungon ne env")
        return None

    try:
        import cohere
    except ImportError:
        logger.error(
            "❌ [RERANK-COHERE] Paketa 'cohere' nuk eshte instaluar. "
            "Ekzekuto: pip install cohere"
        )
        return None

    try:
        return cohere.ClientV2(
            api_key=COHERE_API_KEY,
            timeout=COHERE_RERANK_TIMEOUT,
        )
    except Exception as e:
        logger.error(f"❌ [RERANK-COHERE] Client init deshtoi: {e}")
        return None


def rerank_cohere(
    query_text: str,
    candidates: List[Dict[str, Any]],
    top_n: int = PRECEDENT_RERANK_TOP_N,
) -> List[Dict[str, Any]]:
    """
    V2.3: Rerank me Cohere Rerank API (multilingual v3.0).

    Cohere kthen relevance_score 0-1 per cdo dokument. Ne e ruajme si
    rerank_score (0-1) dhe e skalojme ne 0-10 per konsistence me DeepSeek.
    """
    if not candidates:
        return []

    if len(candidates) < PRECEDENT_RERANK_MIN_CANDIDATES:
        logger.info(
            f"ℹ️ [RERANK-COHERE] {len(candidates)} kandidate < "
            f"{PRECEDENT_RERANK_MIN_CANDIDATES} -> skip rerank"
        )
        return candidates[:top_n]

    client = _get_cohere_client()
    if not client:
        logger.warning("⚠️ [RERANK-COHERE] Duke kaluar ne fallback (RRF)")
        return candidates[:top_n]

    to_rerank = candidates[:PRECEDENT_RERANK_INPUT_N]

    # Nderto dokumentet per Cohere (case_number + excerpt + tema)
    documents = []
    for c in to_rerank:
        cn = c.get("case_number") or c.get("title") or "?"
        excerpt = (c.get("text") or "")[:500]
        excerpt = re.sub(r'\s+', ' ', excerpt).strip()
        topic = c.get("topic_label") or ""

        doc_text = f"{cn}\n"
        if topic:
            doc_text += f"[tema: {topic}]\n"
        doc_text += excerpt

        documents.append(doc_text)

    try:
        response = client.rerank(
            model=COHERE_RERANK_MODEL,
            query=query_text[:2000],
            documents=documents,
            top_n=min(top_n * 2, len(documents)),
        )

        # Cohere kthen .results = [{index, relevance_score}, ...]
        applied = 0
        for result in response.results:
            idx = result.index
            score = result.relevance_score  # 0-1

            if 0 <= idx < len(to_rerank):
                # Ruaj score origjinal 0-1
                to_rerank[idx]["cohere_score"] = float(score)
                # Skalo ne 0-10 per konsistence me DeepSeek
                to_rerank[idx]["rerank_score"] = float(score) * 10.0
                applied += 1

        to_rerank.sort(
            key=lambda x: (
                -x.get("rerank_score", -1.0),
                -x.get("rrf_score", 0.0),
            )
        )

        if to_rerank:
            scores = [c.get("cohere_score", 0) for c in to_rerank]
            logger.info(
                f"✅ [RERANK-COHERE] Cohere vleresoi {applied}/{len(to_rerank)} kandidate | "
                f"max={max(scores):.4f} min={min(scores):.4f} "
                f"avg={sum(scores)/len(scores):.4f}"
            )
        return to_rerank[:top_n]

    except Exception as e:
        logger.error(f"❌ [RERANK-COHERE] Deshtoi: {e}")
        return candidates[:top_n]


# ===========================================================================
# DISPATCHER (V2.3)
# ===========================================================================

def rerank(
    query_text: str,
    candidates: List[Dict[str, Any]],
    top_n: int = PRECEDENT_RERANK_TOP_N,
) -> List[Dict[str, Any]]:
    """
    V2.3: Dispatcher qe zgjedh reranker sipas PRECEDENT_RERANKER.

    Vlera te lejuara:
      - "deepseek" (default): DeepSeek-as-judge (0-10)
      - "cohere": Cohere Rerank API (0-1 -> skalohet ne 0-10)
      - "none": nuk ben rerank, kthen candidates[:top_n]
    """
    if PRECEDENT_RERANKER == "cohere":
        return rerank_cohere(query_text, candidates, top_n=top_n)
    elif PRECEDENT_RERANKER == "deepseek":
        return rerank_deepseek(query_text, candidates, top_n=top_n)
    elif PRECEDENT_RERANKER == "none":
        logger.info("ℹ️ [RERANK] Reranker i çaktivizuar (none) - kthim candidates")
        return candidates[:top_n]
    else:
        logger.warning(
            f"⚠️ [RERANK] Vlerë e panjohur PRECEDENT_RERANKER='{PRECEDENT_RERANKER}' "
            f"- duke perdorur 'deepseek'"
        )
        return rerank_deepseek(query_text, candidates, top_n=top_n)