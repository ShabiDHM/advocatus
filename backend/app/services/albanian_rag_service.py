# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V24.2 (TEMPLATE ESCAPE FIX)
# 1. FIX: Escaped curly braces in VISUAL_STYLE_PROTOCOL ({{...}}) to prevent LangChain variable errors.
# 2. STATUS: Chat and Drafting will now function without crashing on the prompt template.

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
1. SAKTËSIA: Mos shpik fakte apo numra ligjesh.
2. BURIMET: Çdo pohim ligjor duhet të ketë referencën e plotë.
3. GJUHA: Shqipe Standarde Juridike.
"""

# --- THE VISUAL STYLE PROTOCOL (ESCAPED FOR PYTHON) ---
# NOTE: We use double curly braces {{ }} here so Python/LangChain treats them as text, not variables.
VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM PËR FINAL ANSWER):

1. **FORMATI I CITIMIT TË LIGJIT (Highlighter)**:
   - Duhet të përfshijë: Emrin e Ligjit + Numrin e Ligjit (nëse gjendet) + Nenin.
   - Formati i kërkuar: [**{{Emri i Plotë i Ligjit}} {{Nr. i Ligjit}}, {{Neni X}}**](doc://{{Emri_i_Burimit_PDF}})
   
   - E GABUAR: ...sipas [**Neni 4**](doc://...).
   - E SAKTË: ...sipas [**Ligji për Familjen i Kosovës (Nr. 2004/32), Neni 4**](doc://Ligji_Familjes.pdf).

2. **FORMATI I PROVAVE**:
   - Formati i kërkuar: [**PROVA: {{Përshkrimi i Dokumentit}}**](doc://{{Emri_i_Dosjes}})
   - Shembull: ...siç vërtetohet nga [**PROVA: Raporti Mjekësor QKUK**](doc://Raporti_2024.pdf).

3. **STRUKTURA**:
   - Përdor titujt: **BAZA LIGJORE**, **VLERËSIMI I PROVAVE**, **KONKLUZIONI**.
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
    return "\n\n".join([f"[BURIMI: {r.get('source', 'Ligji_Unknown')}]\n{r.get('text', '')}" for r in results])


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
        
        # PHOENIX UPGRADE: Researcher Prompt with ESCAPED Style Protocol
        # We use f-string here, so {input} and {tools} must remain single for replacement,
        # but the {{ }} inside VISUAL_STYLE_PROTOCOL will pass through safely.
        researcher_template = f"""
        Ti je "Juristi AI", një asistent ligjor elitar.
        
        {STRICT_FORENSIC_RULES}
        
        {VISUAL_STYLE_PROTOCOL}

        MJETET E DISPONUESHME:
        {{tools}}
        
        Përdor formatin e mëposhtëm (ReAct):
        Question: Pyetja e hyrjes
        Thought: Mendo çfarë të bësh
        Action: Një nga [{{tool_names}}]
        Action Input: Inputi për veprimin
        Observation: Rezultati i veprimit (Kërko 'Nr.' të ligjit këtu)
        ... (Përsërit nëse duhet)
        Thought: Tani e di përgjigjen.
        Final Answer: Përgjigja përfundimtare duke përdorur citimet e plota të theksuara.

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

        # 3. DRAFTING PROMPT (Updated to match Detailed Style)
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
        RREGULL I FORTË: Përfshi Emrin e Ligjit, Numrin, dhe Nenin në linkun e citimit Markdown.
        """
        
        try:
            response = await self.llm.ainvoke(drafting_prompt)
            return str(response.content)
        except Exception as e:
            logger.error(f"Draft Gen Error: {e}")
            return "Dështoi gjenerimi i draftit ligjor."