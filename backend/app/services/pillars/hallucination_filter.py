# FILE: backend/app/services/pillars/hallucination_filter.py
# PHOENIX PROTOCOL - HALLUCINATION FILTER V5.0 (EXPANDED PATTERNS - CATCHES ALL FORMATS)

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ========== PRECEDENTËT E VERIFIKUAR (E VETMJA LISTË E LEJUAR) ==========
VERIFIED_PRECEDENTS = [
    "PML.nr.682/2024",
    "PML.nr.429/2025",
    "Rev.nr.240/2024",
    "Rev.Nr.541/2024",
    "PML.Nr.185/2025"
]

# ========== TEKSTI ZËVENDËSUES PËR HALUCINACIONET ==========
REPLACEMENT_TEXT = "[Precedent i paverifikuar — hiqeni këtë referencë]"


class HallucinationFilter:
    """
    Filtri i Halucinacioneve V5.0 — WHITELIST ONLY me formate të zgjeruara:
    - Kap PML.nr.XXX/YYYY
    - Kap Rev.nr.XXX/YYYY
    - Kap P.Nr.XXX/YYYY
    - Kap PKR.Nr.XXX/YYYY
    - Kap Vendimi nr.XXX/YY
    - Kap Precedent nr.XXX/YYYY
    - Kap Gj.Sup. nr.XXX/YYYY
    - Çdo format tjetër numerik të ngjashëm
    """

    @staticmethod
    def normalize_precedent(text: str) -> str:
        return text.replace(" ", "").replace("Nr", "nr").replace("nr", "nr").upper()

    @staticmethod
    def is_verified_precedent(precedent: str) -> bool:
        normalized = HallucinationFilter.normalize_precedent(precedent)
        for verified in VERIFIED_PRECEDENTS:
            if HallucinationFilter.normalize_precedent(verified) == normalized:
                return True
        return False

    @staticmethod
    def filter_precedents(text: str) -> str:
        filtered_text, _ = HallucinationFilter.filter_precedents_with_details(text)
        return filtered_text

    @staticmethod
    def filter_precedents_with_details(text: str) -> Tuple[str, List[str]]:
        if not text:
            return text, []
        
        filtered_text = text
        replaced_precedents = []
        
        # PHOENIX FIX V5.0: Pattern i zgjeruar për të kapur çdo format
        precedent_patterns = [
            re.compile(r'PML\.?(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'Rev\.?(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'P\.?(?:Nr|nr)\.?\s*\d+/\d+'),
            re.compile(r'PKR\.?(?:Nr|nr)\.?\s*\d+/\d+'),
            re.compile(r'Vendimi\s+(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'Precedent\s+(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'Gj\.?Sup\.?\s*(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'Gj\.?Sup\.?\s*(?:nr|Nr)\.?\s*\d+/\d{2,4}'),
            re.compile(r'(?:Vendim|Precedent|Aktgjykim|Aktvendim)\s+(?:i\s+)?(?:Gj\.?Sup\.?|nr\.?|Nr\.?)\s*\d+/\d+'),
        ]
        
        found_precedents = set()
        for pattern in precedent_patterns:
            found_precedents.update(pattern.findall(filtered_text))
        
        for found in found_precedents:
            if not HallucinationFilter.is_verified_precedent(found):
                logger.warning(f"🚨 [Filter] Precedent i PALEJUAR u zëvendësua: {found}")
                filtered_text = filtered_text.replace(
                    found,
                    REPLACEMENT_TEXT
                )
                replaced_precedents.append(found)
        
        return filtered_text, replaced_precedents

    @staticmethod
    def clean_response(
        text: str,
        verified_articles: Optional[Set[str]] = None
    ) -> str:
        if not text:
            return text
        
        text = HallucinationFilter.filter_precedents(text)
        
        text = re.sub(
            r'Nënshkruar nga:.*?(?=\n|$)',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        text = re.sub(
            r'\b[A-Z]\.[A-Z]\.\b',
            '',
            text
        )
        
        return text.strip()

    @staticmethod
    def validate_and_clean(
        response_text: str,
        rag_context: str = ""
    ) -> str:
        return HallucinationFilter.clean_response(response_text)


# Singleton instance
hallucination_filter = HallucinationFilter()