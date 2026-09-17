# FILE: backend/app/services/synthesis/post_processing.py
# PHOENIX PROTOCOL - POST PROCESSING V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import re
from typing import Any, Dict

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

def post_process_output(content: str, canonical: CanonicalEntities):
    if not content:
        return content, {
            "hallucinations_fixed": 0,
            "institutions_fixed": 0,
            "prefix_fixes": 0,
        }

    content = cleanup_placeholder_text(content)
    content, prefix_fixes = fix_prefix_duplication(content, canonical)
    content, hall_fixes = detect_and_fix_hallucinations(content, canonical)
    content, inst_fixes = verify_institutions(content, canonical)

    return content, {
        "hallucinations_fixed": hall_fixes,
        "institutions_fixed": inst_fixes,
        "prefix_fixes": prefix_fixes,
    }