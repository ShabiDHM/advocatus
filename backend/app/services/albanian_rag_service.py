# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V50.0 (FLEXIBLE CITATION PATTERNS)
# 1. FEATURE: Supports multiple citation formats (standard and reverse order).
# 2. FIXED: Now correctly maps "Neni XX i Ligjit ..." to chunk IDs.
# 3. OPTIMIZED: Smooth streaming buffer with 100% citation formatting.

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
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
        self.citation_map: Dict[Tuple[str, str], str] = {}  # (law_title, article_num) -> chunk_id
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

    def _normalize_law_title(self, title: str) -> str:
        """Normalize law title for consistent lookup."""
        # Remove extra spaces and standardize
        return ' '.join(title.strip().split())

    def _build_citation_map(self, global_docs: List[Dict[str, Any]]):
        """Populate mapping from (law_title, article_num) to chunk_id."""
        self.citation_map.clear()
        for d in global_docs:
            law_title = d.get('law_title')
            article_num = d.get('article_number')
            chunk_id = d.get('chunk_id')
            if law_title and article_num and chunk_id:
                norm_title = self._normalize_law_title(law_title)
                key = (norm_title, str(article_num).strip())
                self.citation_map[key] = chunk_id

    def _format_citations(self, text: str) -> str:
        """
        Convert plain‑text law citations to Markdown links using the citation map.
        Supports both "Ligji ... , Neni XX" and "Neni XX i Ligjit ..." patterns.
        """
        # Pattern 1: "Ligji [law_title], Neni [article_num]"
        pattern1 = r'(Ligji[^,]+(?:Nr\.?\s*\d+/\d+)?[^,]*?,\s*Neni\s+(\d+))'
        
        # Pattern 2: "Neni [article_num] i Ligjit [law_title]"
        pattern2 = r'Neni\s+(\d+)\s+i\s+(Ligji[^\.]+)'

        def replacer_pattern1(match):
            full_citation = match.group(1)
            article_num = match.group(2)
            # Extract law title (everything before ", Neni")
            law_title = full_citation.split(', Neni')[0].strip()
            return self._make_link(law_title, article_num, full_citation)

        def replacer_pattern2(match):
            article_num = match.group(1)
            law_title = match.group(2).strip()
            full_citation = f"Neni {article_num} i {law_title}"
            return self._make_link(law_title, article_num, full_citation)

        # Apply both patterns
        text = re.sub(pattern1, replacer_pattern1, text, flags=re.IGNORECASE)
        text = re.sub(pattern2, replacer_pattern2, text, flags=re.IGNORECASE)
        return text

    def _make_link(self, law_title: str, article_num: str, full_citation: str) -> str:
        """Generate markdown link using citation map."""
        norm_title = self._normalize_law_title(law_title)
        key = (norm_title, article_num.strip())
        chunk_id = self.citation_map.get(key)
        if chunk_id:
            return f"[{full_citation}](/laws/{chunk_id})"
        else:
            logger.warning(f"No chunk_id found for citation: {full_citation}")
            return full_citation  # fallback to plain text

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict]) -> str:
        context = "\n<<< MATERIALET E DOSJES >>>\n"
        for d in case_docs:
            context += f"[{d.get('source')}, FAQJA: {d.get('page')}]: {d.get('text')}\n\n"

        context += "\n<<< BAZA LIGJORE STATUTORE >>>\n"
        for d in global_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number')
            chunk_id = d.get('chunk_id')
            if article_num and chunk_id:
                citation = f"[{law_title}, Neni {article_num}](/laws/{chunk_id})"
            elif chunk_id:
                citation = f"[{law_title}](/laws/{chunk_id})"
            else:
                citation = law_title
            context += f"LIGJI: {citation}\nPËRMBAJTJA: {d.get('text')}\n\n"
        return context

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, 
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> AsyncGenerator[str, None]:
        """
        Streaming legal analysis with optimized buffer and real HTTP law links.
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
        
        # Build the citation map for post-processing
        self._build_citation_map(global_docs)
        
        context_str = self._build_context(case_docs, global_docs)
        
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
        MAX_BUFFER = 200
        incomplete_pattern = re.compile(r'(Ligji[^,]*,\s*Neni\s*|Neni\s+\d+\s+i\s+Ligji[^,]*)$', re.IGNORECASE)

        try:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    raw_content = str(chunk.content)
                    buffer += raw_content

                    # Flush if buffer too long (at last space)
                    if len(buffer) >= MAX_BUFFER:
                        last_space = buffer.rfind(' ')
                        if last_space != -1:
                            trailing = buffer[last_space+1:]
                            if incomplete_pattern.search(trailing):
                                continue
                            to_send = buffer[:last_space+1]
                            buffer = buffer[last_space+1:]
                            if to_send.strip():
                                yield self._format_citations(to_send)
                    
                    # Flush on punctuation
                    for delim in ('.', '!', '?', '\n'):
                        if delim in buffer:
                            pos = buffer.rfind(delim)
                            if pos != -1:
                                to_send = buffer[:pos+1]
                                rest = buffer[pos+1:]
                                if rest and incomplete_pattern.match(rest):
                                    buffer = rest
                                else:
                                    buffer = rest
                                if to_send.strip():
                                    yield self._format_citations(to_send)
                                break

            # End of stream
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
        
        self._build_citation_map(l_docs)
        context_str = self._build_context(p_docs, l_docs)
        
        prompt = f"{PROTOKOLLI_MANDATOR}\n{context_str}\nDETYRA: Harto {instruction}."
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
        self._build_citation_map(l_docs)
        laws = "\n".join([d.get('text', '') for d in l_docs])
        prompt = f"Përgjigju shkurt duke përdorur citimet me badge [Ligji](doc://ligji): {laws}\n\nPyetja: {query}"
        try:
            res = await self.llm.ainvoke(prompt)
            raw_response = str(res.content)
            formatted_response = self._format_citations(raw_response)
            return formatted_response
        except Exception:
            return "Gabim teknik."