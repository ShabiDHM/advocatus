# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V52.3 (FORCED PRINT DIAGNOSTICS)

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from langchain_openai import ChatOpenAI
from bson import ObjectId

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 120

AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

PROTOKOLLI_MANDATOR = """
**URDHËRA TË RREPTË FORMATIMI:**
1. Çdo argument ligjor DUHET të citojë **nenin konkret** duke përdorur **emrin e plotë zyrtar të ligjit** siç paraqitet në kontekst, duke përfshirë numrin zyrtar nëse ekziston.  
   **Shembull i saktë:** `Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve, Neni 5`  
   **Mos përdorni emra të shkurtuar si "Ligji për Familjen" – përdorni gjithmonë emrin e plotë.**
2. Për çdo ligj të cituar, DUHET të shtoni rreshtin: **RELEVANCA:** [Pse ky nen është thelbësor për rastin].
3. Përdor TITUJT MARKDOWN (###) për të ndarë seksionet.
4. MOS përdor blloqe kodi.
"""

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.citation_map: Dict[Tuple[str, str], str] = {}      # (full_law_title, article_num) -> chunk_id
        self.law_number_map: Dict[Tuple[str, str], str] = {}   # (law_number, article_num) -> chunk_id
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
        return ' '.join(title.strip().split())

    def _extract_law_number(self, text: str) -> Optional[str]:
        match = re.search(r'Nr\.?\s*([\d/]+(?:\-[\d/]+)?)', text, re.IGNORECASE)
        return match.group(1) if match else None

    def _build_citation_map(self, global_docs: List[Dict[str, Any]]):
        self.citation_map.clear()
        self.law_number_map.clear()
        for d in global_docs:
            law_title = d.get('law_title')
            article_num = d.get('article_number')
            chunk_id = d.get('chunk_id')
            if law_title and article_num and chunk_id:
                norm_title = self._normalize_law_title(law_title)
                key = (norm_title, str(article_num).strip())
                self.citation_map[key] = chunk_id
                law_number = self._extract_law_number(law_title)
                if law_number:
                    num_key = (law_number, str(article_num).strip())
                    self.law_number_map[num_key] = chunk_id

    def _format_citations(self, text: str) -> str:
        pattern1 = r'(Ligji[^,]+(?:Nr\.?\s*[\d/]+(?:\-[\d/]+)?)?[^,]*?,\s*Neni\s+(\d+))'
        pattern2 = r'Neni\s+(\d+)\s+i\s+(Ligji[^\.]+)'

        def replacer_pattern1(match):
            full = match.group(1)
            art = match.group(2)
            law_part = full.split(', Neni')[0].strip()
            return self._make_link(law_part, art, full)

        def replacer_pattern2(match):
            art = match.group(1)
            law_part = match.group(2).strip()
            full = f"Neni {art} i {law_part}"
            return self._make_link(law_part, art, full)

        text = re.sub(pattern1, replacer_pattern1, text, flags=re.IGNORECASE)
        text = re.sub(pattern2, replacer_pattern2, text, flags=re.IGNORECASE)
        return text

    def _make_link(self, law_text: str, article_num: str, full_citation: str) -> str:
        # PRINT for guaranteed output
        print(f"CITATION_DIAG: Processing: '{full_citation}'")
        print(f"CITATION_DIAG: law_text='{law_text}', article_num='{article_num}'")

        law_number = self._extract_law_number(law_text)
        if law_number:
            print(f"CITATION_DIAG: Extracted law number: '{law_number}'")
            num_key = (law_number, article_num.strip())
            chunk_id = self.law_number_map.get(num_key)
            if chunk_id:
                print(f"CITATION_DIAG: Found by law number! chunk_id={chunk_id}")
                return f"[{full_citation}](/laws/{chunk_id})"
            else:
                print(f"CITATION_DIAG: No match for law number key: {num_key}")

        norm_title = self._normalize_law_title(law_text)
        key = (norm_title, article_num.strip())
        chunk_id = self.citation_map.get(key)
        if chunk_id:
            print(f"CITATION_DIAG: Found by title! chunk_id={chunk_id}")
            return f"[{full_citation}](/laws/{chunk_id})"
        else:
            print(f"CITATION_DIAG: No match for title key: {key}")

        print(f"CITATION_DIAG: No chunk_id found, returning plain text")
        return full_citation

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
                    raw = str(chunk.content)
                    buffer += raw

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

            if buffer.strip():
                yield self._format_citations(buffer)
            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"Deep Chat Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
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
            raw = str(res.content)
            formatted = self._format_citations(raw)
            return formatted + AI_DISCLAIMER
        except Exception as e:
            logger.error(f"Drafting failure: {e}")
            return f"Gabim gjatë draftimit: {str(e)}" + AI_DISCLAIMER

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None) -> str:
        if not self.llm:
            return ""
        from . import vector_store_service
        l_docs = vector_store_service.query_global_knowledge_base(query_text=query, n_results=5)
        self._build_citation_map(l_docs)
        laws = "\n".join([d.get('text', '') for d in l_docs])
        prompt = f"Përgjigju shkurt duke përdorur citimet me badge [Ligji](doc://ligji): {laws}\n\nPyetja: {query}"
        try:
            res = await self.llm.ainvoke(prompt)
            raw = str(res.content)
            formatted = self._format_citations(raw)
            return formatted
        except Exception:
            return "Gabim teknik."