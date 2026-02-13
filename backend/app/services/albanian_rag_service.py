# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V47.6 (CITATION METADATA INTEGRATION)
# 1. ENHANCED: Global law context now includes explicit law_title and article_number metadata.
# 2. ENHANCED: Pre‑formatted Markdown citation [Ligji, Neni XX](doc://ligji) shown to LLM.
# 3. FIXED: Eliminates hallucination of article numbers via structured metadata.
# 4. STATUS: Full synergy with ingest_laws.py V3.0 article‑level ingestion.

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
LLM_TIMEOUT = 120

AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

PROTOKOLLI_MANDATOR = """
**URDHËRA TË RREPTË FORMATIMI:**
1. Çdo argument ligjor DUHET të citojë **nenin konkret** nga ligji, duke përdorur format:  
   `[Emri i Ligjit, Neni {numri_i_nenit}](doc://ligji)`.  
   **Shembull i saktë:** `[Emri i Ligjit, Neni 5](doc://ligji)`.  
   ⚠️ **NENI X ËSHTË I NDALUAR** – nëse konteksti përmban numrin e nenit, përdore atë; nëse nuk e përmban, përdor formulimin "Neni përkatës" ose cito drejtpërdrejt tekstin pa numër.
2. Për çdo ligj të cituar, DUHET të shtoni rreshtin: **RELEVANCA:** [Pse ky nen është thelbësor për rastin].
3. Përdor TITUJT MARKDOWN (###) për të ndarë seksionet.
4. MOS përdor blloqe kodi.
"""

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL, 
                base_url=OPENROUTER_BASE_URL, 
                api_key=DEEPSEEK_API_KEY,  # type: ignore
                temperature=0.0, 
                streaming=True,
                timeout=LLM_TIMEOUT
            )
        else:
            self.llm = None
        
    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> AsyncGenerator[str, None]:
        """
        DEEP MODE: High-IQ Streaming Legal Analysis + Metadata‑enriched citations.
        """
        if not self.llm:
            yield "Sistemi AI nuk është aktiv."
            yield AI_DISCLAIMER
            return
            
        from . import vector_store_service
        
        case_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=query, case_context_id=case_id, document_ids=document_ids, n_results=20)
        global_docs = vector_store_service.query_global_knowledge_base(query_text=query, jurisdiction=jurisdiction, n_results=15)
        
        context_str = "\n<<< MATERIALET E DOSJES >>>\n"
        for d in case_docs: 
            context_str += f"[{d.get('source')}, FAQJA: {d.get('page')}]: {d.get('text')}\n\n"
        
        context_str += "\n<<< BAZA LIGJORE STATUTORE >>>\n"
        for d in global_docs:
            # PHOENIX: Extract metadata – law_title supersedes source, article_number if available
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number')
            
            if article_num:
                citation = f"[{law_title}, Neni {article_num}](doc://ligji)"
            else:
                citation = f"[{law_title}](doc://ligji)"
            
            context_str += f"LIGJI: {citation}\nPËRMBAJTJA: {d.get('text')}\n\n"
        
        prompt = f"""
        Ti je "Senior Legal Partner". Detyra jote është të japësh një opinion ligjor suprem.
        {PROTOKOLLI_MANDATOR}
        
        **KONTEKSTI I RASTIT:**
        {context_str}
        
        **PYETJA:** "{query}"

        **STRUKTURA (OBLIGATIVE):**
        ### 1. ANALIZA E FAKTEVE
        (Përmbledhje analitike e fakteve nga dosja me citime burimesh)
        
        ### 2. BAZA LIGJORE DHE RELEVANCA
        (Neni -> [Emri i Ligjit](doc://ligji). Shpjegoni RELEVANCËN e secilit nen)
        
        ### 3. KONKLUZIONI STRATEGJIK
        (Rekomandimi yt profesional si avokat i lartë)
        
        Fillo hartimin tani:
        """
        
        try:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    yield str(chunk.content)
            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"Deep Chat Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        """
        Generates a legal draft document with metadata‑aware law citations + disclaimer.
        """
        if not self.llm: 
            return "Sistemi AI Offline." + AI_DISCLAIMER
        from . import vector_store_service
        p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction, case_context_id=case_id, n_results=15)
        l_docs = vector_store_service.query_global_knowledge_base(query_text=instruction, n_results=15)
        
        facts = "\n".join([f"[{r.get('source')}]: {r.get('text')}" for r in p_docs])
        
        # PHOENIX: Enriched law context with citation metadata
        laws = []
        for d in l_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number')
            if article_num:
                citation = f"[{law_title}, Neni {article_num}](doc://ligji)"
            else:
                citation = f"[{law_title}](doc://ligji)"
            laws.append(f"{citation}: {d.get('text')}")
        laws_str = "\n".join(laws)
        
        prompt = f"{PROTOKOLLI_MANDATOR}\nPROVAT: {facts}\nLIGJET: {laws_str}\nDETYRA: Harto {instruction}."
        try:
            res = await self.llm.ainvoke(prompt)
            return str(res.content) + AI_DISCLAIMER
        except Exception as e:
            logger.error(f"Drafting failure: {e}")
            return f"Gabim gjatë draftimit: {str(e)}" + AI_DISCLAIMER

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None) -> str:
        if not self.llm: return ""
        from . import vector_store_service
        l_docs = vector_store_service.query_global_knowledge_base(query_text=query, n_results=5)
        laws = "\n".join([d.get('text', '') for d in l_docs])
        prompt = f"Përgjigju shkurt duke përdorur citimet me badge [Ligji](doc://ligji): {laws}\n\nPyetja: {query}"
        try:
            res = await self.llm.ainvoke(prompt)
            return str(res.content)
        except Exception:
            return "Gabim teknik."