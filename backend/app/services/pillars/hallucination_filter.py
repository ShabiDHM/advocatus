# FILE: backend/app/services/pillars/hallucination_filter.py
# PHOENIX PROTOCOL - HALLUCINATION FILTER V7.0 (CONTEXT-AWARE & SMART PRECEDENT VALIDATION)

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Precedentë bazë të njohur të Kosovës (Whitelist e zgjeruar)
VERIFIED_PRECEDENTS = [
    "PML.NR.682/2024",
    "PML.NR.429/2025",
    "REV.NR.240/2024",
    "REV.NR.541/2024",
    "PML.NR.185/2025",
    "REV.NR.120/2023",
    "REV.NR.315/2022",
    "CN.NR.45/2021"
]


class HallucinationFilter:
    """
    Filtri Inteligjent i Halucinacioneve V7.0:
    - Verifikon precedentët duke i krahasuar me dokumentet reale të lëndës (RAG Context).
    - Nëse një numër lënde gjendet në dokumentet e avokatit, NUK fshihet.
    - Heq nënshkrimet fiktive pa prishur inicialet e palëve (A.B., S.B.).
    """

    @staticmethod
    def normalize_precedent(text: str) -> str:
        return re.sub(r'\s+', '', text).upper()

    @staticmethod
    def get_precedent_patterns() -> List[re.Pattern]:
        return [
            re.compile(r'\b(?:PML|Rev|PKR|P|C|Cn|AC|AA)\.?(?:\s*nr|\s*Nr|\s*NR)?\.?\s*\d+/\d{2,4}\b', re.IGNORECASE),
            re.compile(r'\bVendimi\s+(?:nr|Nr)\.?\s*\d+/\d{2,4}\b', re.IGNORECASE),
            re.compile(r'\bGj\.?Sup\.?\s*(?:nr|Nr)\.?\s*\d+/\d{2,4}\b', re.IGNORECASE),
        ]

    @staticmethod
    def find_all_precedents(text: str) -> Set[str]:
        if not text:
            return set()
        found = set()
        for pattern in HallucinationFilter.get_precedent_patterns():
            found.update(pattern.findall(text))
        return found

    @staticmethod
    def is_precedent_valid(precedent: str, context_text: str = "") -> bool:
        normalized_target = HallucinationFilter.normalize_precedent(precedent)

        # 1. Kontrollo te lista e precedentëve të njohur
        for verified in VERIFIED_PRECEDENTS:
            if HallucinationFilter.normalize_precedent(verified) in normalized_target:
                return True

        # 2. Kontrollo nëse ky numër lënde ndodhet brenda shkresave të ngarkuara nga avokati
        if context_text:
            normalized_context = HallucinationFilter.normalize_precedent(context_text)
            if normalized_target in normalized_context:
                return True

        return False

    @staticmethod
    def filter_precedents(text: str, context_text: str = "") -> str:
        if not text:
            return text

        all_found = HallucinationFilter.find_all_precedents(text)
        cleaned_text = text

        for prec in all_found:
            # Nëse nuk është i vërtetuar dhe nuk gjendet në dokumentet e lëndës
            if not HallucinationFilter.is_precedent_valid(prec, context_text):
                logger.warning(f"🚨 [Hallucination Guard] U hoq referenca fiktive e precedentit: {prec}")
                # E zëvendëson butësisht pa prishur rrjedhën e fjalive
                cleaned_text = cleaned_text.replace(prec, "[Referencë lënde e pa-dokumentuar]")

        return cleaned_text

    @staticmethod
    def clean_response(text: str, rag_context: str = "") -> str:
        """
        Pastron përgjigjen e plotë të AI:
        1. Kontrollon precedentët me kontekstin e shkresave.
        2. Heq vetëm nënshkrimet e rreme në fund të tekstit.
        """
        if not text:
            return text

        # 1. Pastrim i precedentëve
        text = HallucinationFilter.filter_precedents(text, context_text=rag_context)

        # 2. Hiq nënshkrimet fiktive në fund
        text = re.sub(r'(?i)\n*(?:Nënshkruar nga|Avokati mbrojtës|Me respekt,?\s*[A-Za-z\s]+):\s*.*$', '', text)
        text = re.sub(r'\[Emri i Avokatit\]|\[Nënshkrimi\]', '', text)

        return text.strip()

    @staticmethod
    def validate_and_clean(response_text: str, rag_context: str = "") -> str:
        return HallucinationFilter.clean_response(response_text, rag_context=rag_context)


# Singleton
hallucination_filter = HallucinationFilter()