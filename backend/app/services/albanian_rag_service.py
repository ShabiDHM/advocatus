# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - LOGIC RELAXATION
# 1. LOGIC: Removed strict early exit when no docs are found.
# 2. FALLBACK: Added "General Knowledge" mode for the LLM when context is empty.
# 3. UX: The AI will now always attempt an answer, clarifying if it's based on docs or general law.

import os
import asyncio
import logging
import httpx
import json
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any

# Import the graph service instance
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
        context_found = False
        
        try:
            from .embedding_service import generate_embedding

            # --- STEP 1: EMBED ---
            try:
                query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            except Exception:
                # Even if embedding fails, we try to proceed with general knowledge? 
                # No, embedding is critical for RAG. We will log but try to continue if possible.
                logger.error("Embedding failed.")
                query_embedding = None

            if query_embedding:
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

                results = await asyncio.gather(
                    safe_user_search(), 
                    safe_law_search(),
                    safe_graph_search(),
                    return_exceptions=True
                )
                
                user_docs = results[0] if isinstance(results[0], list) else []
                law_docs = results[1] if isinstance(results[1], list) else []
                graph_results = results[2] if isinstance(results[2], list) else []
                
                graph_knowledge = graph_results
                logger.info(f"🔍 RESULTS -> Vectors: {len(user_docs)}, Laws: {len(law_docs)}, Graph Nodes: {len(graph_results)}")

                all_candidates = user_docs + law_docs
                
                # --- STEP 3: RERANK ---
                if all_candidates:
                    reranked = await self._rerank_chunks(query, all_candidates)
                    relevant_chunks = reranked[:7] if reranked else all_candidates[:7]
                    context_found = True
                elif graph_results:
                    context_found = True
            
            # PHOENIX FIX: Removed the "else: yield Error... return" block.
            # We proceed to LLM regardless.

        except Exception as e:
            logger.error(f"RAG Error: {e}")
            yield f"Gabim gjatë kërkimit: {str(e)}"
            return

        # --- STEP 4: GENERATE (PROFESSIONAL PROMPT) ---
        context_string = self._build_prompt_context(relevant_chunks, graph_knowledge)
        
        # PHOENIX FIX: Updated prompt to handle "No Context" gracefully
        system_prompt = """
        Ju jeni "Asistenti Sokratik", një konsulent ligjor i nivelit të lartë (Senior Legal Associate) i specializuar në ligjet e Kosovës dhe Shqipërisë.
        Qëllimi juaj është të ofroni analiza profesionale, të sakta dhe të strukturuara.

        UDHËZIME PËR PËRGJIGJEN:
        1. Nëse ka dokumente në kontekst:
           - SINTETIZO: Përdor informacionin për të ndërtuar një narrativë logjike.
           - CITO: Referoju burimeve (psh. "Sipas Kontratës së Punës...").
        
        2. Nëse NUK ka dokumente specifike (Konteksti bosh):
           - Përgjigju duke u bazuar në parimet e përgjithshme juridike të ligjeve në fuqi.
           - Fillo përgjigjen me: "Bazuar në njohuritë e përgjithshme ligjore (pasi nuk u gjetën dokumente specifike në dosje)..."
           - Ofro udhëzime se çfarë dokumentesh mund të duhen.

        3. INTEGRIMI I GRAFIT: Përdor të dhënat nga 'Analiza e Lidhjeve' si fakte të konfirmuara.
        4. STILI: Përdor gjuhë juridike formale, objektive dhe profesionale.

        FORMATI:
        - Fillo me një përmbledhje ekzekutive.
        - Analizo detajet (Palët, Objektin, Afatet, Detyrimet).
        - Përfundo me një konkluzion ose rekomandim.
        """
        
        user_prompt = f"""
        PYETJA E PËRDORUESIT: {query}

        ---
        MATERIALI I SHQYRTUAR (Nga Dosja):
        {context_string if context_found else "Nuk u gjetën dokumente specifike për këtë kërkim."}
        ---
        
        Bazuar në materialin e mësipërm (ose njohuritë tuaja të përgjithshme nëse mungon materiali), ju lutem hartoni përgjigjen tuaj profesionale:
        """

        # TIER 1: GROQ (CLOUD)
        tier1_failed = False
        try:
            stream = await self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.fine_tuned_model,
                temperature=0.3, # Slightly higher temperature for general knowledge reasoning
                stream=True,
            )
            async for chunk in stream:
                content = getattr(chunk.choices[0].delta, 'content', None)
                if content:
                    yield content
            
            yield "\n\n**Burimi:** Asistenti Sokratik"
            return

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                logger.warning("⚠️ Cloud Limit Reached. Activating Tier 2.")
                tier1_failed = True
            else:
                logger.error(f"Tier 1 Failed: {e}")
                tier1_failed = True

        # TIER 2: LOCAL LLM
        if tier1_failed:
            local_content = await self._call_local_llm(system_prompt, user_prompt)
            if local_content:
                yield "**[Mode: AI Lokale]**\n\n"
                yield local_content
                yield "\n\n**Burimi:** Asistenti Sokratik"
                return
        
        # TIER 3: STATIC FALLBACK (Only if both LLMs fail)
        yield "Kërkesa nuk mund të përpunohej për momentin për shkak të ngarkesës së lartë. Ju lutemi provoni përsëri më vonë."

    def _build_prompt_context(self, chunks: List[Dict], graph_data: List[str]) -> str:
        parts = []
        if graph_data:
            parts.append("=== TË DHËNA NGA ANALIZA E LIDHJEVE (STRUKTUAR) ===")
            parts.extend(graph_data)
            parts.append("==================================================\n")
        
        if chunks:
            parts.append("=== PËRMBAJTJA E DOKUMENTEVE (TEKST) ===")
            for chunk in chunks:
                doc_type = chunk.get('type', 'DOKUMENT')
                name = chunk.get('document_name', 'Burim i Panjohur')
                text = chunk.get('text', '')
                parts.append(f"Burimi: {name} ({doc_type})\nPërmbajtja: {text}\n---")
        return "\n".join(parts)