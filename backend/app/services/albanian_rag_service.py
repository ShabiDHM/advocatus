# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V23.1 (BEAUTIFUL CITATION STYLE)
# 1. STYLE: Implemented "Embedded Citation" protocol ({{LIGJI}} vs [[PROVA]]).
# 2. LOGIC: Forces "Fact-Law-Conclusion" paragraph structure.
# 3. FIX: Ensures the Public Library is queried efficiently for legal basis.

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
1. CITIM I INTEGRUAR: Faktet dhe Ligjet duhet të jenë pjesë e fjalisë, jo lista në fund.
2. SAKTËSIA LIGJORE: Përmend ligjet specifike (Ligji për Familjen, LPK, Kushtetuta).
3. GJUHA: Shqipe Standarde Juridike, ton formal, bindës dhe elokuent.
4. ZERO HALUCINACIONE: Përdor vetëm ligjet dhe faktet e ofruara.
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
        # Explicit keyword args to prevent Pylance errors
        results = vector_store_service.query_private_diary(
            user_id=self.user_id, 
            query_text=query, 
            case_context_id=self.case_id
        )
        if not results: return "No private records found."
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
    return "\n\n".join([f"[LIGJI: {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])


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
        
        # Enhanced Researcher Prompt
        researcher_template = f"""
        Ti je "Juristi AI", një asistent ligjor elitar.
        
        {STRICT_FORENSIC_RULES}

        MJETET E DISPONUESHME:
        {{tools}}

        PROCEDURA E MENDIMIT (ReAct):
        Question: {{input}}
        Thought: Analizo kërkesën ligjore.
        Action: query_private_diary (për fakte) OSE query_public_library (për ligje)
        Observation: Rezultatet...
        Thought: Tani kombino faktet me ligjin.
        Final Answer: Përgjigja përfundimtare juridike.

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
        DUAL-STREAM DRAFTING ENGINE WITH "BEAUTIFUL CITATION" PROTOCOL.
        """
        if not self.llm: return "System Error: No AI Model."

        case_summary = await self._get_case_summary(case_id)
        from . import vector_store_service
        
        # 1. GET FACTS (Private)
        private_docs = vector_store_service.query_private_diary(
            user_id=user_id, 
            query_text=instruction[:300], 
            case_context_id=case_id
        )
        facts_text = "\n\n".join([f"DOKUMENTI: {d.get('text', '')} (Burimi: {d.get('source', '')})" for d in private_docs]) if private_docs else "Nuk u gjetën dokumente specifike."

        # 2. GET LAWS (Public)
        # Search for broader terms like "Family Law", "Custody", "Contract Law" based on instruction
        public_docs = vector_store_service.query_public_library(query_text=instruction[:300])
        laws_text = "\n\n".join([f"LIGJI: {d.get('text', '')} (Burimi: {d.get('source', '')})" for d in public_docs]) if public_docs else "Referohu parimeve të përgjithshme ligjore të Kosovës."

        # 3. THE "BEAUTIFUL CITATION" PROMPT
        drafting_prompt = f"""
        Ti je Avokat Kryesor (Senior Counsel). Stili yt është elokuent, bindës dhe tepër profesional.
        
        {STRICT_FORENSIC_RULES}
        
        --- MATERIALET E DOSJES ---
        FAKTET (Nga Klienti):
        {facts_text}
        
        LIGJET (Nga Baza Ligjore):
        {laws_text}
        
        INFO RASTI: {case_summary}
        ---
        
        UDHËZIMI I DRAFTIMIT:
        {instruction}
        
        DETYRA: Harto dokumentin e plotë juridik.
        
        PROTOKOLLI I STILIT DHE CITIMIT (SHUMË E RËNDËSISHME):
        
        1. STRUKTURA E ARGUMENTIT: Përdor metodën "IRAC" (Issue, Rule, Analysis, Conclusion) për çdo paragraf.
           - Fillo me pretendimin.
           - Mbështete me LIGJIN {{...}}.
           - Vërtetoje me FAKTIN [[...]].
        
        2. FORMATIMI VIZUAL I BURIMEVE:
           - Kur citon një FAKT, përdor kllapa katrore të dyfishta direkt në tekst.
             Shembull: "...siç vërtetohet qartë nga komunikimi me SMS [[PROVA: Mesazhet e dt. 12.02.2024]]."
           
           - Kur citon një LIGJ, përdor kllapa gjarpëruese të dyfishta direkt në tekst.
             Shembull: "...duke u bazuar në interesin më të lartë të fëmijës, siç sanksionohet në {{LIGJI: Neni 6 i LPF-së}}."

        3. TONI: Mos përdor lista (bullets) për argumentet kryesore. Shkruaj në paragrafë të plotë, rrjedhës.
        
        FILLIMI I DOKUMENTIT TANI:
        """
        
        try:
            response = await self.llm.ainvoke(drafting_prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"Draft Gen Error: {e}")
            return "Dështoi gjenerimi i draftit ligjor."