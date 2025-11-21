# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - MULTILINGUAL RAG
# 1. PROMPT: Updated to "Reply in the language of the query".
# 2. CAPABILITY: Now supports Serbian, English, and Albanian questions seamlessly.

import os
import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any

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
        # Use the versatile model for best multilingual performance
        self.fine_tuned_model = "llama-3.3-70b-versatile"
        self.available_doc_ids: List[str] = []
        self.EMBEDDING_TIMEOUT = 10.0
        self.VECTOR_QUERY_TIMEOUT = 15.0 
        self.GROK_4_HEAVY_MODEL = "llama-3.3-70b-versatile"

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

            # Always use standard embedding for consistent multilingual support
            try:
                query_embedding = await asyncio.wait_for(
                    asyncio.to_thread(generate_embedding, query, language='standard'),
                    timeout=self.EMBEDDING_TIMEOUT
                )
                chunk_count = 5
                relevant_chunks = await asyncio.to_thread(
                    self.vector_store.query_by_vector,
                    embedding=query_embedding, case_id=case_id, n_results=chunk_count, document_ids=document_ids
                )
            except Exception as e:
                logger.error(f"RAG Search failed: {e}")

            if not relevant_chunks:
                yield "Nuk munda të gjej informacion relevant. / I couldn't find relevant information. / Nisam mogao pronaći relevantne informacije."
                return

        except Exception as e:
            logger.error(f"RAG Error: {e}", exc_info=True)
            yield f"Error: {str(e)}"
            return

        # --- Generation Phase ---
        context_string = self._build_prompt_context(relevant_chunks)
        
        # PHOENIX FIX: Multilingual System Prompt
        system_prompt = """
        You are a professional legal AI assistant.
        1. Analyze the provided Context strictly.
        2. Answer the User's Question accurately based ONLY on the Context.
        3. **LANGUAGE INSTRUCTION:** Detect the language of the User's Question (Albanian, Serbian, English, etc.) and reply in that SAME language.
        """
        
        user_prompt = f"""
        CONTEXT:
        {context_string}
        
        USER QUESTION: 
        {query}
        """

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
                    
            yield "\n\n**Note:** AI generated response based on provided documents."

        except Exception as e:
            logger.error(f"RAG Generation Error: {e}", exc_info=True)
            yield "Error generating response."

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            name = chunk.get('document_name', 'Doc')
            text = chunk.get('text', '')
            parts.append(f"SOURCE: {name}\nCONTENT: {text}")
        return "\n\n---\n\n".join(parts)