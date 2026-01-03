# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V25.5 (DEDUPLICATION)
# 1. FIX: Removed all duplicated class and function declarations.
# 2. STATUS: Clean, final version ready for execution.

import os
import asyncio
import logging
from typing import List, Optional, Any, Dict
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
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))  

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):
1. HIERARKIA E BURIMEVE: Global KB = LIGJI. Case KB = FAKTET. Mos shpik fakte. Mos shpik ligje.
2. PROTOKOLLI I THJESHTËSIMIT (CHAT ONLY): Në Chat: Shpjego ligjet thjesht. Në Draftim: Përdor gjuhë profesionale.
3. CITIM I DETYRUESHËM: Çdo ligj ose provë duhet të ketë linkun Markdown specifik.
"""
VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM):
1. **FORMATI I LIGJIT (Blue Text)**: [**{{Emri}} {{Nr.}}, {{Neni X}}**](doc://{{Burimi}})
2. **FORMATI I PROVAVE (Yellow Badge)**: [**PROVA: {{Përshkrimi}}**](doc://{{Dosja}})
3. **STRUKTURA**: Përdor tituj: **BAZA LIGJORE**, **FAKTET**.
"""

# --- Tools ---
class PrivateDiaryTool(BaseTool):
    name: str = "query_private_diary"
    description: str = "CASE KNOWLEDGE BASE (FAKTET). Përdore këtë mjet për të kërkuar fakte, dëshmi, data, ose informacione specifike nga dokumentet e rastit."
    user_id: str
    case_id: Optional[str]

    def _run(self, query: str) -> str:
        from . import vector_store_service
        try:
            results = vector_store_service.query_private_diary(user_id=self.user_id, query_text=query, case_context_id=self.case_id)
            if not results: return "Nuk u gjetën të dhëna në dokumentet e rastit për këtë pyetje."
            return "\n\n".join([f"[BURIMI (FAKT): {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])
        except Exception as e: return f"Gabim në kërkimin e fakteve: {e}"
    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Pyetja specifike për faktet e rastit.")

@tool("query_public_library")
def query_public_library_tool(query: str) -> str:
    """GLOBAL KNOWLEDGE BASE (LIGJI). Përdore këtë mjet për të kërkuar ligje, nene, rregullore, ose koncepte juridike."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_public_library(query_text=query)
        if not results: return "Nuk u gjet asnjë ligj ose nen relevant për këtë pyetje."
        return "\n\n".join([f"[BURIMI (LIGJ): {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e: return f"Gabim në kërkimin e ligjeve: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.llm = None
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, temperature=0.0, streaming=False, timeout=LLM_TIMEOUT)
        
        researcher_template = f"""
        Ti je "Juristi AI", këshilltar ligjor strategjik dhe i saktë.
        
        {STRICT_FORENSIC_RULES}
        {VISUAL_STYLE_PROTOCOL}

        MJETET E DISPONUESHME:
        {{tools}}
        
        PROTOKOLLI I MENDIMIT (DUAL BRAIN):
        1. ANALIZO PYETJEN: A është pyetje për LIGJIN (psh. "çfarë thotë neni X?") apo për FAKTET e rastit (psh. "kur u nënshkrua kontrata?")?
        2. ZGJIDH MJETIN E DUHUR:
           - Për pyetje për LIGJIN, përdor **query_public_library**.
           - Për pyetje për FAKTET, përdor **query_private_diary**.
        3. PËRGJIGJU: Kombino informacionin nga mjetet për të dhënë një përgjigje të plotë.
        
        FORMATI REACT (DETYRUESHËM):
        Question: {{input}}
        Thought: Mendimi im hap pas hapi se çfarë duhet të bëj.
        Action: Një nga [{{tool_names}}]
        Action Input: Inputi për veprimin
        Observation: Rezultati i veprimit
        ... (Vazhdo derisa të kesh përgjigjen)
        Thought: Tani e di përgjigjen përfundimtare.
        Final Answer: Përgjigja përfundimtare për klientin, e formatuar sipas protokollit vizual.
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: return ""
            oid = ObjectId(case_id)
            case = await self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1})
            return f"RASTI AKTUAL: {case.get('case_name', '')}. Përshkrimi: {case.get('description', '')}" if case else ""
        except: return ""
    
    def _create_agent_executor(self, session_tools: List) -> AgentExecutor:
        if not self.llm: raise ValueError("LLM not initialized")
        agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        return AgentExecutor(agent=agent, tools=session_tools, verbose=True, handle_parsing_errors=True, max_iterations=MAX_ITERATIONS)

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, **kwargs) -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [PrivateDiaryTool(user_id=user_id, case_id=case_id), query_public_library_tool]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            
            legal_keywords = ['ligji', 'neni', 'procedura', 'kodi', 'padi', 'ankes', 'aktgjykim', 'kushtetuta']
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in legal_keywords):
                hint = "HINT: Kjo pyetje duket se ka të bëjë me LIGJIN. Përdor mjetin e duhur."
            else:
                hint = "HINT: Kjo pyetje duket se ka të bëjë me FAKTET e rastit. Përdor mjetin e duhur."

            input_text = f"""
            {hint}
            PYETJA ORIGJINALE: "{query}"
            KONTEKSTI I RASTIT: {case_summary}
            """
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk arrita të gjeneroj një përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return f"Gabim teknik në agjentin AI: {str(e)[:100]}"
    
    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            try:
                p_docs = vector_store_service.query_private_diary(user_id=user_id, query_text=instruction[:300], case_context_id=case_id)
                facts = "\n".join([d.get('text', '') for d in p_docs]) if p_docs else "S'ka dokumente specifike."
            except Exception as e:
                facts = "Gabim në marrjen e fakteve."
            
            try:
                l_docs = vector_store_service.query_public_library(instruction[:300])
                laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "Referohu parimeve ligjore."
            except Exception as e:
                laws = "Gabim në marrjen e ligjeve."

            drafting_prompt = f"""
            Ti je Avokat Kryesor. Harto një DOKUMENT ZYRTAR LIGJOR.
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            --- MATERIALET ---
            [FAKTET]: {facts}
            [LIGJI]: {laws}
            [RASTI]: {case_summary}
            --- UDHËZIMI ---
            {instruction}
            --- DETYRA ---
            Harto dokumentin e plotë. Përdor gjuhë formale dhe cito saktë.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except asyncio.TimeoutError:
            return "Koha skadoi."
        except Exception as e:
            return f"Gabim draftimi: {str(e)[:200]}"