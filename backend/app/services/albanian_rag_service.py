# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V52.5 (IMPROVED BUFFER FLUSH)

import os
import sys
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
        print(f"CITATION_DIAG: Processing: '{full_citation}'", flush=True)
        print(f"CITATION_DIAG: law_text='{law_text}', article_num='{article_num}'", flush=True)

        law_number = self._extract_law_number(law_text)
        if law_number:
            print(f"CITATION_DIAG: Extracted law number: '{law_number}'", flush=True)
            num_key = (law_number, article_num.strip())
            chunk_id = self.law_number_map.get(num_key)
            if chunk_id:
                print(f"CITATION_DIAG: Found by law number! chunk_id={chunk_id}", flush=True)
                return f"[{full_citation}](/laws/{chunk_id})"
            else:
                print(f"CITATION_DIAG: No match for law number key: {num_key}", flush=True)

        norm_title = self._normalize_law_title(law_text)
        key = (norm_title, article_num.strip())
        chunk_id = self.citation_map.get(key)
        if chunk_id:
            print(f"CITATION_DIAG: Found by title! chunk_id={chunk_id}", flush=True)
            return f"[{full_citation}](/laws/{chunk_id})"
        else:
            print(f"CITATION_DIAG: No match for title key: {key}", flush=True)

        print(f"CITATION_DIAG: No chunk_id found, returning plain text", flush=True)
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
        print("CITATION_DIAG: chat method started", flush=True)
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
        MAX_BUFFER = 2000  # Increased to allow more complete sentences
        # Patterns for incomplete citations at the end of buffer
        incomplete_start = re.compile(r'(Ligji[^,]*,\s*Neni\s*|Neni\s+\d+\s+i\s+Ligji[^,]*)$', re.IGNORECASE)
        # Also pattern for a complete citation start (for checking after delimiter)
        complete_start = re.compile(r'^(Ligji[^,]*,\s*Neni\s+\d+|Neni\s+\d+\s+i\s+Ligji[^,]*)', re.IGNORECASE)

        try:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    raw = str(chunk.content)
                    buffer += raw

                    # First, try to flush on punctuation (safe boundaries)
                    flushed = False
                    for delim in ('.', '!', '?', '\n'):
                        if delim in buffer:
                            # Find the last occurrence of this delimiter
                            pos = buffer.rfind(delim)
                            if pos != -1:
                                # Look at the text after this delimiter
                                rest = buffer[pos+1:].lstrip()
                                # If the rest starts with a citation, keep it in buffer
                                if rest and complete_start.match(rest):
                                    print(f"BUFFER_DIAG: Holding rest after delimiter: '{rest[:50]}...'", flush=True)
                                    continue  # Don't flush this delimiter yet
                                # Otherwise, flush up to and including delimiter
                                to_send = buffer[:pos+1]
                                buffer = buffer[pos+1:]
                                if to_send.strip():
                                    print(f"BUFFER_DIAG: Flushing on delimiter '{delim}', len={len(to_send)}", flush=True)
                                    yield self._format_citations(to_send)
                                flushed = True
                                break  # Only flush once per chunk

                    if flushed:
                        continue

                    # If no punctuation flush, check buffer size
                    if len(buffer) >= MAX_BUFFER:
                        # Try to find last space before MAX_BUFFER
                        last_space = buffer.rfind(' ', 0, MAX_BUFFER)
                        if last_space != -1:
                            # Check if the part after last_space is an incomplete citation start
                            trailing = buffer[last_space+1:]
                            if incomplete_start.search(trailing):
                                # Can't split here; find an earlier space if possible
                                earlier_space = buffer.rfind(' ', 0, last_space)
                                if earlier_space != -1:
                                    last_space = earlier_space
                                    trailing = buffer[last_space+1:]
                                else:
                                    # No earlier space, have to flush anyway, but log warning
                                    print(f"BUFFER_DIAG: WARNING: Forced flush may split citation: '{trailing[:50]}...'", flush=True)
                            to_send = buffer[:last_space+1]
                            buffer = buffer[last_space+1:]
                            if to_send.strip():
                                print(f"BUFFER_DIAG: Flushing due to MAX_BUFFER, len={len(to_send)}", flush=True)
                                yield self._format_citations(to_send)
                        else:
                            # No space found, just flush everything (rare)
                            if buffer.strip():
                                print(f"BUFFER_DIAG: Flushing all due to MAX_BUFFER (no space)", flush=True)
                                yield self._format_citations(buffer)
                            buffer = ""

            # End of stream: flush remaining buffer
            if buffer.strip():
                print(f"BUFFER_DIAG: Flushing final buffer, len={len(buffer)}", flush=True)
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