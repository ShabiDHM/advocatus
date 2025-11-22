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
        self.EMBEDDING_TIMEOUT = 10.0
        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 10.0

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
            
        # 1. Prepare data: Map text back to chunk objects to reconstruct order
        text_to_chunk_map = {c.get('text', ''): c for c in chunks}
        documents = list(text_to_chunk_map.keys())
        
        try:
            # 2. Call the Unified AI Core
            async with httpx.AsyncClient(timeout=self.RERANK_TIMEOUT) as client:
                response = await client.post(
                    f"{self.AI_CORE_URL}/reranking/sort",
                    json={"query": query, "documents": documents}
                )
                response.raise_for_status()
                data = response.json()
                
                # 3. Reconstruct list in new sorted order
                sorted_texts = data.get("reranked_documents", [])
                reranked_chunks = []
                for text in sorted_texts:
                    if text in text_to_chunk_map:
                        reranked_chunks.append(text_to_chunk_map[text])
                
                return reranked_chunks
                
        except Exception as e:
            logger.warning(f"⚠️ [RAG] Reranking failed (falling back to vector order): {e}")
            # Fallback: return original list
            return chunks

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
                
                # 2. High Recall Retrieval (Fetch 15, Keep 5)
                initial_fetch_count = 15
                
                raw_chunks = await asyncio.to_thread(
                    self.vector_store.query_by_vector,
                    embedding=query_embedding, 
                    case_id=case_id, 
                    n_results=initial_fetch_count, 
                    document_ids=document_ids
                )
                
                # 3. High Precision Reranking (Juristi AI Core)
                if raw_chunks:
                    reranked_chunks = await self._rerank_chunks(query, raw_chunks)
                    # Keep only the Top 5 most relevant
                    relevant_chunks = reranked_chunks[:5]
                else:
                    relevant_chunks = []

            except Exception as e:
                logger.error(f"RAG Search/Rerank failed: {e}")

            if not relevant_chunks:
                yield "Nuk munda të gjej informacion relevant në dokumentet e çështjes. / I couldn't find relevant information. / Nisam mogao pronaći relevantne informacije."
                return

        except Exception as e:
            logger.error(f"RAG Error: {e}", exc_info=True)
            yield f"Gabim gjatë kërkimit: {str(e)}"
            return

        # 4. Context Construction & Generation
        context_string = self._build_prompt_context(relevant_chunks)
        
        # PHOENIX FIX: KOSOVO JURISDICTION SPECIALIZATION
        system_prompt = """
        Jeni "Juristi AI", asistent ligjor i avancuar i specializuar për legjislacionin dhe praktikën ligjore të Republikës së Kosovës.

        UDHËZIME STRIKTE TË OPERIMIT:
        1. **Baza Ligjore:** Përgjigju VETËM duke u bazuar në KONTEKSTIN e dhënë më poshtë. Mos gjenero informata ligjore nga kujtesa e jashtme nëse nuk mbështeten nga dokumentet.
        2. **Hierarkia e Normave:** Respekto hierarkinë ligjore: Kushtetuta > Ligjet (Gazeta Zyrtare) > Aktet Nënligjore (Udhëzime Administrative/Rregullore).
        3. **Citimi dhe Referencat:**
           - Kur citon një ligj, përdor formatin zyrtar: "Sipas Nenit X, paragrafi Y të Ligjit Nr. [Numri]..."
           - Referoju saktë titujve të dokumenteve.
        4. **Gjuha dhe Terminologjia:**
           - Përdor terminologji të saktë juridike në gjuhën Shqipe.
           - Nëse pyetja është në ANGLISHT -> Përgjigju në ANGLISHT.
           - Nëse pyetja është në SERBISHT -> Përgjigju në SERBISHT (Gjuhë zyrtare në Kosovë).
           - Nëse pyetja është në SHQIP -> Përgjigju në SHQIP.
        5. **Paqartësia:** Nëse konteksti nuk e përmban përgjigjen e plotë, thuaj qartë: "Nuk ka informacion të mjaftueshëm në dokumentet e ofruara për të dhënë një opinion ligjor të saktë."

        Qëllimi yt është të japësh këshilla ligjore të sakta, të bazuara në prova, dhe të formatuara qartë për juristët.
        """
        
        user_prompt = f"""
        KONTEKSTI LIGJOR (BURIMET):
        {context_string}
        
        PYETJA E PËRDORUESIT: 
        {query}
        """

        try:
            stream = await self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.fine_tuned_model,
                temperature=0.1, # Low temperature for legal precision
                stream=True,
            )
            async for chunk in stream:
                content = getattr(chunk.choices[0].delta, 'content', None)
                if content:
                    yield content
                    
            yield "\n\n**Burimi:** Gjeneruar nga Juristi AI bazuar në dokumentet e çështjes."

        except Exception as e:
            logger.error(f"RAG Generation Error: {e}", exc_info=True)
            yield "Ndodhi një gabim gjatë gjenerimit të përgjigjes."

    def _build_prompt_context(self, chunks: List[Dict]) -> str:
        parts = []
        for chunk in chunks:
            name = chunk.get('document_name', 'Dokument pa titull')
            text = chunk.get('text', '')
            parts.append(f"DOKUMENTI: {name}\nPËRMBAJTJA: {text}")
        return "\n\n---\n\n".join(parts)