import os
import asyncio
import logging
import httpx
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
        self.fine_tuned_model = "llama-3.3-70b-versatile"
        self.available_doc_ids: List[str] = []
        
        # Configuration
        self.EMBEDDING_TIMEOUT = 60.0  # Increased for BGE-M3
        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 30.0     # Increased for BGE-Reranker-M3

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
            
        # 1. Prepare data
        text_to_chunk_map = {c.get('text', ''): c for c in chunks}
        documents = list(text_to_chunk_map.keys())
        
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
                    if text in text_to_chunk_map:
                        reranked_chunks.append(text_to_chunk_map[text])
                
                return reranked_chunks
                
        except Exception as e:
            logger.warning(f"⚠️ [RAG] Reranking failed (falling back to vector order): {e}")
            return chunks

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        try:
            from .embedding_service import generate_embedding

            # 1. Embed
            try:
                query_embedding = await asyncio.wait_for(
                    asyncio.to_thread(generate_embedding, query, language='standard'),
                    timeout=self.EMBEDDING_TIMEOUT
                )
                
                # 2. Retrieve
                initial_fetch_count = 15
                raw_chunks = await asyncio.to_thread(
                    self.vector_store.query_by_vector,
                    embedding=query_embedding, 
                    case_id=case_id, 
                    n_results=initial_fetch_count, 
                    document_ids=document_ids
                )
                
                # 3. Rerank
                if raw_chunks:
                    reranked_chunks = await self._rerank_chunks(query, raw_chunks)
                    relevant_chunks = reranked_chunks[:5]
                else:
                    relevant_chunks = []

            except Exception as e:
                logger.error(f"RAG Search/Rerank failed: {e}")

            if not relevant_chunks:
                yield "Nuk munda të gjej informacion relevant në dokumentet e çështjes."
                return

        except Exception as e:
            logger.error(f"RAG Error: {e}", exc_info=True)
            yield f"Gabim teknik: {str(e)}"
            return

        # 4. Generate
        context_string = self._build_prompt_context(relevant_chunks)
        
        # PHOENIX FIX: DUAL JURISDICTION (KOSOVO + ALBANIA)
        system_prompt = """
        Jeni "Juristi AI", ekspert ligjor për hapësirën shqipfolëse (Kosovë dhe Shqipëri).

        PROTOKOLLI I JURIDIKSIONIT:
        1. **Identifiko Vendin:** Analizo dokumentet për të kuptuar vendin (p.sh., "Prishtinë", "EUR", "Gjykata Themelore" = KOSOVË. "Tiranë", "LEK", "Gjykata e Rrethit" = SHQIPËRI).
        2. **Supozimi i Parazgjedhur (Default):** Nëse dokumenti nuk specifikon vendin, supozo se zbatohet ligji i **Republikës së Kosovës** (Ligji për Marrëdhëniet e Detyrimeve, Kodi Penal i Kosovës).
        3. **Përgjigja e Dyfishtë:** Nëse pyetja është e përgjithshme dhe ka dallime thelbësore, cito ligjin e Kosovës fillimisht, pastaj atë të Shqipërisë.

        UDHËZIME TË TJERA:
        - Përgjigju VETËM bazuar në KONTEKSTIN e dhënë më poshtë.
        - Mos shpik ligje. Nëse dokumenti nuk e përmend ligjin, thuaj: "Dokumenti nuk citon ligjin specifik, por në kontekstin e Kosovës kjo rregullohet zakonisht nga..."
        - Përdor gjuhën e pyetjes (Shqip/Anglisht/Serbisht).

        Qëllimi yt është të japësh interpretim saktë juridik duke i dhënë përparësi kontekstit të Kosovës kur ka paqartësi.
        """
        
        user_prompt = f"""
        KONTEKSTI NGA DOKUMENTET:
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
                    
            yield "\n\n**Burimi:** Juristi AI (Analizë e dokumenteve të ofruara)"

        except Exception as e:
            logger.error(f"RAG Generation Error: {e}", exc_info=True)
            yield "Ndodhi një gabim gjatë gjenerimit."

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            name = chunk.get('document_name', 'Dokument')
            text = chunk.get('text', '')
            parts.append(f"BURIMI: {name}\nTEKSTI: {text}")
        return "\n\n---\n\n".join(parts)