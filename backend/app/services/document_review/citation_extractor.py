# FILE: backend/app/services/document_review/citation_extractor.py
# PHOENIX PROTOCOL - CITATION EXTRACTOR V1.16
# V1.16: NAMED LAW PATTERNS — njoh Kushtetutën, KEDNJ, Konventa OKB si ligje.
#        FIX për mis-attribution kur nenet 24, 53, 54, 3, 6, 8, 12, 13, 19
#        caktoheshin gabimisht në KODI PENAL (fallback i heading-ut të mëparshëm).
# V1.15: MAX_LAW_DISTANCE 500 → 5000.
# V1.14: CASE-NUMBER-PREFIX EXCLUSION.
# V1.13: SUPER CLOSE AFTER — prefiks "të/i/e".
# V1.12: LEGACY LAW EXTRACTION.
# V1.11: PRECEDING LAW PRIORITY.
# V1.10: MAX_LAW_DISTANCE 500.

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional

from .constants import (
    MAX_ARTICLE_CITATIONS,
    MAX_CASE_NUMBERS,
    MAX_CONTEXT_CHARS,
)
from .patterns import (
    ARTICLE_PATTERN,
    LAW_NUMBER_PATTERN,
    LAW_NUMBER_LEGACY_PATTERN,
    LAW_NUMBER_WITH_NAME_PATTERN,
    LAW_NAME_PATTERN,
    ABBREV_PATTERN,
    CASE_NUMBER_PATTERN,
)
from .helpers import (
    is_valid_law_abbrev,
    normalize_law_number,
    normalize_case_number,
    extract_context,
    split_into_sentences,
)

logger = logging.getLogger(__name__)


# V1.15: U rrit nga 500 → 5000.
# Arsyetimi:
#   - Draftet ligjore shqipe kanë seksione me 9-18 nene nën një heading.
#   - Distanca reale heading → neni i fundit: 500-2000 chars.
#   - Me 500, fallback-i AFTER merrte ligjin e seksionit pasardhës.
#   - 5000 mbulon të gjitha rastet reale pa rrezik marrjeje nga TOC.
MAX_LAW_DISTANCE = 5000

# V1.13: Distanca maksimale për "close after"
MAX_CLOSE_AFTER_DISTANCE = 35

# V1.14: Prefikse numrash çështjesh që NUK janë ligje.
# Nga praktika gjyqësore e Kosovës: P, PML, PA, PA1, PP, PP.I, PP.II,
# Rev, KML, KM, C, CA, CML, GJ, GJK, K, KI, KŽ, etj.
CASE_NUMBER_PREFIXES: Set[str] = {
    "P", "PML", "PA", "PA1", "PA2",
    "PP", "PP1", "PP2", "PPI", "PPII",
    "REV", "KML", "KM", "K",
    "C", "CA", "CML", "CM",
    "GJ", "GJK", "KI", "KZ",
}

# V1.14: Pattern për "KPRK-së", "KPRK-t" (genitive suffix albanian)
GENITIVE_SUFFIX_PATTERN = re.compile(
    r'\b([A-ZËÇ]{3,7})[-–](?:së|s|t|të|it|in|ut|ve|vet)\b'
)


# ═══════════════════════════════════════════════════════════════════════════
# V1.16: NAMED LAW PATTERNS — ligje pa numër (Kushtetuta, KEDNJ, Konventa)
# ═══════════════════════════════════════════════════════════════════════════
#
# Pse: Draftet citojnë shpesh "Nenet 24, 53, 54 të Kushtetutës" ose
# "Nenet 6, 8, 13 të KEDNJ". Pa këto patterns, extractor-i bie fallback në
# heading-un e mëparshëm (shpesh "KODI PENAL") dhe atribuon gabimisht.
#
# Zgjidhja: Regjistro këto si ligje me emër kanonik në law_index.
#

NAMED_LAW_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r'\bKushtetut(?:a|ës|ën|e)s?(?:\s+(?:e|të|së)\s+Republikës\s+së\s+Kosovës)?\b',
            re.IGNORECASE | re.UNICODE,
        ),
        'Kushtetuta e Republikës së Kosovës',
    ),
    (
        re.compile(
            r'\bKonvent(?:a|ës|ën|e)s?\s+Evropiane\s+për\s+të\s+Drejtat\s+e\s+Njeriut\b',
            re.IGNORECASE | re.UNICODE,
        ),
        'Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)',
    ),
    (
        re.compile(r'\bKEDNJ\b', re.UNICODE),
        'Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)',
    ),
    (
        re.compile(
            r'\bKonvent(?:a|ës|ën|e)s?\s+(?:e|së)\s+OKB-së\s+për\s+të\s+Drejtat\s+e\s+Fëmijës\b',
            re.IGNORECASE | re.UNICODE,
        ),
        'Konventa e OKB-së për të Drejtat e Fëmijës',
    ),
    (
        re.compile(
            r'\bKonvent(?:a|ës|ën|e)s?\s+për\s+të\s+Drejtat\s+e\s+Fëmijës\b',
            re.IGNORECASE | re.UNICODE,
        ),
        'Konventa për të Drejtat e Fëmijës',
    ),
]


def _split_article_numbers(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r'\s*[,;]\s*|\s+dhe\s+', raw.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_case_number_prefix(abbr_upper: str, text: str, end_pos: int) -> bool:
    """
    V1.14: Kontrollo nëse akronimi i gjetur është prefiks numri çështjeje.
    Shembull: "PML" në "PML.Nr. 122/2025" → True.
    """
    # 1. Kontrollo listën e prefiksave të njohur
    if abbr_upper in CASE_NUMBER_PREFIXES:
        # Verifiko që ndiqet nga ".Nr." ose "Nr." ose " nr"
        after = text[end_pos:end_pos + 12]
        if re.match(r'^\s*\.?\s*[Nn]r\.?', after):
            return True
    return False


def _build_law_position_index(text: str) -> List[Tuple[int, str]]:
    laws: List[Tuple[int, str]] = []

    # 1. "Ligji Nr. XX/L-YYY <emri>"
    for match in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        num = normalize_law_number(match.group(1))
        if not num:
            continue
        name = (match.group(2) or "").strip()
        law_str = f"{num} {name}".strip() if name else num
        laws.append((match.start(), law_str))

    # 2. "XX/L-YYY"
    for match in LAW_NUMBER_PATTERN.finditer(text):
        num = normalize_law_number(match.group(0))
        if not num:
            continue
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), num))

    # 3. Legacy "2004/32"
    for match in LAW_NUMBER_LEGACY_PATTERN.finditer(text):
        raw = f"{match.group(1)}/{match.group(2)}"
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), raw))

    # 4. Akronime të pastra (KPRK, KPK, LPK, etj.)
    for match in ABBREV_PATTERN.finditer(text):
        abbr = match.group(1)
        if not is_valid_law_abbrev(abbr):
            continue
        abbr_upper = abbr.upper()

        # V1.14: Përjashto prefikset e numrave të çështjeve (PML, P, PA1, ...)
        if _is_case_number_prefix(abbr_upper, text, match.end()):
            logger.debug(
                f"[V1.14] Skip abbrev '{abbr}' — case number prefix"
            )
            continue

        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), abbr_upper))

    # 5. V1.14: "KPRK-së", "KPRK-t" (Albanian genitive suffix)
    for match in GENITIVE_SUFFIX_PATTERN.finditer(text):
        abbr = match.group(1)
        if not is_valid_law_abbrev(abbr):
            continue
        abbr_upper = abbr.upper()
        if _is_case_number_prefix(abbr_upper, text, match.end()):
            continue
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), abbr_upper))

    # 6. Emra të plotë ligjesh
    for match in LAW_NAME_PATTERN.finditer(text):
        full_match = match.group(0).strip()
        if len(full_match) < 15:
            continue
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), full_match))

    # V1.16: Emrat e ligjeve të njohura (Kushtetuta, KEDNJ, Konventa)
    for pattern, canonical_name in NAMED_LAW_PATTERNS:
        for match in pattern.finditer(text):
            too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
            if too_close:
                continue
            laws.append((match.start(), canonical_name))

    laws.sort(key=lambda x: x[0])
    return laws


def _find_nearest_law(
    law_index: List[Tuple[int, str]],
    position: int,
    max_distance: int = MAX_LAW_DISTANCE,
    text: str = "",
) -> str:
    """
    V1.15: Zgjidh ligjin më të afërt për një nen.

    Radha:
      0. SUPER CLOSE AFTER — ligji menjëherë pas me connector "të/i/e".
      1. Closest BEFORE (brenda max_distance = 5000).
      2. Closest AFTER (fallback vetëm nëse BEFORE mungon ose është > 5000).
    """
    if not law_index:
        return ""

    # FAZA 0 — SUPER CLOSE AFTER me connector
    following_close: List[Tuple[int, str]] = []
    for pos, name in law_index:
        if pos <= position:
            continue
        distance = pos - position
        if distance > MAX_CLOSE_AFTER_DISTANCE:
            continue
        between = text[position:pos] if text else ""
        if re.search(r'\b(të|te|i|e)\b', between, re.IGNORECASE):
            following_close.append((pos, name))

    if following_close:
        following_close.sort(key=lambda x: x[0] - position)
        chosen = following_close[0][1]
        logger.debug(f"[V1.15] Neni@{position}: SUPER CLOSE AFTER → '{chosen}'")
        return chosen

    # FAZA 1 — Closest BEFORE (me max_distance = 5000)
    preceding: List[Tuple[int, str]] = [
        (pos, name) for pos, name in law_index if pos <= position
    ]
    if preceding:
        preceding.sort(key=lambda x: position - x[0])
        best_pos, best_law = preceding[0]
        if position - best_pos <= max_distance:
            return best_law

    # FAZA 2 — Closest AFTER (fallback)
    following: List[Tuple[int, str]] = [
        (pos, name) for pos, name in law_index if pos > position
    ]
    if following:
        following.sort(key=lambda x: x[0] - position)
        best_pos, best_law = following[0]
        if best_pos - position <= max_distance:
            return best_law

    return ""


def _normalize_article_number(
    article_num: str,
    paragraph: Optional[str],
) -> Tuple[str, Optional[str]]:
    if paragraph is not None:
        return article_num, paragraph
    if "." not in article_num:
        return article_num, paragraph
    parts = article_num.split(".")
    if len(parts) != 2:
        return article_num, paragraph
    if not (parts[0].isdigit() and parts[1].isdigit()):
        return article_num, paragraph
    if not parts[0] or not parts[1]:
        return article_num, paragraph
    return parts[0], parts[1]


def _score_article_citation(c: Dict[str, Any]) -> Tuple[int, int, int]:
    return (
        1 if c.get("paragraph") else 0,
        1 if c.get("law_hint") and c["law_hint"].strip() else 0,
        len(c.get("context", "") or ""),
    )


def _dedupe_articles_by_number(
    citations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not citations:
        return citations

    by_number: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for c in citations:
        num = c.get("number", "")
        if not num:
            continue

        if num not in by_number:
            by_number[num] = c
            order.append(num)
            continue

        if _score_article_citation(c) > _score_article_citation(by_number[num]):
            by_number[num] = c

    deduped = [by_number[n] for n in order]
    removed = len(citations) - len(deduped)
    if removed > 0:
        logger.info(
            f"🧹 [V1.16 Dedup] Hequr {removed} nene te dyfishuara "
            f"({len(citations)} → {len(deduped)})"
        )
    return deduped


def extract_articles_with_context(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    law_index = _build_law_position_index(text)
    sentences = split_into_sentences(text)
    citations: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, Optional[str], str]] = set()
    current_pos = 0

    for sentence in sentences:
        sentence_start = text.find(sentence, current_pos)
        if sentence_start == -1:
            sentence_start = current_pos
        current_pos = sentence_start + len(sentence)

        for match in ARTICLE_PATTERN.finditer(sentence):
            raw_numbers = match.group(1)
            paragraph_raw = match.group(2)

            numbers = _split_article_numbers(raw_numbers)

            for article_num_raw in numbers:
                article_num, paragraph = _normalize_article_number(
                    article_num_raw, paragraph_raw
                )

                article_pos = sentence_start + match.start()
                law_hint = _find_nearest_law(
                    law_index, article_pos, text=text,
                )
                context = extract_context(sentence, match.start(), window=100)

                key = (article_num, paragraph, law_hint.lower())
                if key in seen:
                    continue
                seen.add(key)

                citations.append({
                    "number": article_num,
                    "paragraph": paragraph,
                    "law_hint": law_hint,
                    "context": context[:MAX_CONTEXT_CHARS],
                    "sentence": sentence[:500],
                    "position": article_pos,
                })

                if len(citations) >= MAX_ARTICLE_CITATIONS:
                    return _dedupe_articles_by_number(citations)

    return _dedupe_articles_by_number(citations)


def extract_law_numbers(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for match in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        num = normalize_law_number(match.group(1))
        if not num or num in seen:
            continue
        seen.add(num)
        name = (match.group(2) or "").strip()
        results.append({
            "number": num,
            "name": name,
            "context": extract_context(text, match.start(), window=80),
        })

    for match in LAW_NUMBER_PATTERN.finditer(text):
        num = normalize_law_number(match.group(0))
        if not num or num in seen:
            continue
        seen.add(num)
        results.append({
            "number": num,
            "name": "",
            "context": extract_context(text, match.start(), window=80),
        })

    for match in LAW_NUMBER_LEGACY_PATTERN.finditer(text):
        raw = f"{match.group(1)}/{match.group(2)}"
        if raw in seen:
            continue
        ctx_start = max(0, match.start() - 60)
        ctx = text[ctx_start:match.start() + 20].lower()
        if not any(k in ctx for k in ["ligj", "kodi", "nr.", "nr "]):
            continue
        seen.add(raw)
        results.append({
            "number": raw,
            "name": "",
            "context": extract_context(text, match.start(), window=80),
        })

    logger.info(
        f"🔬 [V1.16] extract_law_numbers: {len(results)} ligje"
    )
    return results


def extract_law_names(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for match in LAW_NAME_PATTERN.finditer(text):
        name = match.group(1).strip()
        if len(name) < 5:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "name": name,
            "context": extract_context(text, match.start(), window=80),
        })
    return results


def extract_abbreviations(text: str) -> List[str]:
    if not text:
        return []
    abbrevs: Set[str] = set()
    for match in ABBREV_PATTERN.finditer(text):
        abbr = match.group(1)
        abbr_upper = abbr.upper()

        # V1.14: Përjashto prefikset e numrave të çështjeve
        if _is_case_number_prefix(abbr_upper, text, match.end()):
            continue

        if is_valid_law_abbrev(abbr):
            abbrevs.add(abbr_upper)

    # V1.14: Shto "KPRK-së" etj. si akronime
    for match in GENITIVE_SUFFIX_PATTERN.finditer(text):
        abbr = match.group(1)
        abbr_upper = abbr.upper()
        if _is_case_number_prefix(abbr_upper, text, match.end()):
            continue
        if is_valid_law_abbrev(abbr):
            abbrevs.add(abbr_upper)

    return sorted(abbrevs)


def _is_likely_own_case(text: str, position: int, context: str) -> bool:
    context_lower = context.lower()
    cited_markers = [
        "mëparshëm", "meparshem", "mëparshme", "meparshme",
        "referuar", "cituar", "shih", "referohet",
        "në vendimin e", "ne vendimin e",
        "vendimi i mëparshëm",
    ]
    if any(marker in context_lower for marker in cited_markers):
        return False
    if position < 500 or position > len(text) - 500:
        return True
    return False


def _looks_like_law_code(case_number: str, context: str) -> bool:
    if "/L-" in case_number or "/l-" in case_number.lower():
        return True
    if re.search(r'\d{2}/L-\d+', case_number, re.IGNORECASE):
        return True
    return False


def extract_case_numbers(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for match in CASE_NUMBER_PATTERN.finditer(text):
        prefix = match.group(1).upper()
        num_part = match.group(2).rstrip(".,;:")
        if not num_part:
            continue
        raw = f"{prefix}.nr.{num_part}"
        normalized = normalize_case_number(raw)
        if normalized in seen:
            continue
        position = match.start()
        context = extract_context(text, position, window=100)

        if _looks_like_law_code(normalized, context):
            logger.debug(f"[V1.16] Skip case_number '{normalized}' — ne fakt kod ligji")
            continue

        seen.add(normalized)
        is_own = _is_likely_own_case(text, position, context)
        results.append({
            "case_number": normalized,
            "prefix": prefix,
            "position": position,
            "is_likely_own": is_own,
            "context": context,
        })

        if len(results) >= MAX_CASE_NUMBERS:
            break
    return results


def build_citation_profile(text: str) -> Dict[str, Any]:
    if not text:
        return {
            "articles": [], "laws_by_number": [], "laws_by_name": [],
            "abbreviations": [], "case_numbers": [],
            "own_case_numbers": [], "cited_case_numbers": [], "stats": {},
        }

    articles = extract_articles_with_context(text)
    laws_by_number = extract_law_numbers(text)
    laws_by_name = extract_law_names(text)
    abbreviations = extract_abbreviations(text)
    case_numbers = extract_case_numbers(text)

    own_cases = [c for c in case_numbers if c["is_likely_own"]]
    cited_cases = [c for c in case_numbers if not c["is_likely_own"]]

    stats = {
        "total_articles": len(articles),
        "unique_article_numbers": len(set(a["number"] for a in articles)),
        "articles_with_law_hint": sum(1 for a in articles if a["law_hint"]),
        "articles_without_law_hint": sum(1 for a in articles if not a["law_hint"]),
        "articles_with_paragraph": sum(1 for a in articles if a.get("paragraph")),
        "total_laws_by_number": len(laws_by_number),
        "total_laws_by_name": len(laws_by_name),
        "total_abbreviations": len(abbreviations),
        "total_case_numbers": len(case_numbers),
        "own_case_numbers": len(own_cases),
        "cited_case_numbers": len(cited_cases),
    }

    logger.info(
        f"🔬 [EXTRACTOR V1.16] Profile built: "
        f"articles={stats['total_articles']} "
        f"(with_law_hint={stats['articles_with_law_hint']}, "
        f"with_paragraph={stats['articles_with_paragraph']}), "
        f"laws_by_number={stats['total_laws_by_number']}, "
        f"laws_by_name={stats['total_laws_by_name']}, "
        f"abbrs={stats['total_abbreviations']}, "
        f"cases={stats['total_case_numbers']} "
        f"(own={stats['own_case_numbers']}, cited={stats['cited_case_numbers']})"
    )

    return {
        "articles": articles,
        "laws_by_number": laws_by_number,
        "laws_by_name": laws_by_name,
        "abbreviations": abbreviations,
        "case_numbers": case_numbers,
        "own_case_numbers": [c["case_number"] for c in own_cases],
        "cited_case_numbers": [c["case_number"] for c in cited_cases],
        "stats": stats,
    }