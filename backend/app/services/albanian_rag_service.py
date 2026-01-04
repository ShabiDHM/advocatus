# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V30.2 (GENERALIZED PROCESS)
# 1. FIX: Removed the hardcoded, specific "alimentacioni" example from the prompt.
# 2. PROMPT: Replaced it with a generalized, abstract example of the correct thought process.
# 3. STATUS: Robust and adaptable to any user query.

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

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT:
1. DY MENDJET: BAZA E LIGJEVE (LIGJI) dhe BAZA E LËNDËS (FAKTET).
2. NDAJE TË RREPTË: Mos shpik fakte. Mos shpik ligje.
3. JURIDIKSIONI: Përgjigju VETËM sipas ligjeve të REPUBLIKËS SË KOSOVËS.
4. PËRGJEGJËSIA E PARSIMIT: Ti je përgjegjës për të nxjerrë (parse) emrin, numrin dhe nenin e ligjit nga teksti që merr nga mjetet.
"""

VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I CITIMIT PROFESIONAL (DETYRUESHËM):
1. CITIMI I FAKTIT: Çdo fakt nga 'Baza e Lëndës' DUHET të citohet me faqe. Shembull: "...siç shihet në kontratë (Burimi: Kontrata e Shitjes, fq. 2)."
2. CITIMI I LIGJIT: Çdo ligj nga 'Baza e Ligjeve' DUHET të citohet me formatin e plotë Markdown. Shembull: "...në përputhje me [**Ligji për Procedurën Civile Nr. 04/L-172, Neni 450**](doc://LigjiProceduraCivile.pdf)."
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
        
        # PHOENIX FIX: Replaced specific example with a generalized process.
        researcher_template = f"""
        Ti je "Juristi AI", ekspert ligjor për juridiksionin e KOSOVËS. Detyra jote është të përgjigjesh pyetjeve duke përdorur mjetet e tua për të gjetur fakte dhe ligje.
        
        {STRICT_FORENSIC_RULES}
        {VISUAL_STYLE_PROTOCOL}

        MJETET E TUA:
        {{tools}}
        
        PROCESI I MENDIMIT (NDIQE KËTË PROCES PËR ÇDO PYETJE):

        Question: [Pyetja e përdoruesit]
        Thought: Së pari, më duhet të kuptoj çfarë informacioni kërkohet. A janë fakte specifike të rastit, apo informacione të përgjithshme ligjore? Bazuar në këtë, unë do të zgjedh mjetin e duhur. Nëse më duhen fakte, do të përdor `query_case_knowledge_base`. Nëse më duhet ligji, do të përdor `query_global_knowledge_base`.
        Action: [Emri i mjetit të zgjedhur]
        Action Input: [Termi i kërkimit për mjetin]
        Observation: [Rezultati i kthyer nga mjeti, p.sh. një fragment teksti nga një dokument ose ligj]
        Thought: Tani që kam informacionin nga mjeti, do ta analizoj atë dhe do ta formuloj një përgjigje përfundimtare. Unë DUHET të ndjek `PROTOKOLLIN E CITIMIT PROFESIONAL` në përgjigjen time.
        Final Answer: [Përgjigjja e plotë dhe e cituar për përdoruesin]

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
            facts = "\n".join([f"({r.get('source', '')}, fq. {r.get('page', 'N/A')}) {r.get('text', '')}" for r in p_docs]) if p_docs else "S'ka fakte specifike."
            
            l_docs = vector_store_service.query_global_knowledge_base(instruction[:300], jurisdiction='ks')
            laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "S'ka ligje specifike."

            drafting_prompt = f"""
            Ti je Avokat Kryesor, ekspert i ligjeve të KOSOVËS. Harto një dokument zyrtar.
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            ---
            BAZA E LËNDËS (FAKTET): {facts}
            ---
            BAZA E LIGJEVE (LIGJI I KOSOVËS): {laws}
            ---
            RASTI: {case_summary}
            UDHËZIMI: {instruction}
            ---
            DETYRA: Harto draftin e plotë duke cituar faktet dhe ligjet saktësisht.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"