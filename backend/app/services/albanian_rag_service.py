# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - KOSOVO LEGAL EDITION (FINAL)
# 1. ENGINE: DeepSeek V3 (via OpenRouter) for SOTA reasoning.
# 2. PROMPT: Engineered specifically for "Republika e Kosovës" legal terminology.
# 3. ARCHITECTURE: Hybrid (Local Storage/Search + Cloud Intelligence).

import os
import asyncio
import logging
import httpx
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any
from openai import AsyncOpenAI

# Import the graph service instance
from .graph_service import graph_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION (OPENROUTER) ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 

# OpenRouter Configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# The OpenRouter ID for DeepSeek V3
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# Local Backup Configuration (Fail-safe)
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# Protocol Definitions
class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

class AlbanianRAGService:
    def __init__(
        self,
        vector_store: VectorStoreServiceProtocol,
        llm_client: Any,
        language_detector: LanguageDetectorProtocol
    ):
        self.vector_store = cast(VectorStoreServiceProtocol, vector_store)
        self.language_detector = language_detector
        
        # --- INIT OPENROUTER CLIENT ---
        if DEEPSEEK_API_KEY:
            self.client = AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY, 
                base_url=OPENROUTER_BASE_URL
            )
            logger.info("✅ Juristi AI Engine: OpenRouter (DeepSeek V3) Activated.")
        else:
            logger.critical("❌ API Key missing! System will fallback to Local CPU (Slow).")
            self.client = None

        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 10.0

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk: full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Local AI Service to sort documents by relevance before sending to Cloud.
        """
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
            logger.warning(f"⚠️ Local Reranking skipped: {e}")
            return list(unique_chunks.values())

    async def _call_local_backup(self, system_prompt: str, user_prompt: str) -> str:
        """
        Fallback if OpenRouter is down or credit runs out.
        """
        logger.warning("🔄 Switching to Local Backup Model (CPU)...")
        try:
            payload = {
                "model": LOCAL_MODEL_NAME,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "stream": False
            }
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(LOCAL_LLM_URL, json=payload)
                data = response.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"❌ Local Backup Failed: {e}")
            return "Kërkesa nuk mund të përpunohej. Ju lutemi provoni përsëri më vonë."

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        graph_knowledge = []
        
        # --- PHASE 1: RETRIEVAL (LOCAL SERVER) ---
        try:
            from .embedding_service import generate_embedding
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            
            if query_embedding:
                async def safe_vector_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids
                    )
                
                async def safe_kb_search():
                    # Only search general law if we are looking at the whole case
                    if not document_ids:
                        return await asyncio.to_thread(
                            self.vector_store.query_legal_knowledge_base,
                            embedding=query_embedding, n_results=3
                        )
                    return []

                async def safe_graph_search():
                    if not document_ids:
                        keywords = [w for w in query.split() if len(w) > 4]
                        results = []
                        for k in keywords:
                            results.extend(await asyncio.to_thread(graph_service.find_hidden_connections, k))
                        return list(set(results))
                    return []

                results = await asyncio.gather(
                    safe_vector_search(), safe_kb_search(), safe_graph_search(), return_exceptions=True
                )

                user_docs = results[0] if isinstance(results[0], list) else []
                kb_docs = results[1] if isinstance(results[1], list) else []
                graph_knowledge = results[2] if isinstance(results[2], list) else []

                raw_candidates = user_docs + kb_docs
                if raw_candidates:
                    relevant_chunks = await self._rerank_chunks(query, raw_candidates)
                    relevant_chunks = relevant_chunks[:8] # Best 8 chunks
                
        except Exception as e:
            logger.error(f"Retrieval Phase Error: {e}")

        # --- PHASE 2: GENERATION (CLOUD AI) ---
        
        # Build Context String
        context_text = ""
        if graph_knowledge:
            context_text += "### TË DHËNA NGA GRAFI:\n" + "\n".join(graph_knowledge[:5]) + "\n\n"
        
        if relevant_chunks:
            context_text += "### DOKUMENTET E GJETURA:\n"
            for chunk in relevant_chunks:
                source = chunk.get('document_name', 'Dokument')
                text = chunk.get('text', '')
                context_text += f"BURIMI: {source}\nPËRMBAJTJA: {text}\n---\n"
        
        if not context_text:
            context_text = "Nuk u gjetën dokumente specifike. Përgjigju bazuar në njohuritë e përgjithshme ligjore."

        # PHOENIX PROTOCOL - KOSOVO LEGAL PROMPT v2
        system_prompt = """
        Ti je "Juristi AI", një Asistent Ligjor i Avancuar i specializuar për sistemin e drejtësisë në Republikën e Kosovës.

        MISIONI:
        Të analizosh dokumentet e dosjes dhe të ofrosh këshilla juridike të sakta, profesionale dhe të bazuara në ligjet në fuqi të Kosovës.

        UDHËZIME STRIKTE:
        1. GJUHA DHE TERMINOLOGJIA:
           - Përdor gjuhën shqipe letrare dhe profesionale.
           - Përdor terminologjinë e saktë ligjore të Kosovës (p.sh. "Kodi Penal i Republikës së Kosovës", "Ligji i Punës", "Gjykata Themelore").
        
        2. BURIMI I INFORMACIONIT:
           - Përgjigju DUKE U BAZUAR KRYESISHT në tekstin e dhënë tek 'DOKUMENTET E GJETURA'.
           - Cito dokumentet ku është e mundur (p.sh. "Sipas Nenit 3 të Kontratës...").
        
        3. MUNGESA E INFORMACIONIT:
           - Nëse 'KONTEKSTI' nuk përmban përgjigjen e saktë, thuaj qartë: "Në dokumentet e ofruara nuk gjendet ky informacion specifik."
           - Më pas, ofro një analizë të bazuar në parimet e përgjithshme të ligjeve të Kosovës që mund të aplikohen.

        4. FORMATI I PËRGJIGJES:
           - Hyrje: Konfirmim i kuptimit të pyetjes.
           - Analizë: Shtjellim i fakteve nga dokumentet dhe baza ligjore.
           - Konkluzion: Përmbledhje e shkurtër ose rekomandim.

        Qëndro objektiv dhe profesional. Mos jep garanci absolute për rezultatin e një çështjeje gjyqësore.
        """

        user_message = f"PYETJA E PËRDORUESIT: {query}\n\nKONTEKSTI I DOSJES:\n{context_text}"

        try:
            if not self.client:
                raise Exception("Client not initialized")

            stream = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3, # Low temperature for factual consistency
                stream=True,
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI"
                }
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            
            yield "\n\n**Burimi:** Juristi AI (DeepSeek Engine)"

        except Exception as e:
            logger.error(f"OpenRouter API Error: {e}")
            yield await self._call_local_backup(system_prompt, user_message)