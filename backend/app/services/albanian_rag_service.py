# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V13.0 (ROLLBACK TO NARRATIVE)
# 1. REVERT: Removed ID extraction for links.
# 2. KEEP: Retained 'Case Summary' injection to prevent amnesia.
# 3. FOCUS: Pure text context for rich descriptions.

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Protocol, cast, Any

from bson import ObjectId
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- PROTOCOLS ---
class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int, jurisdiction: str) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

class AlbanianRAGService:
    def __init__(
        self,
        vector_store: VectorStoreServiceProtocol,
        llm_client: Any, 
        language_detector: LanguageDetectorProtocol,
        db: Any
    ):
        self.vector_store = cast(VectorStoreServiceProtocol, vector_store)
        self.language_detector = language_detector
        self.db = db
        
        if DEEPSEEK_API_KEY:
            self.client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        else:
            self.client = None

    def _extract_search_terms(self, query: str) -> List[str]:
        potential_entities = re.findall(r'\b[A-Z][a-z]{2,}\b', query)
        cleaned_query = query.strip()
        if len(cleaned_query.split()) <= 3:
             potential_entities.append(cleaned_query)
        return list(set(potential_entities))

    async def _get_case_summary(self, case_id: str) -> str:
        try:
            if not self.db: return ""
            case = await self.db.cases.find_one({"_id": ObjectId(case_id)}, {"case_name": 1, "description": 1, "summary": 1, "title": 1})
            if not case: return ""
            
            summary_parts = []
            title = case.get('title') or case.get('case_name')
            if title:
                summary_parts.append(f"EMRI I RASTIT: {title}")
            if case.get('description'):
                summary_parts.append(f"PËRSHKRIMI: {case.get('description')}")
            if case.get('summary'):
                summary_parts.append(f"PËRMBLEDHJA AUTOMATIKE: {case.get('summary')}")
                
            return "\n".join(summary_parts)
        except Exception as e:
            logger.warning(f"Failed to fetch case summary: {e}")
            return ""

    async def retrieve_context(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        from .graph_service import graph_service
        from .embedding_service import generate_embedding

        case_summary = await self._get_case_summary(case_id)
        enriched_query = f"{case_summary}\n\nPyetja Specifike: {query}"

        try:
            query_embedding = await asyncio.to_thread(generate_embedding, enriched_query, 'standard')
            if not query_embedding:
                return ""
        except Exception as e:
            logger.error(f"RAG: Embedding generation failed: {e}")
            return ""

        search_terms = self._extract_search_terms(query)
        
        user_docs, kb_docs, graph_contradictions = [], [], ""
        graph_connections: List[str] = []

        async def fetch_graph_connections():
            tasks = [asyncio.to_thread(graph_service.find_hidden_connections, term) for term in search_terms]
            if not tasks: return []
            results = await asyncio.gather(*tasks, return_exceptions=True)
            flat_results = [item for sublist in results if isinstance(sublist, list) for item in sublist]
            return list(set(flat_results))

        try:
            results = await asyncio.gather(
                asyncio.to_thread(self.vector_store.query_by_vector, embedding=query_embedding, case_id=case_id, n_results=8, document_ids=document_ids),
                asyncio.to_thread(self.vector_store.query_legal_knowledge_base, embedding=query_embedding, n_results=3, jurisdiction='ks'),
                asyncio.to_thread(graph_service.find_contradictions, case_id),
                fetch_graph_connections(),
                return_exceptions=True
            )
            
            user_docs = results[0] if isinstance(results[0], list) else []
            kb_docs = results[1] if isinstance(results[1], list) else []
            graph_contradictions = results[2] if isinstance(results[2], str) and "No direct" not in results[2] else ""
            graph_connections = results[3] if isinstance(results[3], list) else []

        except Exception as e:
            logger.error(f"RAG: Retrieval Phase Error: {e}")

        context_parts = []

        if case_summary:
            context_parts.append(f"### PËRMBLEDHJA E RASTIT:\n{case_summary}")
        
        if graph_connections:
            connections_text = "\n".join([f"- {conn}" for conn in graph_connections])
            context_parts.append(f"### EVIDENCA NGA GRAFI:\n{connections_text}")

        if user_docs:
            # PHOENIX FIX: Removed ID from context string
            doc_chunks_text = "\n".join([f"{chunk.get('text', '')}" for chunk in user_docs])
            context_parts.append(f"### FRAGMENTE RELEVANTE NGA DOKUMENTET:\n{doc_chunks_text}")

        if graph_contradictions:
            context_parts.append(f"### KONTRADIKTAT E MUNDSHME:\n{graph_contradictions}")

        if kb_docs:
            # PHOENIX FIX: Removed ID from context string
            kb_text = "\n".join([f"Nga '{chunk.get('document_name', 'Ligj')}':\n{chunk.get('text', '')}\n---" for chunk in kb_docs])
            context_parts.append(f"### BAZA LIGJORE RELEVANTE:\n{kb_text}")
        
        if not context_parts: return ""
        return "\n\n".join(context_parts)

    async def chat(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        context = await self.retrieve_context(query, case_id, document_ids, jurisdiction)
        if not self.client: return "Klienti AI nuk është inicializuar."

        try:
            # REVERTED TO NARRATIVE PROMPT
            system_prompt = """
            Ti je 'Juristi AI', një Auditor Forensik i lartë.
            
            DETYRA: Analizo kontekstin dhe jep një përgjigje të detajuar, të strukturuar dhe profesionale.
            1. Përdor pika (bullet points) për qartësi.
            2. Cito burimet me saktësi nga teksti.
            3. Mos shpik fakte.
            """
            
            user_message = f"KONTEKSTI:\n{context}\n\nPYETJA: {query}"
            
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                temperature=0.0, 
                max_tokens=1500
            )
            return response.choices[0].message.content or "Gabim në gjenerim."
        except Exception as e:
            logger.error(f"Chat Error: {e}")
            return "Ndodhi një gabim gjatë procesimit të kërkesës."