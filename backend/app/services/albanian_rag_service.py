# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V23.0 (DUAL STREAM LAW + FACT)
# 1. UPGRADE: 'generate_legal_draft' now queries BOTH Private Diary (Facts) AND Public Library (Laws).
# 2. PROMPT: Enforced "Beautiful Citations" - requiring specific Articles (Neni X) for every argument.
# 3. FIX: Resolved Pylance argument mismatches.

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
1. CITIM I KOMBINUAR: Çdo argument duhet të mbështetet në FAKT (nga dosja) dhe në LIGJ (nga biblioteka publike).
   - Shembull: "Sipas Nenit 134 të LPF, kontakti me fëmijën është e drejtë (Ligji), gjë që vërtetohet nga SMS-të (Fakti)..."
2. SAKTËSIA LIGJORE: Përmend ligjet specifike (Ligji për Familjen, LPK, Kushtetuta).
3. GJUHA: Shqipe Standarde Juridike, ton formal dhe bindës.
4. ZERO HALUCINACIONE: Mos shpik nene ligjore që nuk ekzistojnë në kontekst.
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
        DUAL-STREAM DRAFTING ENGINE:
        1. Retrieves FACTS from Private Diary.
        2. Retrieves LAWS from Public Library.
        3. Synthesizes them into a high-level legal document.
        """
        if not self.llm: return "System Error: No AI Model."

        case_summary = await self._get_case_summary(case_id)
        from . import vector_store_service
        
        # STREAM 1: FACT RETRIEVAL (The "What Happened")
        private_docs = vector_store_service.query_private_diary(
            user_id=user_id, 
            query_text=instruction[:300], 
            case_context_id=case_id
        )
        facts_text = "\n\n".join([f"PROVË (Doc): {d.get('text', '')}" for d in private_docs]) if private_docs else "Nuk u gjetën dokumente specifike në dosje."

        # STREAM 2: LAW RETRIEVAL (The "Legal Basis")
        # We query the public library using keywords from the instruction (e.g., "Alimentacion", "Padi", "Zgjidhje martese")
        public_docs = vector_store_service.query_public_library(query_text=instruction[:300])
        laws_text = "\n\n".join([f"LIGJI (Neni/Kodi): {d.get('text', '')}" for d in public_docs]) if public_docs else "Nuk u gjetën ligje specifike."

        # THE SYNTHESIS PROMPT
        drafting_prompt = f"""
        Ti je Avokat i Lartë dhe Ekspert i Hartimit Ligjor.
        
        {STRICT_FORENSIC_RULES}
        
        --- BURIMET E INFORMACIONIT ---
        
        [A] FAKTET E RASTIT (Nga Dosja e Klientit):
        {facts_text}
        
        [B] BAZA LIGJORE (Nga Biblioteka Publike - Ligjet e Kosovës):
        {laws_text}
        
        [C] INFO E LËNDËS:
        {case_summary}
        
        ---
        
        UDHËZIMI I DRAFTIMIT:
        {instruction}
        
        DETYRA KRYESORE:
        Harto një dokument juridik të nivelit të lartë.
        
        KRITERET E "BUKURISË JURIDIKE":
        1. CITIME LIGJORE: Çdo paragraf argumentues MË SË PAKU një referencë ligjore (psh. "Konform nenit 34, paragrafi 2 të LPF...").
        2. KORRELACIONI: Lidh faktin me ligjin. (psh. "Fakti që babai pagoi faturat (Shih Provën 1) përmbush obligimin sipas Nenit X...").
        3. STRUKTURA: Tituj të qartë, gjuhë profesionale, pa gabime drejtshkrimore.
        4. FINALIZIMI: Përfundo me Petitiumin (Kërkesën) e qartë dhe nënshkrimin.
        
        FILLIMI I DOKUMENTIT:
        """
        
        try:
            response = await self.llm.ainvoke(drafting_prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"Draft Gen Error: {e}")
            return "Dështoi gjenerimi i draftit ligjor."