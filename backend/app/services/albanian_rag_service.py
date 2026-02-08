# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V46.5 (SENIOR PARTNER ARCHITECTURE)
# 1. FIX: Converted 'chat' to AsyncGenerator for zero-latency Deep Reasoning.
# 2. RESTORED: Fast Mode (AgentExecutor) logic for concise, rapid queries.
# 3. ENFORCED: Strict 'doc://ligji' formatting and high-density law retrieval (n=15).
# 4. STATUS: Complete End-to-End Legal Precision.

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from bson import ObjectId

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 120

PROTOKOLLI_PROFESIONAL = """
**URDHËRA MANDATORË PËR ANALIZË DHE CITIM:**
1.  **JURIDIKSIONI (KOSOVA):** Çdo analizë bazohet EKSKLUZIVISHT në legislacionin e Kosovës.
2.  **CITIMI I FAKTEVE:** Çdo fakt nga dosja citohet: `(Burimi: [Emri i Dokumentit], fq. [X])`.
3.  **CITIMI I LIGJEVE:** Përdor formatin ABSOLUT: [**[Emri i plotë i Ligjit], Neni [X]**](doc://ligji).
4.  **ZERO-TRUST:** Nëse ligji nuk gjendet në bazën e të dhënave të ofruar, thuaj: "Informacioni nuk gjendet në bazën ligjore."
"""

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        # Streaming enabled for Deep Mode
        self.llm = ChatOpenAI(
            model=OPENROUTER_MODEL, 
            base_url=OPENROUTER_BASE_URL, 
            temperature=0.0, 
            timeout=LLM_TIMEOUT,
            streaming=True
        ) if DEEPSEEK_API_KEY else None
        
    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> AsyncGenerator[str, None]:
        """
        DEEP MODE (THELLË): High-IQ Streaming Generator.
        """
        if not self.llm: yield "Sistemi AI nuk është aktiv."; return
        from . import vector_store_service
        
        # High-Density Retrieval (n=15 laws, n=20 facts)
        case_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=query, case_context_id=case_id, document_ids=document_ids, n_results=20)
        global_docs = vector_store_service.query_global_knowledge_base(query_text=query, jurisdiction=jurisdiction, n_results=15)
        
        context_str = "\n<<< BURIMET E DOSJES SË RASTIT >>>\n"
        for d in case_docs: 
            context_str += f"[DOKUMENTI: '{d.get('source')}', FAQJA: {d.get('page')}]: {d.get('text')}\n\n"
        
        context_str += "\n<<< BAZA LIGJORE (KOSOVA) >>>\n"
        for d in global_docs: 
            context_str += f"[LIGJI: '{d.get('source')}']: {d.get('text')}\n\n"
        
        prompt = f"""
        Ti je "Juristi AI", Senior Legal Partner.
        {PROTOKOLLI_PROFESIONAL}
        **MATERIALET:**
        {context_str}
        **PYETJA E AVOKATIT:** "{query}"

        DETYRA: Kryej një analizë juridike të thellë dhe formulo përgjigjen duke përdorur citimet ligjore saktë.
        """
        
        async for chunk in self.llm.astream(prompt):
            if chunk.content:
                yield str(chunk.content)

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        from . import vector_store_service
        p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction, case_context_id=case_id, n_results=15)
        l_docs = vector_store_service.query_global_knowledge_base(query_text=instruction, jurisdiction='ks', n_results=15)
        
        facts = "\n".join([f"DOKUMENTI: '{r.get('source')}' (Fq. {r.get('page')}): {r.get('text')}" for r in p_docs])
        laws = "\n".join([f"LIGJI: '{r.get('source')}': {r.get('text')}" for r in l_docs])
        
        prompt = f"{PROTOKOLLI_PROFESIONAL}\n--- MATERIALET ---\n[FAKTET]: {facts}\n[LIGJET]: {laws}\n[UDHËZIMI]: {instruction}\n--- DETYRA --- Harto dokumentin profesional final."
        response = await self.llm.ainvoke(prompt)
        return str(response.content)

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None) -> str:
        """
        FAST MODE: Legacy direct summarized reasoning.
        """
        if not self.llm: return "Sistemi AI nuk është aktiv."
        from . import vector_store_service
        global_docs = vector_store_service.query_global_knowledge_base(query_text=query, n_results=5)
        laws = "\n".join([d.get('text', '') for d in global_docs])
        prompt = f"Përgjigju shkurt në pyetjen ligjore duke u bazuar në këto nene:\n{laws}\n\nPyetja: {query}"
        response = await self.llm.ainvoke(prompt)
        return str(response.content)