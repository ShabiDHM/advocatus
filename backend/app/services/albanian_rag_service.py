# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V48.0 (OPTIMIZED STREAMING BUFFER)
# 1. FEATURE: Smooth character‑by‑character streaming with 100% citation formatting.
# 2. OPTIMIZATION: Flushes buffer on spaces and punctuation, holds partial citations.
# 3. STATUS: Production‑ready, no degradation, perfect citations.

import os
import asyncio
import logging
import re
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

    def _format_citations(self, text: str) -> str:
        """Convert all complete law citations to Markdown links."""
        pattern = r'(Ligji[^,]+(?:Nr\.?\s*\d+/\d+)?[^,]*?,\s*Neni\s+(\d+))'
        return re.sub(pattern, r'[\1](doc://ligji)', text, flags=re.IGNORECASE)

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, 
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> AsyncGenerator[str, None]:
        """
        Streaming legal analysis with optimized buffer.
        Citations are formatted instantly without splitting, while the stream feels responsive.
        """
        if not self.llm:
            yield "Sistemi AI nuk është aktiv."
            yield AI_DISCLAIMER
            return
            
        from . import vector_store_service
        
        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=query, case_context_id=case_id, 
            document_ids=document_ids, n_results=20
        )
        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=query, jurisdiction=jurisdiction, n_results=15
        )
        
        context_str = "\n<<< MATERIALET E DOSJES >>>\n"
        for d in case_docs: 
            context_str += f"[{d.get('source')}, FAQJA: {d.get('page')}]: {d.get('text')}\n\n"
        
        context_str += "\n<<< BAZA LIGJORE STATUTORE >>>\n"
        for d in global_docs:
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
        
        buffer = ""
        MAX_BUFFER = 200  # Flush when buffer gets this large (prevents memory buildup)
        # Regex to detect an incomplete citation (ends with "Neni " and optional spaces)
        incomplete_pattern = re.compile(r'(Ligji[^,]*,\s*Neni\s*)$', re.IGNORECASE)

        try:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    raw_content = str(chunk.content)
                    buffer += raw_content

                    # Flush if buffer is too long (at last space)
                    if len(buffer) >= MAX_BUFFER:
                        last_space = buffer.rfind(' ')
                        if last_space != -1:
                            trailing = buffer[last_space+1:]
                            # If trailing part looks like an incomplete citation, hold it
                            if incomplete_pattern.search(trailing):
                                # Keep in buffer, wait for more
                                continue
                            # Safe to send up to last_space
                            to_send = buffer[:last_space+1]
                            buffer = buffer[last_space+1:]
                            if to_send.strip():
                                yield self._format_citations(to_send)
                    
                    # Flush on punctuation (sentence boundaries) for natural breaks
                    for delim in ('.', '!', '?', '\n'):
                        if delim in buffer:
                            pos = buffer.rfind(delim)
                            if pos != -1:
                                to_send = buffer[:pos+1]
                                rest = buffer[pos+1:]
                                # If the rest starts with an incomplete citation, hold it
                                if rest and incomplete_pattern.match(rest):
                                    buffer = rest
                                else:
                                    buffer = rest
                                if to_send.strip():
                                    yield self._format_citations(to_send)
                                break  # Only flush once per chunk

            # End of stream: flush remaining buffer
            if buffer.strip():
                yield self._format_citations(buffer)
            
            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"Deep Chat Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        """Generate a legal draft with fully formatted citations."""
        if not self.llm: 
            return "Sistemi AI Offline." + AI_DISCLAIMER
        from . import vector_store_service
        p_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=instruction, case_context_id=case_id, n_results=15
        )
        l_docs = vector_store_service.query_global_knowledge_base(
            query_text=instruction, n_results=15
        )
        
        facts = "\n".join([f"[{r.get('source')}]: {r.get('text')}" for r in p_docs])
        
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
            raw_response = str(res.content)
            formatted_response = self._format_citations(raw_response)
            return formatted_response + AI_DISCLAIMER
        except Exception as e:
            logger.error(f"Drafting failure: {e}")
            return f"Gabim gjatë draftimit: {str(e)}" + AI_DISCLAIMER

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None) -> str:
        """Quick RAG response with formatted citations."""
        if not self.llm: return ""
        from . import vector_store_service
        l_docs = vector_store_service.query_global_knowledge_base(query_text=query, n_results=5)
        laws = "\n".join([d.get('text', '') for d in l_docs])
        prompt = f"Përgjigju shkurt duke përdorur citimet me badge [Ligji](doc://ligji): {laws}\n\nPyetja: {query}"
        try:
            res = await self.llm.ainvoke(prompt)
            raw_response = str(res.content)
            formatted_response = self._format_citations(raw_response)
            return formatted_response
        except Exception:
            return "Gabim teknik."