# FILE: backend/app/services/document_review/precedent_search.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH V1.2
# V1.2: Query builder i permiresuar:
#       - _STOP_WORDS zgjerohet me terma boilerplate ligjore (gjykata,
#         vendimi, pala, lenda, procedura, etj.) qe prodhonin query gjenerik
#         -> precedentë te palidhur.
#       - Shtuar THEMATIC_KEYWORDS whitelist per tema specifike (dhune
#         familjare, kontakt me femije, psikiatri, sekuestrim, kompensim,
#         etj.). Nese dokumenti permban terma nga whitelist -> query ndertohet
#         VETEM prej tyre (prioritet i larte).
#       - Nese nuk ka terma tematikë -> fallback ne frekuence (si V1.1).
#       - Rezultati: precedentë semantikisht relevantë OSE 0 rezultate
#         (fraza standarde) - qe eshte korrekte.
# V1.1: FIX - Atlas $vectorSearch filter hoqet (index nuk e ka 'category'
#       si filter field). Filtrohet me $match PAS vector search. Fallback:
#       batch_size(20) + limit 200 + max_time_ms(30000).
# V1.0: Kerkim semantik i precedenteve te Gjykates Supreme.

import os
import re
import math
import logging
from typing import List, Dict, Any, Optional

from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)


# ===========================================================================
# CONFIG
# ===========================================================================

PRECEDENT_SIMILARITY_THRESHOLD = float(
    os.getenv("PRECEDENT_SIMILARITY_THRESHOLD", "0.70")
)
PRECEDENT_TOP_K = int(os.getenv("PRECEDENT_TOP_K", "10"))
PRECEDENT_NUM_CANDIDATES = int(os.getenv("PRECEDENT_NUM_CANDIDATES", "300"))
PRECEDENT_ATLAS_LIMIT = int(os.getenv("PRECEDENT_ATLAS_LIMIT", "100"))
PRECEDENT_MAX_EXCERPT_CHARS = 500
PRECEDENT_FALLBACK_SCAN_LIMIT = int(
    os.getenv("PRECEDENT_FALLBACK_SCAN_LIMIT", "200")
)
PRECEDENT_FALLBACK_BATCH_SIZE = int(
    os.getenv("PRECEDENT_FALLBACK_BATCH_SIZE", "20")
)
PRECEDENT_MAX_TEXT_FOR_QUERY = 6000
PRECEDENT_MAX_THEMATIC_TERMS = 10    # V1.2
PRECEDENT_MAX_KEY_TERMS = 5          # V1.2 (ishte 8)

LEGAL_KB_COLLECTION = "legal_knowledge_base"
ATLAS_VECTOR_INDEX = "vector_index"


# ===========================================================================
# PATTERN PER NUMRAT E LENDEVE
# ===========================================================================

CASE_NO_PATTERN = re.compile(
    r'\b(?:PA1|PKR|PML|REV|KMLP|ANR|A\.NR|PZR|CP|AC|PN|KP|'
    r'A|P)\s*\.?\s*(?:nr|Nr|NR|N\.?R)\.?\s*'
    r'(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)

COVER_PAGE_TOKENS = (
    "permbledhje", "përmbledhje",
    "vendime te perzgjedhura", "vendime të përzgjedhura",
    "praktikes gjyqesore", "praktikës gjyqësore",
    "gjykates supreme", "gjykatës supreme",
    "republikes se kosoves", "republikës së kosovës",
)


# ===========================================================================
# STOP WORDS (V1.2: zgjerohet me boilerplate ligjore)
# ===========================================================================

_STOP_WORDS = {
    # ── V1.0/V1.1: bazë ──
    "i", "e", "të", "te", "së", "se", "më", "me", "në", "ne", "nga",
    "për", "per", "ndaj", "tek", "ku", "ka", "pa", "brenda", "para",
    "pas", "si", "ose", "dhe", "po", "jo", "një", "nje", "çdo", "cdo",
    "këtë", "kete", "atij", "asaj", "keta", "keto", "derisa", "nuk",
    "është", "eshte", "janë", "jane", "kanë", "kane", "ishte", "ishin",
    "që", "qe", "por", "edhe", "vetëm", "vetem", "gjithashtu", "atë",
    "ate", "kjo", "ky", "këto", "këta", "kësaj", "kesaj", "këtij",
    "ketij", "prej", "mbi", "nën", "nen", "gjatë", "gjate", "kundër",
    "kunder", "sipas", "tij", "saj", "tyre", "shume", "shumë",

    # ── V1.2: boilerplate ligjore (shkaktonin query gjenerik) ──
    "gjykata", "gjykate", "gjykates", "gjykaten", "gjykatave",
    "gjykimi", "gjykimit", "gjykim",
    "vendimi", "vendim", "vendimit", "vendimet", "vendimeve",
    "aktgjykim", "aktgjykimi", "aktgjykimit",
    "aktvendim", "aktvendimi", "aktvendimit",
    "lenda", "lendes", "lendet", "lende", "lendes",
    "pala", "pales", "palet", "pale", "palesh", "pales",
    "parashtruesi", "parashtrues", "parashtruesit",
    "themelore", "themelor", "apeli", "apelit", "apel",
    "supreme", "shkalles", "shkalle", "shkalla",
    "procedura", "procedure", "procedures", "procedural",
    "procedural", "procedurës", "procedurë",
    "kontrate", "kontrata", "kontrates", "kontratës", "kontratë",
    "dosja", "dosje", "dosjes", "fashikulli", "fashikull", "fashikullit",
    "prokurori", "prokurorit", "prokuroria", "prokuror", "prokurorisë",
    "mbrojtesi", "mbrojtesin", "mbrojtes", "mbrojtesi",
    "klienti", "klientit", "klient", "klientes",
    "avokati", "avokatit", "avokat", "avokates",
    "nisur", "bazuar", "parashtruar", "parashtruara", "parashtroi",
    "dokumenti", "dokument", "dokumentet", "dokumenteve",
    "cituar", "citohet", "referuar", "referohet",
    "ndryshuar", "ndryshon", "ndryshimin", "ndryshim",
    "shkruar", "shkruan", "theksoi", "thekson", "theksuar",
    "vendosi", "vendosur", "vendos",
    "kërkoi", "kerkoi", "kërkuar", "kerkuar", "kërkesë", "kerkese",
    "pranuar", "pranuar", "pranimit", "pranim",
    "refuzuar", "refuzimit", "refuzim",
    "shqyrtimit", "shqyrtim", "shqyrtuar",
    "shkallës", "shkallë", "shkalla",
    "gjyqtari", "gjyqtarit", "gjyqtar", "gjyqtare", "gjyqtarëve",
    "nenin", "nenit", "neneve",
    "kodi", "kodit", "kod",
    "ligji", "ligjit", "ligjet", "ligjeve", "ligj",
    "paragrafi", "paragrafit", "paragraf",
    "referuar", "përcaktuar", "percaktuar",
    "cilësuar", "cilesuar", "kualifikuar",
    "kërkuar", "kerkuar",
    "plotësuar", "plotesuar",
    "konstatuar", "konstaton", "konstatoi",
    "dëgjuar", "degjuar", "dëgjoi", "degjoi",
    "shpallur", "shpalli",
    "nisur", "nis", "filluar", "filloi",
    "bërë", "bere", "bëhet", "behet",
    "dhënë", "dhene", "jep", "jepet",
    "prishur", "prishi", "prish",
    "mbajtur", "mbajti", "mbahet",
    "paraqitur", "paraqiti", "paraqitet", "paraqit",
    "ushtruar", "ushtroi", "ushtron",
    "kundërshtuar", "kundershtuar", "kundërshtoi", "kundershtoi",
    "apeluar", "apeloi", "apelon",
    "ishin", "ish", "ishin", "kishte", "kishin", "kish",
    "mund", "mundet", "do", "duhet", "duhej",
    "gjithashtu", "prandaj", "ndaj", "sepse", "megjithatë", "megjithate",
    "ndërsa", "ndersa", "tashmë", "tashme", "më pas", "me pas",
}


# ===========================================================================
# V1.2: THEMATIC KEYWORDS WHITELIST
# ===========================================================================
# Nese dokumenti permban ndonje nga keto -> query ndertohet VETEM prej tyre.
# Ndarja sipas kategorive lehtëson mirembajtjen.

THEMATIC_KEYWORDS = [
    # ── Dhunë familjare / urdhër mbrojtjeje ──
    "dhune", "dhuna", "dhunes", "dhunës", "dhunë", "dhunshëm", "dhunshem",
    "mbrojtje", "mbrojtjes", "mbrojtjen", "mbrojtur",
    "urdher mbrojtjeje", "urdheri i mbrojtjes", "urdhrit te mbrojtjes",
    "familjare", "familjar", "familjes", "familjen", "familje",
    "bashkeshort", "bashkeshorti", "bashkeshortor", "bashkëshortore",
    "bashkeshortor", "bashkëshorti",
    "prind", "prinderore", "prinderor", "prindëror",
    "kontakt", "kontakti", "kontaktit", "kontakte",
    "vizite", "vizita", "vizitat", "vizitë",
    "femije", "femija", "femijeve", "femijet", "femijë", "femijën",
    "mitur", "mituri", "mitur", "miture", "mitur",
    "kujdestari", "kujdestaria", "kujdestar",
    "adoptim", "adoptimi", "adoptim",
    "ndarje", "ndarja", "bashkeshortore", "bashkëshortore",

    # ── Psikiatri / mjekësi / toksikologji ──
    "psikiatrike", "psikiatri", "psikiatër", "psikiatri",
    "psikologjik", "psikologjike", "psikolog",
    "diagnoze", "diagnoza", "diagnozë", "diagnozat",
    "icd", "icd-10", "icd10",
    "toksikologji", "toksikologjike", "toksikologjik",
    "narkotike", "narkotik", "narkotikë",
    "droga", "droge", "drogë",
    "alkool", "alkooli", "alkoolik", "alkoolizëm",
    "shendetesor", "shendetesore", "shëndetësor",
    "raport mjekësor", "raporti mjekësor",
    "ekspertize", "ekspertiza", "ekspertizë", "ekspertimi",

    # ── Procedurë penale ──
    "arrest", "arresti", "arrestim", "arrestimi",
    "paraburgim", "paraburgimi", "paraburguar",
    "sekuestrim", "sekuestro", "sekuestrimi", "sekuestruar", "sekuestroi",
    "kontroll", "kontrolli", "kontrolluar",
    "akuz", "akuze", "akuza", "akuzë", "akuzat", "akuzuar", "akuzuari",
    "kallzim", "kallzimi", "kallzim", "kallzuar",
    "aktakuze", "aktakuza", "aktakuzë",
    "denim", "denimi", "denuar", "denuari", "denim me",
    "vjedhje", "vjedhja", "vjedhur", "vjedh",
    "grabitje", "grabitja", "grabitur", "grabit",
    "mashtrim", "mashtrimi", "mashtruar", "mashtrues",
    "vrasje", "vrasja", "vrarë", "vrare", "vrasës",
    "krim", "krimi", "kriminal", "kriminale",
    "traffikim", "traffikimi", "traffikuar",
    "armë", "arma", "armët", "armëmbajtje",
    "kundërvajtje", "kundervajtje", "kundërvajtës",
    "fajësi", "faJesi", "fajësia", "fajtor", "fajtore",
    "pafajësi", "pafajesi", "pafajshëm", "pafajshem",

    # ── Procedurë civile / pronësi ──
    "pronesi", "pronesia", "prone", "prona", "prones",
    "pasuri", "pasuria", "pasurie", "pasuror",
    "kompensim", "kompensimi", "kompensuar", "kompensohet",
    "demi", "demit", "dëm", "dëmi", "dëmtuar", "demtuar",
    "kontest", "kontesti", "kontestimi", "kontestuar",
    "kerkespadi", "kerkespadia", "kërkesëpadi", "kërkesa padi",
    "kerkese padie", "kerkesat",
    "trashgimi", "trashgimia", "trashëgimi", "trashëguar",
    "testament", "testamenti", "testamentar",
    "hipotekë", "hipoteka", "hipotekuar",
    "qiradhënie", "qiradhenie", "qira", "qiraja",
    "shitblerje", "shitblerja", "shitur", "blerje",
    "ndërtim", "ndertim", "ndërtimi", "ndërtuar",

    # ── Të drejtat dhe procedura ──
    "shkelje", "shkelja", "shkelur", "shkel",
    "shkelje procedurale", "shkelje thelbesore", "shkelje thelbësore",
    "drejtat", "e drejta", "drejtat e njeriut", "drejtësia",
    "procedurë e rregullt", "gjykim i drejtë", "gjykim i drejte",
    "pafajësi e provuar", "e drejta për mbrojtje",
    "avokat mbrojtës", "mbrojtje ligjore",
    "ankim", "ankimi", "ankuar", "ankohet",
    "rishqyrtim", "rishqyrtimi", "rishqyrtuar",
    "revizion", "revizioni", "reviduar",
    "rikthim", "rikthimi", "rikthyer",
    "ekstradim", "ekstradimi", "ekstraduar",
    "azil", "azili", "azilkërkues",
    "shtetësi", "shtetesi", "shtetas",
    "emigracion", "emigrim", "imigrim",
]


# ===========================================================================
# QUERY BUILDER
# ===========================================================================

def _normalize_for_match(text: str) -> str:
    """Lowercase + heq diakritikat per krahasim me whitelist."""
    if not text:
        return ""
    import unicodedata
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text


def _extract_thematic_terms(
    text: str,
    max_terms: int = PRECEDENT_MAX_THEMATIC_TERMS,
) -> List[str]:
    """
    V1.2: Nxjerr termat tematikë nga whitelist.
    Kthen listen sipas radhës se shfaqjes se pare (jo frekuence), duke
    ruajtur termat origjinale (me diakritika).

    Prioritet i larte ndaj _extract_key_terms.
    """
    if not text:
        return []

    snippet = text[:PRECEDENT_MAX_TEXT_FOR_QUERY].lower()
    normalized_snippet = _normalize_for_match(snippet)

    found: List[str] = []
    seen: set = set()

    for keyword in THEMATIC_KEYWORDS:
        kw_norm = _normalize_for_match(keyword)
        if not kw_norm:
            continue
        if kw_norm in seen:
            continue
        # Kerko ne tekstin e normalizuar (pa diakritika)
        if kw_norm in normalized_snippet:
            seen.add(kw_norm)
            found.append(keyword)
            if len(found) >= max_terms:
                break

    return found


def _extract_key_terms(text: str, max_terms: int = PRECEDENT_MAX_KEY_TERMS) -> List[str]:
    """Nxjerr termat kyc me frekuence (fallback)."""
    if not text:
        return []

    snippet = text[:PRECEDENT_MAX_TEXT_FOR_QUERY]
    words = re.findall(r'\b[a-zA-ZëËçÇ]{4,}\b', snippet)

    freq: Dict[str, int] = {}
    for w in words:
        wl = w.lower()
        if wl in _STOP_WORDS:
            continue
        freq[wl] = freq.get(wl, 0) + 1

    sorted_terms = sorted(freq.items(), key=lambda x: -x[1])
    return [t for t, _ in sorted_terms[:max_terms]]


def build_precedent_query(
    document_type: str = "",
    file_name: str = "",
    doc_text: str = "",
    case_type: Optional[str] = None,
) -> str:
    """
    V1.2: Nderton query semantik per kerkim precedentesh.

    Prioritet:
      1. case_type (kontekst procedural)
      2. document_type
      3. Terma tematikë (whitelist)
      4. Fallback: terma me frekuence

    Nese ka terma tematikë -> query ndertohet VETEM prej tyre
    (dokument_type ruhet gjithashtu si kontekst).
    """
    parts: List[str] = []

    if case_type:
        ct_clean = case_type.replace("→", " ").replace("->", " ")
        ct_clean = " ".join(ct_clean.split())
        if ct_clean:
            parts.append(ct_clean)

    if document_type:
        dt = document_type.strip()
        if dt:
            parts.append(dt)

    # V1.2: Provo termat tematikë se pari
    thematic = _extract_thematic_terms(doc_text)

    if thematic:
        parts.extend(thematic)
        logger.info(
            f"🔍 [PRECEDENT] Query tematik ({len(thematic)} terma): "
            f"{thematic[:5]}..."
        )
    else:
        # Fallback: terma me frekuence
        key_terms = _extract_key_terms(doc_text)
        parts.extend(key_terms)
        logger.info(
            f"🔍 [PRECEDENT] Query frekuence (pa terma tematikë): "
            f"{key_terms[:5]}..."
        )

    query = " ".join(p for p in parts if p).strip()

    if len(query) < 15:
        query = f"Gjykata Supreme {query}".strip()

    logger.info(f"🔍 [PRECEDENT] Query final: '{query[:200]}'")
    return query


# ===========================================================================
# FILTRA
# ===========================================================================

def _is_real_case_number(case_number: str) -> bool:
    """Kontrollo nese case_number eshte numer real lende (jo kopertine)."""
    if not case_number:
        return False

    cn_lower = case_number.lower().strip()

    for token in COVER_PAGE_TOKENS:
        if token in cn_lower:
            return False

    if not re.search(r'\d', case_number):
        return False

    if len(case_number.strip()) < 4:
        return False

    return True


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _format_excerpt(text: str, max_chars: int = PRECEDENT_MAX_EXCERPT_CHARS) -> str:
    if not text:
        return ""
    clean = re.sub(r'\s+', ' ', text).strip()
    if len(clean) <= max_chars:
        return clean
    truncated = clean[:max_chars].rsplit(' ', 1)[0]
    return truncated + "..."


def _extract_real_page(doc: Dict[str, Any]) -> int:
    p = doc.get("actual_page") or doc.get("page") or 1
    try:
        return int(p)
    except (ValueError, TypeError):
        return 1


def _format_result(doc: Dict[str, Any], similarity: float) -> Dict[str, Any]:
    return {
        "case_number": str(doc.get("case_number") or doc.get("title") or "?").strip(),
        "text_excerpt": _format_excerpt(doc.get("text") or ""),
        "page": _extract_real_page(doc),
        "source": str(doc.get("source") or "?").strip(),
        "similarity": round(float(similarity), 4),
        "chunk_id": str(doc.get("chunk_id") or doc.get("_id") or "?"),
    }


# ===========================================================================
# SEARCH
# ===========================================================================

def _search_atlas(
    db,
    query_vector: List[float],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Atlas $vectorSearch PA filter, me $match pas."""
    try:
        coll = db[LEGAL_KB_COLLECTION]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": ATLAS_VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": PRECEDENT_NUM_CANDIDATES,
                    "limit": PRECEDENT_ATLAS_LIMIT,
                }
            },
            {"$addFields": {"similarity": {"$meta": "vectorSearchScore"}}},
            {
                "$match": {
                    "$or": [
                        {"category": "caselaw"},
                        {"is_case_law": True},
                    ]
                }
            },
            {"$limit": top_k * 3},
        ]
        results = list(coll.aggregate(pipeline))
        logger.info(
            f"✅ [PRECEDENT] Atlas $vectorSearch (no filter) ktheu "
            f"{len(results)} kandidate caselaw"
        )
        return results
    except Exception as e:
        logger.warning(f"⚠️ [PRECEDENT] Atlas $vectorSearch deshtoi: {e}")
        return []


def _search_fallback(
    db,
    query_vector: List[float],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Cosine manuale ne Python (batch i vogel + timeout i gjate)."""
    try:
        coll = db[LEGAL_KB_COLLECTION]
        cursor = coll.find(
            {
                "$or": [
                    {"category": "caselaw"},
                    {"is_case_law": True},
                ],
                "embedding": {"$exists": True, "$ne": []},
            },
            {
                "embedding": 1, "text": 1, "case_number": 1, "title": 1,
                "source": 1, "actual_page": 1, "page": 1, "chunk_id": 1,
                "_id": 1, "law_title": 1,
            },
        ).limit(PRECEDENT_FALLBACK_SCAN_LIMIT)

        cursor = cursor.batch_size(PRECEDENT_FALLBACK_BATCH_SIZE)
        cursor = cursor.max_time_ms(30000)

        scored: List[Dict[str, Any]] = []
        for doc in cursor:
            emb = doc.get("embedding")
            if not emb or not isinstance(emb, list):
                continue
            if len(emb) != len(query_vector):
                continue
            sim = _cosine_similarity(query_vector, emb)
            doc["similarity"] = sim
            scored.append(doc)

        scored.sort(key=lambda d: -d["similarity"])

        if scored:
            logger.info(
                f"✅ [PRECEDENT] Fallback cosine skanoi {len(scored)} chunks, "
                f"top similarity={scored[0]['similarity']:.4f}"
            )
        else:
            logger.info("ℹ️ [PRECEDENT] Fallback cosine: asnje chunk i skanueshem")
        return scored[:top_k * 3]
    except Exception as e:
        logger.error(f"❌ [PRECEDENT] Fallback cosine deshtoi: {e}")
        return []


# ===========================================================================
# PUBLIC API
# ===========================================================================

def search_relevant_precedents(
    db,
    query_text: str,
    top_k: int = PRECEDENT_TOP_K,
    threshold: float = PRECEDENT_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Kerkon precedentet me te ngjashem ne legal_knowledge_base.

    Return: liste me dict (case_number, text_excerpt, page, source, similarity, chunk_id)
    Filtrohen: similarity >= threshold, case_number real, dedup sipas case_number.
    """
    if not query_text or not query_text.strip():
        logger.warning("⚠️ [PRECEDENT] Query bosh - kthim []")
        return []

    if db is None:
        logger.error("❌ [PRECEDENT] db=None - kthim []")
        return []

    try:
        query_vector = generate_embedding(query_text)
    except Exception as e:
        logger.error(f"❌ [PRECEDENT] Embedding deshtoi: {e}")
        return []

    if not query_vector:
        logger.error("❌ [PRECEDENT] Embedding bosh - kthim []")
        return []

    candidates = _search_atlas(db, query_vector, top_k)
    used_strategy = "atlas"
    if not candidates:
        candidates = _search_fallback(db, query_vector, top_k)
        used_strategy = "fallback_cosine"

    if not candidates:
        logger.warning(
            f"⚠️ [PRECEDENT] Asnje kandidat nga DB "
            f"(strategjia={used_strategy}). Kthim []"
        )
        return []

    seen_cases: Dict[str, Dict[str, Any]] = {}

    for doc in candidates:
        sim = doc.get("similarity", 0.0)
        if sim < threshold:
            continue

        case_number = str(doc.get("case_number") or doc.get("title") or "").strip()

        if not _is_real_case_number(case_number):
            continue

        if case_number in seen_cases:
            if sim > seen_cases[case_number].get("similarity", 0):
                seen_cases[case_number] = doc
            continue
        seen_cases[case_number] = doc

    sorted_docs = sorted(
        seen_cases.values(),
        key=lambda d: -d.get("similarity", 0.0),
    )

    filtered: List[Dict[str, Any]] = []
    for doc in sorted_docs[:top_k]:
        filtered.append(_format_result(doc, doc.get("similarity", 0.0)))

    logger.info(
        f"🏛️ [PRECEDENT] Strategjia={used_strategy}, "
        f"kandidate={len(candidates)}, "
        f"pas_threshold({threshold})={len(sorted_docs)}, "
        f"final={len(filtered)}"
    )
    for i, p in enumerate(filtered, 1):
        logger.info(
            f"  {i}. [{p['case_number']}] sim={p['similarity']:.4f} "
            f"page={p['page']} chunk_id={p['chunk_id'][:12]}..."
        )

    if not filtered:
        logger.info(
            f"ℹ️ [PRECEDENT] Asnje precedent mbi threshold {threshold} - "
            f"raporti do te shkruaje frazen standarde"
        )

    return filtered


# ===========================================================================
# DIAGNOSTIKE / TEST MANUAL
# ===========================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from app.core.db import get_db

    db = get_db()

    test_query = (
        "Urdher Mbrojtjeje Procedure Penale dhune familjare femije mitur kontakt"
    )

    print(f"\n{'=' * 70}")
    print(f"TEST 1 - Query: '{test_query}'")
    print(f"Threshold: {PRECEDENT_SIMILARITY_THRESHOLD}, Top-K: {PRECEDENT_TOP_K}")
    print('=' * 70)

    results = search_relevant_precedents(db, test_query, top_k=5)
    print(f"\n>>> Rezultatet: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"\n  {i}. [{r['case_number']}] sim={r['similarity']:.4f}")
        print(f"     Burimi: {r['source']}, faqe {r['page']}")
        print(f"     Fragment: {r['text_excerpt'][:200]}...")

    # Test query builder me tekst real
    print(f"\n{'=' * 70}")
    print("TEST 2 - Query builder me tekst shembull")
    print('=' * 70)
    sample_text = """
    Gjykata Themelore ne Prishtine, ne çeshtjen e paditesit Shaban Bala
    kunder te paditurit, ka vendosur per urdher mbrojtjeje per shkak te
    dhunes familjare. Kerkesa permend kontaktin me femijen e mitur dhe
    bashkeshortin. Ekspertiza psikiatrike ka konstatuar diagnozen ICD-10.
    """
    q = build_precedent_query(
        document_type="Vendim",
        file_name="test.pdf",
        doc_text=sample_text,
    )
    print(f"  Query: '{q}'")