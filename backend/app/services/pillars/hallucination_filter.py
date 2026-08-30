# FILE: backend/app/services/pillars/hallucination_filter.py
# PHOENIX PROTOCOL - HALLUCINATION FILTER V3.0 (WHITELIST ONLY - ZERO TOLERANCE)

import re
import logging
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)

# ========== PRECEDENTËT E VERIFIKUAR (E VETMJA LISTË E LEJUAR) ==========
# Kjo është WHITELIST — çdo precedent që NUK është këtu, do të fshihet
VERIFIED_PRECEDENTS = [
    "PML.nr.682/2024",
    "PML.nr.429/2025",
    "Rev.nr.240/2024",
    "Rev.Nr.541/2024",
    "PML.Nr.185/2025"
]


class HallucinationFilter:
    """
    Filtri i Halucinacioneve V3.0 — WHITELIST ONLY:
    - Çdo precedent që NUK është në listën e verifikuar, do të zëvendësohet
    - Nuk ka nevojë të shtojmë halucinacione të reja — whitelist i mbulon të gjitha
    - Nëse LLM shpik "PML.nr.999/2026" — do të kapet automatikisht
    """

    @staticmethod
    def normalize_precedent(text: str) -> str:
        """Normalizon formatin e precedentit për krahasim."""
        return text.replace(" ", "").replace("Nr", "nr").replace("nr", "nr").upper()

    @staticmethod
    def is_verified_precedent(precedent: str) -> bool:
        """Kontrollon nëse precedenti është në whitelist."""
        normalized = HallucinationFilter.normalize_precedent(precedent)
        
        for verified in VERIFIED_PRECEDENTS:
            if HallucinationFilter.normalize_precedent(verified) == normalized:
                return True
        
        return False

    @staticmethod
    def filter_precedents(text: str) -> str:
        """
        Zëvendëson çdo precedent që NUK është në whitelist.
        Kjo kap AUTOMATIKISHT çdo halucinacion të ri.
        """
        if not text:
            return text
        
        filtered_text = text
        
        # Pattern i gjerë për të kapur çdo format të mundshëm
        precedent_patterns = [
            re.compile(r'PML\.?(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'Rev\.?(?:nr|Nr)\.?\s*\d+/\d+'),
            re.compile(r'P\.?(?:Nr|nr)\.?\s*\d+/\d+'),
            re.compile(r'PKR\.?(?:Nr|nr)\.?\s*\d+/\d+'),
        ]
        
        found_precedents = set()
        for pattern in precedent_patterns:
            found_precedents.update(pattern.findall(filtered_text))
        
        for found in found_precedents:
            if not HallucinationFilter.is_verified_precedent(found):
                logger.warning(f"🚨 [Filter] Precedent i PALEJUAR u gjet dhe u zëvendësua: {found}")
                filtered_text = filtered_text.replace(
                    found,
                    "[Nuk u gjet ky precedent në bazën tonë]"
                )
        
        return filtered_text

    @staticmethod
    def clean_response(text: str) -> str:
        """
        Pastron të gjithë përgjigjen e LLM.
        """
        if not text:
            return text
        
        # 1. Filtro precedentët — VETËM whitelist lejohet
        text = HallucinationFilter.filter_precedents(text)
        
        # 2. Hiq nënshkrimet fiktive
        text = re.sub(
            r'Nënshkruar nga:.*?(?=\n|$)',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        # 3. Hiq inicialet fiktive (p.sh. "J.D.")
        text = re.sub(
            r'\b[A-Z]\.[A-Z]\.\b',
            '',
            text
        )
        
        return text.strip()

    @staticmethod
    def validate_and_clean(response_text: str) -> str:
        """
        Funksioni kryesor — pastron përgjigjen e LLM.
        """
        return HallucinationFilter.clean_response(response_text)


# Singleton instance
hallucination_filter = HallucinationFilter()