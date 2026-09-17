# FILE: backend/app/services/albanian_ner_service.py
# PHOENIX PROTOCOL - LEGAL NER SERVICE V33.5
# FIX: DATE prompt + partial name merge + case normalization + LAWYER distinction
# EXHAUSTIVE LEGAL ENTITY EXTRACTION — CHUNK-AWARE, ZERO TRUNCATION

import re
import time
import logging
from typing import List, Tuple, Optional, Dict, Any, Callable, Set

from app.services.llm.llm_client import (
    _call_llm,
    clean_and_parse_json,
    FAST_SEARCH_MODEL,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 8000
DEFAULT_CHUNK_OVERLAP = 500
CONTEXT_WINDOW = 80
MIN_ENTITY_LENGTH = 2
MIN_CONFIDENCE = 0.35

LEGAL_ENTITY_TYPES = [
    "PARTY", "COURT", "JUDGE", "LAWYER", "PROSECUTOR",
    "CASE_NUMBER", "STATUTE", "ARTICLE", "LEGAL_ACTION",
    "EVIDENCE", "WITNESS", "DEADLINE", "CONTRACT_CLAUSE",
    "AMOUNT", "DATE", "LOCATION", "ORGANIZATION",
]

CONFLICTING_ROLES = [
    ("JUDGE", "PROSECUTOR"),
    ("JUDGE", "LAWYER"),
    ("PROSECUTOR", "LAWYER"),
    ("PARTY", "WITNESS"),
    ("JUDGE", "PARTY"),
    ("PROSECUTOR", "PARTY"),
]

ROLE_KEYWORDS = {
    "JUDGE": [
        "gjyqtar", "gjyqtare", "gjyqtari", "gjyqtarja",
        "kryetar i trupit gjykues", "kryesues", "kolegji",
        "trupi gjykues", "gjykatës",
    ],
    "PROSECUTOR": [
        "prokuror", "prokurore", "prokurori", "prokurorja",
        "kryeprokuror", "kryeprokurore", "prokuroria", "prokurorisë",
    ],
    "LAWYER": [
        "avokat", "avokate", "avokati", "avokatja",
        "mbrojtës", "mbrojtësi", "përfaqësues ligjor",
    ],
    "WITNESS": [
        "dëshmitar", "deshmitar", "dëshmitare", "deshmitare",
        "dëshmia e", "deshmia e",
    ],
    "PARTY": [
        "paditës", "padites", "i paditur", "e paditur",
        "parashtrues", "palë", "pale", "zyrtar", "i dëmtuar",
    ],
}

# Labels që përfaqësojnë persona (për case normalization)
PERSON_LABELS = {"PARTY", "JUDGE", "LAWYER", "PROSECUTOR", "WITNESS"}


# ────────────────────────────────────────────────────────────────────────────
# TITLE STRIPPING
# ────────────────────────────────────────────────────────────────────────────

ALBANIAN_TITLES = [
    "Gjyqtari", "Gjyqtarja", "Gjyqtar", "Gjyqtarë",
    "Gjyqtarin", "Gjyqtaren", "Gjyqtarit", "Gjyqtarës",
    "Prokurori", "Prokurorja", "Prokuror", "Prokurorë",
    "Prokurorin", "Prokuroren", "Prokurorit", "Prokurores",
    "Kryeprokurori", "Kryeprokurorja", "Kryeprokuror",
    "Avokati", "Avokatja", "Avokat",
    "Avokatin", "Avokaten", "Avokatit", "Avokatës",
    "Kryetari", "Kryetarja", "Kryetar",
    "Kryetarin", "Kryetaren",
    "Kryesuesi", "Kryesuesja", "Kryesues",
    "Kryesuesin", "Kryesuesen",
    "Drejtori", "Drejtorja", "Drejtor",
    "Z.", "Znj.", "Zotëri", "Zonja",
    "Dr.", "Prof.", "Mr.",
]

ALBANIAN_TITLES.sort(key=len, reverse=True)

ALBANIAN_TITLE_REGEX = re.compile(
    r'^(' + '|'.join(re.escape(t) for t in ALBANIAN_TITLES) + r')\s+',
    re.IGNORECASE,
)


def _strip_title(text: str) -> str:
    if not text:
        return text
    m = ALBANIAN_TITLE_REGEX.match(text)
    if m:
        return text[m.end():].strip()
    return text


def _normalize_entity_text(text: str) -> str:
    """Strip title + normalize whitespace + remove TRAILING punctuation only."""
    if not text:
        return ""
    text = _strip_title(text)
    # V33.5: rstrip only (mos prish thonjëzat e hapura)
    text = text.rstrip(".,;:()[]{}\"'").strip()
    text = " ".join(text.split())
    return text


def _normalize_case(text: str, label: str) -> str:
    """ALL CAPS → Title Case për persona."""
    if label in PERSON_LABELS and text.isupper() and len(text) > 3:
        return text.title()
    return text


# ────────────────────────────────────────────────────────────────────────────
# SPECIAL PATTERNS
# ────────────────────────────────────────────────────────────────────────────

ARTICLE_PATTERN = re.compile(r'^neni\s+\d+', re.IGNORECASE)
CASE_NUMBER_PATTERN = re.compile(
    r'^[A-Z]{1,5}\.?\s*nr\.?\s*\d+',
    re.IGNORECASE,
)


def _is_article_pattern(text: str) -> bool:
    return bool(ARTICLE_PATTERN.match(text))


def _is_case_number_pattern(text: str) -> bool:
    return bool(CASE_NUMBER_PATTERN.match(text))


def _is_partial_name_match(single: str, multi: str) -> bool:
    """
    Kontrollo a është 'single' (fjalë e vetme) një variant i një fjale në 'multi'.
    Trajton rasat shqipe: "Karametën" ↔ "Karameta", "Dobërdolani" ↔ "Dobërdolani".
    """
    sw = single.lower().strip()
    if len(sw) < 5 or len(single.split()) != 1:
        return False

    for word in multi.lower().split():
        if len(word) < 5:
            continue
        # Exact match
        if sw == word:
            return True
        # Albanian case variant: compare first N-2 chars (toleranca për -n, -t, -s, -a)
        compare = min(len(sw), len(word)) - 2
        if compare >= 5 and sw[:compare] == word[:compare]:
            return True
    return False


# ────────────────────────────────────────────────────────────────────────────
# PROMPT
# ────────────────────────────────────────────────────────────────────────────

LEGAL_ENTITY_PROMPT_BASE = f"""Ti je "Specialist i Njohjes së Entiteteve Ligjore" për Republikën e Kosovës.

DETYRA: Nxirr ÇDO entitet ligjor nga teksti i dhënë. Mos anashkalo asnjë.

TIPET E ENTITETEVE (label):
{chr(10).join(f"- {t}" for t in LEGAL_ENTITY_TYPES)}

RREGULLA STRIKTE:
1. Nxirr ÇDO instancë — edhe nëse i njëjti emër shfaqet shumë herë.
2. NUK përfshi titujt në emër:
   - "Gjyqtari Bujar Dobërdolani" → text="Bujar Dobërdolani"
   - "Prokurorja Fikrije Sylejmani" → text="Fikrije Sylejmani"
   - "Dr. Samire Braina" → text="Samire Braina"
3. Përfshi "context" — 80 karaktere përpara dhe pas entitetit.
4. Përfshi "confidence" — 0.0 deri 1.0.
5. Kthe VETËM JSON të vlefshëm.

⚠️  RREGULLA E DETYRUESHME PËR DATAT (DATE):
- Nxirr ÇDO datë në format DD.MM.YYYY ose DD/MM/YYYY ose "15 mars 2026".
- Shembuj: "14.02.2024", "01.02.2024", "17.01.2024", "15 mars 2026".
- Nxirr TË GJITHA datat — edhe në lista kronologjike me 10+ data.
- Nëse teksti ka "17.01.2024", "18.01.2024", "19.01.2024", nxirr të tre veçmas.
- MOS anashkalo datat edhe nëse janë shumë.

⚠️  KUFIZIM KRITIK I ROLEVE:
- I njëjti person NUK MUND të jetë njëkohësisht JUDGE dhe PROSECUTOR.
- I njëjti person NUK MUND të jetë njëkohësisht PARTY dhe WITNESS.
- Përcakto rolin VETËM nga titulli në kontekst:
    * "gjyqtar/gjyqtare", "kryesues" → JUDGE
    * "prokuror/prokurore" → PROSECUTOR
    * "avokat/avokate", "mbrojtës", "përfaqësues ligjor" → LAWYER
    * "dëshmitar" → WITNESS
    * "paditës", "i paditur", "parashtrues", "zyrtar" → PARTY

⚠️  RREGULLA PËR LAWYER:
- LAWYER = person me titull "avokat", "avokate", "mbrojtës", "përfaqësues ligjor".
- MOS klasifiko si LAWYER personat mjekësorë (mjekë, psikiatër, psikologë).
- Ekspertët mjekësorë (edhe pse të caktuar nga gjykata) → WITNESS, jo LAWYER.

⚠️  RREGULLA PËR NENET DHE NUMRAT E LËNDËS:
- "Neni 78", "Neni 78 i KPRK-së" → ARTICLE (JO STATUTE)
- "C.nr. 385/24", "PML.Nr. 185/2025", "PP.II.nr. 122/24F" → CASE_NUMBER (JO STATUTE)
- "Ligji Nr. 08/L-168", "KPPRK Nr. 08/L-032" → STATUTE

FORMATI I DALJES:
{{
  "entities": [
    {{
      "text": "emri pa titull",
      "label": "PARTY",
      "confidence": 0.95,
      "context": "80 chars around the entity"
    }}
  ]
}}

Nëse nuk gjen entitete, kthe: {{"entities": []}}
"""


def _build_prompt(document_type: Optional[str] = None) -> str:
    if not document_type:
        return LEGAL_ENTITY_PROMPT_BASE

    dtype_lower = document_type.lower()
    hint = ""

    if ("kallëzim" in dtype_lower or "kallzim" in dtype_lower
            or "aktakuzë" in dtype_lower or "aktakuze" in dtype_lower
            or "penale" in dtype_lower):
        hint = (
            "\n⚠️  KONTEKST DOKUMENTI: KALLËZIM PENAL / AKTAKUZË.\n"
            "- PROKURORËT janë figura kryesore.\n"
            "- GJYQTARËT mund të përmenden në lidhje me procedura.\n"
            "- AVOKATËT (mbrojtës) duhen nxjerrë si LAWYER.\n"
            "- Mjekët/psikiatrit ekspertë → WITNESS.\n"
        )
    elif "aktgjykim" in dtype_lower or "aktvendim" in dtype_lower or "vendim" in dtype_lower:
        hint = (
            "\n⚠️  KONTEKST DOKUMENTI: AKTGJYKIM / AKTVENDIM.\n"
            "- GJYQTARËT janë figura kryesore.\n"
        )
    elif "padi" in dtype_lower or "kërkesëpadi" in dtype_lower or "kerkesepadi" in dtype_lower:
        hint = (
            "\n⚠️  KONTEKST DOKUMENTI: PADI / KËRKESËPADI.\n"
            "- PALËT dhe AVOKATËT janë figura kryesore.\n"
        )
    elif "ankesë" in dtype_lower or "ankese" in dtype_lower:
        hint = (
            "\n⚠️  KONTEKST DOKUMENTI: ANKESË / MJET JURIDIK.\n"
            "- AVOKATËT dhe PALËT janë figura kryesore.\n"
        )

    return LEGAL_ENTITY_PROMPT_BASE + hint


# ────────────────────────────────────────────────────────────────────────────
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class AlbanianNERService:
    """
    V33.5 — Përmirësime:
    - Prompt: DATE eksplicite + LAWYER vs medical expert.
    - `_merge_partial_names()` — bashkon emra të pjesshëm.
    - `_normalize_case()` — ALL CAPS → Title Case për persona.
    - Fix: `.strip()` → `.rstrip()` për pikësim.
    """

    def __init__(self):
        self.chunk_size = DEFAULT_CHUNK_SIZE
        self.chunk_overlap = DEFAULT_CHUNK_OVERLAP

        self._local_patterns = {
            "CASE_NUMBER": re.compile(
                r'\b(?:[A-Z]{1,4}\.?\s*nr\.?\s*[\w\-\/\.]+|Nr\.?\s*[\w\-\/\.]+)',
                re.IGNORECASE
            ),
            "STATUTE": re.compile(
                r'\b(?:LMD|LPK|KPRK|KPPRK|LSHT|LFK|Ligji\s+për\s+[\w\s]+|Kushtetuta)\b',
                re.IGNORECASE
            ),
            "ARTICLE": re.compile(
                r'\bneni\s+\d+(?:[\.\/]\d+)*',
                re.IGNORECASE
            ),
            "AMOUNT": re.compile(
                r'\b\d{1,3}(?:[\.\s]\d{3})*(?:,\d{2})?\s*(?:€|EUR|euro)\b',
                re.IGNORECASE
            ),
            "DATE": re.compile(
                r'\b\d{1,2}\.\d{1,2}\.\d{4}\b|\b\d{1,2}\s+(?:Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s+\d{4}\b',
                re.IGNORECASE
            ),
            "COURT": re.compile(
                r'\bGjykata\s+(?:Themelore|Komerciale|e Apelit|Supreme|Kushtetuese)\s+(?:e|në)\s+[\w\s]+',
                re.IGNORECASE
            ),
        }

        logger.info(
            f"✅ [NER] Legal NER Service V33.5 Initialized "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap}, "
            f"partial_name_merge=ON, date_prompt=ON)"
        )

    # ────────────────────────────────────────────────────────────────────
    # CHUNKING
    # ────────────────────────────────────────────────────────────────────

    def _chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[Tuple[str, int, int]]:
        if not text:
            return []

        cs = chunk_size if chunk_size is not None else self.chunk_size
        ov = overlap if overlap is not None else self.chunk_overlap

        if len(text) <= cs:
            return [(text, 0, 0)]

        chunks: List[Tuple[str, int, int]] = []
        start = 0
        idx = 0
        step = max(1, cs - ov)

        while start < len(text):
            end = min(start + cs, len(text))
            chunks.append((text[start:end], start, idx))
            if end >= len(text):
                break
            start += step
            idx += 1

        return chunks

    # ────────────────────────────────────────────────────────────────────
    # LLM EXTRACTION
    # ────────────────────────────────────────────────────────────────────

    def _extract_chunk_with_llm(
        self,
        chunk_text: str,
        chunk_idx: int,
        start_offset: int,
        document_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not chunk_text or len(chunk_text.strip()) < 20:
            return []

        try:
            system_prompt = _build_prompt(document_type)

            raw_content = _call_llm(
                system_prompt=system_prompt,
                user_content=chunk_text,
                json_mode=True,
                temperature=0.0,
                model=FAST_SEARCH_MODEL,
            )

            if not raw_content:
                return []

            data = clean_and_parse_json(raw_content)
            if not isinstance(data, dict):
                return []

            entities = data.get("entities")
            if not isinstance(entities, list):
                entities = next(
                    (v for v in data.values() if isinstance(v, list)),
                    []
                )

            results: List[Dict[str, Any]] = []
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                original_text = str(ent.get("text", "")).strip()
                if len(original_text) < MIN_ENTITY_LENGTH:
                    continue

                ent_text = _normalize_entity_text(original_text)
                if len(ent_text) < MIN_ENTITY_LENGTH:
                    ent_text = original_text

                ent_label = str(ent.get("label", "UNKNOWN")).upper().strip()
                if ent_label not in LEGAL_ENTITY_TYPES:
                    ent_label = "UNKNOWN"

                # V33.5: case normalization për persona
                ent_text = _normalize_case(ent_text, ent_label)

                pos_in_chunk = chunk_text.find(original_text)
                if pos_in_chunk == -1:
                    pos_in_chunk = chunk_text.find(ent_text)
                if pos_in_chunk == -1:
                    pos_in_chunk = chunk_text.lower().find(ent_text.lower())
                if pos_in_chunk == -1:
                    pos_in_chunk = 0

                ctx_start = max(0, pos_in_chunk - CONTEXT_WINDOW)
                ctx_end = min(len(chunk_text), pos_in_chunk + len(ent_text) + CONTEXT_WINDOW)
                context = chunk_text[ctx_start:ctx_end].strip()

                try:
                    confidence = float(ent.get("confidence", 0.7))
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    confidence = 0.7

                results.append({
                    "text": ent_text,
                    "original_text": original_text,
                    "label": ent_label,
                    "chunk_index": chunk_idx,
                    "offset_in_chunk": pos_in_chunk,
                    "offset_in_doc": start_offset + pos_in_chunk,
                    "context": context,
                    "confidence": confidence,
                })

            return results

        except Exception as e:
            logger.warning(f"⚠️ [NER] LLM extraction failed on chunk #{chunk_idx}: {e}")
            return []

    # ────────────────────────────────────────────────────────────────────
    # REGEX FALLBACK
    # ────────────────────────────────────────────────────────────────────

    def _extract_chunk_with_regex(
        self,
        chunk_text: str,
        chunk_idx: int,
        start_offset: int
    ) -> List[Dict[str, Any]]:
        if not chunk_text:
            return []

        results: List[Dict[str, Any]] = []
        for label, pattern in self._local_patterns.items():
            for match in pattern.finditer(chunk_text):
                ent_text = match.group(0).strip()
                if len(ent_text) < MIN_ENTITY_LENGTH:
                    continue

                pos = match.start()
                ctx_start = max(0, pos - CONTEXT_WINDOW)
                ctx_end = min(len(chunk_text), pos + len(ent_text) + CONTEXT_WINDOW)

                results.append({
                    "text": ent_text,
                    "original_text": ent_text,
                    "label": label,
                    "chunk_index": chunk_idx,
                    "offset_in_chunk": pos,
                    "offset_in_doc": start_offset + pos,
                    "context": chunk_text[ctx_start:ctx_end].strip(),
                    "confidence": 0.6,
                })
        return results

    # ────────────────────────────────────────────────────────────────────
    # MERGE GROUP + CONFLICT RESOLUTION
    # ────────────────────────────────────────────────────────────────────

    def _merge_group(
        self,
        group: List[Dict[str, Any]],
        winning_label: str
    ) -> Dict[str, Any]:
        best = max(group, key=lambda e: e.get("confidence", 0))
        merged = dict(best)
        merged["label"] = winning_label

        all_chunks = set()
        for e in group:
            for ci in e.get("chunk_indices", [e.get("chunk_index", 0)]):
                all_chunks.add(ci)
        merged["chunk_indices"] = sorted(all_chunks)

        originals = set()
        for e in group:
            if e.get("original_text"):
                originals.add(e["original_text"])
        if originals:
            merged["original_texts"] = sorted(originals)

        return merged

    def _resolve_conflict(
        self,
        group: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        labels = {e["label"] for e in group}
        role_votes: Dict[str, float] = {}

        for e in group:
            label = e["label"]
            context_lower = e.get("context", "").lower()
            confidence = float(e.get("confidence", 0.5))

            role_votes[label] = role_votes.get(label, 0.0) + confidence

            for role, keywords in ROLE_KEYWORDS.items():
                for kw in keywords:
                    if kw in context_lower:
                        role_votes[role] = role_votes.get(role, 0.0) + 2.0
                        break

        if role_votes:
            winning_role = max(role_votes.items(), key=lambda x: x[1])[0]
        else:
            winner_ent = max(group, key=lambda e: e.get("confidence", 0))
            winning_role = winner_ent["label"]

        merged = self._merge_group(group, winning_role)
        merged["role_conflict_resolved"] = sorted(labels)
        merged["role_conflict_winner"] = winning_role
        merged["role_conflict_votes"] = dict(role_votes)

        logger.info(
            f"⚠️ [NER] Role conflict for '{merged['text']}': "
            f"{sorted(labels)} → {winning_role} (votes={dict(role_votes)})"
        )

        return merged

    def _resolve_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(group) == 1:
            return group[0]

        text = group[0]["text"]
        labels = {e["label"] for e in group}

        if _is_article_pattern(text):
            return self._merge_group(group, "ARTICLE")

        if _is_case_number_pattern(text):
            return self._merge_group(group, "CASE_NUMBER")

        if len(labels) == 1:
            return self._merge_group(group, list(labels)[0])

        return self._resolve_conflict(group)

    def _dedupe_and_resolve(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not entities:
            return []

        by_key: Dict[str, List[Dict[str, Any]]] = {}
        for e in entities:
            normalized = _normalize_entity_text(e.get("text", ""))
            if len(normalized) < MIN_ENTITY_LENGTH:
                continue
            e["text"] = normalized
            key = normalized.lower()
            by_key.setdefault(key, []).append(e)

        resolved: List[Dict[str, Any]] = []
        for key, group in by_key.items():
            resolved.append(self._resolve_group(group))

        return resolved

    # ────────────────────────────────────────────────────────────────────
    # V33.5 — PARTIAL NAME MERGE
    # ────────────────────────────────────────────────────────────────────

    def _merge_partial_names(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Bashkon emrat e pjesshëm (mbiemër i vetëm) me emrin e plotë
        kur ka VETËM NJË kandidat në të njëjtin label.

        Shembull:
        - [JUDGE] 'Dobërdolani' + [JUDGE] 'Bujar Dobërdolani' → 'Bujar Dobërdolani'
        - [WITNESS] 'Karametën' + [WITNESS] 'Muhamet Karameta' → 'Muhamet Karameta'
        """
        if not entities:
            return entities

        # Grupo sipas label
        by_label: Dict[str, List[Dict[str, Any]]] = {}
        for e in entities:
            by_label.setdefault(e["label"], []).append(e)

        remove_ids: Set[int] = set()

        for label, group in by_label.items():
            # Vetëm për persona
            if label not in PERSON_LABELS:
                continue

            single_word = [e for e in group if len(e["text"].split()) == 1]
            multi_word = [e for e in group if len(e["text"].split()) > 1]

            for sw in single_word:
                # Gjej kandidatët
                matches = [
                    mw for mw in multi_word
                    if _is_partial_name_match(sw["text"], mw["text"])
                ]

                # Vetëm nëse ka ekzaktësisht 1 kandidat → merge
                if len(matches) == 1:
                    target = matches[0]
                    target.setdefault("chunk_indices", []).extend(
                        sw.get("chunk_indices", [])
                    )
                    target["chunk_indices"] = sorted(set(target["chunk_indices"]))

                    target.setdefault("merged_partial_names", []).append(sw["text"])
                    remove_ids.add(id(sw))

                    logger.info(
                        f"🔗 [NER] Merged partial name '{sw['text']}' → "
                        f"'{target['text']}' (label={label})"
                    )

        return [e for e in entities if id(e) not in remove_ids]

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ────────────────────────────────────────────────────────────────────

    def extract_legal_entities(
        self,
        text: str,
        document_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        warnings: List[str] = []

        if not text or not text.strip():
            return {
                "document_id": document_id,
                "entities_by_type": {t: [] for t in LEGAL_ENTITY_TYPES},
                "entities_flat": [],
                "stats": {
                    "text_length": 0,
                    "total_chunks": 0,
                    "total_entities": 0,
                    "total_raw_entities": 0,
                    "chunks_failed": 0,
                    "role_conflicts_resolved": 0,
                    "unknown_filtered": 0,
                    "low_confidence_filtered": 0,
                    "titles_stripped": 0,
                    "partial_names_merged": 0,
                    "duration_sec": 0.0,
                },
                "warnings": ["Empty text provided"],
            }

        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        total_chunks = len(chunks)

        logger.info(
            f"🔍 [NER] Starting extraction: doc={document_id}, "
            f"len={len(text)} chars, chunks={total_chunks}, "
            f"doc_type={document_type or 'unknown'}"
        )

        all_entities: List[Dict[str, Any]] = []
        chunks_failed = 0
        titles_stripped = 0

        for chunk_text, start_offset, chunk_idx in chunks:
            if progress_callback:
                try:
                    progress_callback("chunk_started", {
                        "chunk_index": chunk_idx,
                        "total_chunks": total_chunks,
                        "document_id": document_id,
                    })
                except Exception:
                    pass

            chunk_entities = self._extract_chunk_with_llm(
                chunk_text, chunk_idx, start_offset,
                document_type=document_type,
            )

            if not chunk_entities:
                chunk_entities = self._extract_chunk_with_regex(
                    chunk_text, chunk_idx, start_offset
                )
                if not chunk_entities:
                    chunks_failed += 1
                    warnings.append(
                        f"Chunk #{chunk_idx} produced 0 entities (LLM+regex)."
                    )

            for e in chunk_entities:
                if (e.get("original_text")
                        and e["original_text"] != e["text"]):
                    titles_stripped += 1

            all_entities.extend(chunk_entities)

            if progress_callback:
                try:
                    progress_callback("chunk_completed", {
                        "chunk_index": chunk_idx,
                        "total_chunks": total_chunks,
                        "entities_found": len(chunk_entities),
                        "document_id": document_id,
                    })
                except Exception:
                    pass

        # 1. Dedup + role resolve
        resolved = self._dedupe_and_resolve(all_entities)

        # 2. V33.5: partial name merge
        before_merge = len(resolved)
        resolved = self._merge_partial_names(resolved)
        partial_names_merged = before_merge - len(resolved)

        # 3. Filtro UNKNOWN
        unknown_filtered = 0
        filtered_by_unknown = []
        for e in resolved:
            if e.get("label") == "UNKNOWN":
                unknown_filtered += 1
            else:
                filtered_by_unknown.append(e)

        # 4. Filtro konfidencë të ulët
        low_conf_filtered = 0
        final_entities = []
        for e in filtered_by_unknown:
            if e.get("confidence", 1.0) < MIN_CONFIDENCE:
                low_conf_filtered += 1
            else:
                final_entities.append(e)

        role_conflicts_resolved = sum(
            1 for e in final_entities if "role_conflict_resolved" in e
        )

        entities_by_type: Dict[str, List[Dict[str, Any]]] = {
            t: [] for t in LEGAL_ENTITY_TYPES
        }
        for ent in final_entities:
            label = ent.get("label", "UNKNOWN")
            if label not in entities_by_type:
                entities_by_type[label] = []
            entities_by_type[label].append(ent)

        duration = round(time.time() - start_time, 2)

        result = {
            "document_id": document_id,
            "entities_by_type": entities_by_type,
            "entities_flat": final_entities,
            "stats": {
                "text_length": len(text),
                "total_chunks": total_chunks,
                "total_entities": len(final_entities),
                "total_raw_entities": len(all_entities),
                "chunks_failed": chunks_failed,
                "role_conflicts_resolved": role_conflicts_resolved,
                "unknown_filtered": unknown_filtered,
                "low_confidence_filtered": low_conf_filtered,
                "titles_stripped": titles_stripped,
                "partial_names_merged": partial_names_merged,
                "duration_sec": duration,
            },
            "warnings": warnings,
        }

        logger.info(
            f"✅ [NER] Extraction complete: doc={document_id}, "
            f"chunks={total_chunks}, entities={len(final_entities)} "
            f"(raw={len(all_entities)}, unknown={unknown_filtered}, "
            f"lowconf={low_conf_filtered}, conflicts={role_conflicts_resolved}, "
            f"titles_stripped={titles_stripped}, "
            f"partial_merged={partial_names_merged}), duration={duration}s"
        )

        if progress_callback:
            try:
                progress_callback("extraction_complete", {
                    "document_id": document_id,
                    "stats": result["stats"],
                })
            except Exception:
                pass

        return result

    # ────────────────────────────────────────────────────────────────────
    # BATCH
    # ────────────────────────────────────────────────────────────────────

    def extract_batch(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        results: Dict[str, Any] = {}
        total_docs = len(documents)
        total_entities = 0
        total_role_conflicts = 0

        logger.info(f"🔍 [NER] Batch extraction: {total_docs} documents")

        for doc_idx, doc in enumerate(documents):
            doc_id = str(doc.get("id") or doc.get("_id") or f"doc_{doc_idx}")
            doc_text = doc.get("text") or ""
            doc_type = doc.get("document_type")

            if progress_callback:
                try:
                    progress_callback("document_started", {
                        "document_index": doc_idx,
                        "total_documents": total_docs,
                        "document_id": doc_id,
                    })
                except Exception:
                    pass

            result = self.extract_legal_entities(
                text=doc_text,
                document_id=doc_id,
                progress_callback=progress_callback,
                document_type=doc_type,
            )
            results[doc_id] = result
            total_entities += result["stats"]["total_entities"]
            total_role_conflicts += result["stats"].get("role_conflicts_resolved", 0)

            if progress_callback:
                try:
                    progress_callback("document_completed", {
                        "document_index": doc_idx,
                        "total_documents": total_docs,
                        "document_id": doc_id,
                        "entities_found": result["stats"]["total_entities"],
                    })
                except Exception:
                    pass

        duration = round(time.time() - start_time, 2)

        return {
            "documents": results,
            "stats": {
                "total_documents": total_docs,
                "total_entities": total_entities,
                "total_role_conflicts_resolved": total_role_conflicts,
                "duration_sec": duration,
            },
        }

    # ────────────────────────────────────────────────────────────────────
    # BACKWARD COMPAT
    # ────────────────────────────────────────────────────────────────────

    def extract_entities(self, text: str) -> List[Tuple[str, str, int]]:
        logger.warning(
            "⚠️ extract_entities() is DEPRECATED. "
            "Use extract_legal_entities() for structured output."
        )
        result = self.extract_legal_entities(text)
        return [
            (e["text"], e["label"], e["offset_in_doc"])
            for e in result["entities_flat"]
        ]

    def get_albanian_placeholder(self, entity_label: str) -> str:
        logger.warning(
            "⚠️ get_albanian_placeholder() is DEPRECATED. "
            "This service no longer performs anonymization."
        )
        return f"[{entity_label.upper()}]"


# ────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ────────────────────────────────────────────────────────────────────────────

ALBANIAN_NER_SERVICE = AlbanianNERService()