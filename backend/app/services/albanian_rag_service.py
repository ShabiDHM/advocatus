# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V22.2 (FULL RESTORATION)
# 1. FIX: Completed the truncated file from previous step.
# 2. FIX: Resolved Pylance error in 'generate_legal_draft' using keyword arguments.
# 3. STATUS: Fully parsable, restoring 'chat' and 'generate_legal_draft' methods.

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

# --- THE FORENSIC CONSTITUTION (Imported Logic) ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):
1. ZERO HALUCINACIONE: Nëse fakti nuk ekziston në kontekst, shkruaj "NUK KA TË DHËNA". Mos hamendëso.
2. CITIM I DETYRUESHËM: Çdo pretendim faktik duhet të ketë referencën nga dokumentet e gjetura.
3. GJUHA: Përdor Shqipe Standarde (e, ë, ç).
4. KONTEKSTI: Përdor vetëm informacionin nga 'Observation' ose 'Case Context'.
"""

# --- Custom Tool Class for Private Diary ---
class PrivateDiaryTool(BaseTool):
    name: str = "query_private_diary"
    description: str = (
        "Access the user's 'Private Diary' & uploaded documents. "
        "Use this FIRST to find specific details about the user's business, past cases, or documents."
    )
    user_id: str
    case_id: Optional[str]
    document_ids: Optional[List[str]] = None

    def _run(self, query: str) -> str:
        # Lazy import to avoid circular dependency
        from . import vector_store_service
        
        # We use explicit keyword arguments to avoid positional mismatches
        # Assuming signature: query_private_diary(user_id, query_text, n_results, case_context_id)
        results = vector_store_service.query_private_diary(
            user_id=self.user_id, 
            query_text=query, 
            case_context_id=self.case_id
        )
        if not results:
            return "No private records found matching the query."
        
        # PHOENIX FIX: Use 'text' key explicitly
        return "\n\n".join([f"[BURIMI: {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])

    async def _arun(self, query: str) -> str:
        return await asyncio.to_thread(self._run, query)
        
    class ArgsSchema(BaseModel):
        query: str = Field(description="The question to search for in the user's private documents.")

# --- Public Library Tool (Stateless) ---
class PublicLibraryInput(BaseModel):
    query: str = Field(description="The topic to search for in the public laws and business regulations.")

@tool("query_public_library", args_schema=PublicLibraryInput)
def query_public_library_tool(query: str) -> str:
    """
    Access the 'Public Library' (Official Laws & Business Regulations).
    Use this to verify compliance, finding labor laws, tax codes, or official procedures.
    """
    from . import vector_store_service
    results = vector_store_service.query_public_library(query_text=query)
    if not results:
        return "No public records found."
    return "\n\n".join([f"[LIGJI/BURIMI: {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            # We enforce the API key into OpenAI client env for LangChain compatibility
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL, 
                base_url=OPENROUTER_BASE_URL, 
                temperature=0.0, # Zero temp for strictness
                streaming=False
            )
        else:
            self.llm = None
        
        # PHOENIX UPGRADE: Enhanced Researcher Prompt with Constitution
        researcher_template = f"""
        Ti je "Juristi AI", një asistent ligjor i saktë dhe profesional.
        
        {STRICT_FORENSIC_RULES}

        TI KE AKSES NË KËTO MJETE (TOOLS):
        {{tools}}

        PROCEDURA E MENDIMIT (ReAct):
        Question: Pyetja e përdoruesit
        Thought: Çfarë duhet të kërkoj? (Planifiko kërkimin)
        Action: Zgjidh mjetin [{{tool_names}}]
        Action Input: Parametri i kërkimit
        Observation: Rezultati nga mjeti
        ... (Përsërit nëse duhet më shumë info)
        Thought: Tani kam informacionin e duhur.
        Final Answer: Përgjigja përfundimtare në Shqipe Standarde.

        Fillo!
        Question: {{input}}
        Thought: {{agent_scratchpad}}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: return ""
            # Handle string vs ObjectId safely
            try:
                oid = ObjectId(case_id)
            except:
                return ""
                
            case = await self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1, "summary": 1, "title": 1})
            if not case: return ""
            parts = [
                f"EMRI I PROJEKTIT: {case.get('title') or case.get('case_name')}", 
                f"PËRSHKRIMI: {case.get('description')}", 
                f"PËRMBLEDHJA: {case.get('summary')}"
            ]
            return "\n".join(filter(None, parts))
        except Exception as e:
            logger.warning(f"Failed to fetch case summary: {e}")
            return ""

    async def chat(
        self, 
        query: str, 
        user_id: str, 
        case_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        jurisdiction: str = 'ks'
    ) -> str:
        """
        Main Chat Handler. Uses ReAct Agent to search and answer.
        """
        if not self.llm:
            return "Sistemi AI nuk është konfiguruar (Mungon API Key)."

        # Initialize Tools with Context
        private_tool_instance = PrivateDiaryTool(user_id=user_id, case_id=case_id, document_ids=document_ids)
        session_tools = [private_tool_instance, query_public_library_tool]

        researcher_agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        researcher_executor = AgentExecutor(
            agent=researcher_agent, 
            tools=session_tools, 
            verbose=True, 
            handle_parsing_errors=True,
            max_iterations=5 # Prevent infinite loops
        )

        case_summary = await self._get_case_summary(case_id)
        doc_context = f" (Fokusohu tek dokumentet ID: {document_ids})" if document_ids else ""
        
        enriched_input = (
            f"Pyetja: \"{query}\"\n"
            f"Juridiksioni: {jurisdiction}\n"
            f"Konteksti i Çështjes:\n{case_summary}{doc_context}"
        )
        
        try:
            # Single Pass Execution
            response = await researcher_executor.ainvoke({"input": enriched_input})
            return response.get('output', "Nuk u gjenerua përgjigje.")

        except Exception as e:
            logger.error(f"Agent Chat Error: {e}", exc_info=True)
            return "Ndodhi një gabim gjatë procesimit të kërkesës nga agjenti."

    async def generate_legal_draft(
        self,
        instruction: str,
        user_id: str,
        case_id: Optional[str]
    ) -> str:
        """
        DIRECT GENERATION MODE (No Agents).
        Used for Drafting to prevent ReAct loops and ensure strict adherence to templates.
        """
        if not self.llm: return "System Error: No AI Model."

        case_summary = await self._get_case_summary(case_id)
        
        # Fetch relevant context FIRST (Manual RAG step)
        # We query the diary strictly to get facts for the draft
        from . import vector_store_service
        
        # PHOENIX FIX: Strict keyword arguments to satisfy Pylance
        context_docs = vector_store_service.query_private_diary(
            user_id=user_id, 
            query_text=instruction[:200], 
            case_context_id=case_id
        )
        
        context_text = "\n\n".join([d.get('text', '') for d in context_docs]) if context_docs else "Nuk ka dokumente shtesë."

        drafting_prompt = f"""
        Ti je një Avokat Ekspert në hartimin e dokumenteve ligjore.
        
        {STRICT_FORENSIC_RULES}
        
        KONTEKSTI NGA DOSJA (FAKTET):
        {context_text}
        
        INFORMACIONI I LËNDËS:
        {case_summary}
        
        ---
        
        UDHËZIMI PËR DRAFTIM:
        {instruction}
        
        DETYRA:
        Harto dokumentin e plotë. Mos përdor placeholders si [VENDOS KËTU] nëse informacioni ekziston në kontekst.
        Nëse informacioni mungon, lëre bosh me [MUNGON].
        
        FILLIMI I DOKUMENTIT:
        """
        
        try:
            response = await self.llm.ainvoke(drafting_prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"Draft Generation Error: {e}")
            return "Dështoi gjenerimi i draftit."