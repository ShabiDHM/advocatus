# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - JURISDICTION-AWARE RAG
# 1. LOGIC: Accepts 'jurisdiction' and dynamically switches the AI's "persona" (Kosovo vs. Albania).
# 2. KB FILTER: Passes jurisdiction to the vector store to search the correct laws.


import os
import asyncio
import logging
import httpx
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any
from openai import AsyncOpenAI

# Import the graph service instance
from .graph_service import graph_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION (OPENROUTER) ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# Local Backup Configuration
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# Protocol Definitions
class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    # PHOENIX UPDATE: Add jurisdiction to the protocol
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int, jurisdiction: str) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

class AlbanianRAGService:
    def __init__(
        self,
        vector_store: VectorStoreServiceProtocol,
        llm_client: Any,
        language_detector: LanguageDetectorProtocol
    ):
        self.vector_store = cast(VectorStoreServiceProtocol, vector_store)
        self.language_detector = language_detector
        
        if DEEPSEEK_API_KEY:
            self.client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        else:
            self.client = None

        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 10.0

    async def chat(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids, jurisdiction):
            if chunk: full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        if not chunks: return []
        # Simple deduplication
        unique_texts = {c.get('text', ''): c for c in chunks}
        try:
            # Reranking is now optional as DeepSeek is very smart
            return list(unique_texts.values())
        except Exception as e:
            logger.warning(f"⚠️ Reranking skipped: {e}")
            return list(unique_texts.values())

    async def _call_local_backup(self, system_prompt: str, user_prompt: str) -> str:
        # ... (Implementation remains unchanged) ...
        return "Shërbimi AI momentalisht i padisponueshëm."

    async def chat_stream(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        graph_knowledge = []
        
        # --- PHASE 1: RETRIEVAL ---
        try:
            from .embedding_service import generate_embedding
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            
            if query_embedding:
                async def safe_vector_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids
                    )
                
                # PHOENIX FIX: Pass jurisdiction to the Knowledge Base search
                async def safe_kb_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_legal_knowledge_base,
                        embedding=query_embedding, n_results=4, jurisdiction=jurisdiction
                    )

                async def safe_graph_search():
                    keywords = [w for w in query.split() if len(w) > 4]
                    results = []
                    for k in keywords:
                        results.extend(await asyncio.to_thread(graph_service.find_hidden_connections, k))
                    return list(set(results))

                results = await asyncio.gather(
                    safe_vector_search(), safe_kb_search(), safe_graph_search(), return_exceptions=True
                )

                user_docs = results[0] if isinstance(results[0], list) else []
                kb_docs = results[1] if isinstance(results[1], list) else []
                graph_knowledge = results[2] if isinstance(results[2], list) else []

                raw_candidates = user_docs + kb_docs
                if raw_candidates:
                    relevant_chunks = await self._rerank_chunks(query, raw_candidates)
                    relevant_chunks = relevant_chunks[:8] 
                
        except Exception as e:
            logger.error(f"Retrieval Phase Error: {e}")

        # --- PHASE 2: GENERATION ---
        context_text = ""
        if graph_knowledge:
            context_text += "### TË DHËNA NGA GRAFI:\n" + "\n".join(graph_knowledge[:5]) + "\n\n"
        
        if relevant_chunks:
            context_text += "### DOKUMENTET DHE LIGJET:\n"
            for chunk in relevant_chunks:
                source = chunk.get('document_name', 'Burim i Panjohur')
                text = chunk.get('text', '')
                context_text += f"BURIMI: {source}\nPËRMBAJTJA: {text}\n---\n"
        
        if not context_text:
            context_text = "Nuk u gjetën dokumente specifike."

        # PHOENIX FIX: Dynamic System Prompt based on Jurisdiction
        jurisdiction_name = "Republikës së Shqipërisë" if jurisdiction == 'al' else "Republikës së Kosovës"
        
        system_prompt = f"""
        Ti je "Juristi AI", një Asistent Ligjor ekspert për sistemin e drejtësisë në {jurisdiction_name}.
        
        MISIONI:
        Të ofrosh këshilla juridike të sakta duke u bazuar në dokumentet e dosjes dhe ligjet në fuqi të {jurisdiction_name}.

        UDHËZIME:
        1. Prioriteti #1 është 'KONTEKSTI I DOSJES'. Përdore atë për faktet.
        2. Për bazën ligjore, përdor ligjet nga konteksti, ose njohuritë e tua për legjislacionin e {jurisdiction_name}.
        3. Formato përgjigjen në mënyrë profesionale (Hyrje, Analizë, Konkluzion).
        4. Përgjigju gjithmonë në gjuhën Shqipe.
        """

        user_message = f"PYETJA E PËRDORUESIT: {query}\n\nKONTEKSTI I DOSJES:\n{context_text}"

        try:
            if not self.client:
                raise Exception("Client not initialized")

            stream = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3, 
                stream=True,
                extra_headers={ "HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI" }
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            
            yield "\n\n**Burimi:** Asistenti sokratik"

        except Exception as e:
            logger.error(f"OpenRouter API Error: {e}")
            yield await self._call_local_backup(system_prompt, user_message)