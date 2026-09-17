# FILE: backend/app/services/pillars/hallucination_filter.py
# PHOENIX PROTOCOL - SUPREME COURT PRECEDENT & CITATION FILTER V10.0
# V10.0: Real precedent validation + filtering against context.
#   - filter_precedents() now ACTUALLY filters hallucinated case numbers
#   - validate_precedents() returns structured validation result
#   - KOSOVO_CASE_NUMBER_REGEX is now USED, not just defined
#   - Safety guard: skip filtering when no context provided

import re
import logging
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# REGEX — Kosovo case number patterns
# ────────────────────────────────────────────────────────────────────────────

KOSOVO_CASE_NUMBER_REGEX = re.compile(
    r'\b(?:PML|Rev|PKR|PA1|AC|CA|A|ANR|KMLP|P|C|Cn)'
    r'\.?\s*(?:nr|Nr|NR)?\.?\s*'
    r'\d+\s*/\s*\d{2,4}\b',
    re.IGNORECASE,
)


# ────────────────────────────────────────────────────────────────────────────
# PLACEHOLDER PATTERNS
# ────────────────────────────────────────────────────────────────────────────

PLACEHOLDER_PATTERNS = [
    r'\[Emri i Avokatit\]',
    r'\[Emri i Gjyqtarit\]',
    r'\[Emri\]',
    r'\[Nënshkrimi\]',
    r'\[Nënshkrim\]',
    r'\[Vula\]',
    r'\[Data\]',
    r'\[Vendi\]',
    r'\[Adresa\]',
    r'\[Numri i Lëndës\]',
    r'\[Referenca\]',
]

SIGNATURE_PATTERN = re.compile(
    r'(?i)\n*\s*(?:'
    r'Nënshkruar nga|'
    r'Nënshkrimi i|'
    r'Avokati mbrojtës|'
    r'Me respekt,?\s*[A-Za-zëç\s]+'
    r')\s*:\s*.*$',
    re.MULTILINE | re.DOTALL,
)


# ────────────────────────────────────────────────────────────────────────────
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class HallucinationFilter:
    """
    V10.0 — Filtri Real i Precedentëve dhe Nënshkrimeve Fiktive:

    1. clean_response()       — Heq nënshkrimet fiktive dhe placeholder-at
    2. find_all_precedents()  — Nxjerr të gjithë numrat e lëndëve nga teksti
    3. validate_precedents()  — Kontrollon a ekzistojnë në context/KB
    4. filter_precedents()    — Heq precedentët e hallucinuar (jo në context)
    5. validate_and_clean()   — Pipeline i plotë

    RREGULL KRYESOR: Nëse nuk ka context, filtrohen VETËM nënshkrimet.
    Precedentët filtrohen VETËM kur ka context për verifikim.
    """

    # ────────────────────────────────────────────────────────────────────
    # UTILITY
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_precedent(text: str) -> str:
        """Normalizon një numër lënde për krahasim (uppercase, whitespace)."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip().upper()

    @staticmethod
    def find_all_precedents(text: str) -> Set[str]:
        """Nxjerr të gjithë numrat e lëndëve nga teksti."""
        if not text:
            return set()
        matches = KOSOVO_CASE_NUMBER_REGEX.findall(text)
        return {re.sub(r'\s+', ' ', m.strip()) for m in matches}

    @staticmethod
    def is_valid_kosovo_case_format(case_str: str) -> bool:
        """Kontrollon a përputhet me format standard kosovar."""
        if not case_str:
            return False
        return bool(KOSOVO_CASE_NUMBER_REGEX.search(case_str))

    # ────────────────────────────────────────────────────────────────────
    # CLEAN RESPONSE — signatures + placeholders
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def clean_response(text: str, rag_context: str = "") -> str:
        """
        Heq nënshkrimet fiktive dhe placeholder-at nga output-i i LLM.
        Nuk filtron precedentët — këtë e bën filter_precedents().
        """
        if not text:
            return text

        cleaned = text

        # 1. Heq nënshkrimet fiktive
        cleaned = SIGNATURE_PATTERN.sub('', cleaned)

        # 2. Heq placeholder-at
        for pattern in PLACEHOLDER_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # 3. Pastro hapësira të tepërta pas heqjes
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

        return cleaned.strip()

    # ────────────────────────────────────────────────────────────────────
    # VALIDATE PRECEDENTS
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def validate_precedents(
        text: str,
        rag_context: str = "",
        known_case_numbers: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        Validon precedentët në output kundrejt context / KB.

        Args:
            text: Output i LLM
            rag_context: Teksti i KB që u dha si kontekst
            known_case_numbers: Set opsional me numra lënde të njohur

        Returns:
            {
                "all_cited": set(),       # Të gjithë numrat në output
                "valid": set(),           # Ata që ekzistojnë në context/KB
                "hallucinated": set(),    # Ata që nuk ekzistojnë
                "has_context": bool,      # A u dha context për verifikim
            }
        """
        cited = HallucinationFilter.find_all_precedents(text)
        if not cited:
            return {
                "all_cited": set(),
                "valid": set(),
                "hallucinated": set(),
                "has_context": bool(rag_context or known_case_numbers),
            }

        # Mblidh numrat e njohur nga context
        known = set()
        if known_case_numbers:
            for cn in known_case_numbers:
                known.add(HallucinationFilter.normalize_precedent(cn))

        if rag_context:
            for c in HallucinationFilter.find_all_precedents(rag_context):
                known.add(HallucinationFilter.normalize_precedent(c))

        # Normalizo cited
        cited_normalized = {
            HallucinationFilter.normalize_precedent(c) for c in cited
        }

        valid = cited_normalized & known
        hallucinated = cited_normalized - known

        return {
            "all_cited": cited_normalized,
            "valid": valid,
            "hallucinated": hallucinated,
            "has_context": bool(known),
        }

    # ────────────────────────────────────────────────────────────────────
    # FILTER PRECEDENTS — actual filtering
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def filter_precedents(text: str, context_text: str = "") -> str:
        """
        V10.0 — Heq nga teksti precedentët që NUK gjenden në context.

        Safety guard: Nëse context_text është bosh, kthen tekstin si është
        (pa filtër) — sepse nuk mund të verifikojmë.

        Args:
            text: Teksti për filtrim
            context_text: Context burimor (KB) për verifikim

        Returns:
            Teksti me precedentë të vlefshëm vetëm
        """
        if not text:
            return text

        # SAFETY: Pa context, nuk filtrojmë
        if not context_text:
            logger.debug(
                "[HALLUCINATION FILTER] No context provided — "
                "skipping precedent filtering"
            )
            return text

        # Mblidh numrat e njohur nga context
        known_raw = HallucinationFilter.find_all_precedents(context_text)
        known_normalized = {
            HallucinationFilter.normalize_precedent(k) for k in known_raw
        }

        if not known_normalized:
            logger.debug(
                "[HALLUCINATION FILTER] No precedents found in context — "
                "skipping filtering"
            )
            return text

        # Numërues për statistikat
        removed_count = [0]

        def replace_match(match: re.Match) -> str:
            matched_text = match.group(0)
            matched_normalized = HallucinationFilter.normalize_precedent(
                matched_text
            )

            if matched_normalized in known_normalized:
                # Valid precedent → keep
                return matched_text

            # Hallucinated → remove
            removed_count[0] += 1
            logger.warning(
                f"🚨 [HALLUCINATION FILTER] Removed hallucinated precedent: "
                f"'{matched_text}' (not found in context)"
            )
            return ''

        cleaned = KOSOVO_CASE_NUMBER_REGEX.sub(replace_match, text)

        if removed_count[0] > 0:
            # Pastro hapësira të tepërta pas heqjes
            cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
            cleaned = re.sub(r'\s+([.,;:])', r'\1', cleaned)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            logger.info(
                f"✅ [HALLUCINATION FILTER] Removed {removed_count[0]} "
                f"hallucinated precedent(s)"
            )

        return cleaned.strip()

    # ────────────────────────────────────────────────────────────────────
    # FULL PIPELINE
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def validate_and_clean(
        response_text: str,
        rag_context: str = "",
        known_case_numbers: Optional[Set[str]] = None,
    ) -> str:
        """
        Pipeline i plotë:
        1. Heq nënshkrimet fiktive + placeholder-at
        2. Filtron precedentët e hallucinuar (vetëm nëse ka context)

        Args:
            response_text: Output i LLM
            rag_context: Context për verifikim precedentësh
            known_case_numbers: Set alternativ me numra lënde të njohur

        Returns:
            Teksti i pastruar
        """
        if not response_text:
            return response_text

        # Step 1: signatures + placeholders
        cleaned = HallucinationFilter.clean_response(
            response_text, rag_context=rag_context
        )

        # Step 2: precedent filtering (vetëm nëse ka context)
        context_for_verification = rag_context
        if not context_for_verification and known_case_numbers:
            # Nëse vetëm known_case_numbers jepet, ndërto context artificial
            context_for_verification = " ".join(known_case_numbers)

        cleaned = HallucinationFilter.filter_precedents(
            cleaned, context_text=context_for_verification
        )

        return cleaned


# ────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ────────────────────────────────────────────────────────────────────────────

hallucination_filter = HallucinationFilter()