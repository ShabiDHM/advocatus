# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - KOSOVO EXCLUSIVE RAG V8
# 1. JURISDICTION: Hardcoded to 'ks' (Republic of Kosovo).
# 2. PROMPT: Strictly defines the AI as a Kosovo Forensic Auditor.
# 3. LOGIC: Ignores foreign jurisdiction requests to prevent hallucinations.

import os
import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Dict, Protocol, cast, Any
from openai import AsyncOpenAI

from .graph_service import graph_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# --- PROTOCOLS ---
class VectorStoreServiceProtocol(Protocol):
    def query_by_vector(self, embedding: List[float], case_id: str, n_results: int, document_ids: Optional[List[str]]) -> List[Dict]: ...
    def query_legal_knowledge_base(self, embedding: List[float], n_results: int, jurisdiction: str) -> List[Dict]: ...

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
            self.client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        else:
            self.client = None

    async def chat(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        # PHOENIX: Force jurisdiction to 'ks' regardless of input
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids, 'ks'):
            if chunk: full_response_parts.append(chunk)
        return "".join(full_response_parts)

    async def _rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        if not chunks: return []
        unique_texts = {c.get('text', ''): c for c in chunks}
        return list(unique_texts.values())

    async def _call_local_backup(self, system_prompt: str, user_prompt: str) -> str:
        return "Shërbimi AI momentalisht i padisponueshëm."

    async def chat_stream(
        self, 
        query: str, 
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks' # Parameter kept for signature compatibility but ignored
    ) -> AsyncGenerator[str, None]:
        
        # PHOENIX: STRICT ENFORCEMENT
        target_jurisdiction = 'ks'
        
        user_docs, kb_docs, graph_knowledge = [], [], []
        
        try:
            from .embedding_service import generate_embedding
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            
            if query_embedding:
                results = await asyncio.gather(
                    asyncio.to_thread(self.vector_store.query_by_vector, embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids),
                    # PHOENIX: Increased KB results to 6, STRICTLY KOSOVO
                    asyncio.to_thread(self.vector_store.query_legal_knowledge_base, embedding=query_embedding, n_results=6, jurisdiction=target_jurisdiction),
                    asyncio.to_thread(graph_service.find_contradictions, case_id),
                    return_exceptions=True
                )
                user_docs = results[0] if isinstance(results[0], list) else []
                kb_docs = results[1] if isinstance(results[1], list) else []
                graph_knowledge = results[2] if isinstance(results[2], str) and "No direct" not in results[2] else ""
        except Exception as e:
            logger.error(f"Retrieval Phase Error: {e}")

        context_text = ""
        if user_docs:
            reranked_user_docs = await self._rerank_chunks(query, user_docs)
            context_text += "### FAKTE NGA DOSJA (EVIDENCA):\n"
            for chunk in reranked_user_docs[:6]:
                context_text += f"DOKUMENTI '{chunk.get('document_name', 'Unknown')}':\n{chunk.get('text', '')}\n---\n"
        
        if graph_knowledge:
            context_text += f"\n### FLAMUJ TË KUQ NGA GRAFI:\n{graph_knowledge}\n---\n"
        
        if kb_docs:
            context_text += "\n### BAZA LIGJORE (LIGJET E KOSOVËS):\n"
            for chunk in kb_docs[:4]: 
                context_text += f"BURIMI '{chunk.get('document_name', 'Ligj')}':\n{chunk.get('text', '')}\n---\n"
        
        if not context_text:
            context_text = "Nuk u gjetën dokumente ose informacione relevante."

        # PHOENIX: Aggressive Kosovo Lawyer Prompt
        system_prompt = f"""
        Ti je "Juristi AI", Avokat Senior Forenzik në Republikën e Kosovës.
        
        DETYRA JOTE:
        Bëj një "Cross-Examination" (Kundër-Pyetje) të fakteve të dosjes kundrejt (A) Logjikës dhe (B) Ligjeve të Kosovës.

        STRUKTURA E PËRGJIGJES (Markdown):

        ### 1. Përmbledhje Ekzekutive
        Përgjigje direkte. Nëse dokumenti ka gabime logjike (data, shuma) ose ligjore (referenca të huaja), fillo menjëherë duke i përmendur ato si "RREZIQE KRITIKE".

        ### 2. Auditim Ligjor & Faktik
        - **Kontrolli i Afateve:** Krahaso të gjitha datat në tekst. A ka data që bien ndesh me njëra-tjetrën? (Psh. Nënshkrimi pas dorëzimit?).
        - **Juridiksioni:** A përmendet Tiranë/Shqipëri? Nëse po, ngre FLAMUR TË KUQ se ky dokument mund të mos jetë i zbatueshëm në Kosovë.
        - **Përputhshmëria:** Krahaso klauzolat me "BAZA LIGJORE" (Ligjet e Kosovës). Cito Nenin specifik nëse gjendet.

        ### 3. Analiza e Dokumentit
        Nxirr detajet kryesore:
        - Palët: ...
        - Objekti: ...
        - Vlera: ...

        ### 4. Rekomandime Strategjike
        Çfarë duhet të përmirësohet ose ndryshohet urgjentisht në dokument?

        STILI I TË MENDUARIT:
        - Mos beso verbërisht tekstin. Nëse data e dokumentit është "228 Dhjetor", kjo është e pamundur. IDENTIFIKOJË KËTË GABIM.
        - Ji specifik. Mos thuaj "sipas ligjit", thuaj "Sipas Nenit X të Ligjit Y (nëse është në kontekst)".
        """

        user_message = f"KONTEKSTI I DOSJES:\n{context_text}\n\nPYETJA/KËRKESA: {query}"

        try:
            if not self.client:
                raise Exception("Client not initialized")

            stream = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1, 
                stream=True,
                extra_headers={ "HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI" }
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            
        except Exception as e:
            logger.error(f"OpenRouter API Error: {e}")
            yield await self._call_local_backup(system_prompt, user_message)