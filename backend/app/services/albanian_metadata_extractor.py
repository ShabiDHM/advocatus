# FILE: backend/app/services/albanian_metadata_extractor.py
# PHOENIX PROTOCOL - METADATA EXTRACTOR V6.0 (UNIVERSAL OPENROUTER & KOSOVO DB INGESTION)

import re
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

class AlbanianMetadataExtractor:
    def __init__(self):
        # Tier 1: Semantic Client
        if API_KEY:
            self.client = OpenAI(
                api_key=API_KEY,
                base_url=OPENROUTER_BASE_URL
            )
        else:
            self.client = None

        # Tier 2: Regex Patterns (Backup për shpejtësi dhe offline)
        self.patterns = {
            'contract_section': re.compile(r'Neni\s+(\d+\.?\d*)[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'date': re.compile(r'(\d{1,2}\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s+\d{4})', re.IGNORECASE),
            'case_reference': re.compile(r'(?:Çështja|Lënda|Numri|Nr\.?)\s*(?:Nr\.?)?\s*([A-Z]{1,3}\.?\s*nr\.?\s*[\w\-\/]+)', re.IGNORECASE),
            'party': re.compile(r'(Paditësi|Padituesi|Pale|E Paditura|I Pandehuri|Parashtruesi)\s*[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'amount': re.compile(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(€|EUR|euro)', re.IGNORECASE),
            'court': re.compile(r'(Gjykat[aë]s?\s+(e|ë)\s+[\w\s]+)', re.IGNORECASE),
            'judge': re.compile(r'(Gjyqtar[i|e]\s+[\w\s]+)', re.IGNORECASE),
        }
        
        logger.info("✅ Kosovo Metadata Extractor V6.0 Initialized")

    def _extract_with_deepseek(self, text: str) -> Optional[Dict[str, Any]]:
        """Nxjerrje semantike e metatëdhënave me dritare të plotë."""
        if not self.client: 
            return None

        truncated_text = text[:20000] 

        system_prompt = """
        Ti je "Specialist i Arkivës dhe Regjistrit Ligjor" për Republikën e Kosovës.
        
        DETYRA:
        Identifiko të dhënat strukturore (Metadata) nga ky dokument.
        
        FUSHAT E KËRKUARA (JSON):
        - court: Emri i Gjykatës apo Institucionit (psh. "Gjykata Themelore në Prishtinë", "QPS", "QKUK").
        - judge: Emri i Gjyqtarit / Zyrtarit përgjegjës.
        - case_number: Numri i Lëndës (format: C.nr... / P.nr... / Doc.nr...).
        - parties: Lista e personave dhe palëve kryesore.
        - document_type: Lloji (Aktgjykim, Padi, Ekspertizë, Procesverbal, Kontratë, Kallëzim Penal).
        - date: Data e saktë e dokumentit.
        - amount: Vlera monetare në EUR (nëse ka).
        - jurisdiction_check: "KOSOVË" ose "E HUAJ".
        
        Përgjigju VETËM me JSON të pastër.
        """

        try:
            response = self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"DOKUMENTI:\n{truncated_text}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
                
        except Exception as e:
            logger.warning(f"⚠️ Metadata Extraction Fallback: {e}")
            return None
        return None

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """Nxjerrje me Regex nëse cloud nuk përgjigjet."""
        metadata = {}
        
        match = self.patterns['case_reference'].search(text)
        if match: metadata['case_number'] = match.group(1)
        
        match = self.patterns['court'].search(text)
        if match: metadata['court'] = match.group(0)
        
        match = self.patterns['judge'].search(text)
        if match: metadata['judge'] = match.group(0)
        
        match = self.patterns['amount'].search(text)
        if match: metadata['amount'] = f"{match.group(1)} {match.group(2)}"
        
        parties = []
        matches = self.patterns['party'].findall(text)
        for m in matches:
            parties.append({"role": m[0], "name": m[1].strip()})
        if parties: metadata['parties'] = parties
        
        return metadata

    def extract(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Tubi kryesor i nxjerrjes së të dhënave."""
        if not text:
            return {}
        
        metadata = self._extract_with_deepseek(text)
        
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

# Global Instance
albanian_metadata_extractor = AlbanianMetadataExtractor()