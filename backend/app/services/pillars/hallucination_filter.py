# FILE: backend/app/services/pillars/hallucination_filter.py
# PHOENIX PROTOCOL - HALLUCINATION FILTER V1.0 (POST-PROCESSING GUARD)

import re
import logging
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)

# ========== PRECEDENTËT E VERIFIKUAR (E VETMJA LISTË E LEJUAR) ==========
VERIFIED_PRECEDENTS = [
    "PML.nr.682/2024",
    "PML.nr.429/2025",
    "Rev.nr.240/2024",
    "Rev.Nr.541/2024",
    "PML.Nr.185/2025"
]

# ========== NENET E VERIFIKUARA NGA BAZA STATUTORE ==========
# Këto do të plotësohen nga RAG search
VERIFIED_ARTICLES: Set[str] = set()

# ========== MODELE TË HALUCINACIONEVE TË NJOHURA ==========
HALLUCINATED_PRECEDENTS = [
    "PML.nr.259/2025",
    "PML.nr.272/2025",
    "PML.Nr.259/2025",
    "PML.Nr.272/2025",
    "P.Nr.561/17",
    "PKR.Nr.06/2019",
    "PKR.Nr.60/2023",
    "PML.Nr.186/2025",
    "PML.nr.186/2025",
    "PML.nr.85/2025",
    "PML.nr.343/2025",
    "Rev.Nr.408/2024",
    "Rev.Nr.195/2025",
    "Rev.Nr.16/2025",
    "P.Nr.3767/2021"
]


class HallucinationFilter:
    """
    Filtri i Halucinacioneve:
    - Pastron përgjigjen e LLM para se t'i shfaqet përdoruesit
    - Zëvendëson precedentët e halucinuar me mesazh të qartë
    - Verifikon nenet me bazën statutore
    - Siguron që përgjigja përmban VETËM të vërteta nga RAG
    """

    @staticmethod
    def filter_precedents(text: str) -> str:
        """
        Zëvendëson çdo precedent të halucinuar me mesazh të qartë.
        """
        filtered_text = text
        
        # 1. Kontrollo halucinacionet e njohura
        for bad_precedent in HALLUCINATED_PRECEDENTS:
            if bad_precedent in filtered_text:
                logger.warning(f"🚨 [Filter] U gjet precedent i halucinuar: {bad_precedent}")
                filtered_text = filtered_text.replace(
                    bad_precedent,
                    "[Nuk u gjet ky precedent në bazën tonë]"
                )
        
        # 2. Kontrollo nëse ka precedentë që nuk janë në listën e verifikuar
        # Pattern: PML.nr.XXX/YYYY, Rev.nr.XXX/YYYY, Rev.Nr.XXX/YYYY, P.Nr.XXX/YY, PKR.Nr.XX/YYYY
        precedent_pattern = re.compile(
            r'(PML\.?(?:nr|Nr)\.?\s*\d+/\d+|Rev\.?(?:nr|Nr)\.?\s*\d+/\d+|P\.?(?:Nr|nr)\.?\s*\d+/\d+|PKR\.?(?:Nr|nr)\.?\s*\d+/\d+)'
        )
        
        found_precedents = precedent_pattern.findall(filtered_text)
        for found in found_precedents:
            # Normalizo për krahasim
            normalized = found.replace(" ", "").replace("Nr", "nr").replace("nr", "nr")
            is_verified = any(
                vp.replace(" ", "").replace("Nr", "nr").replace("nr", "nr") == normalized
                for vp in VERIFIED_PRECEDENTS
            )
            
            if not is_verified:
                logger.warning(f"🚨 [Filter] Precedent i paverifikuar u gjet: {found}")
                filtered_text = filtered_text.replace(
                    found,
                    "[Nuk u gjet ky precedent në bazën tonë]"
                )
        
        return filtered_text

    @staticmethod
    def filter_articles(text: str, verified_articles: Optional[Set[str]] = None) -> str:
        """
        Shënon nenet që nuk janë verifikuar në bazën statutore.
        """
        if verified_articles is None:
            verified_articles = VERIFIED_ARTICLES
        
        filtered_text = text
        
        # Pattern: "Neni X" ose "Neni X, paragrafi Y" ose "Nenin X"
        article_pattern = re.compile(r'Neni[n]?\s+(\d+)')
        
        found_articles = article_pattern.findall(filtered_text)
        for article_num in found_articles:
            if article_num not in verified_articles and verified_articles:
                # Nëse kemi listë të verifikuar dhe neni nuk është aty
                logger.warning(f"🚨 [Filter] Nen i paverifikuar: Neni {article_num}")
                # Nuk e fshijmë, por e shënojmë
                filtered_text = filtered_text.replace(
                    f"Neni {article_num}",
                    f"Neni {article_num} [Duhet verifikuar në bazën statutore]"
                )
        
        return filtered_text

    @staticmethod
    def clean_response(
        text: str,
        verified_articles: Optional[Set[str]] = None
    ) -> str:
        """
        Pastron të gjithë përgjigjen e LLM.
        """
        if not text:
            return text
        
        # 1. Filtro precedentët
        text = HallucinationFilter.filter_precedents(text)
        
        # 2. Filtro nenet (nëse kemi listë të verifikuar)
        if verified_articles:
            text = HallucinationFilter.filter_articles(text, verified_articles)
        
        # 3. Hiq nënshkrimet fiktive
        text = re.sub(
            r'Nënshkruar nga:.*?(?=\n|$)',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        # 4. Hiq inicialet fiktive
        text = re.sub(
            r'\b[A-Z]\.[A-Z]\.\b',
            '',
            text
        )
        
        return text.strip()

    @staticmethod
    def extract_verified_articles_from_rag(rag_context: str) -> Set[str]:
        """
        Nxjerr numrat e neneve nga RAG context për verifikim.
        """
        verified = set()
        
        # Pattern: "Neni X" në RAG context
        article_pattern = re.compile(r'Neni\s+(\d+)')
        matches = article_pattern.findall(rag_context)
        verified.update(matches)
        
        return verified

    @staticmethod
    def validate_and_clean(
        response_text: str,
        rag_context: str = ""
    ) -> str:
        """
        Funksioni kryesor — pastron përgjigjen e LLM.
        """
        # Nxjerr nenet e verifikuara nga RAG
        verified_articles = set()
        if rag_context:
            verified_articles = HallucinationFilter.extract_verified_articles_from_rag(rag_context)
        
        # Pastro përgjigjen
        return HallucinationFilter.clean_response(response_text, verified_articles)


# Singleton instance
hallucination_filter = HallucinationFilter()