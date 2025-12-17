# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - CHAT RAG SYSTEM V11.1 (FINDINGS REMOVAL)
# 1. FIXED: Removed 'query_findings_by_similarity' from Protocol and Logic.
# 2. LOGIC: Relies solely on Document Vectors (with Source Injection) & Graph.
# 3. STATUS: Fully Synchronized.

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Protocol, cast, Any, Set
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
    # REMOVED: query_findings_by_similarity

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
        """
        Simple heuristic to extract potential entities (capitalized words) 
        to query the graph database specifically for them.
        """
        potential_entities = re.findall(r'\b[A-Z][a-z]{2,}\b', query)
        cleaned_query = query.strip()
        if len(cleaned_query.split()) <= 3:
             potential_entities.append(cleaned_query)
        return list(set(potential_entities))

    async def _get_case_summary(self, case_id: str) -> str:
        """Fetches the high-level summary of the case to ground the AI."""
        try:
            if not self.db: return ""
            case = await self.db.cases.find_one({"_id": ObjectId(case_id)}, {"case_name": 1, "description": 1, "summary": 1})
            if not case: return ""
            
            summary_parts = [f"EMRI I RASTIT: {case.get('case_name', 'Pa Emër')}"]
            if case.get('description'):
                summary_parts.append(f"PËRSHKRIMI I PËRGJITHSHËM: {case.get('description')}")
            if case.get('summary'): 
                summary_parts.append(f"PËRMBLEDHJA E RASTIT: {case.get('summary')}")
                
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
        """
        Retrieves and assembles a rich, multi-source context dossier.
        """
        from .graph_service import graph_service
        from .embedding_service import generate_embedding

        try:
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            if not query_embedding:
                return ""
        except Exception as e:
            logger.error(f"RAG: Embedding generation failed: {e}")
            return ""

        search_terms = self._extract_search_terms(query)
        
        user_docs, kb_docs, graph_contradictions = [], [], ""
        graph_connections: List[str] = []
        case_summary = ""

        async def fetch_graph_connections():
            """Fetch connections for each detected entity in the query"""
            tasks = []
            for term in search_terms:
                tasks.append(asyncio.to_thread(graph_service.find_hidden_connections, term))
            if not tasks: return []
            results = await asyncio.gather(*tasks, return_exceptions=True)
            flat_results = []
            for res in results:
                if isinstance(res, list):
                    flat_results.extend(res)
            return list(set(flat_results))

        try:
            # REMOVED: query_findings_by_similarity from gather
            results = await asyncio.gather(
                asyncio.to_thread(self.vector_store.query_by_vector, embedding=query_embedding, case_id=case_id, n_results=8, document_ids=document_ids), # Increased chunks to 8
                asyncio.to_thread(self.vector_store.query_legal_knowledge_base, embedding=query_embedding, n_results=3, jurisdiction='ks'),
                asyncio.to_thread(graph_service.find_contradictions, case_id),
                fetch_graph_connections(),
                self._get_case_summary(case_id),
                return_exceptions=True
            )
            
            user_docs = results[0] if isinstance(results[0], list) else []
            kb_docs = results[1] if isinstance(results[1], list) else []
            graph_contradictions = results[2] if isinstance(results[2], str) and "No direct" not in results[2] else ""
            graph_connections = results[3] if isinstance(results[3], list) else []
            case_summary = results[4] if isinstance(results[4], str) else ""

        except Exception as e:
            logger.error(f"RAG: Retrieval Phase Error: {e}")

        context_parts = []

        # 0. Global Case Context
        if case_summary:
            context_parts.append(f"### INFORMACIONI I PËRGJITHSHËM I RASTIT:\n{case_summary}")
        
        # 1. Direct Graph Evidence
        if graph_connections:
            connections_text = "\n".join([f"- {conn}" for conn in graph_connections])
            context_parts.append(f"### EVIDENCA DIREKTE NGA GRAFI (Lidhjet e Gjetura):\n{connections_text}")

        # 2. Document Fragments (Now with Source Injection from Vector Store)
        if user_docs:
            doc_chunks_text = "\n".join([f"Fragment nga '{chunk.get('document_name', 'Unknown')}':\n{chunk.get('text', '')}\n---" for chunk in user_docs])
            context_parts.append(f"### FRAGMENTE RELEVANTE NGA DOKUMENTET:\n{doc_chunks_text}")

        # 3. Graph Contradictions
        if graph_contradictions:
            context_parts.append(f"### INTELIGJENCA E GRAFIT (Kontradiktat në Çështje):\n{graph_contradictions}")

        # 4. External Law
        if kb_docs:
            kb_text = "\n".join([f"Nga '{chunk.get('document_name', 'Ligj')}':\n{chunk.get('text', '')}\n---" for chunk in kb_docs])
            context_parts.append(f"### BAZA LIGJORE (LIGJET E KOSOVËS):\n{kb_text}")
        
        if not context_parts: return ""
        return "\n\n".join(context_parts)

    async def chat(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        """
        Fallback Chat Method.
        """
        context = await self.retrieve_context(query, case_id, document_ids, jurisdiction)
        if not self.client: return "Klienti AI nuk është inicializuar."

        try:
            system_prompt = """
            Ti je 'Juristi AI', një asistent ligjor strikt dhe preciz.
            
            UDHËZIME TË PANIGOCIUESHME:
            1. Përgjigju VETËM duke u bazuar në KONTEKSTIN e dhënë më poshtë.
            2. Nëse informacioni nuk gjendet në kontekst, thuaj: "Nuk kam informacion të mjaftueshëm në dokumente për t'ju përgjigjur kësaj pyetjeje."
            3. MOS shpik fakte. MOS përdor njohuri të jashtme përveç termave ligjorë bazë.
            4. Cito burimin (p.sh., "Sipas grafit...", "Sipas dokumentit X...").
            5. Përdor Markdown për qartësi.
            """
            
            user_message = f"KONTEKSTI EKSKLUZIV:\n{context}\n\nPYETJA: {query}"
            
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                temperature=0.0, 
                max_tokens=1000
            )
            return response.choices[0].message.content or "Gabim në gjenerim."
        except Exception as e:
            logger.error(f"Chat Error: {e}")
            return "Ndodhi një gabim gjatë procesimit të kërkesës."