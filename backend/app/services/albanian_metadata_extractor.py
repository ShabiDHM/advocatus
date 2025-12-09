# FILE: backend/app/services/albanian_metadata_extractor.py
# PHOENIX PROTOCOL - METADATA EXTRACTOR V5.1 (SYNTAX FIX)
# 1. FIX: Resolved truncated variable name at end of file.
# 2. JURISDICTION: Target strictly "Republic of Kosovo" Institutions.
# 3. SCHEMA: Standardized extraction for Graph & DB ingestion.

import re
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

class AlbanianMetadataExtractor:
    def __init__(self):
        # Tier 1: DeepSeek Client
        if DEEPSEEK_API_KEY:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=OPENROUTER_BASE_URL
            )
        else:
            self.client = None

        # Tier 2: Regex Patterns (Backup)
        # PHOENIX: Optimized for Kosovo context (EUR primary)
        self.patterns = {
            'contract_section': re.compile(r'Neni\s+(\d+\.?\d*)[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'date': re.compile(r'(\d{1,2}\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s+\d{4})', re.IGNORECASE),
            'case_reference': re.compile(r'Çështja\s+(Nr\.?\s*[\w\-\/]+)', re.IGNORECASE),
            'party': re.compile(r'(Paditësi|Padituesi|Pale|E Paditura)\s*[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'amount': re.compile(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(€|EUR|euro)', re.IGNORECASE),
            'court': re.compile(r'(Gjykat[aë]s?\s+(e|ë)\s+[\w\s]+)', re.IGNORECASE),
            'judge': re.compile(r'(Gjykat[aë]s(it)?\s+[\w\s]+)', re.IGNORECASE),
        }
        
        logger.info("✅ Kosovo Metadata Extractor V5.1 Initialized")

    def _extract_with_deepseek(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Tier 1: Semantic Extraction using DeepSeek V3.
        """
        if not self.client: return None

        truncated_text = text[:15000] 

        system_prompt = """
        Ti je "Specialist i Arkivës Ligjore" për Republikën e Kosovës.
        
        DETYRA:
        Identifiko të dhënat strukturore (Metadata) nga dokumenti.
        
        FUSHAT E KËRKUARA (JSON):
        - court: Emri i Gjykatës (psh. "Gjykata Themelore në Prishtinë").
        - judge: Emri i Gjyqtarit.
        - case_number: Numri i Lëndës (format: C.nr... / P.nr...).
        - parties: Lista e palëve.
        - document_type: Lloji (Aktgjykim, Padi, Kontratë).
        - date: Data e dokumentit.
        - amount: Vlera monetare (Prefero EUR).
        - jurisdiction_check: "KOSOVË" ose "E HUAJ" (nëse është Shqipëri/Tjetër).
        
        RREGULLA:
        - Fokusohu te institucionet e Kosovës.
        - Përgjigju VETËM me JSON valid.
        """

        try:
            response = self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"DOKUMENTI:\n{truncated_text}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI Metadata"
                }
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
                
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek Metadata Extraction Failed: {e}")
            return None
        return None

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """
        Tier 2: Regex Backup.
        """
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
        """
        Main extraction pipeline.
        """
        if not text:
            return {}
        
        # 1. Try DeepSeek
        metadata = self._extract_with_deepseek(text)
        
        # 2. Fallback
        if not metadata:
            logger.info("Falling back to Regex Metadata Extraction")
            metadata = self._extract_with_regex(text)
        
        # Standardize Output
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
            "jurisdiction": metadata.get("jurisdiction_check", "UNKNOWN")
        }
        
        return result

# Global Instance
albanian_metadata_extractor = AlbanianMetadataExtractor()