# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - BRANDING UPDATE
# 1. SIGNATURE: Capitalized "Asistenti Sokratik" (Brand Name).
# 2. LOGIC: Remains unchanged (Hybrid Graph+Vector RAG).

import os
import asyncio
import logging
import httpx
import json
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any

# Import the graph service
from .graph_service import graph_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# Protocol Definitions
class LLMClientProtocol(Protocol):
    @property
    def chat(self) -> Any: ...

class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

class AlbanianRAGService:
    def __init__(
        self,
        vector_store: VectorStoreServiceProtocol,
        llm_client: LLMClientProtocol,
        language_detector: LanguageDetectorProtocol
    ):
        self.vector_store = cast(VectorStoreServiceProtocol, vector_store)
        self.llm_client = llm_client
        self.language_detector = language_detector
        self.fine_tuned_model = "llama-3.3-70b-versatile"
        
        self.EMBEDDING_TIMEOUT = 30.0
        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 15.0

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk: full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        if not chunks: return []
        unique_chunks = {c.get('text', ''): c for c in chunks}
        documents = list(unique_chunks.keys())
        chunk_map = unique_chunks
        try:
            async with httpx.AsyncClient(timeout=self.RERANK_TIMEOUT) as client:
                response = await client.post(
                    f"{self.AI_CORE_URL}/reranking/sort",
                    json={"query": query, "documents": documents}
                )
                response.raise_for_status()
                data = response.json()
                sorted_texts = data.get("reranked_documents", [])
                reranked = []
                for text in sorted_texts:
                    if text in chunk_map: reranked.append(chunk_map[text])
                return reranked
        except Exception as e:
            logger.warning(f"⚠️ Reranking failed: {e}")
            return list(unique_chunks.values())

    async def _call_local_llm(self, system_prompt: str, user_prompt: str) -> str:
        logger.info("🔄 TIER 2: Switching to Local LLM...")
        try:
            payload = {
                "model": LOCAL_MODEL_NAME,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "stream": False
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(LOCAL_LLM_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"❌ TIER 2 Failed: {e}")
            return ""

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        graph_knowledge = []
        
        try:
            from .embedding_service import generate_embedding

            # --- STEP 1: EMBED ---
            try:
                query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            except Exception:
                yield "Gabim Teknik: Embedding failed."
                return

            if not query_embedding:
                yield "Gabim Teknik: AI Core unresponsive."
                return

            # --- STEP 2: PARALLEL SEARCH ---
            async def safe_user_search():
                try:
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=8, document_ids=document_ids
                    )
                except Exception: return []

            async def safe_law_search():
                try:
                    return await asyncio.to_thread(
                        self.vector_store.query_legal_knowledge_base,
                        embedding=query_embedding, n_results=4 
                    )
                except Exception: return []

            async def safe_graph_search():
                try:
                    words = [w for w in query.split() if len(w) > 3]
                    connections = []
                    for word in words:
                        found = await asyncio.to_thread(graph_service.find_hidden_connections, word)
                        connections.extend(found)
                    return list(set(connections)) 
                except Exception as e:
                    logger.warning(f"Graph Search Error: {e}")
                    return []

            user_docs, law_docs, graph_results = await asyncio.gather(
                safe_user_search(), 
                safe_law_search(),
                safe_graph_search()
            )
            
            graph_knowledge = graph_results
            logger.info(f"🔍 RESULTS -> Vectors: {len(user_docs)}, Laws: {len(law_docs)}, Graph Nodes: {len(graph_results)}")

            all_candidates = user_docs + law_docs
            
            # --- STEP 3: RERANK ---
            if all_candidates:
                reranked = await self._rerank_chunks(query, all_candidates)
                relevant_chunks = reranked[:7] if reranked else all_candidates[:7]
            elif not graph_results:
                yield "Nuk munda të gjej informacion relevant në dokumentet, ligjet ose analizën grafike."
                return

        except Exception as e:
            logger.error(f"RAG Error: {e}")
            yield f"Gabim gjatë kërkimit: {str(e)}"
            return

        # --- STEP 4: GENERATE ---
        context_string = self._build_prompt_context(relevant_chunks, graph_knowledge)
        
        system_prompt = """
        Jeni "Juristi AI", ekspert ligjor për Kosovë dhe Shqipëri.
        Përdor kontekstin e dhënë për të përgjigjur saktë.
        
        Konteksti përmban:
        1. TEKST NGA DOKUMENTET (Përmbajtja).
        2. INFORMACION NGA GRAFI (Lidhjet, Datat, Entitetet).
        
        Nëse informacioni vjen nga GRAFI, thuaj "Sipas analizës së lidhjeve...".
        """
        user_prompt = f"KONTEKSTI:\n{context_string}\n\nPYETJA: {query}"

        # TIER 1: GROQ (CLOUD)
        tier1_failed = False
        try:
            stream = await self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.fine_tuned_model,
                temperature=0.1,
                stream=True,
            )
            async for chunk in stream:
                content = getattr(chunk.choices[0].delta, 'content', None)
                if content:
                    yield content
            
            # BRANDING CHANGE: Corrected Casing
            yield "\n\n**Burimi:** Asistenti Sokratik"
            return

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                logger.warning("⚠️ Cloud Limit Reached. Activating Tier 2.")
                tier1_failed = True
            else:
                tier1_failed = True

        # TIER 2: LOCAL LLM
        if tier1_failed:
            local_content = await self._call_local_llm(system_prompt, user_prompt)
            if local_content:
                yield "**[Mode: AI Lokale]**\n\n"
                yield local_content
                # BRANDING CHANGE: Corrected Casing
                yield "\n\n**Burimi:** Asistenti Sokratik"
                return
        
        # TIER 3: STATIC
        yield "\n\n⚠️ **Kufiri Ditor i AI është arritur.**\n"
        yield "Ja dokumentet dhe lidhjet që gjeta:\n\n"
        if graph_knowledge:
            yield "**🔗 Lidhjet e Gjetura (Graph):**\n"
            for rel in graph_knowledge[:5]:
                yield f"- {rel}\n"
            yield "\n"
        
        for i, doc in enumerate(relevant_chunks):
            name = doc.get('document_name', 'Dokument')
            yield f"{i+1}. **{name}**\n"

    def _build_prompt_context(self, chunks: List[Dict], graph_data: List[str]) -> str:
        parts = []
        if graph_data:
            parts.append("=== INFORMACION NGA GRAFI (LIDHJET) ===")
            parts.extend(graph_data)
            parts.append("=====================================\n")
        for chunk in chunks:
            doc_type = chunk.get('type', 'DOKUMENT')
            name = chunk.get('document_name', 'Burim')
            text = chunk.get('text', '')
            parts.append(f"[{doc_type} - {name}]: {text}")
        return "\n\n".join(parts)