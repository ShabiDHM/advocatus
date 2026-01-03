# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V25.2 (TYPE FIX)
# 1. FIX: Corrected argument passing in 'query_private_diary' (n_results vs case_id).
# 2. STATUS: Type error resolved.

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

# --- PERFORMANCE CONFIGURATION ---
MAX_ITERATIONS = int(os.environ.get("RAG_MAX_ITERATIONS", "25"))  
MAX_EXECUTION_TIME = int(os.environ.get("RAG_MAX_EXECUTION_TIME", "300"))  
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))  
EARLY_STOPPING_METHOD = os.environ.get("RAG_EARLY_STOPPING", "force")

logger.info(f"RAG Configuration: max_iterations={MAX_ITERATIONS}, max_execution_time={MAX_EXECUTION_TIME}s")

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):

1. HIERARKIA E BURIMEVE:
   - Global KB = LIGJI. Case KB = FAKTET.
   - Mos shpik fakte. Mos shpik ligje.

2. PROTOKOLLI I THJESHTËSIMIT (CHAT ONLY):
   - Në Chat: Shpjego ligjet thjesht për klientin.
   - Në Draftim: Përdor gjuhë profesionale juridike (për Gjykatë).

3. CITIM I DETYRUESHËM: Çdo ligj ose provë duhet të ketë linkun Markdown specifik.
"""

# --- THE VISUAL STYLE PROTOCOL ---
VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM):

1. **FORMATI I LIGJIT (Blue Text / Non-Clickable)**:
   - Formati: [**{{Emri i Ligjit}} {{Nr.}}, {{Neni X}}**](doc://{{Emri_i_Burimit_PDF}})
   - Shembull: ...bazuar në [**Ligji për Familjen Nr. 04/L-032, Neni 4**](doc://ligji.pdf).

2. **FORMATI I PROVAVE (Yellow Badge / Clickable)**:
   - Formati: [**PROVA: {{Përshkrimi i Dokumentit}}**](doc://{{Emri_i_Dosjes}})
   - Shembull: ...siç shihet në [**PROVA: Raporti Mjekësor**](doc://raporti.pdf).

3. **STRUKTURA**:
   - Përdor tituj të qartë: **BAZA LIGJORE**, **FAKTET**, **KËRKESA**.
"""

# --- Custom Tool Class for Private Diary ---
class PrivateDiaryTool(BaseTool):
    name: str = "query_private_diary"
    description: str = "CASE KNOWLEDGE BASE (FACTS). Access specific documents, dates, and evidence."
    user_id: str
    case_id: Optional[str]
    document_ids: Optional[List[str]] = None

    def _run(self, query: str) -> str:
        from . import vector_store_service
        try:
            results = vector_store_service.query_private_diary(
                user_id=self.user_id, 
                query_text=query, 
                case_context_id=self.case_id
            )
            if not results: return "Nuk u gjetën të dhëna private."
            return "\n\n".join([f"[BURIMI (FACT): {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])
        except Exception as e:
            logger.error(f"PrivateDiaryTool error: {e}")
            return "Gabim në aksesimin e ditarit privat."

    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Search query for case facts.")

# --- Public Library Tool ---
class PublicLibraryInput(BaseModel): query: str = Field(description="Search query for laws.")

@tool("query_public_library", args_schema=PublicLibraryInput)
def query_public_library_tool(query: str) -> str:
    """GLOBAL KNOWLEDGE BASE (LAW). Access Official Laws & Regulations."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_public_library(query_text=query)
        if not results: return "Nuk u gjetën ligje."
        return "\n\n".join([f"[BURIMI (LAW): {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e:
        logger.error(f"PublicLibraryTool error: {e}")
        return "Gabim në aksesimin e ligjeve."

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
        
        # CHAT PROMPT (Strategic Advisor)
        researcher_template = f"""
        Ti je "Juristi AI", këshilltar ligjor strategjik.
        
        {STRICT_FORENSIC_RULES}
        {VISUAL_STYLE_PROTOCOL}

        MJETET: {{tools}}
        
        PROTOKOLLI I MENDIMIT (DUAL BRAIN):
        1. Gjej FAKTET (Private Diary).
        2. Gjej LIGJIN (Public Library).
        3. PËRGJIGJU:
           - Përdor stilin shpjegues (Plain Language) për klientin.
           - Përdor seksionin "**📌 Si ndikon kjo në rastin tuaj:**".
        
        Përdor ReAct:
        Question: {{input}}
        Thought: {{agent_scratchpad}}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: return "Nuk ka informacion specifik."
            oid = ObjectId(case_id)
            case = await self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1})
            return f"RASTI: {case.get('case_name', '')}. {case.get('description', '')}" if case else ""
        except: return ""
    
    def _create_agent_executor(self, session_tools: List) -> AgentExecutor:
        if not self.llm: raise ValueError("LLM not initialized")
        agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        return AgentExecutor(
            agent=agent, tools=session_tools, verbose=True, handle_parsing_errors=True,
            max_iterations=MAX_ITERATIONS, max_execution_time=None, return_intermediate_steps=False
        )

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [PrivateDiaryTool(user_id=user_id, case_id=case_id), query_public_library_tool]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            
            input_text = f"""
            PYETJA: "{query}"
            JURIDIKSIONI: {jurisdiction}
            KONTEKSTI: {case_summary}
            
            DETYRA: Përgjigju qartë për klientin (Strategic Advisor).
            """
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return "Gabim teknik."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            # 1. Facts from Case Brain (FIXED ARGUMENTS)
            try:
                p_docs = vector_store_service.query_private_diary(
                    user_id=user_id, 
                    query_text=instruction[:300], 
                    case_context_id=case_id # Pass case_id specifically as keyword arg
                )
                facts = "\n".join([d.get('text', '') for d in p_docs]) if p_docs else "S'ka dokumente specifike."
            except Exception as e:
                logger.warning(f"Error fetching facts: {e}")
                facts = "Gabim në marrjen e fakteve."
            
            # 2. Laws from Global Brain
            try:
                l_docs = vector_store_service.query_public_library(instruction[:300])
                laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "Referohu parimeve ligjore."
            except Exception as e:
                logger.warning(f"Error fetching laws: {e}")
                laws = "Gabim në marrjen e ligjeve."

            # 3. DRAFTING PROMPT (Senior Counsel Mode)
            drafting_prompt = f"""
            Ti je Avokat Kryesor (Senior Counsel).
            Ti po harton një DOKUMENT ZYRËTAR LIGJOR (Për Gjykatë/Institucion).
            
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            
            --- MATERIALET ---
            [FAKTET - CASE BRAIN]: 
            {facts}
            
            [LIGJI - GLOBAL BRAIN]: 
            {laws}
            
            [RASTI]: 
            {case_summary}
            
            --- UDHËZIMI ---
            {instruction}
            
            --- DETYRA ---
            Harto dokumentin e plotë.
            RËNDËSISHME:
            1. Përdor gjuhë formale juridike (JO 'Plain Language' si në chat).
            2. Përdor saktësisht formatin vizual të citimeve (Blue Text) dhe Provave (Yellow Badge).
            3. Argumento fuqishëm duke lidhur ligjin me faktin.
            """
            
            response = await asyncio.wait_for(
                self.llm.ainvoke(drafting_prompt),
                timeout=LLM_TIMEOUT
            )
            return str(response.content)
            
        except asyncio.TimeoutError:
            return f"Koha skadoi. Provoni përsëri."
        except Exception as e:
            return f"Gabim draftimi: {str(e)[:200]}"