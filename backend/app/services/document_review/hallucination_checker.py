# FILE: backend/app/services/document_review/hallucination_checker.py
# PHOENIX PROTOCOL - HALLUCINATION CHECKER V1.20
# V1.20: DATE DISPLAY FORMAT — ISO (2025-01-17) → shqip (17.01.2025).
#        Shtuar _iso_to_albanian_date; _check_dates tani shfaq datat në
#        format shqip në value + message. Snippet mbetet me ISO për search.
# V1.19: SUGGESTION CONTEXT PËR TË GJITHA LLOJET — _has_real_citation_context
#        aplikohet edhe në _check_laws, _check_abbrevs, _check_cases, _check_dates.
# V1.18: ABBREV WORD BLACKLIST + EXTRA_ALLOWED_ARTICLES.
# V1.17: META-LAYER fixes (abbrev replacement patterns, law_name↔number regex).
# V1.16.1: normalizim rasash + heq KPK nga valid_std.

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

from .patterns import (
    DATE_PATTERN,
    DATE_ALBANIAN_PATTERN,
    ARTICLE_PATTERN,
    LAW_NUMBER_PATTERN,
    LAW_NUMBER_LEGACY_PATTERN,
    LAW_NUMBER_WITH_NAME_PATTERN,
    CASE_NUMBER_PATTERN,
    ABBREV_PATTERN,
)
from .helpers import (
    parse_date,
    month_name_to_number,
    normalize_law_number,
    normalize_case_number,
    is_valid_law_abbrev,
)
from .citation_extractor import _normalize_article_number

logger = logging.getLogger(__name__)


CASE_NUMBER_PREFIXES: Set[str] = {
    "PA1", "PKR", "PML", "REV", "KMLP", "ANR", "PZR",
    "CP", "AC", "PN", "KP", "ARJ", "A", "P",
    "KPK", "KPPRK", "KPRK",
}


# ═══════════════════════════════════════════════════════════════════════════
# V1.18 (F1): ABBREV WORD BLACKLIST — fjalë të zakonshme shqipe që ABBREV_PATTERN
# mund t'i kapë si akronime (të gjitha kapitale, 2-6 shkronja).
# ═══════════════════════════════════════════════════════════════════════════

COMMON_ALBANIAN_UPPERCASE_WORDS: Set[str] = {
    "PENAL", "PENALE", "PENALI", "PENALIT",
    "KODI", "KODIT", "KODIN", "KODE",
    "LIGJI", "LIGJIT", "LIGJIN", "LIGJE", "LIGJET",
    "NENI", "NENIT", "NENIN", "NENE", "NENET",
    "GJYKATA", "GJYKATËS", "GJYKATES", "GJYKATEN",
    "FAMILJE", "FAMILJEN", "FAMILJES",
    "KUSHTETUTA", "KUSHTETUTËS", "KUSHTETUTES",
    "PROCEDURA", "PROCEDURËS", "PROCEDURES", "PROCEDUREN",
    "PROKURORIA", "PROKURORISË", "PROKURORISE", "PROKURORINË",
    "APELI", "APELIT", "SUPREME", "SUPREM", "SUPREMIT",
    "KOSOVËS", "KOSOVES", "KOSOVË", "REPUBLIKA", "REPUBLIKËS",
    "REPUBLIKES", "REPUBLIKEN",
    "PARAGRAFI", "PARAGRAFIT", "PIKA", "PIKËS", "PIKES", "KREU", "KREUT",
    "DISPOZITA", "DISPOZITËS", "DISPOZITAVE",
    "PERSON", "PERSONI", "PERSONA", "PERSONAT", "PERSONAVE",
    "DHUNA", "DHUNËS", "DHUNES", "DHUNËN",
    "FËMIJA", "FEMIJA", "FËMIJËS", "FEMIJES",
    "MITUR", "MITURI", "MITURIT",
    "KALLËZIM", "KALLZIM", "KALLËZIMI",
    "KËRKESA", "KERKESA", "KËRKESË", "KERKESE", "KËRKESËN",
    "HUDHJA", "HUDHJE", "HUDHJEN",
    "AKTAKUZA", "AKTAKUZËS", "AKTAKUZEN",
    "AKTGJYKIM", "AKTGJYKIMI", "AKTVENDIM", "AKTVENDIMI",
    "VENDIM", "VENDIMI", "VENDIME", "VENDIMEVE", "VENDIMIT",
    "FAKTI", "FAKTET", "FAKTEVE",
    "PROVA", "PROVAT", "PROVAVE",
    "DOKUMENT", "DOKUMENTI", "DOKUMENTE",
    "SHQIPËRI", "SHQIPERI", "SHQIP",
    "KONVENTA", "KONVENTËS", "TRAKTATI", "TRAKTATIT",
    "ANALIZA", "ANALIZË", "ANALIZEN",
    "RAPORTI", "RAPORT", "RAPORTIM", "RAPORTIMI",
    "SEKSIONI", "SEKSION", "SEKSIONET",
    "GATI", "READY", "PUNË", "PUNE", "PUNES",
    "STATUSI", "STATUS", "STATUSIN",
    "VLERËSIMI", "VLERESIMI",
    "KOMENT", "KOMENTI",
    "KRITIKE", "OPSIONALE", "REKOMANDIM", "REKOMANDIME",
    "PËRMBLEDHJE", "PERMBLEDHJE",
    "PËRFUNDIM", "PERFUNDIM",
    "FJALË", "FJALE",
    "LËNDA", "LENDA", "LËNDE", "LENDE",
    "NUMRI", "NUMRAT",
    "DATA", "DATAT", "DATAVE",
    "ORË", "ORE",
    "SIPAS", "KONFORM",
    "ANGAZHUAR", "ORGANI", "ORGANIT",
    "EKSPERTI", "EKSPERTIZA", "EKSPERTIZE",
    "DËSHMI", "DESHMI", "DËSHMITAR", "DESHMITAR",
    "MENDIM", "MENDIMI",
    "SHKRESA", "SHKRESE",
    "ZGJIDHJE", "ZGJIDHJEN",
    "ZGJIDHUR", "ZGJIDHURA",
    "MASA", "MASAT", "MASAVE",
    "ARRESTI", "ARRESTIM", "ARRESTIMI",
    "NDALIMI", "NDALIM", "NDALIMIT",
    "DENIMI", "DENIM", "DENIMIT", "DENIME",
    "TRAJTIM", "TRAJTIMI", "TRAJTIMIT",
    "HETIM", "HETIMI", "HETIMIT", "HETIME",
    "PADIA", "PADINË", "PADI",
    "PADITËSI", "PADITESI", "PADITUR",
    "PADITURI", "PADITURIT",
    "PËRGJIGJE", "PERGJIGJE", "PËRGJIGJA",
    "ANKESA", "ANKESË", "ANKESE", "ANKESEN",
    "KËRKESËPADI", "KERKESEPADI",
    "PARASHTRESA", "PARASHTRESE",
    "PALË", "PALE", "PALËT", "PALET",
    "SHOQËRIA", "SHOQERIA",
}


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN LAW NAME ↔ NUMBER MAP
# ═══════════════════════════════════════════════════════════════════════════

KNOWN_LAW_NAME_NUMBER_MAP: Dict[str, List[str]] = {
    "kodi penal": ["06/L-074", "06L074"],
    "kodi i procedures penale": ["08/L-032", "08L032"],
    "kodi i procedures penale te kosoves": ["08/L-032", "08L032"],
    "ligji per proceduren kontestimore": ["03/L-006", "03L006"],
    "ligji per marredheniet e detyrimeve": ["04/L-077", "04L077"],
    "ligji per familjen": ["2004/32", "200432"],
    "ligji per mbrojtjen nga dhuna ne familje": [
        "03/L-182", "08/L-185", "03L182", "08L185"
    ],
    "ligji per prokurorine speciale": ["08/L-168", "08L168"],
    "ligji per mbrojtjen e femijes": ["06/L-084", "06L084"],
    "ligji i punes": ["03/L-212", "03L212"],
    "ligji per shoqerite tregtare": ["06/L-016", "06L016"],
    "ligji per gjykaten komerciale": ["08/L-015", "08L015"],
}


_LAW_NAME_WITH_NUMBER_RE = re.compile(
    r'((?:Ligj(?:i|it|in|ji)?|Kod(?:i|it|in)?)\s+'
    r'(?:(?:për|per|e|të|te|i)\s+)?'
    r'[A-Za-zëçËÇ\s\-]{4,80}?)'
    r'\s*[\(\[]?\s*(?:Nr\.?\s*)?'
    r'(\d{2,4}\s*/\s*[A-Za-z]\s*[\-–]?\s*\d{2,4}|\d{4}\s*/\s*\d{1,4})',
    re.IGNORECASE | re.UNICODE,
)


_ABBREV_REPLACEMENT_RE = re.compile(
    r'(?:[Zz]ëvendëso|[Zz]evendeso|ndrysho|kthe)\s+'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?\s+'
    r'(?:me|në|ne)\s+["\'`«“]?([A-Z]{2,6})["\'`»”]?'
    r'|'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?\s+'
    r'(?:në\s+vend\s+të|ne\s+vend\s+te|jo|→|->|=>)\s+'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?'
    r'|'
    r'(?:duhet\s+të\s+jetë|duhet\s+te\s+jete|'
    r'është\s+shkruar\s+si|eshte\s+shkruar\s+si|'
    r'gabimisht\s+shkruar\s+si|gabimisht)\s+'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?\s*'
    r'(?:\(?\s*jo\s+|\(\s*në\s+vend\s+të\s+|\(\s*ne\s+vend\s+te\s+)?'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?',
    re.UNICODE,
)


_ABBREV_WITH_LAW_NUMBER_RE = re.compile(
    r'\b([A-Z]{2,6})\b[\s\-–]*[\(\[]?\s*'
    r'(?:Nr\.?\s*)?'
    r'(\d{2,4}\s*/\s*[A-Za-z]\s*[\-–]?\s*\d{2,4})',
    re.UNICODE,
)


AMBIGUOUS_LAW_ABBREVS: Set[str] = {
    "KPK",
    "KPP",
    "KPPK",
}


_ALBANIAN_CASE_NORMALIZATIONS = [
    (r'\bligjit\b', 'ligji'),
    (r'\bligjin\b', 'ligji'),
    (r'\bligje\b', 'ligji'),
    (r'\bligjet\b', 'ligji'),
    (r'\bligjeve\b', 'ligji'),
    (r'\bligji\b', 'ligji'),
    (r'\bligj\b', 'ligji'),
    (r'\bkodin\b', 'kodi'),
    (r'\bkodet\b', 'kodi'),
    (r'\bkodit\b', 'kodi'),
    (r'\bkod\b', 'kodi'),
    (r'\bproceduren\b', 'procedure'),
    (r'\bprocedures\b', 'procedure'),
    (r'\bprocedura\b', 'procedure'),
    (r'\bprocedurat\b', 'procedure'),
    (r'\bmarredheniet\b', 'marredhenie'),
    (r'\bmarredhenie\b', 'marredhenie'),
    (r'\bdetyrimet\b', 'detyrim'),
    (r'\bdetyrimeve\b', 'detyrim'),
    (r'\bfamiljen\b', 'familje'),
    (r'\bfamiljes\b', 'familje'),
    (r'\bmbrojtjen\b', 'mbrojtje'),
    (r'\bmbrojtjes\b', 'mbrojtje'),
    (r'\bdhunen\b', 'dhune'),
    (r'\bdhunes\b', 'dhune'),
    (r'\bfemijes\b', 'femije'),
    (r'\bfemijen\b', 'femije'),
    (r'\bpunen\b', 'pune'),
    (r'\bpunes\b', 'pune'),
    (r'\bshoqerite\b', 'shoqeri'),
    (r'\bshoqerive\b', 'shoqeri'),
    (r'\btregtare\b', 'tregtar'),
    (r'\btregtareve\b', 'tregtar'),
    (r'\bgjykaten\b', 'gjykate'),
    (r'\bgjykates\b', 'gjykate'),
    (r'\bkontestimore\b', 'kontestim'),
    (r'\bpenale\b', 'penal'),
    (r'\bpenal\b', 'penal'),
    (r'\bspeciale\b', 'speci'),
    (r'\bspecial\b', 'speci'),
    (r'\bkomerciale\b', 'komer'),
    (r'\bkomercial\b', 'komer'),
]


def _normalize_law_name(name: str) -> str:
    if not name:
        return ""
    n = name.strip().lower()
    n = n.replace("ë", "e").replace("ç", "c")
    for pattern, replacement in _ALBANIAN_CASE_NORMALIZATIONS:
        n = re.sub(pattern, replacement, n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


_NORMALIZED_KNOWN_LAW_MAP: Dict[str, List[str]] = {
    _normalize_law_name(k): v for k, v in KNOWN_LAW_NAME_NUMBER_MAP.items()
}


def _normalize_law_num(num: str) -> str:
    if not num:
        return ""
    return re.sub(r'[\s]+', '', num).upper().replace('–', '-')


# ═══════════════════════════════════════════════════════════════════════════
# SUGGESTION CONTEXT
# ═══════════════════════════════════════════════════════════════════════════

SUGGESTION_CONTEXT_KEYWORDS: Tuple[str, ...] = (
    "mungon", "mungojnë", "mungesa",
    "sugjerim", "sugjerohet", "sugjeron",
    "duhet shtuar", "duhet të shtohet",
    "konsiderohet", "konsideruar",
    "rekomandohet", "rekomandim", "i rekomanduar",
    "verifikim manual", "verifikohet manualisht",
    "nuk u gjet", "nuk gjendet", "nuk ekziston",
    "mund të mungojë", "mund të mungojnë",
    "problem:",
    "është shkruar si",
    "është cituar si",
    "korrigjim", "korrigjohet", "korrigjimi",
    "në vend të", "ne vend te",
    "nuk duhet",
    "duhet të jetë", "duhet te jete",
    "rregullorja:", "rregullore:",
    "nene që mund", "nene qe mund",
    "sugjerime:", "sugjerim:",
)


def _has_real_citation_context(
    text: str,
    value: str,
    window: int = 200,
    prefixes: Tuple[str, ...] = ("",),
) -> bool:
    """
    V1.19: Kontrollon nëse vlera shfaqet në kontekst citimi REAL (jo sugjerim).
    Kthen True nëse ka të paktën një dukuri JO në kontekst sugjerimi.
    Kthen False nëse vlera nuk gjendet ose gjendet vetëm në kontekst sugjerimi.
    """
    if not text or not value:
        return False

    found_any = False

    for prefix in prefixes:
        pat = f"{prefix} {value}".strip() if prefix else value
        if not pat:
            continue
        idx = text.find(pat)
        while idx != -1:
            found_any = True
            start = max(0, idx - window)
            end = min(len(text), idx + len(pat) + window)
            ctx = text[start:end].lower()

            if not any(kw in ctx for kw in SUGGESTION_CONTEXT_KEYWORDS):
                return True

            idx = text.find(pat, idx + 1)

    if not found_any:
        return False

    return False


def _has_real_article_context(text: str, article_number: str, window: int = 200) -> bool:
    return _has_real_citation_context(
        text, article_number, window=window,
        prefixes=("Neni", "Nenit", "neni", "nenit", "NENI", "NENIT"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# V1.20: DATE FORMAT — ISO → ALBANIAN (DD.MM.YYYY)
# ═══════════════════════════════════════════════════════════════════════════

def _iso_to_albanian_date(iso_str: str) -> str:
    """
    V1.20: Konverton 2025-01-17 → 17.01.2025 (format shqip).
    Pranon edhe 2025-01-17T12:00 ose variante me hapësirë.
    Nëse nuk përputhet → kthen input-in origjinal (no-op).
    """
    if not iso_str:
        return iso_str
    s = str(iso_str).strip()
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})(.*)$', s)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}{m.group(4)}"
    return iso_str


# ═══════════════════════════════════════════════════════════════════════════
# STRICT LAW VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

_STRICT_LAW_OUTPUT_PATTERN = re.compile(
    r'^(\d{2}/L-\d+|\d{4}/\d{1,4})$'
)


def _is_valid_law_output(s: str) -> bool:
    if not s:
        return False
    return bool(_STRICT_LAW_OUTPUT_PATTERN.match(s.strip()))


def _safe_normalize_law(raw_value: str) -> Optional[str]:
    if not raw_value:
        return None
    s = str(raw_value).strip()
    if not s:
        return None

    n = normalize_law_number(s)
    if n and _is_valid_law_output(n):
        return n

    m = LAW_NUMBER_PATTERN.search(s)
    if m:
        n2 = normalize_law_number(m.group(0))
        if n2 and _is_valid_law_output(n2):
            return n2

    stripped = re.sub(
        r'^(ligj(?:it|i|ji)?|kodi)\s*(?:nr\.?\s*)?', '',
        s, flags=re.IGNORECASE,
    ).strip()
    m = LAW_NUMBER_LEGACY_PATTERN.match(stripped)
    if m:
        candidate = f"{m.group(1)}/{m.group(2)}"
        if _is_valid_law_output(candidate):
            return candidate

    return None


# ═══════════════════════════════════════════════════════════════════════════
# STRICT TITLE SCAN
# ═══════════════════════════════════════════════════════════════════════════

def _extract_law_numbers_from_title_strict(title: str) -> Set[str]:
    found: Set[str] = set()
    if not title:
        return found

    s = str(title)

    for m in LAW_NUMBER_PATTERN.finditer(s):
        n = normalize_law_number(m.group(0))
        if n and _is_valid_law_output(n):
            found.add(n)

    lower = s.lower()
    for m in LAW_NUMBER_LEGACY_PATTERN.finditer(s):
        start = max(0, m.start() - 100)
        ctx = lower[start:m.start() + 10]
        if any(k in ctx for k in ("ligj", "kodi")):
            candidate = f"{m.group(1)}/{m.group(2)}"
            if _is_valid_law_output(candidate):
                found.add(candidate)

    return found


# ═══════════════════════════════════════════════════════════════════════════
# SPLIT ARTICLE LISTS
# ═══════════════════════════════════════════════════════════════════════════

def _split_article_numbers(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r'\s*[,;]\s*|\s+dhe\s+', raw.strip())
    return [p.strip() for p in parts if p.strip()]


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZIM PRECEDENTESH
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_precedent_case(case_number: str) -> Optional[str]:
    if not case_number:
        return None
    m = CASE_NUMBER_PATTERN.search(case_number)
    if m:
        prefix = m.group(1).upper()
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            return None
        raw = f"{prefix}.nr.{num_part}"
        return normalize_case_number(raw)
    return normalize_case_number(case_number) or case_number.upper().strip()


# ═══════════════════════════════════════════════════════════════════════════
# COLLECT SUCCESSOR LAWS
# ═══════════════════════════════════════════════════════════════════════════

_EXPLICIT_LAW_NUMBER_FIELDS = ("law_number", "number", "new_law")
_LAW_TITLE_FIELDS = ("law_title", "law_name")


def _scan_dict_for_laws(d: Dict[str, Any], context_label: str) -> Set[str]:
    found: Set[str] = set()
    if not isinstance(d, dict):
        return found

    for key in _EXPLICIT_LAW_NUMBER_FIELDS:
        val = d.get(key)
        if val:
            n = _safe_normalize_law(str(val))
            if n:
                found.add(n)

    for key in _LAW_TITLE_FIELDS:
        val = d.get(key)
        if val:
            nums = _extract_law_numbers_from_title_strict(str(val))
            if nums:
                found.update(nums)

    return found


def _collect_successor_laws(verification_report: Dict[str, Any]) -> Set[str]:
    successors: Set[str] = set()
    if not verification_report:
        return successors

    top_level = verification_report.get("successor_laws") or []
    for idx, s in enumerate(top_level):
        if isinstance(s, dict):
            successors.update(_scan_dict_for_laws(s, f"successor[{idx}]"))
        elif isinstance(s, str):
            n = _safe_normalize_law(s)
            if n:
                successors.add(n)
            successors.update(_extract_law_numbers_from_title_strict(s))

    for idx, a in enumerate(verification_report.get("articles", []) or []):
        if not isinstance(a, dict):
            continue

        art_num = a.get("article_number", "?")

        law_hint = a.get("law_hint")
        if law_hint:
            n = _safe_normalize_law(str(law_hint))
            if n:
                successors.add(n)
            successors.update(_extract_law_numbers_from_title_strict(str(law_hint)))

        sr = a.get("suggested_replacement")
        if isinstance(sr, dict):
            successors.update(_scan_dict_for_laws(sr, f"art{art_num}.sr"))

        matched_doc = a.get("matched_doc")
        if isinstance(matched_doc, dict):
            successors.update(_scan_dict_for_laws(matched_doc, f"art{art_num}.md"))

        alts = a.get("alternative_laws")
        if isinstance(alts, list):
            for alt_idx, alt in enumerate(alts):
                if isinstance(alt, dict):
                    successors.update(_scan_dict_for_laws(alt, f"art{art_num}.alt{alt_idx}"))

        alt_matched = a.get("matched_document")
        if isinstance(alt_matched, dict):
            successors.update(_scan_dict_for_laws(alt_matched, f"art{art_num}.md2"))

    if successors:
        logger.info(
            f"[HALLUCINATION V1.20] Successor laws collected: {sorted(successors)}"
        )
    else:
        logger.info(f"[HALLUCINATION V1.20] No successor laws collected.")

    return successors


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTORS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_dates_iso(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in DATE_PATTERN.finditer(text):
        dt = parse_date(m.group(1), m.group(2), m.group(3))
        if dt:
            found.add(dt.isoformat()[:10])

    for m in DATE_ALBANIAN_PATTERN.finditer(text):
        month_num = month_name_to_number(m.group(2))
        if not month_num:
            continue
        dt = parse_date(m.group(1), str(month_num), m.group(3))
        if dt:
            found.add(dt.isoformat()[:10])

    return found


def _extract_articles(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in ARTICLE_PATTERN.finditer(text):
        art_raw = m.group(1)
        par_raw = m.group(2)
        parts = _split_article_numbers(art_raw)
        for part in parts:
            if not part:
                continue
            art, _ = _normalize_article_number(part, par_raw)
            if art:
                found.add(art)

    return found


def _extract_laws(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        n = normalize_law_number(m.group(1))
        if n and _is_valid_law_output(n):
            found.add(n)

    for m in LAW_NUMBER_PATTERN.finditer(text):
        n = normalize_law_number(m.group(0))
        if n and _is_valid_law_output(n):
            found.add(n)

    for m in LAW_NUMBER_LEGACY_PATTERN.finditer(text):
        candidate = f"{m.group(1)}/{m.group(2)}"
        if _is_valid_law_output(candidate):
            found.add(candidate)

    return found


def _extract_cases(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in CASE_NUMBER_PATTERN.finditer(text):
        prefix = m.group(1).upper()
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            continue
        raw = f"{prefix}.nr.{num_part}"
        n = normalize_case_number(raw)
        if n:
            found.add(n)

    return found


def _extract_abbrevs(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in ABBREV_PATTERN.finditer(text):
        abbr = m.group(1)
        abbr_up = abbr.upper()
        if abbr_up in CASE_NUMBER_PREFIXES:
            continue
        if abbr_up in COMMON_ALBANIAN_UPPERCASE_WORDS:
            continue
        if is_valid_law_abbrev(abbr):
            found.add(abbr_up)

    return found


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT SNIPPET
# ═══════════════════════════════════════════════════════════════════════════

def _find_snippet(text: str, value: str, window: int = 80) -> str:
    if not text or not value:
        return ""
    idx = text.find(value)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(value) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


# ═══════════════════════════════════════════════════════════════════════════
# CHECKER CLASS
# ═══════════════════════════════════════════════════════════════════════════

class HallucinationChecker:
    def __init__(
        self,
        citation_profile: Dict[str, Any],
        fact_profile: Dict[str, Any],
        verification_report: Dict[str, Any],
        extra_allowed_cases: Optional[Set[str]] = None,
        extra_allowed_dates: Optional[Set[str]] = None,
        extra_allowed_articles: Optional[Set[str]] = None,
    ):
        self.allowed = self._build_allowed(
            citation_profile,
            fact_profile,
            verification_report,
            extra_allowed_cases=extra_allowed_cases,
            extra_allowed_dates=extra_allowed_dates,
            extra_allowed_articles=extra_allowed_articles,
        )
        logger.info(
            f"[HALLUCINATION V1.20] Allowed values: "
            f"dates={len(self.allowed['dates_iso'])}, "
            f"laws={len(self.allowed['laws'])} ({sorted(self.allowed['laws'])}), "
            f"articles={len(self.allowed['articles'])}, "
            f"cases={len(self.allowed['cases'])}, "
            f"abbrevs={len(self.allowed['abbrevs'])}"
        )

    @staticmethod
    def _build_allowed(
        citation_profile: Dict[str, Any],
        fact_profile: Dict[str, Any],
        verification_report: Dict[str, Any],
        extra_allowed_cases: Optional[Set[str]] = None,
        extra_allowed_dates: Optional[Set[str]] = None,
        extra_allowed_articles: Optional[Set[str]] = None,
    ) -> Dict[str, Set[str]]:
        dates_iso: Set[str] = set()
        for d in fact_profile.get("dates", []) or []:
            if d.get("iso"):
                dates_iso.add(d["iso"])

        if extra_allowed_dates:
            for d in extra_allowed_dates:
                if d:
                    dates_iso.add(str(d))

        laws: Set[str] = set()

        base_laws: Set[str] = set()
        for l in citation_profile.get("laws_by_number", []) or []:
            if l.get("number"):
                n = _safe_normalize_law(str(l["number"]))
                if n:
                    base_laws.add(n)
                    laws.add(n)

        for l in verification_report.get("laws_by_number", []) or []:
            if l.get("number"):
                n = _safe_normalize_law(str(l["number"]))
                if n:
                    laws.add(n)

        successors = _collect_successor_laws(verification_report)
        laws.update(successors)

        logger.info(
            f"[HALLUCINATION V1.20] Laws: base={len(base_laws)}, "
            f"successors={len(successors)}, total={len(laws)}"
        )

        articles: Set[str] = set()
        for a in citation_profile.get("articles", []) or []:
            if a.get("number"):
                articles.add(a["number"])

        if extra_allowed_articles:
            before = len(articles)
            for a in extra_allowed_articles:
                if a:
                    articles.add(str(a).strip())
            added = len(articles) - before
            if added > 0:
                logger.info(
                    f"[HALLUCINATION V1.20] Extra allowed articles "
                    f"(from precedents): +{added} → {sorted(extra_allowed_articles)}"
                )

        cases: Set[str] = set()
        for c in citation_profile.get("case_numbers", []) or []:
            if c.get("case_number"):
                n = normalize_case_number(c["case_number"]) or c["case_number"]
                cases.add(n)

        if extra_allowed_cases:
            before = len(cases)
            for cn in extra_allowed_cases:
                if not cn:
                    continue
                norm = _normalize_precedent_case(cn)
                if norm:
                    cases.add(norm)
                cases.add(cn.upper().strip())
            added = len(cases) - before
            if added > 0:
                logger.info(
                    f"[HALLUCINATION V1.20] Extra allowed cases "
                    f"(from precedents): +{added}"
                )

        abbrevs: Set[str] = set()
        for a in citation_profile.get("abbreviations", []) or []:
            abbrevs.add(a.upper())

        return {
            "dates_iso": dates_iso,
            "laws": laws,
            "articles": articles,
            "cases": cases,
            "abbrevs": abbrevs,
        }

    # ────────────────────────────────────────────────────────────────────
    # META-LAYER CHECKS
    # ────────────────────────────────────────────────────────────────────

    def _check_law_name_number_consistency(
        self, content: str,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []

        if not content:
            return issues

        for m in _LAW_NAME_WITH_NUMBER_RE.finditer(content):
            raw_name = m.group(1).strip()
            raw_num = m.group(2).strip()

            name_norm = _normalize_law_name(raw_name)
            num_norm = _normalize_law_num(raw_num)

            matched_key = None
            for known_name in _NORMALIZED_KNOWN_LAW_MAP:
                if known_name in name_norm or name_norm in known_name:
                    matched_key = known_name
                    break

            if not matched_key:
                continue

            valid_nums = {
                _normalize_law_num(v)
                for v in _NORMALIZED_KNOWN_LAW_MAP[matched_key]
            }

            if num_norm not in valid_nums:
                snippet = _find_snippet(content, raw_num, window=80)
                issues.append({
                    "type": "law_name_number_mismatch",
                    "value": f"{raw_name} (Nr. {raw_num})",
                    "severity": "medium",
                    "message": (
                        f"Numri '{raw_num}' nuk i përket '{raw_name}'. "
                        f"Numrat e pranuar: {sorted(valid_nums)}."
                    ),
                    "snippet": snippet,
                })

        return issues

    def _check_abbreviation_replacement(
        self, content: str,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []

        if not content:
            return issues

        allowed_abbrevs = self.allowed.get("abbrevs", set())

        valid_std = {
            "KPRK", "KPPRK", "LPK", "LMD", "LMDHF",
            "LFK", "LSHT", "PSRK", "KRK", "LPTS",
        }

        for m in _ABBREV_REPLACEMENT_RE.finditer(content):
            groups = m.groups()
            from_abbr = to_abbr = None
            for i in range(0, len(groups), 2):
                if i + 1 < len(groups) and groups[i] and groups[i + 1]:
                    from_abbr = groups[i].upper().strip()
                    to_abbr = groups[i + 1].upper().strip()
                    break

            if not from_abbr or not to_abbr:
                continue
            if from_abbr == to_abbr:
                continue

            from_is_valid = (
                from_abbr in valid_std or from_abbr in allowed_abbrevs
            )
            to_is_valid = to_abbr in valid_std

            if from_is_valid and not to_is_valid:
                snippet = _find_snippet(content, m.group(0), window=80)
                issues.append({
                    "type": "invalid_abbrev_replacement",
                    "value": f"{from_abbr} → {to_abbr}",
                    "severity": "high",
                    "message": (
                        f"Rekomandim i gabuar: '{from_abbr}' është akronim "
                        f"standard i vlefshëm, ndërsa '{to_abbr}' nuk është. "
                        f"MOS e zëvendëso."
                    ),
                    "snippet": snippet,
                })

        return issues

    def _check_abbrev_multiple_laws(
        self, content: str,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []

        if not content:
            return issues

        allowed_abbrevs = self.allowed.get("abbrevs", set())
        valid_std = {
            "KPRK", "KPPRK", "LPK", "LMD", "LMDHF",
            "LFK", "LSHT", "PSRK", "KRK", "LPTS",
        }
        known_abbrevs = valid_std | set(allowed_abbrevs)

        abbr_to_nums: Dict[str, Set[str]] = {}
        for m in _ABBREV_WITH_LAW_NUMBER_RE.finditer(content):
            abbr = m.group(1).upper()
            num = _normalize_law_num(m.group(2))
            if abbr not in known_abbrevs:
                continue
            abbr_to_nums.setdefault(abbr, set()).add(num)

        for abbr, nums in abbr_to_nums.items():
            if len(nums) >= 2:
                issues.append({
                    "type": "abbrev_multiple_laws",
                    "value": f"{abbr} ↔ {sorted(nums)}",
                    "severity": "medium",
                    "message": (
                        f"Akronimi '{abbr}' lidhet me {len(nums)} numra të "
                        f"ndryshëm ligjesh: {sorted(nums)}. "
                        f"Kontrollo konsistencën."
                    ),
                    "snippet": _find_snippet(content, abbr, window=100),
                })

        return issues

    # ────────────────────────────────────────────────────────────────────
    # EXISTING CHECKS — V1.19 suggestion context + V1.20 date display
    # ────────────────────────────────────────────────────────────────────

    def _check_dates(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_dates_iso(content)
        unknown = found - self.allowed["dates_iso"]
        issues = []
        for d in sorted(unknown):
            # V1.19: skip nëse shfaqet vetëm në kontekst sugjerimi
            if not _has_real_citation_context(content, d, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.20] Skip date '{d}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            # V1.20: display në format shqip
            display_date = _iso_to_albanian_date(d)

            issues.append({
                "type": "date",
                "value": display_date,                                       # V1.20
                "severity": "high",
                "message": (
                    f"Data '{display_date}' nuk shfaqet në faktet "          # V1.20
                    f"e dokumentit."
                ),
                "snippet": _find_snippet(content, d),  # search ISO original
            })
        return issues

    def _check_articles(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_articles(content)
        unknown = found - self.allowed["articles"]
        issues = []
        for a in sorted(unknown):
            if not _has_real_article_context(content, a):
                logger.info(
                    f"[HALLUCINATION V1.20] Skip article '{a}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            issues.append({
                "type": "article", "value": f"Neni {a}", "severity": "medium",
                "message": f"Neni {a} nuk u gjet ne citimet e dokumentit.",
                "snippet": (
                    _find_snippet(content, f"Neni {a}")
                    or _find_snippet(content, f"Nenit {a}")
                ),
            })
        return issues

    def _check_laws(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_laws(content)
        unknown = found - self.allowed["laws"]
        issues = []
        for l in sorted(unknown):
            # V1.19: skip nëse shfaqet vetëm në kontekst sugjerimi
            if not _has_real_citation_context(content, l, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.20] Skip law '{l}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            issues.append({
                "type": "law", "value": l, "severity": "medium",
                "message": f"Ligji '{l}' nuk u gjet ne citimet e dokumentit.",
                "snippet": _find_snippet(content, l),
            })
        return issues

    def _check_cases(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_cases(content)
        unknown = found - self.allowed["cases"]
        issues = []
        for c in sorted(unknown):
            # V1.19: skip nëse shfaqet vetëm në kontekst sugjerimi
            if not _has_real_citation_context(content, c, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.20] Skip case '{c}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            issues.append({
                "type": "case_number", "value": c, "severity": "high",
                "message": f"Numri i lendes '{c}' nuk u gjet ne dokument.",
                "snippet": _find_snippet(content, c),
            })
        return issues

    def _check_abbrevs(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_abbrevs(content)
        unknown = found - self.allowed["abbrevs"]
        issues = []
        for a in sorted(unknown):
            # V1.19: skip nëse shfaqet vetëm në kontekst sugjerimi
            if not _has_real_citation_context(content, a, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.20] Skip abbrev '{a}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            if a in AMBIGUOUS_LAW_ABBREVS:
                severity = "medium"
                msg = (
                    f"Akronimi '{a}' është i njohur si ambigu / jo-standard. "
                    f"Përdor formën e plotë të ligjit ose akronimin standard."
                )
            else:
                severity = "low"
                msg = f"Akronimi '{a}' nuk u gjet ne citimet e dokumentit."

            issues.append({
                "type": "abbreviation", "value": a, "severity": severity,
                "message": msg,
                "snippet": _find_snippet(content, a),
            })
        return issues

    def check_section(
        self, section_key: str, content: str,
    ) -> Dict[str, Any]:
        if not content or not content.strip():
            return {
                "section_key": section_key, "status": "empty", "issues": [],
                "severity_counts": {"high": 0, "medium": 0, "low": 0},
                "counts": {
                    "dates_found": 0, "dates_unknown": 0,
                    "articles_found": 0, "articles_unknown": 0,
                    "laws_found": 0, "laws_unknown": 0,
                    "cases_found": 0, "cases_unknown": 0,
                    "abbrevs_found": 0, "abbrevs_unknown": 0,
                },
            }

        found_dates = _extract_dates_iso(content)
        found_articles = _extract_articles(content)
        found_laws = _extract_laws(content)
        found_cases = _extract_cases(content)
        found_abbrevs = _extract_abbrevs(content)

        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_dates(content))
        issues.extend(self._check_articles(content))
        issues.extend(self._check_laws(content))
        issues.extend(self._check_cases(content))
        issues.extend(self._check_abbrevs(content))
        issues.extend(self._check_law_name_number_consistency(content))
        issues.extend(self._check_abbreviation_replacement(content))
        issues.extend(self._check_abbrev_multiple_laws(content))

        high = sum(1 for i in issues if i["severity"] == "high")
        medium = sum(1 for i in issues if i["severity"] == "medium")
        low = sum(1 for i in issues if i["severity"] == "low")

        if high == 0 and medium == 0:
            status = "clean" if low == 0 else "clean_low"
        else:
            status = "suspect"

        return {
            "section_key": section_key,
            "status": status,
            "issues": issues,
            "severity_counts": {"high": high, "medium": medium, "low": low},
            "counts": {
                "dates_found": len(found_dates),
                "dates_unknown": len(found_dates - self.allowed["dates_iso"]),
                "articles_found": len(found_articles),
                "articles_unknown": len(found_articles - self.allowed["articles"]),
                "laws_found": len(found_laws),
                "laws_unknown": len(found_laws - self.allowed["laws"]),
                "cases_found": len(found_cases),
                "cases_unknown": len(found_cases - self.allowed["cases"]),
                "abbrevs_found": len(found_abbrevs),
                "abbrevs_unknown": len(found_abbrevs - self.allowed["abbrevs"]),
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL API
# ═══════════════════════════════════════════════════════════════════════════

def check_all_sections(
    sections: Dict[str, Any],
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    extra_allowed_cases: Optional[Set[str]] = None,
    extra_allowed_dates: Optional[Set[str]] = None,
    extra_allowed_articles: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    checker = HallucinationChecker(
        citation_profile, fact_profile, verification_report,
        extra_allowed_cases=extra_allowed_cases,
        extra_allowed_dates=extra_allowed_dates,
        extra_allowed_articles=extra_allowed_articles,
    )

    per_section: Dict[str, Any] = {}
    total_issues = 0
    sev_totals = {"high": 0, "medium": 0, "low": 0}
    suspicious: List[str] = []

    for key, sec in sections.items():
        content = (sec or {}).get("content", "") if isinstance(sec, dict) else ""
        report = checker.check_section(key, content)
        per_section[key] = report

        total_issues += len(report["issues"])
        for s in ("high", "medium", "low"):
            sev_totals[s] += report["severity_counts"].get(s, 0)

        for issue in report["issues"]:
            sev = issue.get("severity", "?")
            itype = issue.get("type", "?")
            ival = issue.get("value", "?")
            imsg = issue.get("message", "")
            isnip = (issue.get("snippet", "") or "")[:160]
            logger.info(
                f"[HALLUCINATION V1.20] 📌 section={key} severity={sev} "
                f"type={itype} value='{ival}'"
            )
            logger.info(f"[HALLUCINATION V1.20]    message: {imsg}")
            if isnip:
                logger.info(f"[HALLUCINATION V1.20]    snippet: {isnip}")

        if report["status"] == "suspect":
            suspicious.append(key)

    if sev_totals["high"] > 0 or sev_totals["medium"] > 0:
        global_status = "suspect"
    elif sev_totals["low"] > 0:
        global_status = "clean_low"
    else:
        global_status = "clean"

    logger.info(
        f"[HALLUCINATION V1.20] Status={global_status}, "
        f"total_issues={total_issues} "
        f"(high={sev_totals['high']}, medium={sev_totals['medium']}, "
        f"low={sev_totals['low']}), "
        f"suspicious_sections={suspicious}"
    )

    return {
        "status": global_status,
        "total_issues": total_issues,
        "severity_totals": sev_totals,
        "per_section": per_section,
        "suspicious_sections": suspicious,
    }