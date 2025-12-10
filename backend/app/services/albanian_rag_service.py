# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - KOSOVO EXCLUSIVE RAG V9.0 (RETRIEVAL-ONLY)
# 1. ARCHITECTURE: This service is NO LONGER an AI engine. Its sole responsibility is now RETRIEVAL.
# 2. DEPRECATION: Removed the large, complex internal LLM prompt.
# 3. FOCUS: Implements a 'retrieve_context' method that gathers structured Findings, Graph data, and Vector chunks.
# 4. DELEGATION: The calling service (e.g., chat_service) is now responsible for sending the context to the LLM.

import os
import asyncio
import logging
from typing import List, Optional, Dict, Protocol, cast, Any
from openai import AsyncOpenAI

# PHOENIX: Removed direct dependency on graph_service at the top level
# from .graph_service import graph_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- PROTOCOLS ---
class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int, jurisdiction: str) -> List[Dict]: ...
    # PHOENIX: Add the new required method to the protocol for type safety
    def query_findings_by_similarity(self, case_id: str, embedding: List[float], n_results: int) -> List[Dict]: ...

class LanguageDetectorProtocol(Protocol):
    def detect_language(self, text: str) -> bool: ...

class AlbanianRAGService:
    def __init__(
        self,
        vector_store: VectorStoreServiceProtocol,
        llm_client: Any, # Kept for signature, but will not be used for generation
        language_detector: LanguageDetectorProtocol,
        db: Any # PHOENIX: Pass the database client for direct findings query
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
        Retrieves and assembles a rich, multi-source context dossier for a given query.
        This is the new core function of the RAG service.
        """
        # PHOENIX: Dynamically import graph_service here to avoid circular dependencies
        from .graph_service import graph_service
        from .embedding_service import generate_embedding

        # 1. Generate a single embedding for the user's query
        try:
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            if not query_embedding:
                logger.warning("RAG: Failed to generate query embedding.")
                return "Nuk u gjetën informacione relevante (problem me embedding)."
        except Exception as e:
            logger.error(f"RAG: Embedding generation failed: {e}")
            return "Nuk u gjetën informacione relevante (problem teknik)."

        # 2. Concurrently fetch from all three context sources
        user_docs, kb_docs, graph_knowledge, structured_findings = [], [], "", []
        
        try:
            results = await asyncio.gather(
                # Source 1: Raw text chunks from documents
                asyncio.to_thread(self.vector_store.query_by_vector, embedding=query_embedding, case_id=case_id, n_results=5, document_ids=document_ids),
                # Source 2: Legal knowledge base (Kosovo Law)
                asyncio.to_thread(self.vector_store.query_legal_knowledge_base, embedding=query_embedding, n_results=3, jurisdiction='ks'),
                # Source 3: High-level contradictions from the graph
                asyncio.to_thread(graph_service.find_contradictions, case_id),
                # PHOENIX: SOURCE 4: High-density structured findings (The most important context!)
                asyncio.to_thread(self.vector_store.query_findings_by_similarity, case_id=case_id, embedding=query_embedding, n_results=7),
                return_exceptions=True
            )
            
            user_docs = results[0] if isinstance(results[0], list) else []
            kb_docs = results[1] if isinstance(results[1], list) else []
            graph_knowledge = results[2] if isinstance(results[2], str) and "No direct" not in results[2] else ""
            structured_findings = results[3] if isinstance(results[3], list) else []

        except Exception as e:
            logger.error(f"RAG: Retrieval Phase Error: {e}")

        # 3. Assemble the context dossier, prioritizing structured findings
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
            return "Nuk u gjet asnjë informacion relevant në dosje për këtë pyetje."

        return "\n\n".join(context_parts)


    async def chat(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        """
        DEPRECATED METHOD - Maintained for compatibility.
        The logic has been moved to the calling service (e.g., chat_service).
        This now serves as a simple wrapper around the new 'retrieve_context' logic.
        """
        # This function is now just a placeholder. The real logic is in the calling service
        # which will first call retrieve_context and then call the LLM.
        # For now, we can simulate a basic response for any old code that might still call this.
        logger.warning("DEPRECATION WARNING: Direct 'chat' method on RAG service is outdated. Refactor to use 'retrieve_context'.")
        
        context = await self.retrieve_context(query, case_id, document_ids, jurisdiction)
        
        # A simple, non-streaming call for basic compatibility
        if not self.client:
            return "Klienti AI nuk është inicializuar."

        try:
            system_prompt = "Ti je një asistent ligjor. Përgjigju pyetjes bazuar në kontekstin e dhënë."
            user_message = f"KONTEKSTI:\n{context}\n\nPYETJA: {query}"
            
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content or "Pati një problem gjatë gjenerimit të përgjigjes."
        except Exception as e:
            logger.error(f"Fallback Chat Error: {e}")
            return "Ndodhi një gabim në komunikimin me shërbimin AI."