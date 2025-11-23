# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - HYBRID RAG (Cloud -> Local -> Static)
# 1. TIER 1: Groq (High IQ, Streaming).
# 2. TIER 2: Local Ollama (Free, Fail-safe).
# 3. TIER 3: Document List (Ultimate Fallback).

import os
import asyncio
import logging
import httpx
import json
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any

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
        
        # Configuration
        self.EMBEDDING_TIMEOUT = 30.0
        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 15.0

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        """Non-streaming wrapper."""
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk:
                full_response_parts.append(chunk)
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
        """TIER 2: Internal Local AI Call"""
        logger.info("🔄 TIER 2: Switching to Local LLM...")
        try:
            payload = {
                "model": LOCAL_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
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

            # --- STEP 2: SEARCH ---
            async def safe_user_search():
                try:
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids
                    )
                except Exception: return []

            async def safe_law_search():
                try:
                    return await asyncio.to_thread(
                        self.vector_store.query_legal_knowledge_base,
                        embedding=query_embedding, n_results=5 
                    )
                except Exception: return []

            user_docs, law_docs = await asyncio.gather(safe_user_search(), safe_law_search())
            all_candidates = user_docs + law_docs
            
            # --- STEP 3: RERANK ---
            if all_candidates:
                reranked = await self._rerank_chunks(query, all_candidates)
                relevant_chunks = reranked[:7] if reranked else all_candidates[:7]
            else:
                yield "Nuk munda të gjej informacion relevant në dokumentet e çështjes ose në bazën ligjore."
                return

        except Exception as e:
            logger.error(f"RAG Error: {e}")
            yield f"Gabim gjatë kërkimit: {str(e)}"
            return

        # --- STEP 4: GENERATE (HYBRID TIERED SYSTEM) ---
        context_string = self._build_prompt_context(relevant_chunks)
        
        system_prompt = """
        Jeni "Juristi AI", ekspert ligjor për Kosovë dhe Shqipëri.
        Përdor VETËM kontekstin e mëposhtëm. Cito burimin.
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
            
            yield "\n\n**Burimi:** Juristi AI (Cloud)"
            return # Tier 1 Success

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                logger.warning("⚠️ Cloud Limit Reached. Activating Tier 2.")
                tier1_failed = True
            else:
                # Genuine error, but we try fallback anyway
                logger.error(f"Cloud Error: {e}")
                tier1_failed = True

        # TIER 2: LOCAL LLM (FALLBACK)
        if tier1_failed:
            local_content = await self._call_local_llm(system_prompt, user_prompt)
            if local_content:
                yield "**[Mode: AI Lokale]**\n\n"
                yield local_content
                yield "\n\n**Burimi:** Juristi AI (Local)"
                return # Tier 2 Success
        
        # TIER 3: STATIC LIST (FINAL SAFETY NET)
        yield "\n\n⚠️ **Kufiri Ditor i AI është arritur dhe AI Lokale nuk u përgjigj.**\n"
        yield "Ja dokumentet që gjeta për ju:\n\n"
        for i, doc in enumerate(relevant_chunks):
            name = doc.get('document_name', 'Dokument pa emër')
            yield f"{i+1}. **{name}**\n"

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            doc_type = chunk.get('type', 'DOKUMENT')
            name = chunk.get('document_name', 'Burim')
            text = chunk.get('text', '')
            parts.append(f"[{doc_type} - {name}]: {text}")
        return "\n\n".join(parts)