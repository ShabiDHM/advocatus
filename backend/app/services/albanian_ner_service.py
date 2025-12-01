# FILE: backend/app/services/albanian_ner_service.py
# PHOENIX PROTOCOL - NER ENGINE V4.1
# 1. ENGINE: DeepSeek V3 (OpenRouter) for high-precision Albanian Entity Extraction.
# 2. FALLBACK: Retains 'AI_CORE_URL' (Local Spacy) as backup.
# 3. COMPATIBILITY: Returns standard (text, label, index) format for graph building.

import os
import httpx
import json
import logging
from typing import List, Tuple, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

# Legacy/Local Core
AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

class AlbanianNERService:
    """
    Service responsible for detecting Named Entities (PII) using Hybrid Intelligence.
    Tier 1: DeepSeek V3 (Cloud)
    Tier 2: Juristi AI Core (Local Spacy)
    """
    def __init__(self):
        self.timeout = 15.0 # Slightly higher for LLM
        
        if DEEPSEEK_API_KEY:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=OPENROUTER_BASE_URL
            )
        else:
            self.client = None

    def _extract_with_deepseek(self, text: str) -> Optional[List[dict]]:
        """
        Uses SOTA LLM to extract entities. Returns raw list of dicts.
        """
        if not self.client: return None

        # Truncate to avoid massive costs on huge docs, though DeepSeek is cheap.
        # 10k chars is enough to get the main parties and context.
        truncated_text = text[:10000]

        system_prompt = """
        Ti je një ekspert i Nxjerrjes së Entiteteve (NER) për dokumente ligjore shqipe.
        
        DETYRA:
        Identifiko entitetet në tekstin e dhënë dhe ktheji në format JSON.
        
        KATEGORITË:
        - PERSON: Emra njerëzish (p.sh. "Agim Gashi", "Dr. Vjosa Osmani").
        - ORGANIZATION: Kompani, institucione, gjykata (p.sh. "Gjykata Themelore", "PTK sh.a.").
        - LOCATION: Qytete, shtete, adresa (p.sh. "Prishtinë", "Rruga Luan Haradinaj").
        - DATE: Data specifike (p.sh. "12/05/2023", "15 Janar").
        - MONEY: Shuma parash (p.sh. "5000 Euro", "10,000 €").

        FORMATI:
        [
          {"text": "Agim Gashi", "label": "PERSON"},
          {"text": "Prishtinë", "label": "LOCATION"}
        ]
        
        Mos përfshi asnjë tekst tjetër përveç JSON.
        """

        try:
            response = self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": truncated_text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI NER"
                }
            )
            
            content = response.choices[0].message.content
            if not content: return None
            
            data = json.loads(content)
            
            # Normalize response (handle if LLM wraps in "entities": [...])
            if isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], list): return data[key]
                return []
            elif isinstance(data, list):
                return data
                
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek NER Failed: {e}")
            return None
        return None

    def _extract_with_local_core(self, text: str) -> List[dict]:
        """
        Fallback to local microservice.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{AI_CORE_URL}/ner/extract",
                    json={"text": text}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("entities", [])
        except Exception as e:
            logger.error(f"❌ Local Core NER Failed: {e}")
            return []

    def extract_entities(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Main entry point. Orchestrates Tier 1 -> Tier 2.
        Returns: List of (entity_text, entity_label, start_char_index).
        """
        if not text: return []
        
        raw_entities = []
        
        # 1. Try DeepSeek
        raw_entities = self._extract_with_deepseek(text)
        
        # 2. Fallback to Local
        if raw_entities is None:
            raw_entities = self._extract_with_local_core(text)
            
        if not raw_entities:
            return []

        results = []
        # Post-processing to find indices (LLMs don't return offsets)
        for ent in raw_entities:
            name = ent.get("text", "").strip()
            label = ent.get("label", "UNKNOWN").upper()
            
            if not name: continue
            
            # Simple find (Caveat: Finds first occurrence only)
            # For graph building, simply knowing the entity exists is usually sufficient.
            start_index = text.find(name)
            
            # Map common LLM variations to standard labels if needed
            if label in ["ORG", "ORGANIZATE"]: label = "ORGANIZATION"
            if label in ["PER", "PERSONA"]: label = "PERSON"
            if label in ["LOC", "LOKACION", "VEND"]: label = "LOCATION"
            if label in ["DATE", "DATA"]: label = "DATE"
            
            if start_index != -1:
                results.append((name, label, start_index))
                
        return results
    
    def get_albanian_placeholder(self, entity_label: str) -> str:
        """ 
        Maps the entity label to an Albanian placeholder for anonymization. 
        """
        placeholders = {
            "PER": "[EMRI_PERSONI_ANONIMIZUAR]",
            "PERSON": "[EMRI_PERSONI_ANONIMIZUAR]",
            "ORG": "[ORGANIZATË_ANONIMIZUAR]",
            "ORGANIZATION": "[ORGANIZATË_ANONIMIZUAR]",
            "LOC": "[VENDNDODHJA_ANONIMIZUAR]",
            "LOCATION": "[VENDNDODHJA_ANONIMIZUAR]",
            "GPE": "[VENDNDODHJA_ANONIMIZUAR]",
            "DATE": "[DATA_ANONIMIZUAR]",
            "MONEY": "[VLERA_MONETARE_ANONIMIZUAR]",
            "CASE_NUMBER": "[NUMRI_ÇËSHTJES_ANONIMIZUAR]",
        }
        return placeholders.get(entity_label.upper(), f"[{entity_label}_ANONIMIZUAR]")
        
# --- Global Instance ---
ALBANIAN_NER_SERVICE = AlbanianNERService()