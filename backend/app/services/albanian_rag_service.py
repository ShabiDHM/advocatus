# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V46.8 (UNIFIED LEGAL REASONING)
# 1. FIX: Eliminated LMD hallucinations in Family cases by forcing Lex Specialis hierarchy.
# 2. FIX: Hardened token-by-token streaming for Deep Mode.
# 3. ENFORCED: Professional citation badge format: [Ligji, Neni](doc://ligji).
# 4. STATUS: Senior Partner Intelligence fully restored.

import os
import asyncio
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from langchain_openai import ChatOpenAI
from bson import ObjectId

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

PROTOKOLLI_PROFESIONAL = """
**URDHËRA MANDATORË PËR AVOKATIN AI:**
1. JURIDIKSIONI: Bazohu VETËM në ligjet e Kosovës.
2. HIERARKIA: Për Alimentacion/Kujdestari, përdor VETËM [Ligji Nr. 2004/32 Për Familjen e Kosovës, Neni X](doc://ligji). MOS përdor LMD-në.
3. CITIMI I FAKTEVE: (Burimi: [Emri i Dokumentit], fq. [X]).
4. CITIMI I LIGJEVE: [Emri i Plotë i Ligjit, Neni X](doc://ligji).
"""

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.llm = ChatOpenAI(
            model=OPENROUTER_MODEL, 
            base_url=OPENROUTER_BASE_URL, 
            api_key=DEEPSEEK_API_KEY, # type: ignore
            temperature=0.0, 
            streaming=True
        ) if DEEPSEEK_API_KEY else None

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> AsyncGenerator[str, None]:
        if not self.llm: yield "Sistemi AI nuk është aktiv."; return
        from . import vector_store_service
        
        # Deep Retrieval (n=15 laws)
        case_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=query, case_context_id=case_id, n_results=20)
        global_docs = vector_store_service.query_global_knowledge_base(query_text=query, jurisdiction=jurisdiction, n_results=15)
        
        context_str = "\n<<< BURIMET E DOSJES >>>\n"
        for d in case_docs: context_str += f"[{d.get('source')}, FAQJA: {d.get('page')}]: {d.get('text')}\n\n"
        context_str += "\n<<< BAZA LIGJORE (STATUTI) >>>\n"
        for d in global_docs: context_str += f"LIGJI: '{d.get('source')}': {d.get('text')}\n\n"
        
        prompt = f"""
        Ti je "Juristi AI", Senior Legal Partner.
        {PROTOKOLLI_PROFESIONAL}
        **KONTEKSTI I RASTIT:**
        {context_str}
        **PYETJA E AVOKATIT:** "{query}"
        
        DETYRA: Formulo një analizë statutore të detajuar. Çdo argument duhet të citojë ligjin special përkatës me formatin [Ligji](doc://ligji).
        """
        async for chunk in self.llm.astream(prompt):
            if chunk.content: yield str(chunk.content)

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        from . import vector_store_service
        p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction, case_context_id=case_id, n_results=15)
        l_docs = vector_store_service.query_global_knowledge_base(query_text=instruction, n_results=15)
        facts = "\n".join([f"DOKUMENTI: '{r.get('source')}': {r.get('text')}" for r in p_docs])
        laws = "\n".join([f"LIGJI: '{r.get('source')}': {r.get('text')}" for r in l_docs])
        prompt = f"{PROTOKOLLI_PROFESIONAL}\nPROVAT: {facts}\nLIGJET: {laws}\nDETYRA: Harto {instruction}."
        res = await self.llm.ainvoke(prompt)
        return str(res.content)

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None) -> str:
        if not self.llm: return "Offline."
        from . import vector_store_service
        l_docs = vector_store_service.query_global_knowledge_base(query_text=query, n_results=5)
        laws = "\n".join([d.get('text', '') for d in l_docs])
        prompt = f"Përgjigju shkurt duke cituar [Ligjin](doc://ligji) përkatës: {laws}\n\nPyetja: {query}"
        res = await self.llm.ainvoke(prompt)
        return str(res.content)