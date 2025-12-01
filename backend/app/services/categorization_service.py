# FILE: backend/app/services/categorization_service.py
# PHOENIX PROTOCOL - CATEGORIZATION ENGINE V4.1
# 1. ENGINE: DeepSeek V3 (OpenRouter) for "Semantic Understanding" classification.
# 2. HIERARCHY: Cloud API -> Local Microservice -> Local LLM.
# 3. LABELS: Optimized for Kosovo Legal System.

import os
import httpx
import logging
import json
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

# Legacy/Local Services
AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

class CategorizationService:
    """
    Service responsible for smart document tagging.
    Tier 1: DeepSeek V3 (Cloud) - High Precision
    Tier 2: Juristi AI Core (Local Zero-Shot) - Fast Backup
    Tier 3: Ollama (Local GenAI) - Last Resort
    """
    def __init__(self):
        self.timeout = 15.0
        
        # OpenRouter Client
        if DEEPSEEK_API_KEY:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=OPENROUTER_BASE_URL
            )
        else:
            self.client = None

        # Standardized Categories for Kosovo Law
        self.default_labels = [
            "Kontratë",                 
            "Vendim Gjyqësor",          
            "Padi / Kërkesëpadi",      
            "Ankesë",
            "Provë Materiale",
            "Ligj / Akt Nënligjor",      
            "Faturë / Financat",
            "Korrespondencë Zyrtare"
        ]

    def _categorize_with_deepseek(self, text: str, labels: List[str]) -> Optional[str]:
        """
        Uses DeepSeek V3 to understand the document type.
        """
        if not self.client: return None

        # Truncate to first 3000 chars (usually contains the Title/Header/Intro)
        truncated_text = text[:3000] 
        labels_str = ", ".join([f'"{l}"' for l in labels])

        system_prompt = f"""
        Ti je "Juristi AI - Arkivisti", një ekspert për klasifikimin e dokumenteve ligjore.
        
        DETYRA:
        Analizo tekstin e dhënë dhe caktoje në SAKTËSISHT NJË nga kategoritë e mëposhtme:
        [{labels_str}]
        
        RREGULLA:
        1. Nëse është e paqartë, zgjidh kategorinë më të afërt.
        2. Kthe vetëm JSON: {{"category": "Emri i Kategorisë"}}
        3. Mos shto asnjë tekst tjetër.
        """

        try:
            response = self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"DOKUMENTI:\n{truncated_text}"}
                ],
                temperature=0.1, # Deterministic
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI Categorization"
                }
            )
            
            content = response.choices[0].message.content
            if content:
                data = json.loads(content)
                return data.get("category")
                
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek Categorization Failed: {e}")
            return None
        
        return None

    def _categorize_with_ai_core(self, text: str, labels: List[str]) -> Optional[str]:
        """Fallback: Local Zero-Shot Model."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{AI_CORE_URL}/categorization/categorize",
                    json={"text": text, "candidate_labels": labels}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("predicted_category")
        except Exception as e:
            logger.warning(f"⚠️ AI Core Categorization Failed: {e}")
            return None

    def _categorize_with_ollama(self, text: str, labels: List[str]) -> Optional[str]:
        """Last Resort: Local Llama."""
        try:
            truncated_text = text[:1000]
            labels_str = ", ".join([f'"{l}"' for l in labels])
            
            payload = {
                "model": LOCAL_MODEL_NAME,
                "messages": [{"role": "user", "content": f"Classify this text into one of [{labels_str}]. Return JSON {{'category': 'name'}}.\n\nText: {truncated_text}"}],
                "stream": False,
                "format": "json"
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(LOCAL_LLM_URL, json=payload)
                data = response.json()
                content = data.get("message", {}).get("content", "")
                result = json.loads(content)
                return result.get("category")
        except Exception:
            return None

    def categorize_document(self, text: str, custom_labels: Optional[List[str]] = None) -> str:
        """
        Main pipeline execution.
        """
        if not text or len(text.strip()) < 10:
            return "E Papërcaktuar"
            
        labels = custom_labels if custom_labels else self.default_labels
        
        # 1. Tier 1: DeepSeek (Smartest)
        category = self._categorize_with_deepseek(text, labels)
        if category: return category

        # 2. Tier 2: AI Core (Fastest Local)
        category = self._categorize_with_ai_core(text, labels)
        if category: return category

        # 3. Tier 3: Ollama (Backup Local)
        category = self._categorize_with_ollama(text, labels)
        if category: return category

        return "E Papërcaktuar"

# --- Global Instance ---
CATEGORIZATION_SERVICE = CategorizationService()