# FILE: backend/app/services/synthesis/canonical.py
# PHOENIX PROTOCOL - CANONICAL ENTITIES V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import re
from typing import Dict, Any, Set, List, Optional, Tuple
from difflib import SequenceMatcher

from .constants import SIMILARITY_BOOST_FIRST_WORD


# ═══════════════════════════════════════════════════════════════════════════
# TEXT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def dedup_adjacent_words(text: str) -> str:
    if not text:
        return text
    words = text.split()
    if len(words) < 2:
        return text
    result: List[str] = [words[0]]
    for i in range(1, len(words)):
        prev_lower = result[-1].lower().strip(".,;:")
        curr_lower = words[i].lower().strip(".,;:")
        if prev_lower == curr_lower:
            continue
        result.append(words[i])
    return " ".join(result)


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def similarity_with_boost(a: str, b: str) -> float:
    base = similarity(a, b)
    a_parts = a.strip().split()
    b_parts = b.strip().split()
    if a_parts and b_parts and a_parts[0].lower() == b_parts[0].lower():
        return min(1.0, base + SIMILARITY_BOOST_FIRST_WORD)
    return base


def normalize_for_match(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(
        r'\b(gjyqtari|gjyqtarja|prokurori|prokurorja|avokati|avokatja|'
        r'dr\.?|prof\.?|mr\.?|znj\.?|z\.?|m\.sc\.?)\b',
        '',
        text,
    )
    text = re.sub(r'[.,;:\(\)\[\]"\']', '', text)
    text = " ".join(text.split())
    return text.strip()


def is_known_entity(
    name: Optional[str],
    canonical: "CanonicalEntities",
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    if not name:
        return (False, None, None)
    key = name.strip().lower()
    if key in canonical.persons:
        return (True, key, canonical.persons[key])
    normalized = normalize_for_match(name)
    if normalized in canonical.persons:
        return (True, normalized, canonical.persons[normalized])
    return (False, None, None)


# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL ENTITIES
# ═══════════════════════════════════════════════════════════════════════════

class CanonicalEntities:
    def __init__(self):
        self.persons: Dict[str, Dict[str, Any]] = {}
        self.organizations: Dict[str, Dict[str, Any]] = {}
        self.case_numbers: Set[str] = set()

    def add_person(self, name, role=None, institution=None):
        if not name or len(name.strip()) < 3:
            return
        name = dedup_adjacent_words(name.strip())
        key = name.lower()
        if key not in self.persons:
            self.persons[key] = {
                "canonical": name,
                "variants": set(),
                "roles": set(),
                "institutions": set(),
            }
        entry = self.persons[key]
        entry["variants"].add(name)
        if role:
            entry["roles"].add(role.strip())
        if institution:
            entry["institutions"].add(institution.strip())

    def add_organization(self, name):
        if not name or len(name.strip()) < 3:
            return
        key = name.strip().lower()
        if key not in self.organizations:
            self.organizations[key] = {
                "canonical": name.strip(),
                "variants": set(),
            }
        self.organizations[key]["variants"].add(name.strip())

    def add_case_number(self, case_number):
        if case_number and len(case_number.strip()) >= 3:
            self.case_numbers.add(case_number.strip())

    def get_all_person_keys(self):
        return list(self.persons.keys())

    def get_person(self, key):
        return self.persons.get(key)

    def stats(self):
        return {
            "persons": len(self.persons),
            "organizations": len(self.organizations),
            "case_numbers": len(self.case_numbers),
        }