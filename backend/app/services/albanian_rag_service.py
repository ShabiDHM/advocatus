# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V27.1 (TYPE FIX)
# 1. FIX: Removed '.bind()' from LLM init to resolve Pylance Type Error.
# 2. LOGIC: Relying on 'create_react_agent' internal stop-sequence handling.
# 3. STATUS: Type-Safe & Operational.

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

MAX_ITERATIONS = int(os.environ.get("RAG_MAX_ITERATIONS", "15")) 
MAX_EXECUTION_TIME = int(os.environ.get("RAG_MAX_EXECUTION_TIME", "120"))  
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "60"))  

logger.info(f"RAG Configuration: max_iterations={MAX_ITERATIONS}")

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):

1. DUALITY OF BRAINS (DY MENDJET):
   - BAZA E LIGJEVE (GLOBAL) = LIGJI (Kodet, Kushtetuta, Rregulloret).
   - BAZA E LËNDËS (CASE) = FAKTET (Dokumentet e ngarkuara, Provat, Deklaratat).
   
2. STRICT SEPARATION:
   - Mos përdor 'Baza e Lëndës' për të shpikur ligje.
   - Mos përdor 'Baza e Ligjeve' për të shpikur fakte specifike të çështjes.

3. CITIM I DETYRUESHËM: 
   - Çdo fakt duhet të ketë burimin: [**Dokumenti X**](doc://...).
   - Çdo ligj duhet të ketë burimin: [**Ligji Y**](doc://...).
"""

VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM):
1. **FORMATI I LIGJIT (Blue Text)**: [**{{Emri i Ligjit}} {{Nr.}}, {{Neni X}}**](doc://{{Emri_i_Burimit_PDF}})
2. **FORMATI I PROVAVE (Yellow Badge)**: [**PROVA: {{Përshkrimi i Dokumentit}}**](doc://{{Emri_i_Dosjes}})
3. **STRUKTURA**: **BAZA E LIGJEVE**, **BAZA E LËNDËS (FAKTET)**, **ANALIZA**.
"""

# --- TOOL 1: BAZA E LËNDËS (FACTS) ---
class CaseKnowledgeBaseTool(BaseTool):
    name: str = "query_case_knowledge_base"
    description: str = "SEARCH FACTS in 'BAZA E LËNDËS'. Use this to find specific details, dates, names, or evidence inside the User's uploaded documents."
    user_id: str
    case_id: Optional[str]
    document_ids: Optional[List[str]] = None

    def _run(self, query: str) -> str:
        from . import vector_store_service
        try:
            results = vector_store_service.query_case_knowledge_base(
                user_id=self.user_id, 
                query_text=query, 
                case_context_id=self.case_id,
                document_ids=self.document_ids
            )
            if not results: return "BAZA E LËNDËS: Nuk u gjetën të dhëna relevante në dosje."
            return "\n\n".join([f"[BURIMI I FAKTIT: {r.get('source', 'Unknown')}]\n{r.get('text', '')}" for r in results])
        except Exception as e:
            logger.error(f"CaseKnowledgeBase Tool error: {e}")
            return f"Gabim teknik në aksesimin e Bazës së Lëndës: {e}"

    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Search query for facts.")

# --- TOOL 2: BAZA E LIGJEVE (LAWS) ---
class GlobalKnowledgeBaseInput(BaseModel): query: str = Field(description="Search query for laws.")

@tool("query_global_knowledge_base", args_schema=GlobalKnowledgeBaseInput)
def query_global_knowledge_base_tool(query: str) -> str:
    """SEARCH LAWS in 'BAZA E LIGJEVE'. Use this to find Official Laws, Penal Codes, and Regulations."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_global_knowledge_base(query_text=query)
        if not results: return "BAZA E LIGJEVE: Nuk u gjetën ligje specifike."
        return "\n\n".join([f"[BURIMI LIGJOR: {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e:
        logger.error(f"GlobalKnowledgeBase Tool error: {e}")
        return f"Gabim teknik në aksesimin e ligjeve: {e}"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            # PHOENIX FIX: Removed .bind() to return a clean ChatOpenAI object (BaseLanguageModel)
            # 'create_react_agent' handles the stop sequence internally.
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
        
        # PROMPT FIX: Extremely strict formatting instructions
        researcher_template = f"""
        Ti je "Juristi AI", Arkitekt Ligjor Strategjik.
        
        {STRICT_FORENSIC_RULES}
        {VISUAL_STYLE_PROTOCOL}

        MJETET E DISPONUESHME (TOOLS):
        {{tools}}
        
        PROTOKOLLI I MENDIMIT (DUAL BRAIN PROCESS):
        1. HAPI 1: Konsulto 'BAZA E LËNDËS' për të gjetur FAKTET e çështjes.
        2. HAPI 2: Konsulto 'BAZA E LIGJEVE' për të gjetur LIGJIN e aplikueshëm.
        3. HAPI 3: Sintetizo përgjigjen duke aplikuar Ligjin mbi Faktet.
        
        FORMATI REACT (STRICT - MUST FOLLOW EXACTLY):
        Question: The input question
        Thought: I should check...
        Action: One of [{{tool_names}}]
        Action Input: "The search query string"
        Observation: [The result will appear here]
        ... (Repeat Thought/Action/Observation)
        Thought: I have enough information.
        Final Answer: The final response to the user.
        
        IMPORTANT: 
        - Action and Action Input must be on separate lines.
        - Do not output empty lines between Action and Action Input.
        
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
        
        # PHOENIX: 'create_react_agent' requires 'llm' to be a BaseLanguageModel, not a RunnableBinding.
        agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        
        return AgentExecutor(
            agent=agent, 
            tools=session_tools, 
            verbose=True, 
            handle_parsing_errors=True, 
            max_iterations=MAX_ITERATIONS, 
            max_execution_time=MAX_EXECUTION_TIME, 
            return_intermediate_steps=False
        )

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [
                CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), 
                query_global_knowledge_base_tool
            ]
            
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            
            input_text = f"""
            PYETJA: "{query}"
            JURIDIKSIONI: {jurisdiction}
            KONTEKSTI (Case Meta-Data): {case_summary}
            DOKUMENTE TE ZGJEDHURA NË 'BAZA E LËNDËS': {len(document_ids) if document_ids else 0}
            """
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Ndjesë, ndodhi një gabim në procesimin e kërkesës. Provoni përsëri."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            # 1. RETRIEVE FACTS FROM CASE KB
            try:
                p_docs = vector_store_service.query_case_knowledge_base(
                    user_id=user_id, 
                    query_text=instruction[:300], 
                    case_context_id=case_id
                )
                facts = "\n".join([d.get('text', '') for d in p_docs]) if p_docs else "S'ka dokumente specifike."
            except Exception as e:
                facts = "Gabim në marrjen e fakteve."
            
            # 2. RETRIEVE LAW FROM GLOBAL KB
            try:
                l_docs = vector_store_service.query_global_knowledge_base(instruction[:300])
                laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "Referohu parimeve ligjore."
            except Exception as e:
                laws = "Gabim në marrjen e ligjeve."

            drafting_prompt = f"""
            Ti je Avokat Kryesor.
            
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            
            --- MATERIALET ---
            [BAZA E LËNDËS (FAKTET)]: 
            {facts}
            
            [BAZA E LIGJEVE (LIGJI)]: 
            {laws}
            
            [RASTI]: {case_summary}
            [UDHËZIMI]: {instruction}
            
            DETYRA: Harto dokumentin.
            """
            
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
            
        except Exception as e:
            return f"Gabim draftimi: {str(e)[:200]}"