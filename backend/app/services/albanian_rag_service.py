# FILE: backend/app/services/albanian_rag_service.py
# PROTOKOLLI PHOENIX - SHËRBI MI DOKTRINAR RAG V282.37
# V282.37: ASYNC + PARALLEL PRE-VERIFY —
#          - `_verify_single_article` (sync) thirrej direkt në loop async →
#            bllokonte event loop për çdo nen (SSE heartbeats, chat-e tjera,
#            detyra background ngrinin). Tani: asyncio.to_thread + asyncio.gather.
#          - Verifikimi i neneve tani PARALEL (më parë sekuencial). Për 5 nene
#            ~5x më i shpejtë.
#          - Wrap në try/except → në defekt upstream, `{}` trajtohet si missing
#            (nuk hedh exception, nuk ndal chat-in).
# V282.36: KEYERROR GUARD —
#          - `verified_articles` / `ambiguous_articles` / `missing_articles`
#            përdornin `v["exists"]` direkt. Nëse `_verify_single_article`
#            kthen dict pa 'exists' (version mismatch, defekt upstream,
#            exception e brendshme), chat hedh KeyError para se të arrijë
#            LLM. Tani përdoret helper `_is_verified(v)` me `.get()`.
# V282.35: ASYNC RAG INTEGRATION (DRAFTING + STATUTORY).
# V282.34: ROBUSTNESS (backspace, precedent regex, async DB, dead code).
# V282.33: SMART GLOBAL N_RESULTS.
# V282.32: GLOBAL FETCH KUR user_wants_global=True.
# V282.31: TIMING + CASE CONTEXT (A+B+C).
# V282.30: DYNAMIC RULE 19 REMINDER.
# V282.29: CITED PRECEDENTS VERIFICATION.
# V282.28: FORCE REMINDER FINAL.
# V282.27: REVERT DYNAMIC CHUNKS DEFAULT.

import logging
import re
import time
import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from app.services.rag.intent_detector import IntentDetector, QueryDepthDetector
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.response_generator import ResponseGenerator
from app.services.rag.chat_query_extractor import extract_legal_query
from app.services.rag.cross_doc_comparator import (
    user_wants_comparison,
    build_comparison_table,
)
from app.services.rag.timeline_builder import (
    user_wants_timeline,
    extract_events,
    build_timeline,
)

from app.services.rag.instructions import NATURAL_COUNSEL_INSTRUCTION
from app.services.rag.cache import (
    _get_cached_case_docs,
    _set_cached_case_docs,
    _chunks_cache_key,
    _get_cached_chunks,
    _set_cached_chunks,
    CACHE_TTL_CASE_DOCS,
    CACHE_TTL_CASE_CHUNKS,
)
from app.services.rag.text_utils import (
    GLOBAL_SEARCH_TRIGGERS,
    _user_wants_global_search,
    _detect_relevant_documents,
)
from app.services.rag.block_builders import (
    _format_alternative_laws,
    _build_contradictions_block,
    _build_suspects_block,
    _build_cited_precedents_block,
)
from app.services.rag.official_cleaner import (
    _format_direct_answer,
)
from app.services.rag.intent_helpers import (
    is_valid_legal_report,
    detect_requested_pillar,
)

from app.services.document_review.mongo_verifier import _verify_single_article
from app.services.document_review.citation_extractor import build_citation_profile
from app.services.document_review.fact_extractor import build_fact_profile
from app.services.pillars.base_pillar_service import BasePillarService

from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.statutory_verification_service import StatutoryVerificationService

from app.services.llm.llm_client import FAST_SEARCH_MODEL

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTE
# ═══════════════════════════════════════════════════════════════════════════

MAX_DOCS_FOR_CONTRADICTION_SCAN = 30

_GLOBAL_N_DEFAULT = 15
_GLOBAL_N_PRECEDENT_SPECIFIC = 5


# ═══════════════════════════════════════════════════════════════════════════
# V282.33: DETEKTIM I PYETJEVE ME PRECEDENT SPECIFIK
# ═══════════════════════════════════════════════════════════════════════════

_PRECEDENT_QUERY_RE = re.compile(
    r'\b(?:PML|REV|KMLP|PP\.II|PP\.I|CA|AC|P|C)'
    r'[\s\.]+'
    r'(?:nr\.?|Nr\.?|NR\.?)?'
    r'[\s\.]*'
    r'\d+\s*[/\.]\s*\d+',
    re.IGNORECASE,
)


def _detect_specific_precedent_query(query: str) -> bool:
    """V282.33/34: Kontrollon nëse query përmban numër specifik precedenti."""
    if not query:
        return False
    return bool(_PRECEDENT_QUERY_RE.search(query))


# ═══════════════════════════════════════════════════════════════════════════
# V282.30: DYNAMIC RULE 19 REMINDERS
# ═══════════════════════════════════════════════════════════════════════════

_RULE_19_REMINDER_VERIFIED = """

═══════════════════════════════════════════════════════════════════════════
🛑 REMINDER I DETYRUESHËM PARA PËRGJIGJES (Rule 19)
═══════════════════════════════════════════════════════════════════════════
Të gjithë precedentët e cituar EKZISTOJNË në bazën e Gjykatës Supreme.

Forma e saktë e citimit:
  ✅ "Sipas bazës së Gjykatës Supreme: Në vendimin PML.Nr.X/YYYY, ..."
  ❌ "Sipas dokumenteve të fashikullit: ..." (E GABUAR për këta precedentë)
  ❌ "Gjykata Supreme thotë... pa burim" (E GABUAR)
"""

_RULE_19_REMINDER_UNVERIFIED = """

═══════════════════════════════════════════════════════════════════════════
🛑 REMINDER I DETYRUESHËM PARA PËRGJIGJES (Rule 19)
═══════════════════════════════════════════════════════════════════════════
Këta precedentë NUK ekzistojnë në bazën e Gjykatës Supreme.
Ata janë cituar vetëm në dokumentet e fashikullit.

Forma e saktë e citimit:
  ✅ "Sipas [emri_i_dokumentit]: Në vendimin X, Gjykata Supreme ..."
  ❌ "Në vendimin X, Gjykata Supreme sanksionon..." (pa burim — E GABUAR)
  ❌ "Sipas bazës së Gjykatës Supreme: ..." (E GABUAR — nuk janë verifikuar)
"""

_RULE_19_REMINDER_MIXED = """

═══════════════════════════════════════════════════════════════════════════
🛑 REMINDER I DETYRUESHËM PARA PËRGJIGJES (Rule 19)
═══════════════════════════════════════════════════════════════════════════
Ky fashikull përmban DY kategori precedentësh:

1. ✅ TË VERIFIKUAR (nga baza e Gjykatës Supreme):
   → Forma: "Sipas bazës së Gjykatës Supreme: Në vendimin PML.Nr.X/YYYY, ..."

2. ⚠️ VETËM TË CITUAR (jo në bazë, vetëm në dokumente):
   → Forma: "Sipas [emri_i_dokumentit]: Në vendimin X, ..."

🛑 NUK LEJOHET të përziesh kategoritë. Kontrollo bllokun lart për secilin.
"""


# ═══════════════════════════════════════════════════════════════════════════
# V282.31 (A): ENRICHED CASE METADATA
# ═══════════════════════════════════════════════════════════════════════════

def _extract_case_metadata(case_doc: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """V282.31: Nxjerr metadata e zgjeruar nga case_doc për system_prompt."""
    if not case_doc:
        return {}

    meta: Dict[str, str] = {}

    opp = case_doc.get("opposing_party")
    if opp:
        if isinstance(opp, dict):
            name = opp.get("name", "")
            lawyer = opp.get("lawyer", "")
            if name:
                meta["opposing_party"] = f"{name}" + (f" (av. {lawyer})" if lawyer else "")
        elif isinstance(opp, str):
            meta["opposing_party"] = opp

    court = case_doc.get("court_name") or case_doc.get("court")
    if court:
        if isinstance(court, dict):
            court = court.get("name", "")
        if court:
            meta["court"] = str(court)

    court_info = case_doc.get("court_info") or {}
    if isinstance(court_info, dict) and court_info.get("judge"):
        meta["judge"] = str(court_info["judge"])

    deadline = case_doc.get("deadline")
    if deadline:
        meta["deadline"] = str(deadline)

    amount = case_doc.get("disputed_amount") or case_doc.get("claim_value")
    if amount:
        meta["disputed_amount"] = str(amount)

    desc = case_doc.get("description")
    if desc and isinstance(desc, str) and len(desc.strip()) > 0:
        meta["description"] = desc.strip()[:500]

    tags = case_doc.get("tags")
    if tags and isinstance(tags, list):
        meta["tags"] = ", ".join(str(t) for t in tags[:10])

    status = case_doc.get("status")
    if status:
        meta["status"] = str(status)

    return meta


def _build_case_header(
    case_title: str,
    client_name: str,
    client_position: str,
    detected_domain: str,
    current_date_str: str,
    case_meta: Dict[str, str],
) -> str:
    """V282.31: Ndërton header të pasur me metadata e lëndës."""
    lines = [
        f'LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | '
        f'KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}'
    ]

    meta_parts: List[str] = []
    if case_meta.get("opposing_party"):
        meta_parts.append(f'KUNDËRSHTARI: **{case_meta["opposing_party"]}**')
    if case_meta.get("court"):
        meta_parts.append(f'GJYKATA: **{case_meta["court"]}**')
    if case_meta.get("judge"):
        meta_parts.append(f'GJYQTARI: **{case_meta["judge"]}**')
    if case_meta.get("deadline"):
        meta_parts.append(f'AFATI: **{case_meta["deadline"]}**')
    if case_meta.get("disputed_amount"):
        meta_parts.append(f'VLERA: **{case_meta["disputed_amount"]}**')
    if case_meta.get("status"):
        meta_parts.append(f'STATUSI: **{case_meta["status"]}**')
    if case_meta.get("tags"):
        meta_parts.append(f'TAG: {case_meta["tags"]}')

    if meta_parts:
        lines.append(" | ".join(meta_parts))

    if case_meta.get("description"):
        lines.append(f'PËRSHKRIMI I LËNDËS: {case_meta["description"]}')

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# V282.36: VERIFICATION HELPER (KeyError guard)
# ═══════════════════════════════════════════════════════════════════════════

def _is_verified(v: Dict[str, Any]) -> bool:
    """
    V282.36: Kthen True nëse verifikimi rezultoi me ekzistencë.
    Përdor .get() në vend të v["exists"] — parandalon KeyError kur
    _verify_single_article kthen dict pa 'exists' (version mismatch, defekt
    upstream, exception e brendshme).
    """
    return bool(v.get("exists"))


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════════════════

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info(
            f"✅ [RAG] Juristi AI Natural Client Service V282.37 Initialized "
            f"(chat model: {FAST_SEARCH_MODEL}, "
            f"judicial-docs whitelist: ON, dual-law rule: ON, query-depth: ON, "
            f"pre-verify: ASYNC+PARALLEL, fast-path: DIRECT, dynamic-cleaner: ON, "
            f"timing: ON, multi-law-chat: ON, global-on-demand: ON, "
            f"no-fake-precedents: ON, pure-chat: ON, query-aware-docs: ON, "
            f"stemming: ON, caching: ON, comparison: ON, timeline: ON, "
            f"contradiction-scan: ON, suspects-injection: ON, no-boilerplate: ON, "
            f"precedent-source: ON, precedent-verified: ON, "
            f"dynamic-rule19: ON, force-reminder: ON, "
            f"parallel-vector-fetch: ON, enriched-case-context: ON, "
            f"auto-timeline: ON, global-fetch-on-user-request: ON, "
            f"smart-global-nresults: ON, "
            f"partial-coverage-fix: ON, dynamic-chunks: ON, "
            f"modularized: ON, async-db: ON, async-rag-pillars: ON, "
            f"verify-guard: ON, chat-history: DELEGATED)."
        )

    def _optimize_query(self, query: str) -> str:
        cleaned = query.strip()
        preambles = [
            r"^\s*më\s+trego\s+rreth\s+",
            r"^\s*më\s+trego\s+për\s+",
            r"^\s*a\s+mund\s+të\s+më\s+ndihmosh\s+me\s+",
            r"^\s*ju\s+lutem\s+më\s+gjej\s+",
            r"^\s*kërko\s+për\s+",
            r"^\s*gjej\s+nenin\s+",
        ]
        for preamble in preambles:
            cleaned = re.sub(preamble, "", cleaned, flags=re.IGNORECASE)

        abbreviations = {
            "LMD": "Ligji për Marrëdhëniet e Detyrimeve",
            "LSHT": "Ligji për Shoqëritë Tregtare",
            "KPRK": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            "KPPRK": "Kodi i Procedurës Penale të Kosovës",
            "LPK": "Ligji për Procedurën Kontestimore",
            "LFK": "Ligji për Familjen i Kosovës",
            "PSRK": "Prokuroria Speciale e Republikës së Kosovës",
        }
        for abbr, expansion in abbreviations.items():
            pattern = rf"\b{re.escape(abbr)}\b"
            cleaned = re.sub(
                pattern,
                lambda m, exp=expansion: f"{m.group(0)} ({exp})",
                cleaned,
                flags=re.IGNORECASE,
            )

        return cleaned.strip()

    async def chat(
        self,
        query: str,
        user_id: str,
        case_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        jurisdiction: str = 'ks',
        history: Optional[List[Dict[str, Any]]] = None,
        domain: Optional[str] = 'automatic'
    ) -> AsyncGenerator[str, None]:

        _t0 = time.time()

        def _lap(label: str):
            logger.info(f"⏱️ [TIMING] {label}: {time.time() - _t0:.2f}s")

        current_date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

        client_position = "PALË NË PROCEDURË"
        client_name = "Klienti / Parashtruesi"
        case_title = "Lënda Ligjore"
        case_meta: Dict[str, str] = {}
        db_documents: List[Dict[str, Any]] = []
        case_doc = None
        c_oid = None

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

                _q1 = time.time()
                case_doc = await asyncio.to_thread(
                    self.db.cases.find_one, {"_id": c_oid}
                )
                logger.info(f"⏱️ [TIMING]   mongo_case_query: {time.time() - _q1:.2f}s")

                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    case_title = case_doc.get("title") or case_doc.get("case_name") or case_title
                    case_meta = _extract_case_metadata(case_doc)
                    if case_meta:
                        logger.info(
                            f"📋 [Case Context V282.37] Metadata e zbuluar: "
                            f"{sorted(case_meta.keys())}"
                        )
            except Exception as ex:
                logger.info(f"Could not read client case (fallback defaults): {ex}")

        _lap("load_case")

        if history is None:
            history = []

        _lap("load_history")

        from app.services import vector_store_service
        query_lower = query.lower()
        optimized_query = self._optimize_query(query)

        has_specific_precedent = _detect_specific_precedent_query(query)
        if has_specific_precedent:
            logger.info("🎯 [V282.37] Precedent specifik u zbulua në query — global n_results reduktohet")

        legal_query = extract_legal_query(query)
        _lap("extract_legal_query")

        verified_context = ""
        pre_verify_disclaimer = ""
        verified_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        ambiguous_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        missing_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

        if legal_query["is_legal_query"] and legal_query["articles"]:
            # V282.37: PARALLEL + NON-BLOCKING verification
            _t_verify = time.time()

            async def _verify_one(art: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
                """V282.37: Thirrje sync e _verify_single_article në thread pool."""
                try:
                    v = await asyncio.to_thread(
                        _verify_single_article,
                        self.db,
                        art["number"],
                        art.get("paragraph"),
                        art.get("law_hint", ""),
                    )
                    return (art, v or {})
                except Exception as e:
                    logger.warning(
                        f"[PreVerify V282.37] Verifikimi dështoi për "
                        f"Neni {art.get('number')}: {e}"
                    )
                    return (art, {})

            verification_results: List[Tuple[Dict[str, Any], Dict[str, Any]]] = list(
                await asyncio.gather(
                    *[_verify_one(art) for art in legal_query["articles"]]
                )
            )

            logger.info(
                f"⏱️ [TIMING]   pre_verify ({len(verification_results)} articles parallel): "
                f"{time.time() - _t_verify:.2f}s"
            )

            # V282.36: .get() për robustness
            verified_articles = [(a, v) for a, v in verification_results if _is_verified(v)]
            ambiguous_articles = [
                (a, v) for a, v in verification_results
                if not _is_verified(v) and v.get("alternative_laws")
            ]
            missing_articles = [
                (a, v) for a, v in verification_results
                if not _is_verified(v) and not v.get("alternative_laws")
            ]

            if (
                missing_articles
                and not verified_articles
                and not ambiguous_articles
                and not legal_query["has_general_query"]
            ):
                refusal_text = "⚠️ Nuk mund të konfirmoj nenet e mëposhtme në bazën e verifikuar ligjore:\n\n"
                for art, _ in missing_articles:
                    law_part = f" të {art['law_hint']}" if art.get("law_hint") else ""
                    refusal_text += f"- Neni {art['number']}{law_part}\n"
                refusal_text += "\nPër përmbajtjen e saktë, rekomandohet verifikim me tekstin zyrtar të ligjit."

                yield refusal_text
                _lap("refusal_total")
                return

            if ambiguous_articles:
                for art, v in ambiguous_articles:
                    alts = _format_alternative_laws(v)
                    reason = v.get("match_reason", "")
                    if reason.startswith("multiple_laws_no_hint"):
                        pre_verify_disclaimer += (
                            f"⚠️ Neni {art['number']} ekziston në disa ligje, "
                            f"por nuk u specifikua cili. Alternativat e gjetura: {alts}.\n"
                            f"   Për citim të saktë, specifiko ligjin (p.sh. \"Neni "
                            f"{art['number']} i [Ligjit]\").\n"
                        )
                    else:
                        pre_verify_disclaimer += (
                            f"⚠️ Neni {art['number']} nuk u gjet me hint '{art.get('law_hint', '')}', "
                            f"por ekziston në: {alts}. Kontrollo burimin e saktë.\n"
                        )
                pre_verify_disclaimer += "\n"

            if missing_articles:
                for art, _ in missing_articles:
                    law_part = f" i {art['law_hint']}" if art.get("law_hint") else ""
                    pre_verify_disclaimer += (
                        f"⚠️ Neni {art['number']}{law_part} nuk u gjet në bazën e verifikuar ligjore. "
                        f"Nuk mund të konfirmoj përmbajtjen e tij.\n"
                    )
                pre_verify_disclaimer += "\n"

            if verified_articles:
                verified_context = "\n\n📖 NENET E VERIFIKUARA NGA BAZA LIGJORE:\n"
                for art, v in verified_articles:
                    doc = v.get("matched_doc") or {}
                    law_title = doc.get("law_title", "") or art.get("law_hint", "Ligj i panjohur")
                    text_excerpt = doc.get("text_excerpt", "")
                    verified_context += f"\n**{law_title} — Neni {art['number']}**\n{text_excerpt}\n"

            if ambiguous_articles:
                verified_context += "\n\n⚠️ NENE QË EKZISTOJNË NË DISA LIGJE (kërkojnë specifikim):\n"
                for art, v in ambiguous_articles:
                    alts = _format_alternative_laws(v)
                    reason = v.get("match_reason", "")
                    if reason.startswith("multiple_laws_no_hint"):
                        verified_context += (
                            f"\n**Neni {art['number']}** — ekziston në "
                            f"{len(v.get('alternative_laws', []))} ligje të ndryshme: {alts}\n"
                            f"NUK CITO ligj specifik pa specifikim nga përdoruesi. "
                            f"Informo përdoruesin për alternativat dhe kërko sqarim.\n"
                        )
                    else:
                        verified_context += (
                            f"\n**Neni {art['number']}** — hint '{art.get('law_hint', '')}' "
                            f"nuk matchoi, por neni ekziston në: {alts}\n"
                            f"Informo përdoruesin për mospërputhjen dhe listo alternativat.\n"
                        )

            logger.info(
                f"🔎 [PreVerify V282.37] articles total={len(verification_results)} "
                f"verified={len(verified_articles)} ambiguous={len(ambiguous_articles)} "
                f"missing={len(missing_articles)} has_general={legal_query['has_general_query']}"
            )

        _lap("pre_verify")

        has_document_selection = bool(document_ids and len(document_ids) > 0)
        should_fetch_global = QueryDepthDetector.should_fetch_global_docs(query, has_document_selection)
        query_depth = QueryDepthDetector.detect(query)

        user_wants_global = _user_wants_global_search(query_lower)

        if not user_wants_global:
            if should_fetch_global:
                logger.info(
                    f"⏭️ [V282.37] Skip global — pyetje faktuale pa kërkesë eksplicite "
                    f"për precedentë."
                )
            should_fetch_global = False
        else:
            logger.info(
                f"🌐 [V282.37] Global search AKTIV — përdoruesi kërkoi precedentë/jurisprudencë"
            )

        logger.info(
            f"🎯 [QueryDepth] Depth={query_depth} | "
            f"Doc selected={has_document_selection} | "
            f"Fetch global={should_fetch_global} | "
            f"User wants global={user_wants_global}"
        )

        is_case_wide_request = any(kw in query_lower for kw in [
            "analizo rastin", "analizë e rastit", "analizë standarde e rastit",
            "pasqyra ekzekutive e lëndës", "pasqyra e lëndës", "raportin master",
            "autopsi e plotë", "fashikull", "gjithë fashikullit", "shkeljet", "kronologjia"
        ])

        is_statutory_verification = any(kw in query_lower for kw in [
            "verifiko nenet", "a janë të sakta nenet", "referencat ligjore",
            "baza ligjore", "nenet e ligjit", "nxirr nenet", "kontrollo nenet"
        ])

        if is_case_wide_request:
            user_intent = "COMPREHENSIVE_ANALYSIS"
        elif is_statutory_verification:
            user_intent = "STATUTORY_VERIFICATION"
        else:
            user_intent = IntentDetector.detect(query)

        is_factual_legal_query = (
            legal_query["is_legal_query"]
            and len(verified_articles) > 0
            and not has_document_selection
            and not is_case_wide_request
            and not is_statutory_verification
            and user_intent not in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES", "DRAFTING"]
        )

        if is_factual_legal_query:
            logger.info(
                f"⚡ [FastPath V282.37 DIRECT] Skip LLM — return verified text directly "
                f"({len(verified_articles)} verified articles)"
            )

            direct_answer = _format_direct_answer(verified_articles, pre_verify_disclaimer)
            yield direct_answer

            _lap("direct_total")
            return

        if case_id and self.db is not None:
            try:
                cached_docs = await _get_cached_case_docs(str(case_id))

                if cached_docs is not None:
                    db_documents = cached_docs
                    logger.info(
                        f"⚡ [Cache HIT V282.37] case_docs: {len(db_documents)} docs "
                        f"(saved ~2.5s)"
                    )
                    _lap("load_docs")
                else:
                    doc_filter: Dict[str, Any] = {
                        "$or": [{"case_id": str(case_id)}, {"case_id": c_oid}],
                        "status": {"$ne": "DELETED"}
                    }

                    if document_ids and len(document_ids) > 0:
                        doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                        doc_strs = [str(did) for did in document_ids]
                        doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                    _q2 = time.time()

                    def _fetch_docs():
                        return list(
                            self.db.documents.find(doc_filter).sort(
                                [("created_at", 1), ("_id", 1)]
                            )
                        )

                    db_documents = await asyncio.to_thread(_fetch_docs)
                    logger.info(f"⏱️ [TIMING]   mongo_docs_query ({len(db_documents)} docs): {time.time() - _q2:.2f}s")
                    _lap("load_docs")

                    if db_documents:
                        await _set_cached_case_docs(str(case_id), db_documents, ttl=CACHE_TTL_CASE_DOCS)
                        logger.info(f"💾 [Cache MISS V282.37] case_docs cached (TTL={CACHE_TTL_CASE_DOCS}s)")
            except Exception as ex:
                logger.info(f"Could not read client documents (fallback empty): {ex}")

        # ═══════════════════════════════════════════════════════════════════════
        # STRUCTURAL CONTRADICTION + SUSPECTS SCAN
        # ═══════════════════════════════════════════════════════════════════════
        internal_contradictions: List[Dict[str, Any]] = []
        reported_contradictions: List[Dict[str, Any]] = []
        all_suspects: List[Dict[str, Any]] = []

        if db_documents and len(db_documents) <= MAX_DOCS_FOR_CONTRADICTION_SCAN:
            t_contr = time.time()
            for doc in db_documents:
                d_text = (
                    doc.get("content")
                    or doc.get("extracted_text")
                    or doc.get("text")
                    or ""
                )
                if not d_text.strip():
                    continue
                d_fname = doc.get("file_name") or doc.get("title") or "?"

                try:
                    cit = build_citation_profile(d_text)
                    own_cns = set(cit.get("own_case_numbers", []) or [])

                    fp = build_fact_profile(
                        d_text,
                        source_document=d_fname,
                        own_case_numbers=own_cns,
                    )

                    for c in fp.get("contradictions", []):
                        c["_source_file"] = d_fname
                        internal_contradictions.append(c)

                    for c in fp.get("reported_contradictions", []):
                        c["_source_file"] = d_fname
                        reported_contradictions.append(c)

                    for s in fp.get("suspects", []):
                        s["_source_file"] = d_fname
                        all_suspects.append(s)
                except Exception as e:
                    logger.info(f"[Contradiction/suspect scan] {d_fname}: {e}")
                    continue

            logger.info(
                f"⏱️ [TIMING]   contradiction_scan ({len(db_documents)} docs): "
                f"{time.time() - t_contr:.2f}s | "
                f"internal={len(internal_contradictions)}, "
                f"reported={len(reported_contradictions)}, "
                f"suspects={len(all_suspects)}"
            )
        else:
            logger.info(
                f"⏭️ [V282.37] Skip contradiction scan — "
                f"{len(db_documents)} docs > limit {MAX_DOCS_FOR_CONTRADICTION_SCAN}"
            )

        contradictions_block = _build_contradictions_block(
            internal_contradictions,
            reported_contradictions,
        )
        suspects_block = _build_suspects_block(all_suspects)

        _lap("contradiction_scan")

        _wants_comparison = user_wants_comparison(query_lower)

        _skip_doc_filter = (
            user_intent in ("COMPREHENSIVE_ANALYSIS", "STATUTORY_VERIFICATION", "DRAFTING")
            or _wants_comparison
        )

        context_documents = db_documents
        if db_documents and len(db_documents) > 1 and not _skip_doc_filter:
            context_documents, was_filtered = _detect_relevant_documents(query, db_documents, max_match=3)
            if was_filtered:
                logger.info(
                    f"🎯 [V282.37] Query-aware docs: {len(context_documents)}/{len(db_documents)} "
                    f"dokumente të zgjedhura për kontekst LLM: "
                    f"{[d.get('file_name', '?') for d in context_documents]}"
                )
            else:
                logger.info(
                    f"📚 [V282.37] Pa filtrim dokumentesh — konteksti përfshin të gjitha "
                    f"{len(db_documents)} dokumentet"
                )
        elif _skip_doc_filter and db_documents:
            logger.info(
                f"📚 [V282.37] SKIP query-aware filter (intent={user_intent}, "
                f"comparison={_wants_comparison}) — "
                f"konteksti përfshin të gjitha {len(db_documents)} dokumentet"
            )

        # ═══════════════════════════════════════════════════════════════════════
        # CROSS-DOC COMPARISON + TIMELINE
        # ═══════════════════════════════════════════════════════════════════════
        comparison_block = ""
        timeline_block = ""

        try:
            if _wants_comparison and len(db_documents) >= 2:
                comparison_block = build_comparison_table(context_documents)
                if comparison_block:
                    logger.info(
                        f"📊 [V282.37] Tabelë krahasuese aktivizuar "
                        f"({len(comparison_block)} chars)"
                    )
        except Exception as e:
            logger.info(f"Comparison build skipped (feature opsional): {e}")

        _timeline_should_build = (
            user_wants_timeline(query_lower)
            or user_intent in ("COMPREHENSIVE_ANALYSIS", "STATUTORY_VERIFICATION")
        )

        try:
            if _timeline_should_build and db_documents:
                events = extract_events(db_documents, max_per_doc=15)
                timeline_block = build_timeline(events)
                if timeline_block:
                    logger.info(
                        f"📅 [V282.37] Timeline aktivizuar "
                        f"({len(events)} ngjarje, auto={'po' if user_intent in ('COMPREHENSIVE_ANALYSIS','STATUTORY_VERIFICATION') else 'jo'})"
                    )
        except Exception as e:
            logger.info(f"Timeline build skipped (feature opsional): {e}")

        cited_precedents_block = ""
        if user_wants_global:
            cited_precedents_block = _build_cited_precedents_block(
                db_documents,
                db=self.db,
            )

        single_doc_obj = db_documents[0] if (document_ids and len(document_ids) == 1 and db_documents) else None

        sample_text = ""
        if single_doc_obj:
            sample_text = (single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or "")[:10000]
        elif db_documents:
            sample_text = " ".join([(d.get("content") or d.get("extracted_text") or "")[:2000] for d in db_documents])

        detected_domain = BasePillarService.detect_case_domain(
            case_title=case_title,
            context_str=sample_text,
            manifest_str=""
        )

        exec_query = optimized_query
        system_prompt = ""

        case_docs_cache_key = _chunks_cache_key(
            str(case_id or ""),
            str(user_id or ""),
            optimized_query,
            document_ids,
        )

        # ═══════════════════════════════════════════════════════════════════════
        # PARALLEL VECTOR FETCH
        # ═══════════════════════════════════════════════════════════════════════
        _N_RESULTS_BY_INTENT = {
            "COMPREHENSIVE_ANALYSIS": 30,
            "STATUTORY_VERIFICATION": 25,
            "DRAFTING": 25,
        }
        vector_n_results = _N_RESULTS_BY_INTENT.get(user_intent, 25)

        _needs_global_vec = (
            (
                should_fetch_global
                and user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]
            )
            or user_wants_global
        )

        _global_n = (
            _GLOBAL_N_PRECEDENT_SPECIFIC
            if has_specific_precedent
            else _GLOBAL_N_DEFAULT
        )

        async def _fetch_case_vec():
            cached = await _get_cached_chunks(case_docs_cache_key)
            if cached is not None:
                logger.info(
                    f"⚡ [Cache HIT V282.37] vector_case: {len(cached)} chunks"
                )
                return cached
            try:
                result = await asyncio.to_thread(
                    vector_store_service.query_case_knowledge_base,
                    user_id=user_id,
                    query_text=optimized_query,
                    case_context_id=case_id,
                    document_ids=document_ids,
                    n_results=vector_n_results,
                )
                if result:
                    await _set_cached_chunks(case_docs_cache_key, result, ttl=CACHE_TTL_CASE_CHUNKS)
                    logger.info(
                        f"💾 [Cache MISS V282.37] vector_case cached "
                        f"(n_results={vector_n_results}, intent={user_intent})"
                    )
                return result or []
            except Exception as e:
                logger.warning(f"[vector_case] failed: {e}")
                return []

        async def _fetch_global_vec():
            try:
                return await asyncio.to_thread(
                    vector_store_service.query_global_knowledge_base,
                    query_text=optimized_query,
                    n_results=_global_n,
                ) or []
            except Exception as e:
                logger.warning(f"[vector_global] failed: {e}")
                return []

        _t_vec = time.time()

        if _needs_global_vec:
            case_docs, global_docs = await asyncio.gather(
                _fetch_case_vec(),
                _fetch_global_vec(),
            )
            logger.info(
                f"⚡ [V282.37 Parallel] vector_case + vector_global: "
                f"{time.time() - _t_vec:.2f}s | "
                f"case={len(case_docs)} chunks, "
                f"global={len(global_docs)} chunks "
                f"(n_results={_global_n}, specific_precedent={has_specific_precedent})"
            )
        else:
            case_docs = await _fetch_case_vec()
            global_docs = []

        _lap("vector_case+global")

        # ─── Branches ───
        if user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            if not _needs_global_vec:
                logger.info(f"⏭️ [QueryDepth] Skip global_docs (factual + document selected)")

            manifest_str, context_str, _ = ContextBuilder.build_with_whitelist(
                case_docs, global_docs, db_documents, context_documents
            )
            _lap("context_builder")

            case_header = _build_case_header(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                detected_domain=detected_domain,
                current_date_str=current_date_str,
                case_meta=case_meta,
            )

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor dhe Këshilltari Kryesor në Kosovë".
            {case_header}

            {NATURAL_COUNSEL_INSTRUCTION}

            {contradictions_block}

            {suspects_block}

            {cited_precedents_block}

            {comparison_block}
            {timeline_block}

            SHKRESAT E LËNDËS ({len(context_documents)} DOKUMENTE NË FASHIKULL):
            {manifest_str}
            {context_str}
            """

        elif user_intent == "STATUTORY_VERIFICATION":
            dossier_blocks = []
            for idx, doc in enumerate(context_documents, 1):
                doc_title = doc.get("file_name") or f"Dokumenti #{idx}"
                raw_text = (doc.get("content") or doc.get("extracted_text") or "").strip()
                p_count = doc.get("page_count", "1")
                dossier_blocks.append(f"SHKRESA #{idx}: {doc_title} (Faqe: {p_count})\n{raw_text}\n")

            context_docs = "\n".join(dossier_blocks)
            _lap("statutory_context")

            t_rag = time.time()
            try:
                rag_ctx, _ = await BasePillarService.get_rag_context_async(
                    user_id=str(user_id or ""),
                    case_id=str(case_id or ""),
                    query_text=optimized_query,
                    n_results=8,
                )
                logger.info(
                    f"⏱️ [TIMING]   rag_context_async (statutory): "
                    f"{time.time() - t_rag:.2f}s ({len(rag_ctx)} chars)"
                )
            except Exception as _re:
                logger.warning(f"⚠️ [V282.37] get_rag_context_async dështoi (statutory): {_re}")
                rag_ctx = ""

            base_prompt = StatutoryVerificationService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=context_docs,
                manifest_str="",
                case_domain=detected_domain,
                query_text=optimized_query,
                user_id=user_id,
                case_id=case_id,
                db=self.db,
                rag_context=rag_ctx,
            )
            system_prompt = base_prompt + "\n\n" + NATURAL_COUNSEL_INSTRUCTION
            if contradictions_block:
                system_prompt += "\n\n" + contradictions_block
            if suspects_block:
                system_prompt += "\n\n" + suspects_block

        elif user_intent == "DRAFTING":
            if not _needs_global_vec:
                logger.info(f"⏭️ [V282.37] Skip global_docs në DRAFTING")

            manifest_str, context_str, _ = ContextBuilder.build_with_whitelist(
                case_docs, global_docs, db_documents, context_documents
            )
            _lap("context_builder")

            t_rag = time.time()
            try:
                rag_ctx, _ = await BasePillarService.get_rag_context_async(
                    user_id=str(user_id or ""),
                    case_id=str(case_id or ""),
                    query_text=optimized_query,
                    n_results=8,
                )
                logger.info(
                    f"⏱️ [TIMING]   rag_context_async (drafting): "
                    f"{time.time() - t_rag:.2f}s ({len(rag_ctx)} chars)"
                )
            except Exception as _re:
                logger.warning(f"⚠️ [V282.37] get_rag_context_async dështoi (drafting): {_re}")
                rag_ctx = ""

            base_prompt = LegalDraftingService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str,
                query=optimized_query,
                case_domain=detected_domain,
                db=self.db,
                user_id=user_id,
                case_id=case_id,
                rag_context=rag_ctx,
            )
            system_prompt = base_prompt + "\n\n" + NATURAL_COUNSEL_INSTRUCTION
            if contradictions_block:
                system_prompt += "\n\n" + contradictions_block
            if suspects_block:
                system_prompt += "\n\n" + suspects_block
            if cited_precedents_block:
                system_prompt += "\n\n" + cited_precedents_block
            exec_query = f"Harto aktin e plotë procedural të kërkuar ({optimized_query}) me strukturë solemne gjyqësore."
        else:
            if not _needs_global_vec:
                logger.info(f"⏭️ [V282.37] Skip global_docs (chat i thjeshtë)")

            manifest_str, context_str, _ = ContextBuilder.build_with_whitelist(
                case_docs, global_docs, db_documents, context_documents
            )
            _lap("context_builder")

            case_header = _build_case_header(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                detected_domain=detected_domain,
                current_date_str=current_date_str,
                case_meta=case_meta,
            )

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor dhe Këshilltari Kryesor në Kosovë".
            {case_header}

            {NATURAL_COUNSEL_INSTRUCTION}

            {pre_verify_disclaimer}{verified_context}

            {contradictions_block}

            {suspects_block}

            {cited_precedents_block}

            {comparison_block}
            {timeline_block}

            SHKRESAT E LËNDËS ({len(context_documents)} DOKUMENTE NË FASHIKULL):
            {manifest_str}
            {context_str}
            """

        # ═══════════════════════════════════════════════════════════════════════
        # V282.30: DYNAMIC RULE 19 REMINDER
        # ═══════════════════════════════════════════════════════════════════════
        if cited_precedents_block:
            has_verified = "✅ TË VERIFIKUAR NË BAZËN E GJYKATËS SUPREME" in cited_precedents_block
            has_unverified = "⚠️ VETËM TË CITUAR" in cited_precedents_block

            if has_verified and has_unverified:
                system_prompt += _RULE_19_REMINDER_MIXED
                logger.info("[Rule19 V282.37] Reminder: MIXED (verified + unverified)")
            elif has_verified:
                system_prompt += _RULE_19_REMINDER_VERIFIED
                logger.info("[Rule19 V282.37] Reminder: VERIFIED only")
            elif has_unverified:
                system_prompt += _RULE_19_REMINDER_UNVERIFIED
                logger.info("[Rule19 V282.37] Reminder: UNVERIFIED only")
            else:
                logger.warning(
                    "[Rule19 V282.37] cited_precedents_block ekziston por nuk "
                    "përmban asnjë marker të njohur."
                )

        _lap("pre_llm")

        full_generated_response = ""
        _first_token_logged = False
        async for content in self.response_generator.generate_stream(
            system_prompt,
            exec_query,
            context="",
            history=history,
            model=FAST_SEARCH_MODEL,
        ):
            if not _first_token_logged:
                _first_token_logged = True
                logger.info(f"⏱️ [TIMING]   llm_first_token: {time.time() - _t0:.2f}s")
            full_generated_response += content
            yield content

        _lap("llm_stream")

        lower_resp = full_generated_response.lower()
        llm_failed = any(marker in lower_resp for marker in [
            "përkohësisht i ngarkuar",
            "gabim teknik",
            "error code:",
            "upstream error",
        ])

        if llm_failed:
            logger.warning(
                f"⚠️ [V282.37] LLM dështoi. "
                f"Output: {full_generated_response[:100]}..."
            )
            _lap("total")
            return

        _lap("total")


__all__ = [
    "AlbanianRAGService",
    "NATURAL_COUNSEL_INSTRUCTION",
    "GLOBAL_SEARCH_TRIGGERS",
    "is_valid_legal_report",
    "detect_requested_pillar",
]