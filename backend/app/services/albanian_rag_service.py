# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - KOSOVO EXCLUSIVE RAG V9.2 (RETRIEVAL OPTIMIZATION)
# 1. OPTIMIZATION: Increased legal document retrieval limit (n=3 -> n=5) for better coverage.
# 2. CLEANUP: Chat method retained as fallback, but primary generation is now in Chat Service.

import os
import asyncio
import logging
from typing import List, Optional, Dict, Protocol, cast, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- PROTOCOLS ---
class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int, jurisdiction: str) -> List[Dict]: ...
    def query_findings_by_similarity(self, case_id: str, embedding: List[float], n_results: int) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

class AlbanianRAGService:
    def __init__(
        self,
        vector_store: VectorStoreServiceProtocol,
        llm_client: Any, 
        language_detector: LanguageDetectorProtocol,
        db: Any
    ):
        self.vector_store = cast(VectorStoreServiceProtocol, vector_store)
        self.language_detector = language_detector
        self.db = db
        
        if DEEPSEEK_API_KEY:
            self.client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        else:
            self.client = None

    async def retrieve_context(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        """
        Retrieves and assembles a rich, multi-source context dossier.
        """
        from .graph_service import graph_service
        from .embedding_service import generate_embedding

        try:
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            if not query_embedding:
                return ""
        except Exception as e:
            logger.error(f"RAG: Embedding generation failed: {e}")
            return ""

        user_docs, kb_docs, graph_knowledge, structured_findings = [], [], "", []
        
        try:
            # PHOENIX OPTIMIZATION: Increased Legal Knowledge retrieval to 5 chunks
            # PHOENIX OPTIMIZATION: Increased Findings retrieval to 10 chunks for deep fact-checking
            results = await asyncio.gather(
                asyncio.to_thread(self.vector_store.query_by_vector, embedding=query_embedding, case_id=case_id, n_results=5, document_ids=document_ids),
                asyncio.to_thread(self.vector_store.query_legal_knowledge_base, embedding=query_embedding, n_results=5, jurisdiction='ks'),
                asyncio.to_thread(graph_service.find_contradictions, case_id),
                asyncio.to_thread(self.vector_store.query_findings_by_similarity, case_id=case_id, embedding=query_embedding, n_results=10),
                return_exceptions=True
            )
            
            user_docs = results[0] if isinstance(results[0], list) else []
            kb_docs = results[1] if isinstance(results[1], list) else []
            graph_knowledge = results[2] if isinstance(results[2], str) and "No direct" not in results[2] else ""
            structured_findings = results[3] if isinstance(results[3], list) else []

        except Exception as e:
            logger.error(f"RAG: Retrieval Phase Error: {e}")

        context_parts = []
        
        if structured_findings:
            findings_text = "\n".join([f"- [{f.get('category', 'FAKT')}]: {f.get('finding_text', 'N/A')}" for f in structured_findings])
            context_parts.append(f"### FAKTE KYÇE NGA DOSJA (Gjetjet e Sistemit):\n{findings_text}")

        if user_docs:
            doc_chunks_text = "\n".join([f"Fragment nga '{chunk.get('document_name', 'Unknown')}':\n\"...{chunk.get('text', '')}...\"\n---" for chunk in user_docs])
            context_parts.append(f"### FRAGMENTE RELEVANTE NGA DOKUMENTET:\n{doc_chunks_text}")
        
        if graph_knowledge:
            context_parts.append(f"### INTELIGJENCA E GRAFIT (Kontradiktat):\n{graph_knowledge}")
        
        if kb_docs:
            kb_text = "\n".join([f"Nga '{chunk.get('document_name', 'Ligj')}':\n{chunk.get('text', '')}\n---" for chunk in kb_docs])
            context_parts.append(f"### BAZA LIGJORE (LIGJET E KOSOVËS):\n{kb_text}")
        
        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    async def chat(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        """
        [DEPRECATED] - Logic moved to chat_service.py for centralized prompt control.
        Kept as fallback.
        """
        context = await self.retrieve_context(query, case_id, document_ids, jurisdiction)
        
        if not self.client:
            return "Klienti AI nuk është inicializuar."

        try:
            system_prompt = """
            Ti je 'Juristi AI', asistent ligjor inteligjent.
            DETYRA: Përgjigju pyetjes duke përdorur KONTEKSTIN e dhënë.
            RREGULL: Përdor Markdown (Bold, List, Header) për formatim.
            """
            
            user_message = f"KONTEKSTI:\n{context}\n\nPYETJA: {query}"
            
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content or "Error."
        except Exception as e:
            logger.error(f"Chat Error: {e}")
            return "Error."