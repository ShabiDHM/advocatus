# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V46.0 (LOGIC SWAP)
# 1. FIX: Swapped the prompt logic between 'chat' (DEEP) and 'fast_rag' (FAST).
# 2. RESULT: "Thellë" now produces the detailed, professional analysis.
# 3. RESULT: "Shpejtë" now produces the concise summary paragraph.

import os
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool, tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from bson import ObjectId

logger = logging.getLogger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
MAX_ITERATIONS = 10
LLM_TIMEOUT = 120

PROTOKOLLI_PROFESIONAL = """
**URDHËRA MANDATORË PËR ANALIZË DHE CITIM:**
1.  **JURIDIKSIONI I REPUBLIKËS SË KOSOVËS (ABSOLUT):** Çdo analizë duhet të bazohet **EKSKLUZIVISHT** në legislacionin e Kosovës. **MOS** përmend kurrë ligjet e Shqipërisë.
2.  **CITIMI I FAKTEVE (Nga "Baza e Lëndës"):** Çdo fjali me informacion nga një dokument **DUHET** të përfundojë me citim. FORMATI: `(Burimi: [Emri i Dokumentit], fq. [numri])`
3.  **ANALIZA DHE CITIMI I LIGJEVE (Nga "Baza e Ligjeve"):** Shpjego shkurtimisht çfarë thotë neni dhe pse është relevant. FORMATI I CITIMIT (ABSOLUT): `[**[Emri i plotë i Ligjit] Nr. [Numri], Neni [numri]**](doc://[Emri i plotë i Ligjit] Nr. [Numri], Neni [numri])`
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
            results = vector_store_service.query_case_knowledge_base(user_id=self.user_id, query_text=query, case_context_id=self.case_id, document_ids=self.document_ids)
            if not results: return "BAZA E LËNDËS: S'ka të dhëna."
            formatted = [f"DOKUMENTI: '{r.get('source', 'Pacaktuar')}' (FAQJA: {r.get('page', 'N/A')}) -> PËRMBAJTJA: {r.get('text', '')}" for r in results]
            return "\n\n".join(formatted)
        except Exception as e: return f"Gabim: {e}"
    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Search query for facts.")

@tool("query_global_knowledge_base")
def query_global_knowledge_base_tool(query: str) -> str:
    """Kërko LIGJE në 'BAZA E LIGJEVE' (Kodet, Rregulloret) vetëm për Kosovën."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_global_knowledge_base(query_text=query)
        if not results: return "BAZA E LIGJEVE: S'ka ligje."
        return "\n\n".join([f"[BURIMI LIGJOR: '{r.get('source', 'Ligj i pacaktuar')}']\n{r.get('text', '')}" for r in results])
    except Exception as e: return f"Gabim: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, temperature=0.0, streaming=False, timeout=LLM_TIMEOUT, max_retries=2)
        else:
            self.llm = None
        
        researcher_template = f"Ti je 'Juristi AI'.\n{PROTOKOLLI_PROFESIONAL}\nMJETET: {{tools}}\nFORMATI REACT:\nQuestion: ...\nThought: ...\nAction: Një nga [{{tool_names}}]\nAction Input: ...\nObservation: ...\nFinal Answer: ...\n\nFillo!\nQuestion: {{input}}\nThought: {{agent_scratchpad}}"
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: return ""
            oid = ObjectId(case_id)
            case = self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1})
            return f"RASTI: {case.get('case_name', '')}. {case.get('description', '')}" if case else ""
        except: return ""
    
    def _create_agent_executor(self, session_tools: List) -> AgentExecutor:
        if not self.llm: raise ValueError("LLM not initialized")
        agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        return AgentExecutor(agent=agent, tools=session_tools, verbose=True, handle_parsing_errors=True, max_iterations=MAX_ITERATIONS, return_intermediate_steps=False)

    # --- DEEP MODE (THELLË) ---
    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            from . import vector_store_service
            
            # 1. Get Context (Same as FAST mode)
            case_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=query, case_context_id=case_id, document_ids=document_ids, n_results=25)
            global_docs = vector_store_service.query_global_knowledge_base(query_text=query, jurisdiction=jurisdiction, n_results=5)
            
            context_str = "\n<<< BURIMI PRIMAR: DOKUMENTET E DOSJES >>>\n"
            if case_docs:
                for d in case_docs: context_str += f"[DOKUMENTI: '{d.get('source', 'N/A')}', FAQJA: {d.get('page', 'N/A')}]:\n{d.get('text', '')}\n\n"
            else: context_str += "\n<<< MUNGON >>>\n"
            
            if global_docs:
                context_str += "\n<<< BURIMI SEKONDAR: BAZA LIGJORE >>>\n"
                for d in global_docs: context_str += f"[LIGJI: '{d.get('source', 'N/A')}']:\n{d.get('text', '')}\n\n"
            
            # PHOENIX: Use the DETAILED, PROFESSIONAL prompt for DEEP mode
            deep_professional_prompt = f"""
            Ti je "Juristi AI", një asistent ligjor analitik dhe tejet preciz.
            {PROTOKOLLI_PROFESIONAL}
            
            **MATERIALET PËR ANALIZË:**
            {context_str}
            
            **PYETJA E AVOKATIT:** "{query}"

            **DETYRA JOTE (HAP PAS HAPI):**
            1.  **Sintetizo Faktet:** Lexo me kujdes materialet dhe strukturo përgjigjen me seksione të qarta (Pretendimet, Kundërshtimet, etj.), duke cituar faktet.
            2.  **Sintetizo dhe Analizo Ligjin:** Krijo një seksion "BAZA LIGJORE E APLIKUESHME". Për çdo nen ligjor relevant:
                a.  Gjej tekstin e plotë të nenit brenda kontekstit `[LIGJI: '...']`.
                b.  Shpjego substancën e nenit.
                c.  Lidhe nenin me faktet e rastit.
                d.  Cito nenin sipas protokollit.
            
            **VERIFIKIM I DYFISHTË:**
            - A i kam vendosur dy yje (`**`) rreth citimeve ligjore?
            - A është numri i nenit identik brenda `[]` dhe `doc://`?
            - A kam ofruar shpjegim për çdo ligj të cituar?

            Formulo përgjigjen FINALE TANI.
            """
            response = await self.llm.ainvoke(deep_professional_prompt)
            return str(response.content)

        except Exception as e:
            logger.error(f"Deep Chat (RAG) error: {e}", exc_info=True)
            return f"Ndjesë, ndodhi një gabim në analizën e thellë."

    # --- FAST MODE (SHPEJTË) ---
    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            # PHOENIX: Use the Agent for FAST mode to get a direct, concise answer.
            tools = [ CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), query_global_knowledge_base_tool ]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""PYETJA: "{query}"\nKONTEKSTI: {case_summary}"""
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Fast Chat (Agent) error: {e}", exc_info=True)
            return "Ndjesë, nuk arrita të marr informacionin shpejt."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        # This function remains unchanged.
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction[:500], case_context_id=case_id)
            facts = "\n\n".join([f"--- FAKT NGA: '{r.get('source', 'Dokument')}' (Fq. {r.get('page', 'N/A')}) ---\n{r.get('text', '')}" for r in p_docs]) if p_docs else "S'ka fakte specifike."
            law_keywords = "procedura civile shpenzimet familja detyrimet"
            l_docs = vector_store_service.query_global_knowledge_base(f"{instruction} {law_keywords}", jurisdiction='ks')
            laws = "\n".join([f"LIGJI: {d.get('text', '')}" for d in l_docs]) if l_docs else "S'ka ligje specifike."
            drafting_prompt = f"Ti je 'Mjeshtër i Litigimit'.\n{PROTOKOLLI_PROFESIONAL}\nURDHËR: MODALI GHOSTWRITER (STRIKT):\n1. Prodho VETËM tekstin e dokumentit final.\n2. MOS shto asnjë koment shtesë.\n--- MATERIALET ---\n[FAKTET]: {facts}\n[LIGJET]: {laws}\n[UDHËZIMI]: {instruction}\n---\nDETYRA: Harto dokumentin final TANI."
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"