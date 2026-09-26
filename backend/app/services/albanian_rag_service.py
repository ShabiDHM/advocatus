# FILE: backend/app/services/albanian_rag_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI DOKTRINAR RAG V282.23
# V282.23: STRUCTURED SUSPECTS INJECTION —
#          - Agregon suspects nga TË GJITHA dokumentet në fashikull
#            (build_fact_profile per secilin).
#          - Injekton suspects_block në system_prompt për intent-et
#            COMPREHENSIVE_ANALYSIS, DRAFTING, dhe GENERAL_CHAT.
#          - Fix për bug-un ku chat-i shfaqte vetëm 3/15 persona të dyshuar
#            sepse LLM-ja lexonte vetëm 3000 chars e parë të një dokumenti.
# V282.22: STRUCTURAL CONTRADICTION SCAN.
# V282.21: LOG CLEANUP.
# V282.20: DUAL HISTORY UNIFIED.

import os
import logging
import re
import json
import time
import hashlib
from collections import Counter
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId

import redis.asyncio as aioredis

from app.core.config import settings

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
from app.services.document_review.mongo_verifier import _verify_single_article
from app.services.document_review.citation_extractor import build_citation_profile
from app.services.document_review.fact_extractor import build_fact_profile
from app.services.pillars.base_pillar_service import BasePillarService

from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.statutory_verification_service import StatutoryVerificationService

from app.services.llm.llm_client import DEEP_ANALYSIS_MODEL, FAST_SEARCH_MODEL

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V282.18: REDIS CACHE
# ═══════════════════════════════════════════════════════════════════════════

_redis_client: Optional[aioredis.Redis] = None

CACHE_TTL_CASE_DOCS = 600
CACHE_TTL_CASE_CHUNKS = 300

MAX_DOCS_FOR_CONTRADICTION_SCAN = 30


async def _get_redis() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        redis_url = (
            getattr(settings, "REDIS_URL", None)
            or os.getenv("REDIS_URL", "")
        )
        if not redis_url:
            logger.info("[Cache] REDIS_URL nuk është konfiguruar — cache çaktivizuar")
            return None

        _redis_client = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await _redis_client.ping()
        logger.info("✅ [Cache] Redis client initialized (async)")
        return _redis_client
    except Exception as e:
        logger.warning(f"⚠️ [Cache] Redis init failed — cache çaktivizuar: {e}")
        _redis_client = None
        return None


def _serialize_docs_for_cache(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in docs:
        d2 = dict(d)
        if "_id" in d2 and not isinstance(d2["_id"], str):
            d2["_id"] = str(d2["_id"])
        out.append(d2)
    return out


async def _get_cached_case_docs(case_id: str) -> Optional[List[Dict[str, Any]]]:
    client = await _get_redis()
    if not client:
        return None
    try:
        cache_key = f"case_docs_v1:{case_id}"
        cached = await client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.info(f"[Cache] get case_docs failed (fallback DB): {e}")
    return None


async def _set_cached_case_docs(case_id: str, docs: List[Dict[str, Any]], ttl: int = CACHE_TTL_CASE_DOCS) -> None:
    client = await _get_redis()
    if not client:
        return
    try:
        cache_key = f"case_docs_v1:{case_id}"
        payload = json.dumps(_serialize_docs_for_cache(docs), ensure_ascii=False, default=str)
        await client.setex(cache_key, ttl, payload)
    except Exception as e:
        logger.info(f"[Cache] set case_docs failed (best-effort): {e}")


def _chunks_cache_key(
    case_id: str,
    user_id: str,
    query: str,
    document_ids: Optional[List[str]],
) -> str:
    src = f"{case_id}|{user_id}|{query.lower().strip()}|{','.join(sorted(document_ids or []))}"
    h = hashlib.sha1(src.encode("utf-8")).hexdigest()[:16]
    return f"case_chunks_v1:{h}"


async def _get_cached_chunks(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    client = await _get_redis()
    if not client:
        return None
    try:
        cached = await client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.info(f"[Cache] get chunks failed (fallback vector): {e}")
    return None


async def _set_cached_chunks(cache_key: str, chunks: List[Dict[str, Any]], ttl: int = CACHE_TTL_CASE_CHUNKS) -> None:
    client = await _get_redis()
    if not client:
        return
    try:
        payload = json.dumps(chunks, ensure_ascii=False, default=str)
        await client.setex(cache_key, ttl, payload)
    except Exception as e:
        logger.info(f"[Cache] set chunks failed (best-effort): {e}")


# ═══════════════════════════════════════════════════════════════════════════
# V282.12: FJALË KYÇE PËR KËRKIM EKSPLICIT TË PRECEDENTËVE
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_SEARCH_TRIGGERS = [
    "precedent", "precedente", "precedentë",
    "jurisprudenc",
    "gjykata supreme", "gjykatës supreme",
    "praktikë gjyqësore", "praktike gjyqesore", "praktikën gjyqësore",
    "vendime gjyqësore",
    "aktgjykim supreme",
    "mendim juridik",
    "qëndrim parimor", "qendrim parimor",
]


def _user_wants_global_search(query_lower: str) -> bool:
    return any(trigger in query_lower for trigger in GLOBAL_SEARCH_TRIGGERS)


# ═══════════════════════════════════════════════════════════════════════════
# V282.17: STEMMING I THJESHTË PËR SHQIP
# ═══════════════════════════════════════════════════════════════════════════

_STEM_SUFFIXES = [
    "imit", "imin", "imi", "im",
    "jen", "jes", "jet", "je",
    "esit", "esin", "esa", "esë", "es", "ës",
    "ave", "ava", "eve", "eva",
    "in", "ën", "un", "it", "ës", "së",
    "ja", "je", "a", "i", "u", "e", "ë",
]


def _stem_albanian(word: str) -> str:
    if not word or len(word) < 4:
        return word.lower()
    w = word.lower()
    for suf in _STEM_SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def _words_match(w1: str, w2: str) -> bool:
    if not w1 or not w2:
        return False
    s1 = _stem_albanian(w1)
    s2 = _stem_albanian(w2)
    if s1 == s2:
        return True
    if len(s1) >= 4 and len(s2) >= 4:
        if s1 in s2 or s2 in s1:
            return True
        if s1[:4] == s2[:4]:
            return True
    return False


_MATCH_STOPWORDS = {
    "dokument", "dokumente", "dokumentet", "dokumenti", "dokumentin",
    "lenda", "lende", "lenden", "lendja", "fashikull", "fashikulli",
    "shkresa", "shkresat", "shkresen",
    "trego", "thuaj", "thoni", "themi", "flas", "flitet",
    "refuzimi", "refuzim", "ankesa", "ankes", "aktakuza", "aktakuzes",
    "kerkesa", "kerkes", "vendimi", "vendim", "aktvendim",
    "për", "per", "me", "nga", "në", "ne", "të", "te",
    "eshte", "është", "jane", "janë", "ishte", "ishin",
    "cili", "cila", "cilin", "cilat", "kush", "cfare", "çfarë",
    "kam", "kemi", "keni", "kanë", "kane",
    "kjo", "ky", "keta", "keto", "ato", "ata",
    "gjith", "gjithë", "gjithe", "krejt",
    "pse", "si", "ku", "kur",
}


def _extract_meaningful_words(text: str, min_len: int = 5) -> set:
    raw = re.findall(r'\b\w{' + str(min_len) + r',}\b', text.lower())
    return {w for w in raw if w not in _MATCH_STOPWORDS}


def _detect_relevant_documents(
    query: str,
    documents: List[Dict[str, Any]],
    max_match: int = 3,
) -> Tuple[List[Dict[str, Any]], bool]:
    if not documents or not query:
        return documents, False

    query_words = _extract_meaningful_words(query, min_len=5)
    if not query_words:
        return documents, False

    matched = []
    for doc in documents:
        fname = (doc.get("file_name") or doc.get("title") or "").lower()
        fname_clean = re.sub(r'[._\-]+', ' ', fname)
        fname_words = _extract_meaningful_words(fname_clean, min_len=4)

        for qw in query_words:
            if any(_words_match(qw, fw) for fw in fname_words):
                matched.append(doc)
                break

    if 1 <= len(matched) <= max_match:
        return matched, True

    return documents, False


# ═══════════════════════════════════════════════════════════════════════════
# UDHËZIMI I BASHKËPUNIMIT + ANTI-HALUDINACIONI
# ═══════════════════════════════════════════════════════════════════════════
NATURAL_COUNSEL_INSTRUCTION = """
UDHËZIME TË BASHKËPUNIMIT ME AVOKATIN DHE KLIENTIN:
1. BASHKËPUNIM I ZGJUAR DHE DIALOG I NATYRSHËM:
   - Dëgjoni me vëmendje kërkesën e përdoruesit. Nëse përdoruesi bën një pyetje paraprake, kërkon sqarim apo thotë se do të paraqesë një shkresë: përgjigjuni si një këshilltar i vërtetë njerëzor ligjor (pa shabllone mekanike dhe me mirëkuptim të plotë).
   - MOS sajo asnjëherë raporte imagjinare kur përdoruesi ende nuk e ka dhënë tekstin apo pyetjen konkrete.
2. SAKTËSI DHE BAZË LIGJORE:
   - Përgjigjuni në gjuhë standarde juridike të Republikës së Kosovës.
   - Mbështetuni në faktet reale të shkresave të lëndës dhe në dispozitat përkatëse.

═══════════════════════════════════════════════════════════════════════════
⚠️ RREGULLA TË PAFEKSIONUESHME ANTI-HALUDINACION (TË DETYRUESHME)
═══════════════════════════════════════════════════════════════════════════

1. PËRDOR VETËM NENET QË JANË NË KONTEKST:
   - Nëse në kontekstin e mësipërm nuk shfaqet neni konkret → NUK MUND TË CITOSH atë nen.
   - NUK LEJOHET të shpikësh numra neni, emra ligjesh, afate ose procedura që nuk shfaqen në kontekst.
   - Nëse informacioni mungon → thuaj:
     "Ky informacion nuk gjendet në shkresat e fashikullit. Rekomandohet verifikim me burimin zyrtar."

2. IDENTIFIKO SAKTËSISHT LIGJIN — KURRË MOS I NDËRRO:
   - **KPK**  = Kodi i Procedurës Penale (Nr. 08/L-032) → PROCEDURA PENALE
   - **KPRK** = Kodi Penal (Nr. 06/L-074)             → DËNIME, REHABILITIM
   - **LPK**  = Ligji për Procedurën Kontestimore (Nr. 03/L-006) → PROCEDURA CIVILE
   - **LMD**  = Ligji për Marrëdhëniet e Detyrimeve (Nr. 04/L-077) → DETYRIME, DËME
   - **LMDHF** = Ligji për Mbrojtjen nga Dhuna në Familje (Nr. 03/L-182 → 08/L-185) → URDHRA MBROJTJEJE
   - **LFK**  = Ligji për Familjen (Nr. 2004/32)      → ÇËSHTJE FAMILJARE
   - **Kushtetuta** e Republikës së Kosovës           → TË DREJTAT THEMELORE

3. KURRË MOS PËRZIJ LËMIE LIGJORE:
   - Çështje CIVILE (C.nr., urdhër mbrojtjeje, divorc, kujdestari) → NUK cito KPRK.
   - Çështje PENALE (P.nr., PKR, kallëzim) → NUK cito LPK.
   - Rehabilitimi penal NUK aplikohet në çështje civile.

4. ⚠️ LIGJET ME NUMËR (KRITIKE):
   - KUR dokumenti citon "Ligji Nr. XX/L-YYY" → PËRDOR ATË NUMËR TË SAKTË.
   - NUK LEJOHET ta zëvendësosh me një version tjetër pa përmendur burimin.
   - SHEMBULL: Nëse dokumenti shkruan "03/L-182" → shkruaj "03/L-182".

5. FORMATO CITIMET SAKTËSISHT:
   - "Neni X i [Ligjit]" — KURRË "Neni X.Y".
   - Shembull i GABUAR: "Neni 93 i KPK-së" (duhet KPRK).

6. AFATET PROCEDURALE:
   - Cito afatin VETËM me burim: "Sipas [dokumenti/neni], afati është X".
   - NËSE nuk gjendet afat → shkruaj "Afati: kontrollo manualisht".

7. ⚠️ KONTRADIKTAT E BRENDSHME (PËRKUFIZIM I NGUSHTË):
   - KONTRADIKTË = mosputhje FAKTIKE brenda TË NJËJTIT dokument:
       * Dy data të ndryshme për të njëjtin fakt (p.sh. "29.04.2024" vs "21.04.2024")
       * Dy kohëzgjatje të ndryshme (p.sh. "6 muaj" vs "12 muaj")
       * Dy distanca të ndryshme (p.sh. "100 metra" vs "50 metra")
       * Dy shuma të ndryshme (p.sh. "5,000€" vs "10,000€")
   - NUK JANË KONTRADIKTA:
       * Mospajtimi midis palëve (mbrojtësi pretendon X, gjykata vendos Y) — KJO është procedurë normale
       * Argumentet e kundërta të palëve
       * Vendimi i gjykatës kundër pretendimit të njërës palë
   - NËSE gjen kontradiktë faktike → cito TË DYJA vlerat + thuaj ku shfaqen.
   - NËSE nuk ka kontradiktë faktike → thuaj SAKTËSISHT:
       "Nuk u identifikuan kontradikta faktike brenda dokumenteve."

8. STRUKTURA E PËRGJIGJES:
   - Fillimisht identifiko çfarë pyet përdoruesi.
   - Pastaj jep përgjigjen bazuar vetëm në kontekst.
   - Në fund, shkruaj SAKTËSISHT këtë fjali (fjala për fjalë):
     "Verifikoni me burimin zyrtar për saktësi të plotë."

9. STATUSI I DOKUMENTIT:
   - NËSE dokumenti përmban "KËSHILLË JURIDIKE" ose "afat ankimi" → NUK është i plotfuqishëm.

10. ZERO SHABLLONE TË PËRGJITHSHME:
    - ÇDO fjali duhet të ketë lidhje me shkresat ose pyetjen e avokatit.

11. ⚠️ LIGJE TË DYFISHTA / TË NDRYSHME (KRITIKE):
    - NËSE dokumentet e fashikullit citojnë DY OSE MË SHUMË ligje të ndryshme për të njëjtën çështje → LISTOJI TË GJITHA me burimin e saktë.
    - NUK LEJOHET të zgjedhësh vetëm një ligj pa përmendur tjetrin.

12. ⚠️ NENE TË PAVERIFIKUAR (KRITIKE):
    - KUR në kontekst shfaqet "⚠️ Neni X ... nuk u gjet në bazën e verifikuar ligjore":
       → NUK LEJOHET të përshkruash, përgjithësosh, ose spekulosh përmbajtjen e atij neni.
       → Vetëm njofto mungesën dhe vazhdo me pjesën tjetër të pyetjes.
       → NËSE pyetja kishte vetëm atë nen → rekomando verifikim me tekstin zyrtar.

13. ⚠️ NENE QË EKZISTOJNË NË DISA LIGJE:
    - KUR në kontekst shfaqet "⚠️ Neni X ekziston në disa ligje", NUK LEJOHET të zgjedhësh vetëm një ligj.
    - LISTO TË GJITHA alternativat e gjetura dhe kërko sqarim.

14. ⚠️ PRECEDENTËT E GJYKATËS SUPREME:
    - NËSE në kontekst shfaqet seksioni "<<< JURISPRUDENCA DHE DITURIA GLOBALE E KOSOVËS >>>":
       → PËRDOR VETËM numrat e lëndëve që shfaqen Aty (të etiketuar "🏛️ BURIMI:").
       → NUK LEJOHET të shpikësh numra lëndësh që nuk shfaqen në kontekst.
    - NËSE NUK ka seksion "JURISPRUDENCA" në kontekst:
       → NUK LEJOHET të përmendësh asnjë numër precedenti.

15. ⚠️ KRAHASIMI MIDIS DOKUMENTEVE:
    - KUR në kontekst shfaqet seksioni "<<< KRAHASIM MIDIS DOKUMENTEVE >>>":
       → Bazohu EKSPLICITISHT në tabelën e dhënë.
       → Mos shpik nene që nuk janë në tabelë.

16. ⚠️ KRONOLOGJIA:
    - KUR në kontekst shfaqet seksioni "<<< KRONOLOGJIA E NGJARJEVE >>>":
       → Bazohu EKSPLICITISHT në datat e dhëna.
       → NUK LEJOHET të shpikësh data që nuk shfaqen në listë.

17. ⚠️ KONTRADIKTA TË BRENDSHME TË DOKUMENTEVE (KRITIKE):
    - KUR në kontekst shfaqet seksioni "⚠️ KONTRADIKTA TË BRENDSHME TË DOKUMENTEVE":
       → Këto janë FAKTE KRITIKE të zbuluara automatikisht nga sistemi.
       → DUHET T'I PËRMENDËSH në përgjigje nëse janë relevante.
       → KUR përdoruesi pyet për kontradikta → LISTOJI TË GJITHA me zonën
         (dispozitiv/arsyetim/propozim) dhe vlerat kontradiktore.
       → NUK LEJOHET të thuash "nuk u identifikuan kontradikta" nëse ky seksion
         përmban kontradikta.

18. ⚠️ PERSONA TË DYSHUAR / TË AKUZUAR (KRITIKE):
    - KUR në kontekst shfaqet seksioni "👥 PERSONA TË IDENTIFIKUAR NË DOKUMENTE":
       → Kjo listë përmban TË GJITHË personat e identifikuar automatikisht nga
         strukturat e dokumenteve (GRUPI I/II/III, lista të numëruara, etj.).
       → KUR përdoruesi pyet "Kush janë personat e dyshuar?" → LISTOJI TË GJITHË
         personat nga ky seksion me pozicionin/rolin e tyre.
       → NUK LEJOHET të listosh vetëm 2-3 persona nëse seksioni ka më shumë.
       → Citon numrin TOTAL (p.sh. "12 persona të identifikuar në dokument").
       → NËSE pyetja kërkon vetëm kategori specifike (p.sh. "gjyqtarët") →
         filtro sipas fjalëve kyçe në pozicion_hint.
"""


def is_valid_legal_report(text: str) -> bool:
    if not text or len(text.strip()) < 150:
        return False
    lower_text = text.lower()
    error_markers = [
        "përkohësisht i ngarkuar", "error code:", "context_length_exceeded",
        "max_num_tokens", "upstream error", "not a valid model",
        "no endpoints found", "gabim teknik"
    ]
    for marker in error_markers:
        if marker in lower_text:
            return False
    return True


def detect_requested_pillar(query_lower: str) -> Optional[str]:
    if "shtjella 1" in query_lower or "shtjella_1" in query_lower or "ekzaminimi" in query_lower or "fakti" in query_lower:
        return "PILLAR_1"
    if "shtjella 2" in query_lower or "shtjella_2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower:
        return "PILLAR_2"
    if "shtjella 3" in query_lower or "shtjella_3" in query_lower or "kundërshtimet" in query_lower or "plani" in query_lower:
        return "PILLAR_3"
    return None


def _format_alternative_laws(v: Dict[str, Any]) -> str:
    alts = v.get("alternative_laws", [])
    if not alts:
        return ""

    titles: List[str] = []
    for a in alts:
        if isinstance(a, dict):
            t = a.get("law_title") or a.get("title") or ""
            if t:
                titles.append(t)
        else:
            titles.append(str(a))

    if not titles:
        return "(ligje të panjohura)"
    return "; ".join(titles[:5]) + (" ..." if len(titles) > 5 else "")


def _build_contradictions_block(
    internal: List[Dict[str, Any]],
    reported: List[Dict[str, Any]],
) -> str:
    if not internal and not reported:
        return ""

    parts: List[str] = []

    if internal:
        parts.append("\n\n═══════════════════════════════════════════════════════════════════════════")
        parts.append("⚠️ KONTRADIKTA TË BRENDSHME TË DOKUMENTEVE (zbuluar automatikisht)")
        parts.append("═══════════════════════════════════════════════════════════════════════════")
        parts.append("")
        parts.append("⚠️ Këto janë mosputhje FAKTIKE brenda TË NJËJTIT dokument. DUHET PËRMENDUR.")
        parts.append("")
        for c in internal:
            values = " vs ".join(str(v) for v in c.get("values", []))
            src = c.get("_source_file", "?")
            zone = c.get("zone_label", "?")
            parts.append(f"📌 [{src}] {c.get('type', '?')}")
            parts.append(f"   Zona: {zone}")
            parts.append(f"   Vlerat kontradiktore: **{values} {c.get('unit', '')}**")
            for ex in c.get("examples", [])[:3]:
                parts.append(f"   Shembull: {ex[:250]}")
            parts.append("")
        parts.append("⚠️ KËTO JANË FAKTE KRITIKE — DUHET TË PËRMENDEN NË PËRGJIGJE.")

    if reported:
        parts.append("\n\n═══════════════════════════════════════════════════════════════════════════")
        parts.append("ℹ️ KONTRADIKTA TË RAPORTUARA (jo të vetë dokumenteve tona)")
        parts.append("═══════════════════════════════════════════════════════════════════════════")
        parts.append("")
        for c in reported:
            values = " vs ".join(str(v) for v in c.get("values", []))
            src = c.get("_source_file", "?")
            parts.append(f"📌 [{src}] {c.get('type', '?')}")
            parts.append(f"   Vlerat: **{values} {c.get('unit', '')}**")
            parts.append("")

    return "\n".join(parts)


def _build_suspects_block(
    suspects: List[Dict[str, Any]],
) -> str:
    """
    V282.23: Ndërton bllokun e personave të identifikuar për system_prompt.
    """
    if not suspects:
        return ""

    parts: List[str] = []
    parts.append("\n\n═══════════════════════════════════════════════════════════════════════════")
    parts.append(f"👥 PERSONA TË IDENTIFIKUAR NË DOKUMENTE ({len(suspects)} total)")
    parts.append("═══════════════════════════════════════════════════════════════════════════")
    parts.append("")
    parts.append("⚠️ Kjo listë është nxjerrë automatikisht nga strukturat e dokumenteve")
    parts.append("   (lista të numëruara, GRUPI I/II/III, sektorë të tjerë).")
    parts.append("⚠️ DUHET T'U PËRGJIGJESH me TË GJITHË personat kur pyetet.")
    parts.append("")

    # Grupim sipas source file
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for s in suspects:
        src = s.get("_source_file", "?")
        by_file.setdefault(src, []).append(s)

    for src, items in by_file.items():
        parts.append(f"📄 Nga dokumenti: {src}")
        for s in items:
            name = s.get("name", "?")
            pos = s.get("position_hint", "") or "(pa rol të specifikuar)"
            parts.append(f"   • {name} — {pos[:120]}")
        parts.append("")

    return "\n".join(parts)


def _build_cited_precedents_block(
    db_documents: List[Dict[str, Any]],
) -> str:
    """
    V282.23: Nxjerr numrat e lëndëve të CITUAR NË DOKUMENTE (jo own).
    Injektohet në system_prompt kur përdoruesi kërkon precedentë.
    """
    from app.services.document_review.citation_extractor import extract_case_numbers

    if not db_documents:
        return ""

    cited_by_doc: Dict[str, List[str]] = {}
    for doc in db_documents:
        text = doc.get("content") or doc.get("extracted_text") or doc.get("text") or ""
        if not text.strip():
            continue
        fname = doc.get("file_name") or doc.get("title") or "?"
        cases = extract_case_numbers(text)
        cited = [c["case_number"] for c in cases if not c.get("is_likely_own")]
        if cited:
            cited_by_doc[fname] = cited

    if not cited_by_doc:
        return ""

    parts = [
        "\n\n═══════════════════════════════════════════════════════════════════════════",
        "📚 PRECEDENTË TË CITUAR NË DOKUMENTET E FASHIKULLIT",
        "═══════════════════════════════════════════════════════════════════════════",
        "",
        "⚠️ Këta numra janë CITUAR NË TEKSTIN E DOKUMENTEVE të fashikullit.",
        "NUK janë shpikje — dokumenti i referon si precedentë të Gjykatës Supreme.",
        "DUHET T'I LISTOSH në përgjigje kur përdoruesi pyet për precedentë.",
        "",
    ]
    for fname, cases in cited_by_doc.items():
        parts.append(f"📄 {fname}:")
        for cn in cases:
            parts.append(f"   • {cn}")
        parts.append("")

    return "\n".join(parts)


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info(
            f"✅ [RAG] Juristi AI Natural Client Service V282.23 Initialized "
            f"(chat model: {FAST_SEARCH_MODEL}, "
            f"judicial-docs whitelist: ON, dual-law rule: ON, query-depth: ON, "
            f"pre-verify: ON, fast-path: DIRECT, dynamic-cleaner: ON, timing: ON, "
            f"multi-law-chat: ON, global-on-demand: ON, no-fake-precedents: ON, "
            f"pure-chat: ON, query-aware-docs: ON, stemming: ON, caching: ON, "
            f"comparison: ON, timeline: ON, contradiction-scan: ON, "
            f"suspects-injection: ON, chat-history: DELEGATED)."
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
            r"\bLMD\b": "Ligji për Marrëdhëniet e Detyrimeve",
            r"\bLSHT\b": "Ligji për Shoqëritë Tregtare",
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            r"\bKPPRK\b": "Kodi i Procedurës Penale të Kosovës",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLFK\b": "Ligji për Familjen i Kosovës",
            r"\bPSRK\b": "Prokuroria Speciale e Republikës së Kosovës",
        }
        for abbr, expansion in abbreviations.items():
            cleaned = re.sub(abbr, f"{abbr} ({expansion})", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _unwrap_lines(self, text: str) -> str:
        lines = text.splitlines()
        result: List[str] = []
        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                result.append("")
                continue
            if result and result[-1]:
                prev = result[-1].rstrip()
                if prev.endswith((",", "-", "—", "–")) or (stripped and stripped[0].islower()):
                    result[-1] = prev + " " + stripped.lstrip()
                    continue
            result.append(stripped)
        return "\n".join(result)

    def _extract_gazette_info(self, raw: str) -> Optional[str]:
        m = re.search(
            r'GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS\s*/\s*Nr\.?\s*(\d+)\s*/\s*([^,\n]+)',
            raw,
            re.IGNORECASE,
        )
        if m:
            return f"Gazeta Zyrtare Nr. **{m.group(1)}** / {m.group(2).strip()}"
        return None

    def _extract_law_number_from_source(self, source: str) -> str:
        if not source:
            return ""
        m = re.search(r'(\d{2})\s*[_ ]?\s*L\s*[-_ ]?\s*(\d{2,4})', source, re.IGNORECASE)
        if m:
            return f"Ligji Nr. {m.group(1)}/L-{m.group(2)}"
        return ""

    def _is_document_header_line(self, line: str) -> bool:
        stripped = line.strip()
        if len(stripped) < 25:
            return False
        if stripped.endswith("."):
            return False
        letters = [c for c in stripped if c.isalpha()]
        if len(letters) < 15:
            return False
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio < 0.7:
            return False
        words = stripped.split()
        if len(words) < 4:
            return False
        return True

    def _is_law_header_candidate(self, line: str) -> bool:
        stripped = line.strip()
        if len(stripped) < 25:
            return False
        if stripped.endswith("."):
            return False
        letters = [c for c in stripped if c.isalpha()]
        if len(letters) < 15:
            return False
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio < 0.7:
            return False
        words = stripped.split()
        has_nr = bool(re.search(r'\bNR\.?\b', stripped, re.IGNORECASE))
        if has_nr or len(words) >= 4:
            return True
        return False

    def _is_header_continuation(self, line: str) -> bool:
        stripped = line.strip()
        if len(stripped) < 8:
            return False
        letters = [c for c in stripped if c.isalpha()]
        if len(letters) < 5:
            return False
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        return upper_ratio >= 0.8

    def _remove_repeated_headers(self, lines: List[str]) -> List[str]:
        candidates: List[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and self._is_document_header_line(stripped):
                candidates.append(stripped)

        if not candidates:
            return lines

        counts = Counter(candidates)
        repeated = {l for l, c in counts.items() if c >= 2}
        if not repeated:
            return lines

        return [l for l in lines if l.strip() not in repeated]

    def _clean_official_text(self, raw: str) -> str:
        if not raw:
            return ""
        text = raw

        text = re.sub(
            r'^.*GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*$',
            '',
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)

        lines = text.splitlines()
        lines = self._remove_repeated_headers(lines)
        text = "\n".join(lines)

        lines = text.splitlines()
        filtered: List[str] = []
        skip_next_caps = False

        for line in lines:
            stripped = line.strip()

            if skip_next_caps:
                skip_next_caps = False
                if stripped and stripped.isupper() and 5 <= len(stripped) < 100 and stripped.split():
                    continue

            if self._is_law_header_candidate(stripped):
                skip_next_caps = True
                continue

            filtered.append(line)

        text = "\n".join(filtered)

        text = self._unwrap_lines(text)

        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = re.sub(r'\n[ \t]+', '\n', text)

        return text.strip()

    def _format_direct_answer(
        self,
        verified_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]],
        pre_verify_disclaimer: str,
    ) -> str:
        parts: List[str] = []

        if pre_verify_disclaimer:
            parts.append(pre_verify_disclaimer.strip())

        for art, v in verified_articles:
            doc = v.get("matched_doc") or {}
            law_title_raw = doc.get("law_title") or art.get("law_hint", "Ligj i panjohur")
            source_file = doc.get("source", "") or ""
            page = doc.get("page")
            article_number = art.get("number", "")
            raw_body = doc.get("text_excerpt", "") or ""

            gazette_info = self._extract_gazette_info(raw_body)
            law_number = self._extract_law_number_from_source(source_file)
            clean_body = self._clean_official_text(raw_body)

            parts.append(f"## ⚖️ Neni {article_number}")
            parts.append(f"#### 📘 {law_title_raw}")

            if clean_body:
                parts.append("---")
                parts.append(clean_body)

            source_meta: List[str] = []
            if law_number:
                source_meta.append(f"**{law_number}**")
            if gazette_info:
                source_meta.append(gazette_info)
            if page is not None:
                source_meta.append(f"Faqe **{page}**")
            if source_file:
                source_meta.append(f"`{source_file}`")

            if source_meta:
                parts.append("---")
                parts.append(f"📎 **Burimi zyrtar:** " + " · ".join(source_meta))

        parts.append("---")
        parts.append(
            "*ℹ️ Teksti i mësipërm është marrë drejtpërdrejt nga baza zyrtare ligjore "
            "e Republikës së Kosovës — pa përpunim nga AI.*\n\n"
            "*💬 Për interpretim, aplikim në fashikull, ose analizë të thelluar, "
            "vazhdoni me pyetjen tuaj.*\n\n"
            "*⚖️ Verifikoni me burimin zyrtar për saktësi të plotë.*"
        )

        return "\n\n".join(parts)

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
        db_documents: List[Dict[str, Any]] = []
        case_doc = None
        c_oid = None

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

                _q1 = time.time()
                case_doc = self.db.cases.find_one({"_id": c_oid})
                logger.info(f"⏱️ [TIMING]   mongo_case_query: {time.time() - _q1:.2f}s")

                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    case_title = case_doc.get("title") or case_doc.get("case_name") or case_title

            except Exception as ex:
                logger.info(f"Could not read client case (fallback defaults): {ex}")

        _lap("load_case")

        if history is None:
            history = []

        _lap("load_history")

        from app.services import vector_store_service
        query_lower = query.lower()
        optimized_query = self._optimize_query(query)

        legal_query = extract_legal_query(query)
        _lap("extract_legal_query")

        verified_context = ""
        pre_verify_disclaimer = ""
        verified_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        ambiguous_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        missing_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

        if legal_query["is_legal_query"] and legal_query["articles"]:
            verification_results: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
            for art in legal_query["articles"]:
                v = _verify_single_article(
                    self.db,
                    art["number"],
                    art.get("paragraph"),
                    art.get("law_hint", ""),
                )
                verification_results.append((art, v))

            verified_articles = [(a, v) for a, v in verification_results if v["exists"]]
            ambiguous_articles = [
                (a, v) for a, v in verification_results
                if not v["exists"] and v.get("alternative_laws")
            ]
            missing_articles = [
                (a, v) for a, v in verification_results
                if not v["exists"] and not v.get("alternative_laws")
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
                f"🔎 [PreVerify V282.23] articles total={len(verification_results)} "
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
                    f"⏭️ [V282.23] Skip global — pyetje faktuale pa kërkesë eksplicite "
                    f"për precedentë."
                )
            should_fetch_global = False
        else:
            logger.info(
                f"🌐 [V282.23] Global search AKTIV — përdoruesi kërkoi precedentë/jurisprudencë"
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
                f"⚡ [FastPath V282.23 DIRECT] Skip LLM — return verified text directly "
                f"({len(verified_articles)} verified articles)"
            )

            direct_answer = self._format_direct_answer(verified_articles, pre_verify_disclaimer)
            yield direct_answer

            _lap("direct_total")
            return

        if case_id and self.db is not None:
            try:
                cached_docs = await _get_cached_case_docs(str(case_id))

                if cached_docs is not None:
                    db_documents = cached_docs
                    logger.info(
                        f"⚡ [Cache HIT V282.23] case_docs: {len(db_documents)} docs "
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
                    db_documents = list(self.db.documents.find(doc_filter).sort([("created_at", 1), ("_id", 1)]))
                    logger.info(f"⏱️ [TIMING]   mongo_docs_query ({len(db_documents)} docs): {time.time() - _q2:.2f}s")
                    _lap("load_docs")

                    if db_documents:
                        await _set_cached_case_docs(str(case_id), db_documents, ttl=CACHE_TTL_CASE_DOCS)
                        logger.info(f"💾 [Cache MISS V282.23] case_docs cached (TTL={CACHE_TTL_CASE_DOCS}s)")
            except Exception as ex:
                logger.info(f"Could not read client documents (fallback empty): {ex}")

        # ═══════════════════════════════════════════════════════════════════════
        # V282.23: STRUCTURAL CONTRADICTION + SUSPECTS SCAN
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
                f"⏭️ [V282.23] Skip contradiction scan — "
                f"{len(db_documents)} docs > limit {MAX_DOCS_FOR_CONTRADICTION_SCAN}"
            )

        contradictions_block = _build_contradictions_block(
            internal_contradictions,
            reported_contradictions,
        )
        suspects_block = _build_suspects_block(all_suspects)

        _lap("contradiction_scan")

        context_documents = db_documents
        if db_documents and len(db_documents) > 1:
            context_documents, was_filtered = _detect_relevant_documents(query, db_documents, max_match=3)
            if was_filtered:
                logger.info(
                    f"🎯 [V282.23] Query-aware docs: {len(context_documents)}/{len(db_documents)} "
                    f"dokumente të zgjedhura për kontekst LLM: "
                    f"{[d.get('file_name', '?') for d in context_documents]}"
                )
            else:
                logger.info(
                    f"📚 [V282.23] Pa filtrim dokumentesh — konteksti përfshin të gjitha "
                    f"{len(db_documents)} dokumentet"
                )

        # ═══════════════════════════════════════════════════════════════════════
        # V282.19: CROSS-DOC COMPARISON + TIMELINE
        # ═══════════════════════════════════════════════════════════════════════
        comparison_block = ""
        timeline_block = ""

        try:
            if user_wants_comparison(query_lower) and len(db_documents) >= 2:
                comparison_block = build_comparison_table(context_documents)
                if comparison_block:
                    logger.info(
                        f"📊 [V282.23] Tabelë krahasuese aktivizuar "
                        f"({len(comparison_block)} chars)"
                    )
        except Exception as e:
            logger.info(f"Comparison build skipped (feature opsional): {e}")

        try:
            if user_wants_timeline(query_lower) and db_documents:
                events = extract_events(db_documents, max_per_doc=15)
                timeline_block = build_timeline(events)
                if timeline_block:
                    logger.info(
                        f"📅 [V282.23] Timeline aktivizuar ({len(events)} ngjarje)"
                    )
        except Exception as e:
            logger.info(f"Timeline build skipped (feature opsional): {e}")

        # V282.23: Cited precedents (kur përdoruesi kërkon precedentë)
        cited_precedents_block = ""
        if user_wants_global:
            cited_precedents_block = _build_cited_precedents_block(db_documents)

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
        whitelist: Dict[str, Any] = {"articles": [], "articles_display": [], "laws_abbrev": [], "laws_number": [], "pairs": [], "laws_by_file": {}, "source_filter": "unknown"}

        case_docs_cache_key = _chunks_cache_key(
            str(case_id or ""),
            str(user_id or ""),
            optimized_query,
            document_ids,
        )
        case_docs = await _get_cached_chunks(case_docs_cache_key)

        if case_docs is not None:
            logger.info(
                f"⚡ [Cache HIT V282.23] vector_case: {len(case_docs)} chunks "
                f"(saved ~4s)"
            )
            _lap("vector_case")
        else:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id,
                query_text=optimized_query,
                case_context_id=case_id,
                document_ids=document_ids,
                n_results=25
            )
            _lap("vector_case")
            if case_docs:
                await _set_cached_chunks(case_docs_cache_key, case_docs, ttl=CACHE_TTL_CASE_CHUNKS)
                logger.info(f"💾 [Cache MISS V282.23] vector_case cached (TTL={CACHE_TTL_CASE_CHUNKS}s)")

        if user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            if should_fetch_global:
                global_docs = vector_store_service.query_global_knowledge_base(
                    query_text=optimized_query, n_results=15
                )
                _lap("vector_global")
            else:
                global_docs = []
                logger.info(f"⏭️ [QueryDepth] Skip global_docs (factual + document selected)")

            manifest_str, context_str, whitelist = ContextBuilder.build_with_whitelist(
                case_docs, global_docs, db_documents, context_documents
            )
            _lap("context_builder")

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor dhe Këshilltari Kryesor në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

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
            whitelist = ContextBuilder._extract_whitelist_from_case_files(db_documents)
            _lap("statutory_context")

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
                db=self.db
            )
            system_prompt = base_prompt + "\n\n" + NATURAL_COUNSEL_INSTRUCTION
            if contradictions_block:
                system_prompt += "\n\n" + contradictions_block
            if suspects_block:
                system_prompt += "\n\n" + suspects_block

        elif user_intent == "DRAFTING":
            if should_fetch_global:
                global_docs = vector_store_service.query_global_knowledge_base(
                    query_text=optimized_query, n_results=15
                )
                _lap("vector_global")
            else:
                global_docs = []
                logger.info(f"⏭️ [V282.23] Skip global_docs në DRAFTING")

            manifest_str, context_str, whitelist = ContextBuilder.build_with_whitelist(
                case_docs, global_docs, db_documents, context_documents
            )
            _lap("context_builder")

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
                case_id=case_id
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
            if should_fetch_global:
                global_docs = vector_store_service.query_global_knowledge_base(
                    query_text=optimized_query, n_results=15
                )
                _lap("vector_global")
            else:
                global_docs = []
                logger.info(f"⏭️ [V282.23] Skip global_docs (chat i thjeshtë)")

            manifest_str, context_str, whitelist = ContextBuilder.build_with_whitelist(
                case_docs, global_docs, db_documents, context_documents
            )
            _lap("context_builder")

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor dhe Këshilltari Kryesor në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

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
                f"⚠️ [V282.23] LLM dështoi. "
                f"Output: {full_generated_response[:100]}..."
            )
            _lap("total")
            return

        _lap("total")