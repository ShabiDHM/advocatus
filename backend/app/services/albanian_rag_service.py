# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V46.9 (ENFORCED BADGE INTEGRITY)
# 1. FIX: Command-based prompt ensures every law is wrapped in [Text](doc://ligji).
# 2. FIX: Hardened Lex Specialis for Kosovo Family cases.
# 3. STATUS: 100% Unabridged. Senior Partner reasoning with active badges.

import os, asyncio, logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from langchain_openai import ChatOpenAI
from bson import ObjectId

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

PROTOKOLLI_PROFESIONAL = """
**URDHËRA MANDATORË PËR HARTIM:**
1. Çdo referencë ligjore DUHET të rrethohet me: [Emri i Ligjit, Neni X](doc://ligji).
2. Çdo fakt nga dosja DUHET të rrethohet me: (Burimi: [Dokumenti], fq. [X]).
3. Për Alimentacion/Kujdestari, përdor VETËM [Ligjin Nr. 2004/32 Për Familjen e Kosovës](doc://ligji).
4. MOS përdor LMD për çështje të fëmijëve.
"""

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.llm = ChatOpenAI(
            model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, 
            api_key=DEEPSEEK_API_KEY, # type: ignore
            temperature=0.0, streaming=True
        ) if DEEPSEEK_API_KEY else None
        
    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> AsyncGenerator[str, None]:
        if not self.llm: yield "Sistemi AI nuk është aktiv."; return
        from . import vector_store_service
        
        # Retrieval Depth: 15 laws
        case_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=query, case_context_id=case_id, document_ids=document_ids, n_results=20)
        global_docs = vector_store_service.query_global_knowledge_base(query_text=query, jurisdiction=jurisdiction, n_results=15)
        
        context_str = "<<< MATERIALET E RASTIT >>>\n"
        for d in case_docs: context_str += f"[{d.get('source')}, fq.{d.get('page')}]: {d.get('text')}\n\n"
        context_str += "\n<<< BAZA LIGJORE STATUTORE >>>\n"
        for d in global_docs: context_str += f"LIGJI: '{d.get('source')}': {d.get('text')}\n\n"
        
        prompt = f"{PROTOKOLLI_PROFESIONAL}\nKONTEKSTI:\n{context_str}\n\nPYETJA: {query}\n\nDETYRA: Analizo dhe përgjigju duke përdorur citimet statutore me badge [Ligji](doc://ligji)."
        
        async for chunk in self.llm.astream(prompt):
            if chunk.content: yield str(chunk.content)

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        from . import vector_store_service
        p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction, case_context_id=case_id, n_results=15)
        l_docs = vector_store_service.query_global_knowledge_base(query_text=instruction, n_results=15)
        facts = "\n".join([f"[{r.get('source')}]: {r.get('text')}" for r in p_docs])
        laws = "\n".join([f"[{r.get('source')}]: {r.get('text')}" for r in l_docs])
        prompt = f"{PROTOKOLLI_PROFESIONAL}\nPROVAT: {facts}\nLIGJET: {laws}\nDETYRA: Harto {instruction} duke përdorur citimet me badge [Ligji](doc://ligji)."
        res = await self.llm.ainvoke(prompt)
        return str(res.content)

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None) -> str:
        if not self.llm: return ""
        from . import vector_store_service
        l_docs = vector_store_service.query_global_knowledge_base(query_text=query, n_results=5)
        laws = "\n".join([d.get('text', '') for d in l_docs])
        prompt = f"Përgjigju shkurt duke përdorur citimet me badge [Ligji](doc://ligji) bazuar në: {laws}\n\nPyetja: {query}"
        res = await self.llm.ainvoke(prompt)
        return str(res.content)