# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - DEEPSEEK V3 INTEGRATION
# 1. ENGINE: Replaced Groq with DeepSeek V3 (via OpenAI SDK).
# 2. LOGIC: Hybrid Architecture - Local Embeddings + Cloud Reasoning.
# 3. COST: Optimized context window to keep API costs negligible.

import os
import asyncio
import logging
import httpx
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any
from openai import AsyncOpenAI, APIError

# Import the graph service instance
from .graph_service import graph_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat" # Points to DeepSeek V3

# Local Backup Configuration (in case internet fails)
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
        llm_client: Any, # Placeholder, we init our own client
        language_detector: LanguageDetectorProtocol
    ):
        self.vector_store = cast(VectorStoreServiceProtocol, vector_store)
        self.language_detector = language_detector
        
        # --- INIT DEEPSEEK CLIENT ---
        if DEEPSEEK_API_KEY:
            self.client = AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY, 
                base_url=DEEPSEEK_BASE_URL
            )
            logger.info("✅ DeepSeek V3 Activated for Juristi AI.")
        else:
            logger.critical("❌ DEEPSEEK_API_KEY missing! Chat will fail or fallback.")
            self.client = None

        # Configuration
        self.AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
        self.RERANK_TIMEOUT = 10.0

    async def chat(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> str:
        """
        Main entry point for chat. Returns full string response.
        """
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids):
            if chunk: full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Calls local ai-core-service to rerank results. 
        Keep this LOCAL to save API tokens and improve relevance.
        """
        if not chunks: return []
        
        # Deduplicate
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
        Fallback to Local CPU model if DeepSeek is down/unpaid.
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
            return "Shërbimi është momentalisht i padisponueshëm."

    async def chat_stream(self, query: str, case_id: str, document_ids: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        relevant_chunks = []
        graph_knowledge = []
        context_found = False
        
        # --- PHASE 1: RETRIEVAL (LOCAL SERVER) ---
        # Your server handles this part for free and fast.
        try:
            from .embedding_service import generate_embedding

            # 1. Embed Query
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            
            if query_embedding:
                # 2. Parallel Search (Vector DB + Knowledge Base + Graph)
                async def safe_vector_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_by_vector,
                        embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids
                    )
                
                async def safe_kb_search():
                    return await asyncio.to_thread(
                        self.vector_store.query_legal_knowledge_base,
                        embedding=query_embedding, n_results=3
                    )

                async def safe_graph_search():
                    # Simple keyword graph lookup
                    keywords = [w for w in query.split() if len(w) > 4]
                    results = []
                    for k in keywords:
                        results.extend(await asyncio.to_thread(graph_service.find_hidden_connections, k))
                    return list(set(results))

                results = await asyncio.gather(
                    safe_vector_search(), 
                    safe_kb_search(), 
                    safe_graph_search(), 
                    return_exceptions=True
                )

                user_docs = results[0] if isinstance(results[0], list) else []
                kb_docs = results[1] if isinstance(results[1], list) else []
                graph_knowledge = results[2] if isinstance(results[2], list) else []

                # 3. Rerank (Local CPU)
                raw_candidates = user_docs + kb_docs
                if raw_candidates:
                    relevant_chunks = await self._rerank_chunks(query, raw_candidates)
                    relevant_chunks = relevant_chunks[:8] # Send top 8 chunks to DeepSeek
                    context_found = True
                
        except Exception as e:
            logger.error(f"Retrieval Phase Error: {e}")
            # We continue even if retrieval fails, relying on LLM's general knowledge

        # --- PHASE 2: GENERATION (DEEPSEEK API) ---
        
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

        # Professional System Prompt
        system_prompt = """
        Ju jeni "Juristi AI", një asistent ligjor i avancuar për profesionistët në Kosovë.
        
        UDHËZIME:
        1. Analizo pyetjen e përdoruesit duke përdorur kontekstin e ofruar.
        2. Nëse konteksti përmban përgjigjen, cito dokumentet (p.sh. "Sipas kontratës...").
        3. Nëse konteksti nuk ka informacion, përdor njohuritë e tua për ligjet e Kosovës, por thekso se informacioni është i përgjithshëm.
        4. Stili: Profesional, objektiv, dhe i saktë juridikisht.
        5. Përgjigju në gjuhën Shqipe.
        """

        user_message = f"PYETJA: {query}\n\nKONTEKSTI:\n{context_text}"

        try:
            if not self.client:
                raise Exception("DeepSeek Client not initialized")

            stream = await self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3, # Low temp for precision
                stream=True
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            
            # Footer to confirm source (Remove in production if desired)
            yield "\n\n**Burimi:** Juristi AI"

        except Exception as e:
            logger.error(f"DeepSeek API Error: {e}")
            # Failover to Local CPU Model
            yield await self._call_local_backup(system_prompt, user_message)