# FILE: backend/app/services/albanian_ner_service.py
# PHOENIX PROTOCOL - NER CLOUD INDEPENDENCE V32.0 (CENTRALIZED GATEWAY & GDPR COMPLIANT)

import os
import json
import logging
import re
from typing import List, Tuple, Optional, Dict, Any

# Importimi nga Porta Qendrore e LLM
from app.services.llm.llm_client import (
    _call_llm,
    clean_and_parse_json,
    FAST_MODEL
)

logger = logging.getLogger(__name__)


class AlbanianNERService:
    """
    Shërbimi i Njohjes së Entiteteve (NER) dhe Mbrojtjes GDPR:
    - Përdor portën qendrore të unifikuar LLM për identifikimin e personave, organizatave dhe datave.
    - Rezervë e hekurt lokale (Local Regex Extractor) për mbrojtjen e të dhënave personale (PII).
    """

    def __init__(self):
        logger.info("✅ [NER] Albanian NER Service V32.0 Initialized with Centralized LLM Gateway.")

    def extract_entities_local(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Nxjerrje lokale me rregulla strikte për mbrojtje GDPR 
        edhe kur shërbimi cloud është offline.
        """
        results = []
        
        titles_pattern = r"\b(avokat|avokati|gjyqtar|gjyqtari|aksionar|aksionari|drejtor|drejtori|punëmarrës|punëmarrësi|punëdhënës|punëdhënësi|z\.|znj\.)\s+([A-Z][a-zëç]+(?:\s+[A-Z][a-zëç]+)+)\b"
        name_pattern = r"\b([A-Z][a-zëç]+)\s+([A-Z][a-zëç]+)\b"
        
        legal_exceptions = {
            "Gjykata", "Themelore", "Komerciale", "Apelit", "Supreme", "Kodi", "Penal", "Procedurës", 
            "Marrëdhëniet", "Detyrimeve", "Pronësinë", "Ligji", "Kushtetues", "Republikës",
            "Departamenti", "Ekonomik", "Creative", "Team", "ShPK", "SHPK", "NUI", "ARBK"
        }
        
        # 1. Emrat me tituj profesionalë
        for match in re.finditer(titles_pattern, text, flags=re.IGNORECASE):
            name = match.group(2)
            if not any(part in legal_exceptions for part in name.split()):
                idx = text.find(name)
                if idx != -1:
                    results.append((name, "PERSON", idx))
                    
        # 2. Emrat standardë me dy fjalë të mëdha
        for match in re.finditer(name_pattern, text):
            name = match.group(0)
            part1 = match.group(1)
            part2 = match.group(2)
            if part1 not in legal_exceptions and part2 not in legal_exceptions:
                idx = text.find(name)
                if idx != -1:
                    results.append((name, "PERSON", idx))
                    
        return results

    def extract_entities(self, text: str) -> List[Tuple[str, str, int]]:
        if not text: 
            return []
            
        prompt = (
            "Ti je ekspert i Njohjes së Entiteteve Ligjore (NER) për Kosovën.\n"
            "DETYRA: Identifiko entitetet e mëposhtme: PERSON, ORGANIZATION, LOCATION, DATE, MONEY.\n"
            "Kthe VETËM një JSON me formatin: {'entities': [{'text': 'Emri', 'label': 'PERSON'}]}"
        )

        try:
            raw_content = _call_llm(
                system_prompt=prompt,
                user_content=text[:12000],
                json_mode=True,
                temperature=0.0,
                model=FAST_MODEL
            )

            if raw_content:
                data = clean_and_parse_json(raw_content)
                entities = data.get("entities") if isinstance(data, dict) else None
                if not entities and isinstance(data, dict):
                    entities = next(iter(data.values()), [])

                results = []
                for ent in (entities if isinstance(entities, list) else []):
                    name = ent.get("text", "").strip()
                    label = ent.get("label", "UNKNOWN").upper().strip()
                    idx = text.find(name)
                    if name and idx != -1: 
                        results.append((name, label, idx))

                if results:
                    return results

        except Exception as e:
            logger.warning(f"⚠️ Cloud NER dështoi: {e}. Po përdoret nxjerrësi lokal GDPR.")

        # Fallback lokal i sigurt
        return self.extract_entities_local(text)

    def get_albanian_placeholder(self, entity_label: str) -> str:
        placeholder_map = {
            "PERSON": "[EMRI_ANONIMIZUAR]", 
            "ORGANIZATION": "[ORGANIZATË_ANONIMIZUAR]", 
            "LOCATION": "[VENDNDODHJA_ANONIMIZUAR]", 
            "DATE": "[DATA_ANONIMIZUAR]",
            "MONEY": "[VLERA_ANONIMIZUAR]"
        }
        return placeholder_map.get(entity_label.upper(), f"[{entity_label}_ANONIMIZUAR]")


ALBANIAN_NER_SERVICE = AlbanianNERService()