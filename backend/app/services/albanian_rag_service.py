# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V28.0 (IRONCLAD)
# 1. PROMPT: Rewrote the ReAct prompt to be brutally simple and strict to fix model compliance issues.
# 2. SAFETY: Ensured 'handle_parsing_errors=True' is active to allow the agent to self-correct.
# 3. STATUS: Final Production Candidate.

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

MAX_ITERATIONS = int(os.environ.get("RAG_MAX_ITERATIONS", "10"))
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "90"))  

logger.info(f"RAG Configuration: max_iterations={MAX_ITERATIONS}")

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT:
1. DY MENDJET: BAZA E LIGJEVE (LIGJI) dhe BAZA E LËNDËS (FAKTET).
2. NDAJE TË RREPTË: Mos shpik fakte. Mos shpik ligje.
3. CITIM I DETYRUESHËM: Çdo fakt duhet të ketë burimin.
"""

VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT:
1. LIGJI (Blue Text): [**Emri i Ligjit, Neni X**](doc://...)
2. PROVA (Yellow Badge): [**PROVA: Përshkrimi**](doc://...)
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
            return "\n\n".join([f"[BURIMI I FAKTIT: {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])
        except Exception as e:
            return f"Gabim në aksesimin e Bazës së Lëndës: {e}"

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
    except Exception as e:
        return f"Gabim në aksesimin e ligjeve: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, temperature=0.0, streaming=False, timeout=LLM_TIMEOUT, max_retries=2)
        else:
            self.llm = None
        
        # PROMPT FIX: Ironclad, brutally simple instructions to prevent model deviation.
        researcher_template = f"""
        Ti je "Juristi AI". Përdor mjetet për të gjetur faktet dhe ligjet.
        
        {STRICT_FORENSIC_RULES}

        MJETET:
        {{tools}}
        
        PËRDOR KËTË FORMAT TË SAKTË:

        Question: Pyetja që duhet t'i përgjigjesh
        Thought: Mendimi im hap pas hapi.
        Action: Një nga [{{tool_names}}]
        Action Input: Kërkimi im për mjetin.
        Observation: Rezultati i mjetit (kjo do të plotësohet automatikisht)
        Thought: Tani kam informacionin e nevojshëm.
        Final Answer: Përgjigja përfundimtare për përdoruesin.

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
        return AgentExecutor(
            agent=agent, 
            tools=session_tools, 
            verbose=True, 
            handle_parsing_errors=True, # SAFETY NET: Agent tries to fix its own mistakes.
            max_iterations=MAX_ITERATIONS, 
            return_intermediate_steps=False
        )

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [ CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), query_global_knowledge_base_tool ]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""PYETJA: "{query}"\nKONTEKSTI: {case_summary}"""
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return f"Ndjesë, ndodhi një gabim i papritur në procesimin e kërkesës."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            try:
                p_docs = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=instruction[:300], case_context_id=case_id)
                facts = "\n".join([d.get('text', '') for d in p_docs]) if p_docs else "S'ka fakte specifike."
            except Exception as e:
                facts = "Gabim në marrjen e fakteve."
            
            try:
                l_docs = vector_store_service.query_global_knowledge_base(instruction[:300])
                laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "S'ka ligje specifike."
            except Exception as e:
                laws = "Gabim në marrjen e ligjeve."

            drafting_prompt = f"""
            Ti je Avokat Kryesor. Harto një dokument zyrtar.
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            ---
            BAZA E LËNDËS (FAKTET): {facts}
            ---
            BAZA E LIGJEVE (LIGJI): {laws}
            ---
            RASTI: {case_summary}
            UDHËZIMI: {instruction}
            ---
            DETYRA: Harto draftin e plotë.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            return f"Gabim draftimi: {str(e)[:200]}"