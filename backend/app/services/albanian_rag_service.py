# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - GRAPH UNLOCKED
# 1. LOGIC FIX: Enabled Graph Search for BOTH 'Document Mode' and 'Case Mode'.
# 2. RESULT: Maximum context (Laws + Graph + Document) provided for every query.

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
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# Local Backup Configuration
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
        
        # --- PHASE 1: RETRIEVAL ---
        try:
            from .embedding_service import generate_embedding
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            
            if query_embedding:
                # 1. User Documents (Filtered by ID if provided)
                async def safe_vector_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids
                    )
                
                # 2. Knowledge Base (ALWAYS ENABLED)
                async def safe_kb_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_legal_knowledge_base,
                        embedding=query_embedding, n_results=3
                    )

                # 3. Graph (ALWAYS ENABLED)
                # PHOENIX FIX: Graph search enabled for BOTH single-doc and full-case modes
                async def safe_graph_search():
                    try:
                        keywords = [w for w in query.split() if len(w) > 4]
                        results = []
                        for k in keywords:
                            results.extend(await asyncio.to_thread(graph_service.find_hidden_connections, k))
                        return list(set(results))
                    except Exception:
                        return []

                results = await asyncio.gather(
                    safe_vector_search(), safe_kb_search(), safe_graph_search(), return_exceptions=True
                )

                user_docs = results[0] if isinstance(results[0], list) else []
                kb_docs = results[1] if isinstance(results[1], list) else []
                graph_knowledge = results[2] if isinstance(results[2], list) else []

                # Combine: User Docs + Laws
                raw_candidates = user_docs + kb_docs
                
                # 3. Rerank Everything Together
                if raw_candidates:
                    relevant_chunks = await self._rerank_chunks(query, raw_candidates)
                    relevant_chunks = relevant_chunks[:8] 
                
        except Exception as e:
            logger.error(f"Retrieval Phase Error: {e}")

        # --- PHASE 2: GENERATION ---
        context_text = ""
        if graph_knowledge:
            context_text += "### TË DHËNA NGA GRAFI (KONTEKST SHTESË):\n" + "\n".join(graph_knowledge[:5]) + "\n\n"
        
        if relevant_chunks:
            context_text += "### DOKUMENTET DHE LIGJET E GJETURA:\n"
            for chunk in relevant_chunks:
                doc_type = chunk.get('type', 'DOKUMENT')
                source = chunk.get('document_name', 'Burim i Panjohur')
                text = chunk.get('text', '')
                context_text += f"LLOJI: {doc_type} | BURIMI: {source}\nPËRMBAJTJA: {text}\n---\n"
        
        if not context_text:
            context_text = "Nuk u gjetën dokumente specifike. Përgjigju bazuar në njohuritë e tua të përgjithshme ligjore."

        system_prompt = """
        Ti je "Juristi AI", një Asistent Ligjor i Avancuar i specializuar për sistemin e drejtësisë në Republikën e Kosovës.

        MISIONI:
        Të analizosh dokumentet e dosjes dhe të ofrosh këshilla juridike të sakta, profesionale dhe të bazuara në ligjet në fuqi të Kosovës.

        UDHËZIME STRIKTE:
        1. KOMBINIMI I BURIMEVE:
           - Përdor 'DOKUMENTET E PËRDORUESIT' për faktet e rastit.
           - Përdor 'LIGJET E GJETURA' për bazën ligjore.
           - Përdor 'TË DHËNA NGA GRAFI' për kontekst rreth entiteteve.
           - Nëse 'LIGJET' mungojnë në kontekst, përdor njohuritë e tua të brendshme për Kodin Penal/Civil të Kosovës.

        2. FORMATI I PËRGJIGJES:
           - Hyrje: Konfirmim i pyetjes.
           - Analizë Faktike: Çfarë thonë dokumentet?
           - Analizë Ligjore: Çfarë thotë ligji për këto fakte?
           - Konkluzion: Rekomandim profesional.

        3. GJUHA: Shqipe letrare, profesionale (p.sh. "Sipas Nenit X...").

        Qëndro objektiv dhe profesional.
        """

        user_message = f"PYETJA E PËRDORUESIT: {query}\n\nKONTEKSTI I KOMBINUAR:\n{context_text}"

        try:
            if not self.client:
                raise Exception("Client not initialized")

            stream = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3, 
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
            
            yield "\n\n**Burimi:** Asistenti sokratik"

        except Exception as e:
            logger.error(f"OpenRouter API Error: {e}")
            yield await self._call_local_backup(system_prompt, user_message)