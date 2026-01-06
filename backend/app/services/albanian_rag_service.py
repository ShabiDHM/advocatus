# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V36.1 (COMPILER MODE)
# 1. VISUALS: Hard-coded the Markdown Badge syntax into the final task instruction to force compliance.
# 2. OUTPUT: Added aggressive 'Negative Constraints' to ban conversational filler and meta-structure lists.
# 3. LOGIC: Optimized fact context injection for better citation accuracy.

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

# --- PHOENIX PROTOCOL OF LEGAL EXPERTISE ---
PROTOKOLLI_I_EKSPERTIZES_LIGJORE = """
URDHËRA TË PADISKUTUESHËM PËR FORMATIN DHE STILIN:

1.  **STRUKTURA VIZUALE (BADGES & LINKS):**
    *   **PËR FAKTE (DOKUMENTE):** Duhet të përdorësh këtë format ekzakt për të krijuar "Yellow Badges":
        `[**PROVA: Emri i Dokumentit, fq. X**](doc://evidence)`
    *   **PËR LIGJE:** Duhet të përdorësh këtë format ekzakt për të krijuar "Blue Links":
        `[**Ligji Nr. XX, Neni Y**](doc://law)`

2.  **CITIMI I DETYRUESHËM:**
    *   Çdo paragraf faktik duhet të përfundojë me një citim vizual (Yellow Badge).
    *   Çdo argument ligjor duhet të përmbajë citimin vizual (Blue Link).

3.  **JURIDIKSIONI:** Vetëm Ligjet e Republikës së Kosovës.
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
                user_id=self.user_id, 
                query_text=query, 
                case_context_id=self.case_id, 
                document_ids=self.document_ids
            )
            if not results: return "BAZA E LËNDËS: Nuk u gjetën të dhëna."
            
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
        if not results: return "BAZA E LIGJEVE: Nuk u gjetën ligje."
        return "\n\n".join([f"[BURIMI LIGJOR: {r.get('source', 'Ligji')}]\n{r.get('text', '')}" for r in results])
    except Exception as e:
        return f"Gabim në aksesimin e ligjeve: {e}"

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
        
        # CHAT PROMPT
        researcher_template = f"""
        Ti je "Juristi AI", Këshilltar Ligjor i Lartë.
        {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}
        
        MJETET E TUA: {{tools}}
        
        SHEMBULL I PËRGJIGJES SË PËRSOSUR (Visual):
        Final Answer:
        Sipas provave, palët kanë nënshkruar marrëveshjen [**PROVA: Kontrata.pdf, fq. 1**](doc://evidence).
        Kjo është në përputhje me [**Ligjin për Detyrimet, Neni 15**](doc://law).

        ---
        PËRDOR FORMATIN REACT:
        Question: ...
        Thought: ...
        Action: Një nga [{{tool_names}}]
        Action Input: ...
        Observation: ...
        ...
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
        return AgentExecutor(
            agent=agent, 
            tools=session_tools, 
            verbose=True, 
            handle_parsing_errors=True, 
            max_iterations=MAX_ITERATIONS, 
            return_intermediate_steps=False
        )

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [ CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), query_global_knowledge_base_tool ]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""PYETJA: "{query}"\nJURIDIKSIONI I KËRKUAR: {jurisdiction.upper()}\nKONTEKSTI: {case_summary}"""
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return f"Ndjesë, ndodhi një gabim në procesimin e kërkesës."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            p_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, 
                query_text=instruction[:300], 
                case_context_id=case_id
            )
            
            # Formatted exactly for the LLM to pick up Name and Page
            facts = ""
            if p_docs:
                for r in p_docs:
                    src = r.get('source', 'Dokument')
                    pg = r.get('page', 'N/A')
                    facts += f"--- FAKT NGA DOKUMENTI: '{src}' (Faqja: {pg}) ---\nTEKSTI: {r.get('text', '')}\n\n"
            else:
                facts = "S'ka fakte specifike në dispozicion."
            
            l_docs = vector_store_service.query_global_knowledge_base(
                instruction[:300], 
                jurisdiction='ks'
            )
            laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "S'ka ligje specifike në dispozicion."

            drafting_prompt = f"""
            Ti je "Mjeshtër i Litigimit" (Ghostwriter), avokat elitar në Kosovë.
            {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}

            **URDHËRA TË HEKURT PËR FORMATIN (COMPILER MODE):**
            1.  **VETËM DOKUMENT:** Prodho vetëm tekstin e dokumentit final.
            2.  **NDALOHET:** Mos shkruaj "Analiza:", "Përmbledhje:", "Konkluzion:", "Struktura e Dokumentit:", apo ndonjë koment tjetër meta-tekstual.
            3.  **NDALOHET:** Mos përshëndet ("Të nderuar...", "Ja dokumenti..."). Fillo direkt me kokën e aktit.

            **URDHËRA PËR CITIME VIZUALE:**
            Për çdo fakt, DUHET të përdorësh formatin: `[**PROVA: Emri i Dokumentit, fq. X**](doc://evidence)`.
            Mos përdor kurrë tekst të thjeshtë si "Burimi: ...".

            **URDHËR I ARGUMENTIMIT:**
            Përdor informacionin e përdoruesit ("unemployed", "debts") për të ndërtuar argumente ligjore (p.sh. Neni për aftësinë financiare në Ligjin e Familjes).

            --- MATERIALET ---
            [FAKTET E VËRTETUARA]: 
            {facts}
            
            [LIGJET RELEVANTE]: 
            {laws}
            
            [UDHËZIMI I PËRDORUESIT]: 
            {instruction}
            ---
            
            DETYRA: Gjenero dokumentin final TANI.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"