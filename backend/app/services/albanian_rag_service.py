# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - DUAL RAG & FAIL-SAFE EXECUTION
# 1. FEATURE: Searches User Docs AND Law Library in parallel.
# 2. SAFETY: Uses try/except inside asyncio.gather to prevent total crash.
# 3. DEBUG: Logs vector generation and search results count.

import os
import asyncio
import logging
import httpx
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any

logger = logging.getLogger(__name__)

class LLMClientProtocol(Protocol):
    @property
    def chat(self) -> Any: ...

# UPDATED PROTOCOL: Includes Knowledge Base query capability
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
        self.available_doc_ids: List[str] = []
        
        # Configuration
        self.EMBEDDING_TIMEOUT = 60.0
        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 30.0

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk:
                full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Sends candidate chunks to Juristi AI Core for semantic reranking.
        """
        if not chunks:
            return []
            
        # Deduplicate chunks based on text content to avoid repetition
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
        relevant_chunks = []
        try:
            from .embedding_service import generate_embedding

            # 1. Embed the Query
            try:
                query_embedding = await asyncio.wait_for(
                    asyncio.to_thread(generate_embedding, query, language='standard'),
                    timeout=self.EMBEDDING_TIMEOUT
                )
                
                # --- DEBUG VECTOR ---
                if query_embedding:
                    logger.info(f"🧬 Vector Generated. Length: {len(query_embedding)}")
                else:
                    logger.error("❌ Vector is None!")
                    yield "Gabim teknik: Vektori nuk u gjenerua."
                    return
                # --------------------

                # 2. DUAL SEARCH (FAIL-SAFE WRAPPERS)
                # We wrap calls to prevent one failure from stopping the other
                
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

                # Execute safely in parallel
                user_docs, law_docs = await asyncio.gather(safe_user_search(), safe_law_search())
                
                # --- DIAGNOSTIC LOGS ---
                logger.info(f"🔍 RAG DIAGNOSIS -> User Docs: {len(user_docs)} | Law Docs: {len(law_docs)}")
                if law_docs:
                    logger.info(f"📜 Top Law Found: {law_docs[0].get('document_name')}")
                # -----------------------

                # Combine results
                all_candidates = user_docs + law_docs
                
                # 3. Unified Reranking with Fallback
                if all_candidates:
                    reranked_chunks = await self._rerank_chunks(query, all_candidates)
                    
                    if not reranked_chunks:
                        logger.warning("⚠️ Reranker returned 0 results. Falling back to raw results.")
                        relevant_chunks = all_candidates[:7]
                    else:
                        # Keep Top 7
                        relevant_chunks = reranked_chunks[:7]
                else:
                    relevant_chunks = []

            except Exception as e:
                logger.error(f"RAG Workflow Failed: {e}", exc_info=True)

            if not relevant_chunks:
                yield "Nuk munda të gjej informacion relevant në dokumentet e çështjes ose në bazën ligjore."
                return

        except Exception as e:
            logger.error(f"RAG Critical Error: {e}", exc_info=True)
            yield f"Gabim teknik: {str(e)}"
            return

        # 4. Generate Response
        context_string = self._build_prompt_context(relevant_chunks)
        
        system_prompt = """
        Jeni "Juristi AI", ekspert ligjor për hapësirën shqipfolëse (Kosovë dhe Shqipëri).

        PROTOKOLLI I JURIDIKSIONIT:
        1. **Identifiko Vendin:** 
           - "Prishtinë", "EUR", "Gjykata Themelore" -> KOSOVË. 
           - "Tiranë", "LEK", "Gjykata e Rrethit" -> SHQIPËRI.
        2. **Default:** Nëse nuk specifikohet, supozo se zbatohet ligji i **Republikës së Kosovës**.
        
        UDHËZIME TË OPERIMIT:
        - Përdor KONTEKSTIN e dhënë më poshtë (Dokumente dhe Ligje).
        - Nëse pyetja është ligjore, cito saktë nga seksioni "LIGJI" (psh. "Sipas Nenit 4...").
        - Përgjigju në gjuhën e pyetjes.

        Nëse konteksti nuk mjafton, thuaj: "Nuk kam informacion të mjaftueshëm në dokumentet e ofruara ose në bibliotekën ligjore."
        """
        
        user_prompt = f"""
        KONTEKSTI (DOKUMENTE DHE LIGJE):
        {context_string}
        
        PYETJA: 
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
                    
            yield "\n\n**Burimi:** Juristi AI"

        except Exception as e:
            logger.error(f"RAG Generation Error: {e}", exc_info=True)
            yield "Ndodhi një gabim gjatë gjenerimit."

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            doc_type = chunk.get('type', 'DOKUMENT') # 'LAW' or 'DOKUMENT'
            name = chunk.get('document_name', 'Burim')
            text = chunk.get('text', '')
            
            label = "LIGJI (BAZA LIGJORE)" if doc_type == "LAW" else "DOKUMENTI I ÇËSHTJES"
            parts.append(f"[{label}]: {name}\n{text}")
            
        return "\n\n---\n\n".join(parts)