# FILE: backend/app/services/albanian_metadata_extractor.py
# PHOENIX PROTOCOL - METADATA EXTRACTOR V7.0 (CENTRALIZED LLM GATEWAY & FAIL-SAFE JSON PARSER)

import re
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

# Importimi nga Porta Qendrore e LLM
from app.services.llm.llm_client import (
    _call_llm,
    clean_and_parse_json,
    FAST_MODEL
)

logger = logging.getLogger(__name__)


class AlbanianMetadataExtractor:
    """
    Ekstraktuesi Qendror i Metatëdhënave Ligjore për Kosovë (V7.0):
    - Përdor portën qendrore me fallback automatik (GPT-4o-mini / DeepSeek).
    - Pastron tag-et <think> dhe markdown json pa u rrëzuar kurrë.
    - Rezervë e sigurt me Regex për nxjerrje offline.
    """

    def __init__(self):
        self.patterns = {
            'contract_section': re.compile(r'Neni\s+(\d+\.?\d*)[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'date': re.compile(r'(\d{1,2}\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s+\d{4})', re.IGNORECASE),
            'case_reference': re.compile(r'(?:Çështja|Lënda|Numri|Nr\.?)\s*(?:Nr\.?)?\s*([A-Z]{1,3}\.?\s*nr\.?\s*[\w\-\/]+)', re.IGNORECASE),
            'party': re.compile(r'(Paditësi|Padituesi|Pale|E Paditura|I Pandehuri|Parashtruesi)\s*[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'amount': re.compile(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(€|EUR|euro)', re.IGNORECASE),
            'court': re.compile(r'(Gjykat[aë]s?\s+(e|ë)\s+[\w\s]+)', re.IGNORECASE),
            'judge': re.compile(r'(Gjyqtar[i|e]\s+[\w\s]+)', re.IGNORECASE),
        }
        logger.info("✅ Kosovo Metadata Extractor V7.0 Initialized with Centralized LLM Gateway")

    def _extract_with_llm(self, text: str) -> Optional[Dict[str, Any]]:
        """Nxjerrje semantike me portën qendrore me fallback dhe pastrim JSON."""
        truncated_text = text[:25000]

        system_prompt = """
        Ti je "Specialist i Arkivës dhe Regjistrit Ligjor" për Republikën e Kosovës.
        
        DETYRA JOTE:
        Identifiko dhe nxirr të dhënat strukturore (Metadata) nga ky dokument.
        
        FUSHAT E DETYRUESHME (FORMATI JSON):
        - court: Emri i Gjykatës apo Institucionit (psh. "Gjykata Komerciale e Kosovës", "Gjykata Themelore në Prishtinë", "QPS").
        - judge: Emri i Gjyqtarit / Kryetarit të trupit gjykues.
        - case_number: Numri i Lëndës (psh. "KE.nr.662/2022", "C.nr.120/21", "P.nr.45/20").
        - parties: Lista e palëve me rolet e tyre ekzakte.
        - document_type: Lloji (Aktvendim, Aktgjykim, Padi, Kundërpadi, Ekspertizë, Kontratë).
        - date: Data e saktë e shkresës.
        - amount: Vlera monetare në EUR (nëse përmendet).
        - jurisdiction_check: "KOSOVË" ose "E HUAJ".
        
        Kthe VETËM objektin JSON të vlefshëm.
        """

        try:
            raw_content = _call_llm(
                system_prompt=system_prompt,
                user_content=f"TEKSTI I DOKUMENTIT PËR METADATA:\n{truncated_text}",
                json_mode=True,
                temperature=0.0,
                model=FAST_MODEL
            )

            if raw_content:
                parsed_json = clean_and_parse_json(raw_content)
                if parsed_json and isinstance(parsed_json, dict):
                    return parsed_json

        except Exception as e:
            logger.warning(f"⚠️ Metadata LLM Extraction Warning: {e}")

        return None

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """Nxjerrje me Regex nëse shërbimi i AI nuk përgjigjet."""
        metadata = {}
        
        match = self.patterns['case_reference'].search(text)
        if match: 
            metadata['case_number'] = match.group(1)
        
        match = self.patterns['court'].search(text)
        if match: 
            metadata['court'] = match.group(0)
        
        match = self.patterns['judge'].search(text)
        if match: 
            metadata['judge'] = match.group(0)
        
        match = self.patterns['amount'].search(text)
        if match: 
            metadata['amount'] = f"{match.group(1)} {match.group(2)}"
        
        parties = []
        matches = self.patterns['party'].findall(text)
        for m in matches:
            parties.append({"role": m[0], "name": m[1].strip()})
        if parties: 
            metadata['parties'] = parties
        
        return metadata

    def extract(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Tubi kryesor i nxjerrjes së metatëdhënave."""
        if not text:
            return {}
        
        metadata = self._extract_with_llm(text)
        
        # Nëse dështoi LLM, kalo te Regex
        if not metadata:
            metadata = self._extract_with_regex(text)
        
        result = {
            "document_id": document_id,
            "extraction_timestamp": datetime.now().isoformat(),
            "court": metadata.get("court"),
            "judge": metadata.get("judge"),
            "case_number": metadata.get("case_number"),
            "parties": metadata.get("parties", []),
            "document_type": metadata.get("document_type"),
            "amount": metadata.get("amount"),
            "date": metadata.get("date"),
            "jurisdiction": metadata.get("jurisdiction_check", "KOSOVË")
        }
        
        return result


# Instanca globale
albanian_metadata_extractor = AlbanianMetadataExtractor()