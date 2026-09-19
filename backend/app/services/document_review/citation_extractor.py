# FILE: backend/app/services/document_review/citation_extractor.py
# PHOENIX PROTOCOL - CITATION EXTRACTOR V1.3
# V1.3: FIX KRITIK — ligji caktohet duke gjetur ligjin MË TË AFËRT (para OSE pas)
#       nenit, jo vetëm përpara. Kjo zgjidh formën shqipe "nenin 3, 6, 7... të Ligjit Nr. X".
# V1.2: FIX për is_likely_own + law position-aware (vetëm përpara — i gabuar).
# V1.1: FIX për is_likely_own.
# V1.0: Ekstraktim deterministik.

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


# ═══════════════════════════════════════════════════════════════════════════
# V1.3: LAW POSITION INDEX — gjej ligjin më të afërt (para OSE pas)
# ═══════════════════════════════════════════════════════════════════════════

MAX_LAW_DISTANCE = 200  # Sa karaktere larg mund të jetë ligji nga neni


def _build_law_position_index(text: str) -> List[Tuple[int, str]]:
    """
    V1.3: Krijon listë me (position, law_name) për të gjitha ligjet në tekst.
    Renditur sipas pozicionit.

    Prioritet:
    1. Ligje me numër + emër ("Ligjit Nr. 03/L-182 Për X Y Z") → preferohen
    2. Vetëm numrat e ligjeve ("03/L-182") → shtohen vetëm nëse nuk ka me-emër afër
    3. Akronimet ("LPK", "LMDHF") → shtohen gjithmonë
    """
    laws: List[Tuple[int, str]] = []

    # 1. Ligje me numër + emër
    for match in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        num = normalize_law_number(match.group(1))
        if not num:
            continue
        name = (match.group(2) or "").strip()
        law_str = f"{num} {name}".strip() if name else num
        laws.append((match.start(), law_str))

    # 2. Vetëm numrat (skip nëse ka me-emër brenda 30 char)
    for match in LAW_NUMBER_PATTERN.finditer(text):
        num = normalize_law_number(match.group(0))
        if not num:
            continue
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), num))

    # 3. Akronimet
    for match in ABBREV_PATTERN.finditer(text):
        abbr = match.group(1)
        if not is_valid_law_abbrev(abbr):
            continue
        laws.append((match.start(), abbr.upper()))

    laws.sort(key=lambda x: x[0])
    return laws


def _find_nearest_law(
    law_index: List[Tuple[int, str]],
    position: int,
    max_distance: int = MAX_LAW_DISTANCE,
) -> str:
    """
    V1.3: Gjej ligjin më të afërt (para OSE pas) një pozicioni.
    Preferon distancën më të vogël absolute.
    """
    if not law_index:
        return ""

    best_law = ""
    best_dist = float('inf')

    for law_pos, law_name in law_index:
        dist = abs(law_pos - position)
        if dist < best_dist and dist <= max_distance:
            best_dist = dist
            best_law = law_name

    return best_law


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT ARTICLES (sentence-aware + nearest-law)
# ═══════════════════════════════════════════════════════════════════════════

def extract_articles_with_context(text: str) -> List[Dict[str, Any]]:
    """
    V1.3: Nxjerr nenet me ligjin më të afërt (para ose pas).
    """
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
            article_num = match.group(1)
            paragraph = match.group(2)

            # Pozicioni absolut i nenit në tekst të plotë
            article_pos = sentence_start + match.start()

            # V1.3: Gjej ligjin më të afërt (para ose pas)
            law_hint = _find_nearest_law(law_index, article_pos)

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
                return citations

    return citations


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT LAW NUMBERS
# ═══════════════════════════════════════════════════════════════════════════

def extract_law_numbers(text: str) -> List[Dict[str, Any]]:
    """Nxjerr numrat e ligjeve."""
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

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT LAW NAMES
# ═══════════════════════════════════════════════════════════════════════════

def extract_law_names(text: str) -> List[Dict[str, Any]]:
    """Nxjerr emrat e ligjeve (pa numër)."""
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


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT ABBREVIATIONS
# ═══════════════════════════════════════════════════════════════════════════

def extract_abbreviations(text: str) -> List[str]:
    """Nxjerr akronimet e vlefshme të ligjeve."""
    if not text:
        return []

    abbrevs: Set[str] = set()
    for match in ABBREV_PATTERN.finditer(text):
        abbr = match.group(1)
        if is_valid_law_abbrev(abbr):
            abbrevs.add(abbr.upper())

    return sorted(abbrevs)


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT CASE NUMBERS
# ═══════════════════════════════════════════════════════════════════════════

def _is_likely_own_case(text: str, position: int, context: str) -> bool:
    """Kontrollo nëse numri i lëndës është i këtij dokumenti."""
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


def extract_case_numbers(text: str) -> List[Dict[str, Any]]:
    """Nxjerr numrat e lëndëve me klasifikim OWN/CITED."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for match in CASE_NUMBER_PATTERN.finditer(text):
        prefix = match.group(1).upper()
        num_part = match.group(2)
        raw = f"{prefix}.nr.{num_part}"
        normalized = normalize_case_number(raw)

        if normalized in seen:
            continue
        seen.add(normalized)

        position = match.start()
        context = extract_context(text, position, window=100)
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


# ═══════════════════════════════════════════════════════════════════════════
# BUILD DOCUMENT CITATION PROFILE
# ═══════════════════════════════════════════════════════════════════════════

def build_citation_profile(text: str) -> Dict[str, Any]:
    """Ndërton profilin e plotë të citimeve."""
    if not text:
        return {
            "articles": [],
            "laws_by_number": [],
            "laws_by_name": [],
            "abbreviations": [],
            "case_numbers": [],
            "own_case_numbers": [],
            "cited_case_numbers": [],
            "stats": {},
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
        "total_laws_by_number": len(laws_by_number),
        "total_laws_by_name": len(laws_by_name),
        "total_abbreviations": len(abbreviations),
        "total_case_numbers": len(case_numbers),
        "own_case_numbers": len(own_cases),
        "cited_case_numbers": len(cited_cases),
    }

    logger.info(
        f"🔬 [EXTRACTOR] Profile built: "
        f"articles={stats['total_articles']} "
        f"(with_law_hint={stats['articles_with_law_hint']}), "
        f"laws_by_number={stats['total_laws_by_number']}, "
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