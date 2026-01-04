# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V31.0 (PROFESSIONAL FINESSE)
# 1. PROMPT: Introduced a unified "PROTOKOLLI I EKSPERTIZËS LIGJORE" for clarity.
# 2. PROMPT: Implemented a high-quality, concrete few-shot example to teach professional citation and structure.
# 3. DRAFTING: Enhanced the drafting prompt to better utilize retrieved context.

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
LLM_TIMEOUT = 90

# --- PHOENIX V31.0: UNIFIED PROTOCOL OF LEGAL EXPERTISE ---
PROTOKOLLI_I_EKSPERTIZES_LIGJORE = """
URDHËRA TË PADISKUTUESHËM:

1.  **DY MENDJET (DUAL BRAIN):**
    *   **BAZA E LIGJEVE (LIGJI):** Burimi yt i vetëm për informacion ligjor.
    *   **BAZA E LËNDËS (FAKTET):** Burimi yt i vetëm për faktet specifike të rastit.
    *   **RREGULL I RREPTË:** Mos shpik fakte. Mos shpik ligje.

2.  **JURIDIKSIONI I KOSOVËS:**
    *   Të gjitha përgjigjet dhe analizat duhet të jenë STRICTLY të bazuara në ligjet dhe praktikën e **REPUBLIKËS SË KOSOVËS**. Asnjëherë mos përmend Shqipërinë apo shtete tjera.

3.  **CITIMI PROFESIONAL (DETYRUESHËM):**
    *   **CITIMI I FAKTIT:** Çdo fakt nga 'Baza e Lëndës' DUHET të citohet me emrin e dokumentit dhe faqen.
        *   **Formati:** `(Burimi: [Emri i Dokumentit], fq. [numri])`.
    *   **CITIMI I LIGJIT:** Çdo ligj nga 'Baza e Ligjeve' DUHET të citohet me formatin e plotë Markdown, duke përfshirë emrin, numrin dhe nenin.
        *   **Formati:** `[**Emri i Ligjit Nr. XX/L-XXX, Neni YY**](doc://...).`
    *   **PËRGJEGJËSIA E PARSIMIT:** Ti je përgjegjës për të nxjerrë (parse) këto detaje nga teksti që merr prej mjeteve.
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
            if not results: return "BAZA E LËNDËS: Nuk u gjetën të dhëna."
            return "\n\n".join([f"[BURIMI I FAKTIT: {r.get('source', 'Unknown')}, Faqja: {r.get('page', 'N/A')}]\n{r.get('text', '')}" for r in results])
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
        if not results: return "BAZA E LIGJEVE: Nuk u gjetën ligje."
        return "\n\n".join([f"[BURIMI LIGJOR: {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e:
        return f"Gabim në aksesimin e ligjeve: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.llm = ChatOpenAI(model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, temperature=0.0, streaming=False, timeout=LLM_TIMEOUT, max_retries=2) if DEEPSEEK_API_KEY else None
        
        # PHOENIX V31.0: High-quality few-shot example
        researcher_template = f"""
        Ti je "Juristi AI", Këshilltar Ligjor i Lartë, ekspert për juridiksionin e KOSOVËS.
        
        {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}

        MJETET E TUA:
        {{tools}}
        
        SHEMBULL I PROCESIT TË MENDIMIT DHE PËRGJIGJES PERFEKTE:

        Question: A është e vlefshme kontrata dhe cilat janë obligimet e palëve?
        Thought: Më duhen dy gjëra: 1) Teksti i kontratës nga 'Baza e Lëndës' dhe 2) Ligji relevant për kontratat nga 'Baza e Ligjeve'. Fillimisht, do të kërkoj kontratën.
        Action: query_case_knowledge_base
        Action Input: "teksti i plotë i kontratës së shitjes"
        Observation: [BURIMI I FAKTIT: Kontrata e Shitjes.pdf, Faqja: 2] ...blerësi obligohet të paguajë shumën prej 5000€ brenda 30 ditësh...
        Thought: E gjeta faktin kyç dhe faqen. Tani më duhet ligji për vlefshmërinë e kontratave.
        Action: query_global_knowledge_base
        Action Input: "vlefshmëria e kontratave sipas Ligjit të Detyrimeve në Kosovë"
        Observation: [BURIMI LIGJOR: LMD KOSOVE] Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve, Neni 17, thekson se kontrata është e vlefshme kur palët kanë rënë dakord për elementet thelbësore.
        Thought: Tani kam të gjitha elementet: faktin e cituar dhe ligjin e cituar. Do të ndërtoj përgjigjen time përfundimtare duke i kombinuar ato në mënyrë profesionale dhe duke ndjekur rreptësisht protokollin e citimit.
        Final Answer: 
        Në bazë të analizës së dokumentacionit, kontrata duket të jetë e vlefshme dhe krijon obligime të qarta për palët.

        **1. Analiza e Vlefshmërisë:**
        Kontrata konsiderohet e vlefshme pasi palët kanë arritur marrëveshje për elementet thelbësore, në përputhje me [**Ligji për Marrëdhëniet e Detyrimeve Nr. 04/L-077, Neni 17**](doc://LMD.pdf).

        **2. Obligimet Kryesore:**
        Obligimi kryesor i blerësit është pagesa e çmimit. Specifikisht, blerësi duhet të paguajë shumën prej 5000€ brenda 30 ditësh (Burimi: Kontrata e Shitjes.pdf, fq. 2).

        **Konkluzioni:**
        Kontrata është ligjërisht e detyrueshme dhe obligimet e përcaktuara në të duhet të përmbushen.

        ---
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

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction[:300], case_context_id=case_id)
            facts = "\n".join([f"- {r.get('text', '')} (Burimi: {r.get('source', '')}, fq. {r.get('page', 'N/A')})" for r in p_docs]) if p_docs else "S'ka fakte specifike."
            
            l_docs = vector_store_service.query_global_knowledge_base(instruction[:300], jurisdiction='ks')
            laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "S'ka ligje specifike."

            drafting_prompt = f"""
            Ti je Avokat Kryesor, ekspert i ligjeve të KOSOVËS. Harto një dokument zyrtar profesional.
            
            {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}
            
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
            
            DETYRA: Harto draftin e plotë dhe profesional. Përdor materialet e mësipërme për të ndërtuar argumentet. Çdo fakt dhe ligj që përdor DUHET të citohet saktësisht sipas protokollit.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"