# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL MODIFICATION 2.1
# 1. ADDED: 'chat()' method to satisfy the strict interface requirement of chat_service.py.
#    (This fixes the "AI Unavailable" fallback error).
# 2. RETAINED: The async timeout fix for preventing vector store hangs.

import os
import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --- READ-ONLY PROTOCOL DEFINITIONS ---
class LLMClientProtocol(Protocol):
    @property
    def chat(self) -> Any: ...

class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

# --- SERVICE IMPLEMENTATION ---

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
        self.fine_tuned_model = os.getenv("ALBANIAN_FINETUNED_MODEL", "llama-3.1-8b-instant")
        self.available_doc_ids: List[str] = []

        # Configuration constants
        self.EMBEDDING_TIMEOUT = 10.0
        self.VECTOR_QUERY_TIMEOUT = 15.0 
        self.GROK_4_HEAVY_MODEL = os.getenv("HEAVY_LLM_MODEL", "llama3-70b-8192")

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        """
        Non-streaming wrapper for chat_stream. 
        Consumes the stream and returns the full complete string.
        REQUIRED for compatibility with standard HTTP chat endpoints.
        """
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk:
                full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        try:
            # Lazy import to avoid circular dependency issues
            from .embedding_service import generate_embedding

            try:
                query_embedding = await asyncio.wait_for(
                    asyncio.to_thread(generate_embedding, query),
                    timeout=self.EMBEDDING_TIMEOUT
                )
            except asyncio.TimeoutError:
                yield "Servisi i kërkimit është i zënë. Ju lutem provoni përsëri pas disa minutash."
                return

            chunk_count = self._get_optimal_chunk_count(query)

            # --- PHOENIX PROTOCOL HANG FIX ---
            try:
                relevant_chunks = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=chunk_count, document_ids=document_ids
                    ),
                    timeout=self.VECTOR_QUERY_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"RAG Timeout: Vector store query exceeded {self.VECTOR_QUERY_TIMEOUT}s for case {case_id}.")
                yield "Kërkimi i dokumenteve zgjati më shumë se normalisht dhe u ndërpre. Kjo mund të ndodhë nëse është hera e parë që pyesni për këtë çështje. Provoni përsëri."
                return
            # --- END FIX ---

            if not relevant_chunks:
                yield "Nuk munda të gjej informacion relevant në dokumentet e ngarkuara."
                return

            logger.info(f"RAG: Retrieved {len(relevant_chunks)} chunks for LLM context.")

        except Exception as e:
            logger.error(f"RAG Error during document lookup for case {case_id}: {e}", exc_info=True)
            yield f"Pata një gabim gjatë kërkimit të dokumenteve: {str(e)}"
            return

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

            yield "\n\n**Shënim:** Ky informacion bazohet në dokumentet e dorëzuara dhe nuk zëvendëson këshillën profesionale ligjore."

        except Exception as e:
            logger.error(f"RAG Error during LLM generation: {e}", exc_info=True)
            yield f"Pata një gabim të brendshëm gjatë gjenerimit të përgjigjes: {str(e)}"

    # (All helper methods below this line remain unchanged)
    def _get_optimal_chunk_count(self, query: str) -> int:
        query_length = len(query.split())
        complex_indicators = ['analizë', 'interpretim', 'risk', 'kontratë', 'ligj', 'rregullore', 'pasojat']
        has_complex_indicators = any(indicator in query.lower() for indicator in complex_indicators)
        if query_length < 10 and not has_complex_indicators: return 3
        elif query_length > 40 or has_complex_indicators: return 7
        return 5

    def _select_model_based_on_complexity(self, query: str, chunks: List[Dict]) -> str:
        complex_indicators = ['analizë', 'interpretim', 'risk', 'kontratë komplekse', 'parashikim', 'pasojë juridike']
        query_complex = any(indicator in query.lower() for indicator in complex_indicators)
        has_multiple_sources = len(chunks) >= 5
        if query_complex or has_multiple_sources: return self.GROK_4_HEAVY_MODEL
        else: return self.fine_tuned_model

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        context_parts = []
        for chunk in chunks:
            doc_id = chunk.get('document_id', 'N/A')
            doc_name = chunk.get('document_name', f'Dokumenti {doc_id}')
            content = chunk.get('text', '')
            context_parts.append(f"BURIMI: {doc_name}\nPERMBAJTJA:\n\"\"\"\n{content}\n\"\"\"")
        return "\n\n---\n\n".join(context_parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        return f"""Konteksti i Dokumenteve Burimore:
---
{context}
---
Pyetja e Përdoruesit:
"{query}"
Përgjigju shkurtimisht dhe drejtpërdrejt, duke u bazuar VETËM në FAKTET nga KONTEKSTI i dhënë. Nëse informacioni nuk gjendet, thuaj 'Informacioni nuk gjendet në dokumentet e ofruara.' Përgjigja duhet të jetë në Shqip."""

    def _get_system_prompt(self) -> str:
        return f"""Ti je një asistent ligjor shqiptar i fokusuar te PËRGJIGJET E FAKTUARA.
Rregullat:
1. Përdor VETËM kontekstin e ofruar.
2. Jepi përgjigje PRECIZE dhe SHKURTRA.
3. Nëse nuk ka informacion, thuaj 'Informacioni nuk gjendet në dokumentet e ofruara.'
4. Mos shpik fakte.
5. Përgjigju gjithmonë në Shqip.
Fillo përgjigjen direkt."""