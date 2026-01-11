# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V41.5 (QUERY EXPANSION)
# 1. LOGIC: Implemented 'Smart Query Expansion' for Global KB lookups.
# 2. FIX: Extracts keywords from Case Documents to enrich the search for relevant laws.
# 3. RESULT: Drastically improves the accuracy of legal citations.

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool, tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from bson import ObjectId

logger = logging.getLogger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
MAX_ITERATIONS = 10
LLM_TIMEOUT = 120

# --- PHOENIX VISUAL STANDARD ---
PROTOKOLLI_VIZUAL = """
URDHËRA PËR STILIN DHE CITIMIN:
1.  **PA LINQE:** Mos përdor asnjë format URL. Përdor vetëm tekst.
2.  **THEKSIM VIZUAL:** Përdor **BOLD** për të theksuar emrat e dokumenteve, ligjeve, datave kyçe dhe shumave monetare.
3.  **CITIMI I FAKTEVE:** 
    *   Formati: "...sipas **[Emri i Dokumentit] (faqe X)**."
4.  **CITIMI I LIGJEVE:**
    *   Formati: "...bazuar në **Nenin X të Ligjit për [Emri]**."
"""

# --- TOOLS ---
class CaseKnowledgeBaseTool(BaseTool):
    name: str = "query_case_knowledge_base"
    description: str = "Kërko FAKTE në 'BAZA E LËNDËS' (dokumentet e ngarkuara)."
    
    user_id: str
    case_id: Optional[str]
    document_ids: Optional[List[str]] = None

    def _run(self, query: str) -> str:
        from . import vector_store_service
        try:
            results = vector_store_service.query_case_knowledge_base(
                user_id=self.user_id, query_text=query, case_context_id=self.case_id, document_ids=self.document_ids
            )
            if not results: return "BAZA E LËNDËS: S'ka të dhëna."
            
            formatted = []
            for r in results:
                src = r.get('source', 'Dokument')
                pg = r.get('page', 'N/A')
                formatted.append(f"DOKUMENTI: '{src}' (Faqja: {pg}) -> PËRMBAJTJA: {r.get('text', '')}")
            
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Gabim në aksesimin e Bazës së Lëndës: {e}"

    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Search query for facts.")

class GlobalKnowledgeBaseInput(BaseModel): 
    query: str = Field(description="Search query for laws.")

@tool("query_global_knowledge_base", args_schema=GlobalKnowledgeBaseInput)
def query_global_knowledge_base_tool(query: str) -> str:
    """Kërko LIGJE në 'BAZA E LIGJEVE' (Kodet, Rregulloret)."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_global_knowledge_base(query_text=query)
        if not results: return "BAZA E LIGJEVE: S'ka ligje."
        return "\n\n".join([f"[BURIMI LIGJOR: {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e:
        return f"Gabim: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL, 
                base_url=OPENROUTER_BASE_URL, 
                temperature=0.0, 
                streaming=False, 
                timeout=LLM_TIMEOUT, 
                max_retries=2
            )
        else:
            self.llm = None
        
        # AGENT PROMPT
        researcher_template = f"""
        Ti je "Juristi AI", Këshilltar Ligjor.
        {PROTOKOLLI_VIZUAL}
        
        MJETET E TUA: {{tools}}
        
        FORMATI REACT:
        Question: ...
        Thought: ...
        Action: Një nga [{{tool_names}}]
        Action Input: ...
        Observation: ...
        Final Answer: ...
        
        Fillo!
        Question: {{input}}
        Thought: {{agent_scratchpad}}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: return ""
            oid = ObjectId(case_id)
            case = await self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1})
            return f"RASTI: {case.get('case_name', '')}. {case.get('description', '')}" if case else ""
        except: return ""
    
    def _create_agent_executor(self, session_tools: List) -> AgentExecutor:
        if not self.llm: raise ValueError("LLM not initialized")
        agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        return AgentExecutor(agent=agent, tools=session_tools, verbose=True, handle_parsing_errors=True, max_iterations=MAX_ITERATIONS, return_intermediate_steps=False)

    # --- MODE 1: DEEP RESEARCH (Agent Loop) ---
    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [ CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), query_global_knowledge_base_tool ]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""PYETJA: "{query}"\nJURIDIKSIONI: {jurisdiction.upper()}\nKONTEKSTI: {case_summary}"""
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return f"Ndjesë, ndodhi një gabim."

    # --- MODE 2: FAST TRACK (Vector RAG) ---
    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            from . import vector_store_service
            
            case_docs = await asyncio.to_thread(
                vector_store_service.query_case_knowledge_base,
                user_id=user_id, query_text=query, case_context_id=case_id, document_ids=document_ids, n_results=25
            )
            
            # PHOENIX FIX: Smart Query Expansion
            expanded_query = query
            if case_docs:
                # Extract potential keywords from the top retrieved documents
                keywords = re.findall(r'\b(?:alimentacion|përgjigje në padi|borxhe|kontestim|marrëveshje|aktgjykim|familjen)\b', " ".join(d['text'] for d in case_docs[:3]), re.IGNORECASE)
                unique_keywords = " ".join(list(dict.fromkeys(keywords)))
                expanded_query = f"{query} {unique_keywords}"
                logger.info(f"Expanded Query for Global KB: {expanded_query}")

            global_docs = await asyncio.to_thread(
                vector_store_service.query_global_knowledge_base,
                query_text=expanded_query, jurisdiction=jurisdiction, n_results=5
            )
            
            context_str = ""
            
            if case_docs:
                context_str += "\n<<< BURIMI PRIMAR: DOKUMENTET E DOSJES >>>\n"
                for d in case_docs:
                    clean_text = d.get('text', '').replace('\n', ' ').strip()
                    context_str += f"[DOKUMENTI: '{d.get('source', 'Padia')}']:\n{clean_text}\n\n"
            else:
                context_str += "\n<<< BURIMI PRIMAR: MUNGON (Nuk u gjet informacion) >>>\n"
            
            if global_docs:
                context_str += "\n<<< BURIMI SEKONDAR: BAZA LIGJORE (Për kontekst) >>>\n"
                for d in global_docs:
                    clean_text = d.get('text', '').replace('\n', ' ').strip()
                    context_str += f"[LIGJI: '{d.get('source', 'Ligj')}']:\n{clean_text}\n\n"

            fast_prompt = f"""
            Ti je "Juristi AI", asistent analitik për një avokat.
            {PROTOKOLLI_VIZUAL}
            
            PYETJA E AVOKATIT: "{query}"
            
            --- INFORMACIONI I GJETUR ---
            {context_str}
            -----------------------------
            
            **RREGULLA KYÇE PËR INTERPRETIMIN E 'AKTGJYKIMIT':**
            
            1. **PROPOZIM i Avokatit:**
               - **Nëse sheh:** "Gjykatës i propozohet...", "Kërkojmë nga gjykata...", "Të nxirret ky Aktgjykim..."
               - **Atëherë:** Ky është **PETITUMI (Kërkesa e Avokatit)**.
               - **Raporto si:** "Pala paditëse kërkon që gjykata të vendosë si vijon: ...". MOS thuaj "Gjykata vendosi".
            
            2. **HISTORIKU i Çështjes:**
               - **Nëse sheh:** "Sipas Aktgjykimit C.nr...", "Duke iu referuar Aktgjykimit..."
               - **Atëherë:** Ky është një vendim i vjetër që citohet si kontekst.
               - **Raporto si:** "Padia i referohet një vendimi të mëparshëm (C.nr...), i cili kishte vendosur që...".
            
            **STRUKTURA E PËRGJIGJES:**
            - Ndaj qartë **Pretendimet e Paditësit** nga **Kundërshtimet e të Paditurit**.
            - Raporto **Historikun** (aktgjykimet e vjetra).
            - Raporto **Kërkesat** (aktgjykimet e propozuara).
            - Cito **Nenin specifik** dhe **Emrin e Ligjit** nga Baza Ligjore.
            
            Përgjigju me saktësi procedurale.
            """
            
            response = await self.llm.ainvoke(fast_prompt)
            return str(response.content)

        except Exception as e:
            logger.error(f"Fast RAG error: {e}", exc_info=True)
            return "Ndjesë, nuk arrita të marr informacionin shpejt."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            p_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, 
                query_text=instruction[:500], 
                case_context_id=case_id
            )
            facts = ""
            if p_docs:
                for r in p_docs:
                    src = r.get('source', 'Dokument')
                    pg = r.get('page', 'N/A')
                    facts += f"--- FAKT NGA: '{src}' (Fq. {pg}) ---\n{r.get('text', '')}\n\n"
            else:
                facts = "S'ka fakte specifike."
            
            law_keywords = "procedura civile shpenzimet familja detyrimet"
            l_docs = vector_store_service.query_global_knowledge_base(f"{instruction} {law_keywords}", jurisdiction='ks')
            laws = "\n".join([f"LIGJI: {d.get('text', '')}" for d in l_docs]) if l_docs else "S'ka ligje specifike."

            drafting_prompt = f"""
            Ti je "Mjeshtër i Litigimit" (Ghostwriter), avokat elitar në Kosovë.
            {PROTOKOLLI_VIZUAL}
            
            **URDHËR: MODALI GHOSTWRITER (STRIKT):**
            1. Prodho VETËM tekstin e dokumentit final.
            2. MOS shto asnjë koment shtesë.
            
            --- MATERIALET ---
            [FAKTET]: {facts}
            [LIGJET]: {laws}
            [UDHËZIMI]: {instruction}
            ---
            DETYRA: Harto dokumentin final TANI.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"