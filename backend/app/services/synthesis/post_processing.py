# FILE: backend/app/services/synthesis/post_processing.py
# PHOENIX PROTOCOL - POST PROCESSING V1.1
# V1.1: Shtuar fix_misattributed_roles() — heq rreshtat si "Pala përgjegjëse:
#       Andi Bala" kur Andi është fëmijë (jo palë). Deterministik, jo-LLM.
# V1.0: Ekstraktuar nga synthesis_service.py V3.8.

import re
from typing import Any, Dict, Optional, Set

from .canonical import (
    CanonicalEntities,
    dedup_adjacent_words,
    is_known_entity,
    normalize_for_match,
    similarity_with_boost,
)
from .constants import (
    SIMILARITY_THRESHOLD,
    SIMILARITY_AMBIGUITY_GAP,
    INSTITUTION_CONTEXT_WINDOW,
)


# ═══════════════════════════════════════════════════════════════════════════
# PREFIX DUPLICATION FIX
# ═══════════════════════════════════════════════════════════════════════════

def fix_prefix_duplication(content: str, canonical: CanonicalEntities):
    if not content:
        return content, 0

    fixes_count = [0]

    pattern = re.compile(
        r'\b([A-ZËÇa-zëç]+)\s+\1\b',
        re.UNICODE | re.IGNORECASE,
    )

    def replacer(match):
        word = match.group(1)
        fixes_count[0] += 1
        return word

    for _ in range(3):
        new_content = pattern.sub(replacer, content)
        if new_content == content:
            break
        content = new_content

    return content, fixes_count[0]


# ═══════════════════════════════════════════════════════════════════════════
# V1.1: MISATTRIBUTED ROLE FIX
# ═══════════════════════════════════════════════════════════════════════════

# Role labels që indikojnë palë ndërgjyqëse
_PARTY_ROLE_PATTERNS = [
    r'pala\s+p[eë]rgjegj[eë]se',
    r'pala\s+e\s+mbrojtur',
    r'i\s+pandehuri',
    r'e\s+d[eë]mtuara',
    r'e\s+paditura',
    r'i\s+padituri',
    r'pala\s+kund[eë]rshtare',
    r'pala\s+kliente',
]

_PARTY_LINE_RE = re.compile(
    r'^(\s*[-•*]?\s*)('
    + r'|'.join(_PARTY_ROLE_PATTERNS)
    + r')(\s*:\s*)(.+?)\s*$',
    re.IGNORECASE | re.UNICODE,
)


def _normalize_simple(name: str) -> str:
    """Normalizo emrin për krahasim: lowercase + heq parenthetical + shkurtesa."""
    if not name:
        return ""
    n = re.sub(r'\([^)]*\)', '', name)
    n = re.sub(r'\s+', ' ', n)
    return n.strip().lower()


def fix_misattributed_roles(
    content: str,
    forbidden_parties: Optional[Set[str]] = None,
) -> tuple:
    """
    V1.1: Heq rreshtat që caktojnë role palësh për emra që janë fëmijë ose
    persona të tjerë që NUK janë palë ndërgjyqëse.

    Shembull i hequr:
        - Pala përgjegjëse: Andi Bala       ← Andi është fëmijë
        - Pala e mbrojtur: Elda              ← Elda është fëmijë

    Args:
        content: teksti i gjeneruar nga LLM
        forbidden_parties: set me emra (lowercase) që NUK duhet të klasifikohen
                          si palë. Bosh ose None → skip.

    Returns:
        (content, fixes_count)
    """
    if not content or not forbidden_parties:
        return content, 0

    # Normalizo emrat
    forbidden_norm: Set[str] = set()
    for fp in forbidden_parties:
        if not fp:
            continue
        forbidden_norm.add(fp.lower().strip())
        # Hiq parantezat
        clean = re.sub(r'\([^)]*\)', '', fp).strip().lower()
        if clean:
            forbidden_norm.add(clean)
        # Shto vetëm emrin e parë (për shkak "Andi Bala" vs "Andi")
        parts = clean.split()
        if parts:
            forbidden_norm.add(parts[0])

    if not forbidden_norm:
        return content, 0

    lines = content.split('\n')
    out: list = []
    fixes = 0

    for line in lines:
        m = _PARTY_LINE_RE.match(line)
        if not m:
            out.append(line)
            continue

        name_part = m.group(4).strip()
        # Nëse emri përmban emër të ndaluar → skip
        line_lower = _normalize_simple(name_part)
        if not line_lower:
            out.append(line)
            continue

        # Kontrollo tokëzim + substring
        is_forbidden = False
        for fname in forbidden_norm:
            if not fname:
                continue
            # Token match: fname si fjalë e plotë në line
            if re.search(rf'(?<!\w){re.escape(fname)}(?!\w)', line_lower):
                is_forbidden = True
                break

        if is_forbidden:
            fixes += 1
            # Skip linjën (nuk e shtojmë)
            continue

        out.append(line)

    return '\n'.join(out), fixes


# ═══════════════════════════════════════════════════════════════════════════
# HALLUCINATION FIX (names)
# ═══════════════════════════════════════════════════════════════════════════

def detect_and_fix_hallucinations(content: str, canonical: CanonicalEntities):
    if not content or not canonical.persons:
        return content, 0

    fixes_count = 0

    name_pattern = re.compile(
        r'(?<![\w])('
        r'(?:Dr\.|Prof\.|Mr\.|Znj\.|Z\.|M\.Sc\.|Gjyqtari|Gjyqtarja|'
        r'Prokurori|Prokurorja|Avokati|Avokatja)\s+'
        r')?'
        r'([A-ZËÇ][a-zëç]+(?:\s+[A-ZËÇ][a-zëç]+){1,3})'
        r'(?![\w])',
        re.UNICODE
    )

    for match in list(name_pattern.finditer(content)):
        title_prefix = match.group(1) or ""
        name_only = match.group(2).strip()

        name_deduped = dedup_adjacent_words(name_only)
        if name_deduped != name_only:
            content = content[:match.start()] + \
                f"{title_prefix}{name_deduped}" + \
                content[match.end():]
            fixes_count += 1
            continue

        is_known, _, _ = is_known_entity(name_only, canonical)
        if is_known:
            continue

        best_match_key = None
        best_score = 0.0
        second_best_score = 0.0

        normalized_input = normalize_for_match(name_only)
        if not normalized_input:
            continue

        for candidate_key in canonical.get_all_person_keys():
            score = max(
                similarity_with_boost(normalized_input, candidate_key),
                similarity_with_boost(name_only, candidate_key),
            )

            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_match_key = candidate_key
            elif score > second_best_score:
                second_best_score = score

        if best_score < SIMILARITY_THRESHOLD:
            continue

        if (best_score - second_best_score) < SIMILARITY_AMBIGUITY_GAP and second_best_score >= SIMILARITY_THRESHOLD:
            continue

        canonical_entry = canonical.get_person(best_match_key)
        if not canonical_entry:
            continue

        canonical_name = canonical_entry["canonical"]
        replacement = f"{title_prefix}{canonical_name}"

        content = content[:match.start()] + replacement + content[match.end():]
        fixes_count += 1

    return content, fixes_count


# ═══════════════════════════════════════════════════════════════════════════
# INSTITUTION VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def verify_institutions(content: str, canonical: CanonicalEntities):
    if not content or not canonical.persons:
        return content, 0

    fixes_count = 0

    for person_key, person_entry in canonical.persons.items():
        known_institutions = person_entry.get("institutions", set())
        if not known_institutions:
            continue

        canonical_name = person_entry["canonical"]
        correct_inst = next(iter(known_institutions))

        start = 0
        while True:
            idx = content.find(canonical_name, start)
            if idx == -1:
                break

            window_start = idx + len(canonical_name)
            window_end = min(len(content), window_start + INSTITUTION_CONTEXT_WINDOW)
            window = content[window_start:window_end]

            wrong_inst_found = None
            for org_key, org_entry in canonical.organizations.items():
                org_canonical = org_entry["canonical"]
                if org_canonical in window:
                    is_correct = any(
                        org_canonical.lower() in inst.lower()
                        or inst.lower() in org_canonical.lower()
                        for inst in known_institutions
                    )
                    if not is_correct:
                        wrong_inst_found = org_canonical
                        break

            if wrong_inst_found:
                wrong_pos_in_window = window.find(wrong_inst_found)
                if wrong_pos_in_window != -1:
                    abs_pos = window_start + wrong_pos_in_window
                    content = (
                        content[:abs_pos]
                        + correct_inst
                        + content[abs_pos + len(wrong_inst_found):]
                    )
                    fixes_count += 1

            start = idx + len(canonical_name)

    return content, fixes_count


# ═══════════════════════════════════════════════════════════════════════════
# PLACEHOLDER CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def cleanup_placeholder_text(content: str) -> str:
    content = re.sub(
        r'(Neni\s+\d+(?:[\.\/]\d+)*)\s*[—\-:]\s*'
        r'\[(?:[^\]]*(?:panjohur|numri|përshkrim|N\/A|i panjohur|e panjohur)[^\]]*)\]\s*',
        r'\1 ',
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r'(Neni\s+\d+(?:[\.\/]\d+)*)\s*[—\-:]\s*'
        r'\((?:[^)]*(?:panjohur|nuk dihet|pa përshkrim)[^)]*)\)\s*',
        r'\1 ',
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r'\[numri\]', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\[përshkrim\]', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\[Ligji i panjohur\]', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\[i panjohur\]', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\[e panjohur\]', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\[N\/A\]', '', content, flags=re.IGNORECASE)
    return content


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC WRAPPER
# ═══════════════════════════════════════════════════════════════════════════

def post_process_output(
    content: str,
    canonical: CanonicalEntities,
    forbidden_parties: Optional[Set[str]] = None,
):
    """
    V1.1: post-process output.
    Args:
        content: teksti i LLM
        canonical: CanonicalEntities
        forbidden_parties: emra (lowercase ose mixed case) që NUK duhet të
                          shfaqen si palë (p.sh. fëmijët).
    """
    if not content:
        return content, {
            "hallucinations_fixed": 0,
            "institutions_fixed": 0,
            "prefix_fixes": 0,
            "misattributed_roles_fixed": 0,
        }

    content = cleanup_placeholder_text(content)
    content, prefix_fixes = fix_prefix_duplication(content, canonical)
    content, hall_fixes = detect_and_fix_hallucinations(content, canonical)
    content, inst_fixes = verify_institutions(content, canonical)
    content, role_fixes = fix_misattributed_roles(content, forbidden_parties)

    return content, {
        "hallucinations_fixed": hall_fixes,
        "institutions_fixed": inst_fixes,
        "prefix_fixes": prefix_fixes,
        "misattributed_roles_fixed": role_fixes,
    }