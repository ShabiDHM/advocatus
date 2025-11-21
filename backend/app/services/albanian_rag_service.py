# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - SMART RAG (DUAL SEARCH)
# 1. LOGIC: Tries Albanian embedding first.
# 2. FALLBACK: If no results, retries with Standard embedding.
# 3. RESULT: Finds documents regardless of detection errors during ingestion.

import os
import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class LLMClientProtocol(Protocol):
    @property
    def chat(self) -> Any: ...

class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...

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
        self.fine_tuned_model = os.getenv("ALBANIAN_FINETUNED_MODEL", "llama-3.3-70b-versatile")
        self.available_doc_ids: List[str] = []
        self.EMBEDDING_TIMEOUT = 10.0
        self.VECTOR_QUERY_TIMEOUT = 15.0 
        self.GROK_4_HEAVY_MODEL = os.getenv("HEAVY_LLM_MODEL", "llama-3.3-70b-versatile")

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk:
                full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        try:
            from .embedding_service import generate_embedding

            # --- STRATEGY 1: Try Albanian Search ---
            try:
                query_embedding_sq = await asyncio.wait_for(
                    asyncio.to_thread(generate_embedding, query, language='albanian'),
                    timeout=self.EMBEDDING_TIMEOUT
                )
                chunk_count = self._get_optimal_chunk_count(query)
                
                relevant_chunks = await asyncio.to_thread(
                    self.vector_store.query_by_vector,
                    embedding=query_embedding_sq, case_id=case_id, n_results=chunk_count, document_ids=document_ids
                )
            except Exception as e:
                logger.warning(f"RAG: Albanian search failed: {e}")

            # --- STRATEGY 2: Fallback to Standard Search if Albanian yielded nothing ---
            if not relevant_chunks:
                logger.info("RAG: No results with Albanian model. Retrying with Standard model...")
                try:
                    query_embedding_std = await asyncio.wait_for(
                        asyncio.to_thread(generate_embedding, query, language='standard'),
                        timeout=self.EMBEDDING_TIMEOUT
                    )
                    relevant_chunks = await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding_std, case_id=case_id, n_results=chunk_count, document_ids=document_ids
                    )
                except Exception as e:
                    logger.error(f"RAG: Standard search failed: {e}")

            if not relevant_chunks:
                logger.warning(f"RAG: No chunks found for query '{query}' in case {case_id} after dual search.")
                yield "Nuk munda të gjej informacion relevant në dokumentet e ngarkuara. (Provoni të rifreskoni faqen ose të ngarkoni dokumentin përsëri)."
                return

            logger.info(f"RAG: Retrieved {len(relevant_chunks)} chunks.")

        except Exception as e:
            logger.error(f"RAG Error during lookup: {e}", exc_info=True)
            yield f"Pata një gabim gjatë kërkimit: {str(e)}"
            return

        # --- Generation Phase ---
        self.available_doc_ids = list(set([chunk['document_id'] for chunk in relevant_chunks if 'document_id' in chunk]))
        context_string = self._build_prompt_context(relevant_chunks)
        user_prompt = self._build_user_prompt(query, context_string)
        system_prompt = self._get_system_prompt()
        selected_model = self._select_model_based_on_complexity(query, relevant_chunks)

        try:
            stream = await self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=selected_model,
                temperature=0.1,
                stream=True,
            )
            async for chunk in stream:
                content = getattr(chunk.choices[0].delta, 'content', None)
                if content:
                    yield content
                    
            yield "\n\n**Shënim:** Ky informacion bazohet në dokumentet e dorëzuara."

        except Exception as e:
            logger.error(f"RAG Generation Error: {e}", exc_info=True)
            yield "Pata një problem gjatë gjenerimit të përgjigjes."

    # Helpers
    def _get_optimal_chunk_count(self, query: str) -> int:
        return 7 if len(query.split()) > 20 else 5

    def _select_model_based_on_complexity(self, query: str, chunks: List[Dict]) -> str:
        return self.GROK_4_HEAVY_MODEL

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            name = chunk.get('document_name', 'Dokument')
            text = chunk.get('text', '')
            parts.append(f"BURIMI: {name}\nTEKSTI: {text}")
        return "\n\n---\n\n".join(parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        return f"Konteksti:\n{context}\n\nPyetja: {query}\nPërgjigju në Shqip duke përdorur vetëm kontekstin."

    def _get_system_prompt(self) -> str:
        return "Ti je një asistent ligjor. Përgjigju saktë dhe vetëm në bazë të fakteve të dhëna. Përgjigju në Shqip."