# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V39.0 (UNIFIED PROFESSIONAL TEXT)
# 1. UX FIX: Removed broken Markdown links from Chat. Switched to **Bold** text citations.
# 2. STANDARDIZATION: Both Chat and Drafting now use the same clean, print-ready citation format.
# 3. LOGIC: Retains "Ghostwriter" mode for drafting and "Advisor" mode for chat.

import os
import asyncio
import logging
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

# --- PHOENIX VISUAL STANDARD (NO LINKS) ---
PROTOKOLLI_VIZUAL = """
URDHËRA PËR STILIN DHE CITIMIN:
1.  **PA LINQE:** Mos përdor asnjë format URL. Përdor vetëm tekst.
2.  **THEKSIM VIZUAL:** Përdor **BOLD** për të theksuar emrat e dokumenteve, ligjeve, dhe numrat e faqeve.
3.  **CITIMI I FAKTEVE:** 
    *   Formati: "...kjo vërtetohet nga **[Emri i Dokumentit] (faqe X)**."
4.  **CITIMI I LIGJEVE:**
    *   Formati: "...sipas **Nenit X të Ligjit për [Emri]**."
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
            
            # Format cleanly for the AI to read
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
        # Env Injection for Pydantic V2 compatibility
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
        
        # CHAT PROMPT (ADVISOR MODE)
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

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            # 1. Facts
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
            
            # 2. Laws
            law_keywords = "procedura civile shpenzimet familja detyrimet"
            l_docs = vector_store_service.query_global_knowledge_base(f"{instruction} {law_keywords}", jurisdiction='ks')
            laws = "\n".join([f"LIGJI: {d.get('text', '')}" for d in l_docs]) if l_docs else "S'ka ligje specifike."

            # DRAFTING PROMPT (GHOSTWRITER MODE)
            drafting_prompt = f"""
            Ti je "Mjeshtër i Litigimit" (Ghostwriter), avokat elitar në Kosovë.
            {PROTOKOLLI_VIZUAL}

            **URDHËR: MODALI GHOSTWRITER (STRIKT):**
            1. Prodho VETËM tekstin e dokumentit final.
            2. MOS shto asnjë koment shtesë ("Ja drafti...", "Analiza...").
            3. Dokumenti duhet të jetë gati për nënshkrim.

            **URDHËR PËR KUNDËRSHTIM:**
            Përdor termat "I pabazuar", "I paligjshëm", "Nuk provohet".
            
            --- MATERIALET ---
            [FAKTET]: 
            {facts}
            
            [LIGJET]: 
            {laws}
            
            [UDHËZIMI]: 
            {instruction}
            ---
            
            DETYRA: Harto dokumentin final TANI.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"