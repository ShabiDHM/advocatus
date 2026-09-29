# FILE: backend/app/api/endpoints/laws_pkg/laws_dictionary.py
# PHOENIX PROTOCOL - LAWS DICTIONARY V6.2 (ZERO HARDCODING - DB-DRIVEN)
#
# V6.2: AKRONIMET nga JSON data file.
#   - Lexon `data/law_acronyms.json` (i editable)
#   - Zgjidh input-e të shkurtra (KPRK, KPPRK, LPK, etj.) në tituj kanonik
#   - NUK hardcoding në kod — të gjitha akronimet në JSON
#   - Kur user jep "KPRK", expand-o në "KODI NR. 06 L 074 KODI PENAL"
#     përpara se të kërkohet në DB
#
# V6.1: FIX G2 — _strip_alpha me diakritika.
# V6.0: RIKONSTRUKSION I PLOTË - HEQUR TË GJITHA HARDCODING.

import re
import json
import logging
from pathlib import Path
from typing import List, Any, Optional, Dict

logger = logging.getLogger(__name__)

LEGAL_KB_COLLECTION = "legal_knowledge_base"
ACRONYMS_FILE_NAME = "law_acronyms.json"


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS - STRING NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

_DIACRITIC_MAP = {
    'ë': 'e', 'Ë': 'E',
    'ç': 'c', 'Ç': 'C',
    'â': 'a', 'Â': 'A',
    'î': 'i', 'Î': 'I',
    'û': 'u', 'Û': 'U',
    'á': 'a', 'Á': 'A',
    'é': 'e', 'É': 'E',
    'í': 'i', 'Í': 'I',
    'ó': 'o', 'Ó': 'O',
    'ú': 'u', 'Ú': 'U',
}


def _normalize_diacritics(text: str) -> str:
    """Normalizon diakritikat shqipe në ASCII për matching Unicode-safe."""
    if not text:
        return ""
    result = text
    for k, v in _DIACRITIC_MAP.items():
        result = result.replace(k, v)
    return result


def _strip_alpha(s: str) -> str:
    """
    Heq hapësirat, hyphens, underscores dhe .pdf extension për matching filename.
    V6.1: NORMALIZON diakritikat PARA strip.
    """
    if not s:
        return ""
    clean = re.sub(r'\.pdf$', '', s.strip(), flags=re.IGNORECASE)
    clean = _normalize_diacritics(clean)
    return re.sub(r'[^a-zA-Z0-9]', '', clean).lower()


def _natural_sort_key(article_any: Any) -> List[int]:
    """Nxjerr numrat nga artikulli për sortim natyral."""
    article = str(article_any) if article_any is not None else "0"
    parts = re.findall(r'\d+', article)
    return [int(p) for p in parts] if parts else [0]


# ═══════════════════════════════════════════════════════════════════════════
# CASE LAW DETECTION
# ═══════════════════════════════════════════════════════════════════════════

_CASE_LAW_KEYWORDS = (
    "CASE_LAW",
    "PRAKTIK",
    "AKTGJYKMET",
    "VENDIM",
)


def _is_case_law(filename_or_title: str) -> bool:
    if not filename_or_title:
        return False
    text = _normalize_diacritics(str(filename_or_title).upper())
    return any(k in text for k in _CASE_LAW_KEYWORDS)


# Backward compatibility alias
_is_academic_file = _is_case_law


# ═══════════════════════════════════════════════════════════════════════════
# ACRONYMS REGISTRY — V6.2
# ═══════════════════════════════════════════════════════════════════════════

_ACRONYMS_CACHE: Optional[Dict[str, str]] = None


def _find_acronyms_file() -> Optional[Path]:
    """Gjen `law_acronyms.json` në disa vende të mundshme."""
    current = Path(__file__).resolve()

    for parent in [current, *current.parents]:
        for sub in ("data", "backend/data"):
            candidate = parent / sub / ACRONYMS_FILE_NAME
            if candidate.exists() and candidate.is_file():
                return candidate

    for base in (Path.cwd(), Path.cwd().parent):
        for sub in ("data", "backend/data"):
            candidate = base / sub / ACRONYMS_FILE_NAME
            if candidate.exists() and candidate.is_file():
                return candidate

    for base in (Path("/app/data"), Path("/app/backend/data")):
        candidate = base / ACRONYMS_FILE_NAME
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def _load_acronyms() -> Dict[str, str]:
    """Lexon akronimet nga JSON (cache in-memory)."""
    global _ACRONYMS_CACHE

    if _ACRONYMS_CACHE is not None:
        return _ACRONYMS_CACHE

    path = _find_acronyms_file()
    if not path:
        logger.warning(
            f"[DICTIONARY] '{ACRONYMS_FILE_NAME}' nuk u gjet — akronimet joaktive"
        )
        _ACRONYMS_CACHE = {}
        return _ACRONYMS_CACHE

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        acronyms = data.get("acronyms", {})
        if not isinstance(acronyms, dict):
            acronyms = {}

        _ACRONYMS_CACHE = acronyms
        logger.info(
            f"[DICTIONARY] Loaded {len(acronyms)} acronyms from {path}"
        )
        return acronyms
    except Exception as e:
        logger.error(f"[DICTIONARY] Acronyms load failed: {e}", exc_info=True)
        _ACRONYMS_CACHE = {}
        return _ACRONYMS_CACHE


def clear_acronyms_cache() -> None:
    """Invalidon cache-in e akronimeve (thirret pas update JSON)."""
    global _ACRONYMS_CACHE
    _ACRONYMS_CACHE = None
    logger.info("[DICTIONARY] Acronyms cache cleared")


def _expand_acronym(raw_title: str) -> Optional[str]:
    """
    V6.2: Nëse input-i është akronim i njohur, kthen expansion-in.
    Kthen None nëse nuk është akronim.
    """
    if not raw_title:
        return None

    acronyms = _load_acronyms()
    if not acronyms:
        return None

    # Normalizo input-in për matching
    normalized_input = raw_title.strip().upper()
    # Edhe pa diakritika
    normalized_ascii = _normalize_diacritics(normalized_input)

    # Provo: 1) exact match, 2) match pa diakritika
    for key, expanded in acronyms.items():
        key_upper = key.upper()
        key_ascii = _normalize_diacritics(key_upper)

        if normalized_input == key_upper:
            return expanded
        if normalized_ascii == key_ascii:
            return expanded

    return None


# ═══════════════════════════════════════════════════════════════════════════
# DB-DRIVEN TITLE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

_STOPWORDS = frozenset({
    "ligji", "ligjin", "ligjit", "kodi", "kodin", "kodit",
    "per", "për", "dhe", "ose", "nga", "me", "ne", "në",
    "te", "të", "se", "së", "nr", "neni", "nenit",
})

_CANONICAL_TITLE_CACHE: Dict[str, Optional[str]] = {}
_CACHE_MAX_SIZE = 1000


def clear_canonical_title_cache() -> None:
    _CANONICAL_TITLE_CACHE.clear()
    logger.info("[DICTIONARY] Canonical title cache cleared")


def _cache_put(key: str, value: Optional[str]) -> None:
    if len(_CANONICAL_TITLE_CACHE) >= _CACHE_MAX_SIZE:
        first_key = next(iter(_CANONICAL_TITLE_CACHE))
        del _CANONICAL_TITLE_CACHE[first_key]
    _CANONICAL_TITLE_CACHE[key] = value


def _find_canonical_title(db, raw_title: str) -> Optional[str]:
    """
    Kërkon titullin kanonik në DB duke provuar 4 strategji me prioritet:
    1. EXACT match
    2. CODE match
    3. SUBSTRING match
    4. DIAKRITIKA-NORMALIZED word match
    """
    if not raw_title or not raw_title.strip():
        return None

    title = raw_title.strip()
    cache_key = _normalize_diacritics(title.lower())

    if cache_key in _CANONICAL_TITLE_CACHE:
        return _CANONICAL_TITLE_CACHE[cache_key]

    collection = db[LEGAL_KB_COLLECTION]

    # ─── 1. EXACT MATCH ─────────────────────────────────────────────────
    doc = collection.find_one(
        {"law_title": {"$regex": f"^{re.escape(title)}$", "$options": "i"}},
        {"law_title": 1},
    )
    if doc and doc.get("law_title"):
        result = doc["law_title"]
        _cache_put(cache_key, result)
        return result

    # ─── 2. CODE MATCH ──────────────────────────────────────────────────
    code_match = re.search(
        r'\d{2,4}\s*[\/\-_\s]\s*[Ll]\s*[\/\-_\s]?\s*\d{2,4}'
        r'|'
        r'\d{4}\s*\/\s*\d{1,4}',
        title,
    )
    if code_match:
        code = code_match.group(0).strip()
        code_clean = re.sub(r'[\s\-_/]+', ' ', code)
        parts = code_clean.split()
        if len(parts) >= 2:
            flex_pattern = r'[\s\-_/]*'.join(re.escape(p) for p in parts)
            doc = collection.find_one(
                {"law_title": {"$regex": flex_pattern, "$options": "i"}},
                {"law_title": 1},
            )
            if doc and doc.get("law_title"):
                result = doc["law_title"]
                _cache_put(cache_key, result)
                return result

    # ─── 3. SUBSTRING MATCH ─────────────────────────────────────────────
    doc = collection.find_one(
        {"law_title": {"$regex": re.escape(title), "$options": "i"}},
        {"law_title": 1},
    )
    if doc and doc.get("law_title"):
        result = doc["law_title"]
        _cache_put(cache_key, result)
        return result

    # ─── 4. DIAKRITIKA-NORMALIZED WORD MATCH ────────────────────────────
    title_norm = _normalize_diacritics(title.lower())
    words = [
        w for w in re.findall(r'\w+', title_norm)
        if len(w) >= 4 and w not in _STOPWORDS
    ]

    if words:
        primary = max(words, key=len)
        candidates = collection.find(
            {"law_title": {"$regex": re.escape(primary), "$options": "i"}},
            {"law_title": 1},
        ).limit(100)

        best_match: Optional[str] = None
        best_score = 0
        min_score = max(1, len(words) // 2)

        for cand in candidates:
            cand_title = cand.get("law_title", "")
            if not cand_title:
                continue
            cand_norm = _normalize_diacritics(cand_title.lower())
            score = sum(
                1 for w in words
                if re.search(rf'\b{re.escape(w)}', cand_norm)
            )
            if score > best_score and score >= min_score:
                best_match = cand_title
                best_score = score

        if best_match:
            _cache_put(cache_key, best_match)
            return best_match

    _cache_put(cache_key, None)
    return None


def _normalize_hallucinated_title(
    raw_title: str,
    article: str = "",
    db=None,
) -> str:
    """
    V6.2: DB-driven normalizim + akronime.
    Strategjia:
    1. Nëse është akronim → expand në titull të plotë
    2. Nëse `db` ofrohet → kërko titullin kanonik
    3. Nëse DB gjen → kthe kanonik
    4. Nëse jo → kthe input e pastruar
    """
    if not raw_title:
        return ""

    title = raw_title.strip()

    # ═══ HAPI 1: Akronime (V6.2) ═══
    acronym_expansion = _expand_acronym(title)
    if acronym_expansion:
        logger.info(
            f"[DICTIONARY] Acronym resolved: '{title}' → '{acronym_expansion[:60]}...'"
        )
        title = acronym_expansion
        # Vazhdo me DB lookup me titullin e expanduar

    # ═══ HAPI 2: DB lookup ═══
    if db is not None:
        canonical = _find_canonical_title(db, title)
        if canonical:
            return canonical

    return title


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "_strip_alpha",
    "_natural_sort_key",
    "_is_case_law",
    "_is_academic_file",
    "_normalize_diacritics",
    "_normalize_hallucinated_title",
    "_find_canonical_title",
    "clear_canonical_title_cache",
    "clear_acronyms_cache",
    "_expand_acronym",
]