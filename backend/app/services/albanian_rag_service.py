# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V24.0 (MARKDOWN LINKS & SHADOW STYLE)
# 1. VISUAL: Switched to Markdown Links [**Text**](doc://Source) to match Frontend styling.
# 2. LOGIC: AI now maps retrieved "BURIMI" directly to "doc://" links.
# 3. STRUCTURE: Enforces specific headers (BAZA LIGJORE, VLERËSIMI I PROVAVE).

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

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT DHE HARTIMIT (STRICT LIABILITY):
1. SAKTËSIA: Mos shpik fakte.
2. BURIMET: Çdo pohim duhet të ketë një LINK drejt burimit.
3. GJUHA: Shqipe Standarde Juridike.
"""

# --- THE VISUAL STYLE PROTOCOL (MARKDOWN LINKS) ---
VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM PËR "FINAL ANSWER"):

1. **CITIMET SI LINQE (SHUMË E RËNDËSISHME)**:
   - Çdo Ligj ose Provë duhet të shkruhet si LINK MARKDOWN.
   - Formati: [**Titulli i Shkurtër**](doc://Emri_i_Burimit)
   
   Shembuj:
   - Për Ligj: ...bazuar në [**Neni 145 i LPF**](doc://Ligji_Nr_2004_32_Familja.pdf).
   - Për Provë: ...siç vërtetohet nga [**Mesazhet SMS**](doc://Deshmite_2024.pdf).

2. **STRUKTURA E PËRGJIGJES**:
   - Përdor gjithmonë këta tituj me BOLD:
     - **BAZA LIGJORE:** (Listo ligjet me bullets ose numra)
     - **VLERËSIMI I PROVAVE:** (Analizo faktet)
     - **KONKLUZIONI:** (Përfundimi)

3. **ESTETIKA**:
   - Titulli brenda linkut duhet të jetë gjithmonë me **BOLD**.
   - Përdor "doc://" para emrit të dosjes në link.
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
        from . import vector_store_service
        results = vector_store_service.query_private_diary(
            user_id=self.user_id, 
            query_text=query, 
            case_context_id=self.case_id
        )
        if not results: return "No private records found."
        # Returns source so LLM can use it in doc:// link
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
    """
    from . import vector_store_service
    results = vector_store_service.query_public_library(query_text=query)
    if not results: return "No public records found."
    return "\n\n".join([f"[BURIMI: {r.get('source', 'Ligjet_e_Kosoves')}]\n{r.get('text', '')}" for r in results])


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL, 
                base_url=OPENROUTER_BASE_URL, 
                temperature=0.0, 
                streaming=False
            )
        else:
            self.llm = None
        
        # PHOENIX UPGRADE: Enhanced Researcher Prompt with MARKDOWN LINK Protocol
        researcher_template = f"""
        Ti je "Juristi AI", një asistent ligjor elitar.
        
        {STRICT_FORENSIC_RULES}
        
        {VISUAL_STYLE_PROTOCOL}

        MJETET E DISPONUESHME:
        {{tools}}
        
        Përdor formatin e mëposhtëm (ReAct):
        Question: Pyetja e hyrjes
        Thought: Mendo çfarë të bësh (Kërko ligje dhe fakte)
        Action: Një nga [{{tool_names}}]
        Action Input: Inputi për veprimin
        Observation: Rezultati i veprimit (Këtu merr emrin e BURIMIT për linkun)
        ... (Përsërit nëse duhet)
        Thought: Tani e di përgjigjen.
        Final Answer: Përgjigja përfundimtare duke përdorur [**Titulli**](doc://Burimi) për çdo citim.

        Fillo!
        Question: {{input}}
        Thought: {{agent_scratchpad}}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: return ""
            try: oid = ObjectId(case_id)
            except: return ""  
            case = await self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1, "summary": 1})
            if not case: return ""
            return f"LËNDA: {case.get('case_name')}\nPËRSHKRIMI: {case.get('description')}\nINFO: {case.get('summary')}"
        except Exception: return ""

    async def chat(
        self, query: str, user_id: str, case_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks'
    ) -> str:
        if not self.llm: return "Sistemi AI nuk është konfiguruar."

        private_tool = PrivateDiaryTool(user_id=user_id, case_id=case_id, document_ids=document_ids)
        session_tools = [private_tool, query_public_library_tool]

        agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        executor = AgentExecutor(agent=agent, tools=session_tools, verbose=True, handle_parsing_errors=True, max_iterations=5)

        case_summary = await self._get_case_summary(case_id)
        input_text = f"Pyetja: \"{query}\"\nJuridiksioni: {jurisdiction}\nKonteksti:\n{case_summary}"
        
        try:
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', "Nuk u gjenerua përgjigje.")
        except Exception as e:
            logger.error(f"Chat Error: {e}")
            return "Gabim teknik gjatë bisedës."

    async def generate_legal_draft(
        self,
        instruction: str,
        user_id: str,
        case_id: Optional[str]
    ) -> str:
        """
        DUAL-STREAM DRAFTING ENGINE.
        """
        if not self.llm: return "System Error: No AI Model."

        case_summary = await self._get_case_summary(case_id)
        from . import vector_store_service
        
        # 1. GET FACTS
        private_docs = vector_store_service.query_private_diary(
            user_id=user_id, 
            query_text=instruction[:300], 
            case_context_id=case_id
        )
        facts_text = "\n\n".join([f"DOKUMENTI: {d.get('text', '')} (Burimi: {d.get('source', '')})" for d in private_docs]) if private_docs else "Nuk u gjetën dokumente specifike."

        # 2. GET LAWS
        public_docs = vector_store_service.query_public_library(query_text=instruction[:300])
        laws_text = "\n\n".join([f"LIGJI: {d.get('text', '')} (Burimi: {d.get('source', '')})" for d in public_docs]) if public_docs else "Referohu parimeve të përgjithshme ligjore të Kosovës."

        # 3. DRAFTING PROMPT (Updated to match Chat Style)
        drafting_prompt = f"""
        Ti je Avokat Kryesor (Senior Counsel).
        
        {STRICT_FORENSIC_RULES}
        {VISUAL_STYLE_PROTOCOL}
        
        --- MATERIALET ---
        FAKTET: {facts_text}
        LIGJET: {laws_text}
        INFO RASTI: {case_summary}
        
        UDHËZIMI: {instruction}
        
        DETYRA: Harto dokumentin e plotë.
        RREGULL I FORTË: Përdor [**Link Markdown**](doc://Burimi) për çdo citim.
        """
        
        try:
            response = await self.llm.ainvoke(drafting_prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"Draft Gen Error: {e}")
            return "Dështoi gjenerimi i draftit ligjor."