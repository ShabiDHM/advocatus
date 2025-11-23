# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - FAIL-SAFE RAG
# 1. QUOTA PROTECTION: Detects AI Limit errors and falls back to "Document Search Mode".
# 2. DUAL SEARCH: Searches Local Documents AND Knowledge Base safely.
# 3. NO-CRASH GUARANTEE: Even if Grok/xAI is down, the user gets search results.

import os
import asyncio
import logging
import httpx
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any

logger = logging.getLogger(__name__)

# Protocol Definitions for Dependency Injection
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
        """
        Non-streaming wrapper for the chat interface.
        """
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk:
                full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Sends candidate chunks to AI Core for semantic reranking.
        """
        if not chunks:
            return []
            
        # Deduplicate based on text content
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
                
                reranked_chunks = []
                for text in sorted_texts:
                    if text in chunk_map:
                        reranked_chunks.append(chunk_map[text])
                
                return reranked_chunks
                
        except Exception as e:
            logger.warning(f"⚠️ [RAG] Reranking failed (falling back to vector order): {e}")
            return list(unique_chunks.values())

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        """
        The Core Logic:
        1. Generate Vector (Embed Query).
        2. Search DB (User Docs + Law).
        3. Rerank Results.
        4. Ask AI to Summarize (With Quota Catch).
        """
        relevant_chunks = []
        try:
            # Import inside method to avoid circular imports during startup
            from .embedding_service import generate_embedding

            # --- STEP 1: GENERATE VECTOR ---
            query_embedding = None
            try:
                # Run sync function in thread
                query_embedding = await asyncio.to_thread(
                    generate_embedding, query, 'standard'
                )
            except Exception as e:
                logger.error(f"❌ Embedding Generation Failed: {e}")
                # If we can't generate a vector, we can't search. Stop here.
                yield "Gabim Teknik: Nuk u arrit të gjenerohej kërkimi (Embedding Error)."
                return

            if not query_embedding:
                logger.error("❌ Vector is None!")
                yield "Gabim Teknik: Shërbimi i AI nuk u përgjigj."
                return

            # --- STEP 2: DUAL SEARCH ---
            async def safe_user_search():
                try:
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, 
                        case_id=case_id, 
                        n_results=10, 
                        document_ids=document_ids
                    )
                except Exception as e:
                    logger.error(f"❌ User Doc Search Failed: {e}")
                    return []

            async def safe_law_search():
                try:
                    return await asyncio.to_thread(
                        self.vector_store.query_legal_knowledge_base,
                        embedding=query_embedding,
                        n_results=5 
                    )
                except Exception as e:
                    logger.error(f"❌ Law Search Failed: {e}")
                    return []

            user_docs, law_docs = await asyncio.gather(safe_user_search(), safe_law_search())
            
            # --- DEBUG LOGS ---
            logger.info(f"🔍 RAG RESULTS -> User Docs: {len(user_docs)} | Law Docs: {len(law_docs)}")

            all_candidates = user_docs + law_docs
            
            # --- STEP 3: RERANKING ---
            if all_candidates:
                reranked_chunks = await self._rerank_chunks(query, all_candidates)
                if not reranked_chunks:
                    relevant_chunks = all_candidates[:7]
                else:
                    relevant_chunks = reranked_chunks[:7]
            else:
                relevant_chunks = []

            if not relevant_chunks:
                yield "Nuk munda të gjej informacion relevant në dokumentet e çështjes ose në bazën ligjore."
                return

        except Exception as e:
            logger.error(f"RAG Critical Error: {e}", exc_info=True)
            yield f"Gabim gjatë kërkimit: {str(e)}"
            return

        # --- STEP 4: GENERATE ANSWER (WITH QUOTA PROTECTION) ---
        context_string = self._build_prompt_context(relevant_chunks)
        
        system_prompt = """
        Jeni "Juristi AI", ekspert ligjor për Kosovë dhe Shqipëri.
        
        RREGULLAT:
        1. Përdor VETËM kontekstin e mëposhtëm.
        2. Cito burimin (psh. "Sipas Kontratës...").
        3. Nëse konteksti nuk mjafton, thuaj "Nuk e di".
        """
        
        user_prompt = f"KONTEKSTI:\n{context_string}\n\nPYETJA: {query}"

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
                    
            yield "\n\n**Burimi:** Juristi AI"

        except Exception as e:
            # --- THE SAFETY NET ---
            error_str = str(e).lower()
            logger.warning(f"⚠️ AI Generation Failed: {error_str}")
            
            if "rate limit" in error_str or "quota" in error_str or "429" in error_str or "billing" in error_str:
                yield "\n\n⚠️ **Kufiri Ditor i AI është arritur.**\n"
                yield "Nuk mund të gjeneroj një përgjigje të re tani, por ja dokumentet që gjeta për ju:\n\n"
                for i, doc in enumerate(relevant_chunks):
                    name = doc.get('document_name', 'Dokument pa emër')
                    yield f"{i+1}. **{name}**\n"
            else:
                yield "\n\n⚠️ Ndodhi një gabim gjatë gjenerimit të përgjigjes, por dokumentet u gjetën me sukses."

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            doc_type = chunk.get('type', 'DOKUMENT')
            name = chunk.get('document_name', 'Burim')
            text = chunk.get('text', '')
            parts.append(f"[{doc_type} - {name}]: {text}")
        return "\n\n".join(parts)