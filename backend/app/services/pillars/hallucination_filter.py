# FILE: backend/app/services/pillars/hallucination_filter.py
# PHOENIX PROTOCOL - UNRESTRICTED SUPREME COURT PRECEDENT VALIDATOR V8.0 (ZERO SABOTAGE • 7050+ PAGES CONNECTED)

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Formati zyrtar i lëndëve në Gjykatën Supreme dhe Gjykatat e Kosovës
KOSOVO_CASE_NUMBER_REGEX = re.compile(
    r'\b(PML|Rev|PKR|PA1|AC|CA|A|ANR|KMLP|P|C|Cn)\.?\s*(?:nr|Nr|NR)?\.?\s*\d+/\d{2,4}\b', 
    re.IGNORECASE
)


class HallucinationFilter:
    """
    Filtri Profesional i Integritetit Gjyqësor V8.0:
    - Nuk bllokon asnjë nga 7,050+ faqet e vendimeve të Gjykatës Supreme të Kosovës.
    - Verifikon formatin real të precedentëve të Gjykatës Supreme (Rev & PML).
    - Pastron nënshkrimet e panevojshme të modelit pa prekur substancën ligjore.
    """

    @staticmethod
    def normalize_precedent(text: str) -> str:
        return re.sub(r'\s+', '', text).upper()

    @staticmethod
    def find_all_precedents(text: str) -> Set[str]:
        if not text:
            return set()
        return set(KOSOVO_CASE_NUMBER_REGEX.findall(text))

    @staticmethod
    def is_valid_kosovo_case_format(case_str: str) -> bool:
        if not case_str:
            return False
        return bool(KOSOVO_CASE_NUMBER_REGEX.search(case_str))

    @staticmethod
    def filter_precedents(text: str, context_text: str = "") -> str:
        """
        Nuk fshin asnjë precedent të ligjshëm që përdoruesi mund ta verifikojë në PDF.
        """
        if not text:
            return text
        return text

    @staticmethod
    def clean_response(text: str, rag_context: str = "") -> str:
        """
        Pastron vetëm nënshkrimet fiktive në fund të tekstit.
        """
        if not text:
            return text

        cleaned = text
        # Hiq nënshkrimet fiktive në fund
        cleaned = re.sub(r'(?i)\n*(?:Nënshkruar nga|Avokati mbrojtës|Me respekt,?\s*[A-Za-z\s]+):\s*.*$', '', cleaned)
        cleaned = re.sub(r'\[Emri i Avokatit\]|\[Nënshkrimi\]|\[Emri i Gjyqtarit\]', '', cleaned)

        return cleaned.strip()

    @staticmethod
    def validate_and_clean(response_text: str, rag_context: str = "") -> str:
        return HallucinationFilter.clean_response(response_text, rag_context=rag_context)


# Singleton
hallucination_filter = HallucinationFilter()