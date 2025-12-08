# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - FINAL POLISH (PREMIUM RESPONSE STRUCTURE)
# 1. PROMPT: Upgraded System Prompt to force a professional "Legal Memo" structure.
# 2. SECTIONS: AI must now generate an Executive Summary, Key Findings, Strategic Analysis, and Recommendations.
# 3. GOAL: Deliver a premium, high-value response that justifies a paid subscription.

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
        full_response_parts = []
        async for chunk in self.chat_stream(query, case_id, document_ids, jurisdiction):
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
        jurisdiction: str = 'ks'
    ) -> AsyncGenerator[str, None]:
        
        user_docs, kb_docs, graph_knowledge = [], [], []
        
        try:
            from .embedding_service import generate_embedding
            query_embedding = await asyncio.to_thread(generate_embedding, query, 'standard')
            
            if query_embedding:
                results = await asyncio.gather(
                    asyncio.to_thread(self.vector_store.query_by_vector, embedding=query_embedding, case_id=case_id, n_results=10, document_ids=document_ids),
                    asyncio.to_thread(self.vector_store.query_legal_knowledge_base, embedding=query_embedding, n_results=4, jurisdiction=jurisdiction),
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
            context_text += "### FAKTE NGA DOSJA (PRIORITET #1):\n"
            for chunk in reranked_user_docs[:6]:
                context_text += f"NGA DOKUMENTI '{chunk.get('document_name', '...')}': \"{chunk.get('text', '')}\"\n---\n"
        
        if graph_knowledge:
            context_text += f"\n### INTELIGJENCA NGA GRAFI (PRIORITET #2):\n{graph_knowledge}\n---\n"
        
        if kb_docs:
            context_text += "\n### BAZA LIGJORE RELEVANTE (PËR REFERENCË):\n"
            for chunk in kb_docs[:3]:
                context_text += f"NGA LIGJI '{chunk.get('document_name', '...')}': \"{chunk.get('text', '')}\"\n---\n"
        
        if not context_text:
            context_text = "Nuk u gjetën dokumente ose informacione relevante për këtë pyetje."

        jurisdiction_name = "Republikës së Shqipërisë" if jurisdiction == 'al' else "Republikës së Kosovës"
        
        # PHOENIX: The "Premium Response" System Prompt
        system_prompt = f"""
        Ti je "Juristi AI", një Këshilltar Ligjor Elitar i specializuar në legjislacionin e {jurisdiction_name}.
        
        MISIONI YT:
        Analizo pyetjen e përdoruesit dhe kontekstin e dhënë për të prodhuar një Memo Ligjore të strukturuar, të qartë dhe me vlerë të lartë.

        STRUKTURA E OBLIGUESHME E PËRGJIGJES (PËRDOR MARKDOWN):

        ### Përmbledhje Ekzekutive
        Përgjigju pyetjes së përdoruesit direkt dhe në mënyrë konçize në 1-2 fjali. Kjo është përgjigja që një avokat i zënë duhet ta lexojë së pari.

        ### Gjetjet Kyçe nga Dosja
        - Listë me pika të fakteve më të rëndësishme që ke gjetur në seksionin "FAKTE NGA DOSJA".
        - Për çdo pikë, CITO burimin e dokumentit (psh. "Sipas Faturës...").

        ### Analiza Strategjike
        Këtu bën lidhjen mes fakteve, inteligjencës nga grafi dhe ligjit.
        - A ka ndonjë kontradiktë të gjetur nga "INTELIGJENCA NGA GRAFI"? Shpjegoje.
        - Si aplikohet "BAZA LIGJORE" mbi "GJETJET KYÇE"?
        - Cilat janë pikat e forta dhe të dobëta të rastit bazuar në këtë analizë?

        ### Rekomandime / Hapat e Ardhshëm
        - Bazuar në analizën tënde, çfarë duhet të bëjë avokati tani?
        - Listë me pika të veprimeve konkrete (psh. "Kërko dokumentin X", "Përgatit një padi bazuar në nenin Y", "Kontakto dëshmitarin Z").

        RREGULLAT KRITIKE:
        - **HIERARKIA:** Gjithmonë bazo arsyetimin te FAKTE NGA DOSJA së pari.
        - **PRECISIONI:** Mos krijo fakte. Nëse informacioni mungon, thuaje qartë.
        - **GJUHA:** Përdor gjuhë profesionale ligjore shqipe.
        """

        user_message = f"KONTEKSTI I PLOTË:\n{context_text}\n\nPYETJA E PËRDORUESIT: {query}"

        try:
            if not self.client:
                raise Exception("Client not initialized")

            stream = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1, # Maximum precision
                stream=True,
                extra_headers={ "HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Premium" }
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            
            # Add a final disclaimer
            yield f"\n\n---\n*Shënim: Kjo analizë është gjeneruar nga AI dhe shërben vetëm për qëllime informative. Verifikoni gjithmonë faktet dhe ligjet përpara se të ndërmerrni veprime ligjore.*"
            
        except Exception as e:
            logger.error(f"OpenRouter API Error: {e}")
            yield await self._call_local_backup(system_prompt, user_message)