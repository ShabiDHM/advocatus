# FILE: backend/app/services/albanian_ner_service.py
# PHOENIX PROTOCOL - NER CLOUD INDEPENDENCE V6.0
# STATUS: Haveri Cord Severed / Production Grade Albanian NER

import os, json, logging
from typing import List, Tuple, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

class AlbanianNERService:
    def __init__(self):
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None

    def extract_entities(self, text: str) -> List[Tuple[str, str, int]]:
        if not text or not self.client: return []
        prompt = "Ti je ekspert i NER. Identifiko: PERSON, ORGANIZATION, LOCATION, DATE, MONEY. Kthe JSON listë: [{'text': '...', 'label': '...'}]"
        try:
            res = self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text[:10000]}],
                temperature=0.1, response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            entities = next(iter(data.values())) if isinstance(data, dict) else []
            results = []
            for ent in (entities if isinstance(entities, list) else []):
                name, label = ent.get("text", ""), ent.get("label", "UNKNOWN").upper()
                idx = text.find(name)
                if name and idx != -1: results.append((name, label, idx))
            return results
        except Exception as e:
            logger.error(f"⚠️ Cloud NER Failed: {e}")
            return []

    def get_albanian_placeholder(self, entity_label: str) -> str:
        map = {"PERSON": "[EMRI_ANONIMIZUAR]", "ORGANIZATION": "[ORGANIZATË_ANONIMIZUAR]", "LOCATION": "[VENDNDODHJA_ANONIMIZUAR]", "DATE": "[DATA_ANONIMIZUAR]"}
        return map.get(entity_label.upper(), f"[{entity_label}_ANONIMIZUAR]")

ALBANIAN_NER_SERVICE = AlbanianNERService()