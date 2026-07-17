# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V59.0 (SAAS CONNECTED)
# 1. FIX: Dynamic key resolution (looks for both OPENROUTER_API_KEY and DEEPSEEK_API_KEY).
# 2. ALIGNMENT: Uses MongoDB Atlas Vector Search exclusively (No ChromaDB).
# 3. STATUS: 100% Independent / 8GB RAM Optimized / Production Ready.

import os
import sys
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# PHOENIX: Look for both potential key names in the environment
API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 120

AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

PROTOKOLLI_MANDATOR = """
**URDHËRA TË RREPTË FORMATIMI (NDIQINI ME PRECIZION):**
1. Çdo citim ligjor DUHET të përmbajë **EMRIN E PLOTË ZYRTAR TË LIGJIT** dhe **NUMRIN ZYRTAR** (p.sh., "Nr. 04/L-077").  
   **Shembull i saktë:** `Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve, Neni 5`  
2. Për çdo ligj të cituar, DUHET të shtoni rreshtin: **RELEVANCA:** [Pse ky nen është thelbësor].
3. Përdor TITUJT MARKDOWN (###) për të ndarë seksionet.
"""

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.citation_map: Dict[Tuple[str, str], str] = {}
        self.law_number_map: Dict[Tuple[str, str], str] = {}
        
        if API_KEY:
            # We connect to OpenRouter using standard OpenAI interface
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL, 
                base_url=OPENROUTER_BASE_URL, 
                api_key=API_KEY, 
                temperature=0.0, 
                streaming=True,
                timeout=LLM_TIMEOUT
            )
            logger.info("✅ [RAG] AI Engine initialized via OpenRouter.")
        else:
            self.llm = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

    def _normalize_law_title(self, title: str) -> str:
        return ' '.join(title.strip().split())

    def _extract_law_number(self, text: str) -> Optional[str]:
        match = re.search(r'Nr\.?\s*([\d/L\-]+)', text, re.IGNORECASE)
        return match.group(1) if match else None

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict]) -> str:
        context = "\n<<< MATERIALET E DOSJES >>>\n"
        for idx, d in enumerate(case_docs):
            context += f"[{d.get('source')}, FAQJA: {d.get('page')}]: {d.get('text')}\n\n"

        context += "\n<<< BAZA LIGJORE STATUTORE >>>\n"
        for d in global_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number', 'N/A')
            context += f"LIGJI: {law_title}, Neni {article_num}\nPËRMBAJTJA: {d.get('text')}\n\n"
        return context

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.llm:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            yield AI_DISCLAIMER
            return

        # Direct import of SaaS Vector Store
        from app.services import vector_store_service

        logger.info(f"🔍 RAG Chat request: query='{query[:100]}...'")

        # 1. Search Case Knowledge Base (Direct Mongo Vector Search)
        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=query, n_results=10
        )

        # 2. Search Global Laws (Direct Mongo Vector Search)
        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=query, n_results=5
        )

        context_str = self._build_context(case_docs, global_docs)

        # === SYSTEM PROMPT ===
        prompt = f"""
        Ti je \"AI Legal Auditor\". Burimi yt i vetëm i së vërtetës është [KONTEKSTI] i dhënë më poshtë.

        **RREGULLI I REFUZIMIT (I DETYRUESHËM):**
        Nëse përgjigjja nuk mund të nxirret nga [KONTEKSTI], je i ndaluar rreptësisht të përgjigjesh.
        Përgjigju VETËM me: "Më vjen keq, por ky informacion nuk gjendet në dokumentet e ngarkuara."

        **PRIORITETI I BURIMEVE:**
        Në rast konflikti midis <<< MATERIALET E DOSJES >>> dhe <<< BAZA LIGJORE STATUTORE >>>, **materialet e dosjes kanë përparësi absolute**.

        {PROTOKOLLI_MANDATOR}

        **KONTEKSTI:**
        {context_str}

        **PYETJA AKTUALE:** "{query}"

        **STRUKTURA (OBLIGATIVE):**
        ### 1. ANALIZA E FAKTEVE

        ### 2. BAZA LIGJORE DHE RELEVANCA

        ### 3. KONKLUZIONI STRATEGJIK

        Fillo hartimin tani:
        """

        try:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    yield chunk.content
            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER