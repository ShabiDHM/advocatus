# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V32.1 (STRUCTURED CREATIVITY)
# 1. UPGRADE: Drafting prompt now explicitly commands the AI to follow the user-provided template structure.
# 2. BEHAVIOR: Balances creative legal argumentation with predictable, structured output.
# 3. STATUS: Final fine-tuning complete.

import os
import asyncio
import logging
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

# --- PHOENIX V31.0: UNIFIED PROTOCOL OF LEGAL EXPERTISE ---
PROTOKOLLI_I_EKSPERTIZES_LIGJORE = """
URDHËRA TË PADISKUTUESHËM:
1.  DY MENDJET (DUAL BRAIN): BAZA E LIGJEVE (LIGJI) dhe BAZA E LËNDËS (FAKTET).
2.  JURIDIKSIONI I KOSOVËS: Analiza duhet të jetë STRICTLY e bazuar në ligjet e REPUBLIKËS SË KOSOVËS.
3.  CITIMI PROFESIONAL (DETYRUESHËM):
    *   CITIMI I FAKTIT: (Burimi: [Emri i Dokumentit], fq. [numri]).
    *   CITIMI I LIGJIT: [**Emri i Ligjit Nr. XX/L-XXX, Neni YY**](doc://...).
"""

# --- TOOLS ---
class CaseKnowledgeBaseTool(BaseTool):
    name: str = "query_case_knowledge_base"
    description: str = "Kërko FAKTE në 'BAZA E LËNDËS' (dokumentet e ngarkuara)."
    user_id: str; case_id: Optional[str]; document_ids: Optional[List[str]] = None
    def _run(self, query: str) -> str:
        from . import vector_store_service
        try:
            results = vector_store_service.query_case_knowledge_base(user_id=self.user_id, query_text=query, case_context_id=self.case_id, document_ids=self.document_ids)
            if not results: return "BAZA E LËNDËS: Nuk u gjetën të dhëna."
            return "\n\n".join([f"[BURIMI I FAKTIT: {r.get('source', 'Unknown')}, Faqja: {r.get('page', 'N/A')}]\n{r.get('text', '')}" for r in results])
        except Exception as e: return f"Gabim në aksesimin e Bazës së Lëndës: {e}"
    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Search query for facts.")

class GlobalKnowledgeBaseInput(BaseModel): query: str = Field(description="Search query for laws.")
@tool("query_global_knowledge_base", args_schema=GlobalKnowledgeBaseInput)
def query_global_knowledge_base_tool(query: str) -> str:
    """Kërko LIGJE në 'BAZA E LIGJEVE' (Kodet, Rregulloret)."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_global_knowledge_base(query_text=query)
        if not results: return "BAZA E LIGJEVE: Nuk u gjetën ligje."
        return "\n\n".join([f"[BURIMI LIGJOR: {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e: return f"Gabim në aksesimin e ligjeve: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.llm = ChatOpenAI(model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, temperature=0.0, streaming=False, timeout=LLM_TIMEOUT, max_retries=2) if DEEPSEEK_API_KEY else None
        
        researcher_template = f"""
        Ti je "Juristi AI", Këshilltar Ligjor i Lartë, ekspert për juridiksionin e KOSOVËS.
        {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}
        MJETET E TUA: {{tools}}
        SHEMBULL I PROCESIT TË MENDIMIT:
        Question: A është e vlefshme kontrata?
        Thought: Më duhet teksti i kontratës nga 'Baza e Lëndës' dhe ligji për kontratat nga 'Baza e Ligjeve'.
        Action: query_case_knowledge_base
        Action Input: "teksti i kontratës"
        Observation: [BURIMI I FAKTIT: Kontrata.pdf, Faqja: 2] ...
        Thought: Tani më duhet ligji.
        Action: query_global_knowledge_base
        Action Input: "vlefshmëria e kontratave Ligji i Detyrimeve Kosovë"
        Observation: [BURIMI LIGJOR: Ligji Nr. 04/L-077...]
        Thought: Kam faktet dhe ligjin. Tani formuloj përgjigjen duke i cituar saktë.
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

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [ CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), query_global_knowledge_base_tool ]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""PYETJA: "{query}"\nJURIDIKSIONI I KËRKUAR: {jurisdiction.upper()}\nKONTEKSTI: {case_summary}"""
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return f"Ndjesë, ndodhi një gabim i papritur."

    # PHOENIX V32.1: STRUCTURED CREATIVITY UPGRADE
    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            # Use the full instruction for better context retrieval
            full_context_query = f"{instruction}\n{case_summary}"
            
            p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=full_context_query, n_results=15, case_context_id=case_id)
            facts = "\n".join([f"- {r.get('text', '')} (Burimi: {r.get('source', '')}, fq. {r.get('page', 'N/A')})" for r in p_docs]) if p_docs else "S'ka fakte specifike në dispozicion."
            
            l_docs = vector_store_service.query_global_knowledge_base(full_context_query, n_results=7, jurisdiction='ks')
            laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "S'ka ligje specifike në dispozicion."

            drafting_prompt = f"""
            Ti je "Mjeshtër i Litigimit", një avokat elitar i specializuar në hartimin e dokumenteve ligjore bindëse dhe strategjike për sistemin gjyqësor të KOSOVËS.
            
            {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}

            **URDHËR I STRUKTURËS (Blueprint Mandate):**
            Udhëzimi nga përdoruesi përmban një `STRUKTURA E KËRKUAR`. Kjo është një plan arkitektonik i padiskutueshëm. Ti DUHET ta ndjekësh këtë strukturë me përpikmëri, duke përdorur titujt dhe renditjen e dhënë. Kreativiteti yt duhet të shprehet *brenda* kësaj strukture, jo duke e ndryshuar atë.

            **URDHËR I ARGUMENTIMIT (Sinteza Ligjore):**
            Mos thjesht listo faktet dhe ligjet. Detyra jote kryesore është t'i lidhësh ato në mënyrë logjike për të ndërtuar një argument të fuqishëm dhe bindës.

            --- MATERIALET E DISPONUESHME ---
            [BAZA E LËNDËS - FAKTET KRYESORE]: 
            {facts}
            
            [BAZA E LIGJEVE - LIGJET RELEVANTE]: 
            {laws}
            
            [PËRMBLEDHJE E RASTIT]: {case_summary}
            ---
            
            [UDHËZIMI SPECIFIK NGA PËRDORUESI]: 
            {instruction}
            ---
            
            DETYRA JOTE:
            1.  **NDIQ STRUKTURËN:** Zbato me përpikmëri `STRUKTURA E KËRKUAR` nga udhëzimi i përdoruesit.
            2.  **NDËRTO ARGUMENTE BINDËSE:** Brenda çdo seksioni të strukturës, zbato "URDHËRIN E ARGUMENTIMIT" për të krijuar një rrjedhë logjike.
            3.  **PËRDOR TONIN E DUHUR:** Përshtat tonin e gjuhës me `LLOJI I DOKUMENTIT` (p.sh., ton assertiv për Padi, ton kundërshtues për Përgjigje në Padi).
            4.  **OPTMIIZO KËRKESËN:** Formulo pjesën përfundimtare (Petitum-in/Kërkesën) në mënyrë të qartë dhe strategjike.
            5.  **Cito me Përpikmëri:** Zbato PROTOKOLLIN E CITIMIT për çdo fakt dhe ligj që përdor.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"