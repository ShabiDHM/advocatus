# FILE: backend/app/services/document_review/citation_extractor.py
# PHOENIX PROTOCOL - CITATION EXTRACTOR V1.8
# V1.8: DEDUP NENESH — nese i njejti numer neni shfaqet dy here (me paragraph
#       dhe pa paragraph), mbaj VETEM versionin me informacion te plote:
#       (1) me paragraph > pa paragraph
#       (2) me law_hint > pa law_hint
#       (3) context me i gjate > me i shkurter
#       Impakti: eliminohen dyfishimet "Neni 384 par.1 (NUK U GJET)" +
#       "Neni 384 (EKZISTON)" ne raport.
# V1.7: Skip case_numbers qe permbajne "/L-" (kode ligjesh).
# V1.6: _build_law_position_index perfshin LAW_NAME_PATTERN.

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


MAX_LAW_DISTANCE = 200


# ═══════════════════════════════════════════════════════════════════════════
# V1.3: LAW POSITION INDEX
# ═══════════════════════════════════════════════════════════════════════════

def _build_law_position_index(text: str) -> List[Tuple[int, str]]:
    laws: List[Tuple[int, str]] = []

    for match in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        num = normalize_law_number(match.group(1))
        if not num:
            continue
        name = (match.group(2) or "").strip()
        law_str = f"{num} {name}".strip() if name else num
        laws.append((match.start(), law_str))

    for match in LAW_NUMBER_PATTERN.finditer(text):
        num = normalize_law_number(match.group(0))
        if not num:
            continue
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), num))

    for match in ABBREV_PATTERN.finditer(text):
        abbr = match.group(1)
        if not is_valid_law_abbrev(abbr):
            continue
        laws.append((match.start(), abbr.upper()))

    for match in LAW_NAME_PATTERN.finditer(text):
        full_match = match.group(0).strip()
        if len(full_match) < 15:
            continue
        too_close = any(abs(pos - match.start()) < 30 for pos, _ in laws)
        if too_close:
            continue
        laws.append((match.start(), full_match))

    laws.sort(key=lambda x: x[0])
    return laws


def _find_nearest_law(
    law_index: List[Tuple[int, str]],
    position: int,
    max_distance: int = MAX_LAW_DISTANCE,
) -> str:
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
# V1.4: ARTICLE NUMBER NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# V1.8: DEDUPE BY ARTICLE NUMBER
# ═══════════════════════════════════════════════════════════════════════════

def _score_article_citation(c: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    V1.8: Score për te zgjedhur versionin me informacion te plote.
    """
    return (
        1 if c.get("paragraph") else 0,
        1 if c.get("law_hint") and c["law_hint"].strip() else 0,
        len(c.get("context", "") or ""),
    )


def _dedupe_articles_by_number(
    citations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V1.8: Dedupliko nenet e njejte (384 par.1 vs 384) → mban vetem nje version.
    Ruan rendin e pare te shfaqjes.
    """
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

        # Zgjedh me score me te larte
        if _score_article_citation(c) > _score_article_citation(by_number[num]):
            by_number[num] = c

    deduped = [by_number[n] for n in order]
    removed = len(citations) - len(deduped)
    if removed > 0:
        logger.info(
            f"🧹 [V1.8 Dedup] Hequr {removed} nene te dyfishuara "
            f"({len(citations)} → {len(deduped)})"
        )
    return deduped


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT ARTICLES
# ═══════════════════════════════════════════════════════════════════════════

def extract_articles_with_context(text: str) -> List[Dict[str, Any]]:
    """
    V1.8: Nxjerr nenet me ligjin më të afërt + dedup pas ekstraktimit.
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
            article_num_raw = match.group(1)
            paragraph_raw = match.group(2)

            article_num, paragraph = _normalize_article_number(
                article_num_raw, paragraph_raw
            )

            article_pos = sentence_start + match.start()
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
                return _dedupe_articles_by_number(citations)

    # V1.8: Dedup perpara kthimit
    return _dedupe_articles_by_number(citations)


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT LAW NUMBERS
# ═══════════════════════════════════════════════════════════════════════════

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
    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT LAW NAMES
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT ABBREVIATIONS
# ═══════════════════════════════════════════════════════════════════════════

def extract_abbreviations(text: str) -> List[str]:
    if not text:
        return []
    abbrevs: Set[str] = set()
    for match in ABBREV_PATTERN.finditer(text):
        abbr = match.group(1)
        if is_valid_law_abbrev(abbr):
            abbrevs.add(abbr.upper())
    return sorted(abbrevs)


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT CASE NUMBERS (V1.7: skip law codes)
# ═══════════════════════════════════════════════════════════════════════════

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
            logger.debug(
                f"[V1.8] Skip case_number '{normalized}' — ne fakt kod ligji"
            )
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


# ═══════════════════════════════════════════════════════════════════════════
# BUILD DOCUMENT CITATION PROFILE
# ═══════════════════════════════════════════════════════════════════════════

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
        f"🔬 [EXTRACTOR V1.8] Profile built: "
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