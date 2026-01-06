# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V34.1 (DEEP CITATION)
# 1. CITATION: Enforced strict law citation (Name + Number + Article + Paragraph + Content).
# 2. PROMPT: Updated examples to show exactly how to cite specific legal clauses.
# 3. STATUS: Optimized for high-precision legal referencing.

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
MAX_ITERATIONS = 10
LLM_TIMEOUT = 120

# --- PHOENIX PROTOCOL OF LEGAL EXPERTISE ---
PROTOKOLLI_I_EKSPERTIZES_LIGJORE = """
URDHËRA TË PADISKUTUESHËM PËR FORMATIN DHE STILIN:

1.  **CITIMI I LIGJIT (STRIKT & I PLOTË):**
    *   Duhet të përfshijë: **Emrin e Ligjit**, **Numrin e Ligjit**, **Nenin**, dhe **Paragrafin** (nëse aplikohet).
    *   Duhet të përfshijë përmbajtjen: Trego çfarë thotë neni.
    *   *Formati Vizual:* [**Ligji Nr. [Nr], Neni [X], paragrafi [Y]**](doc://...)
    *   *Shembull:* "Kjo bazohet në [**Ligjin për Familjen Nr. 2004/32, Neni 331, paragrafi 2**](doc://...), i cili përcakton se alimentacioni mund të ndryshohet nëse ndryshojnë rrethanat."

2.  **CITIMI I FAKTEVE:**
    *   Integro burimin në fjali: "...siç vërtetohet në (Burimi: Padi, fq. 2)."
    *   Mos përdor "Faqja: N/A". Nëse mungon faqja, shkruaj vetëm emrin e dokumentit.

3.  **STRUKTURA:**
    *   Përdor **TEXT BOLD** për data, shuma, dhe emra.
    *   Përdor Lista (Bullet Points).

4.  **JURIDIKSIONI:** Vetëm Ligjet e Republikës së Kosovës.
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
            
            formatted_results = []
            for r in results:
                source = r.get('source', 'Dokument')
                page = r.get('page', 'N/A')
                
                # Logic to clean up "N/A" pages
                citation = f"{source}"
                if page and page != "N/A" and page != "None":
                    citation += f", fq. {page}"
                
                formatted_results.append(f"[BURIMI: {citation}]\n{r.get('text', '')}")

            return "\n\n".join(formatted_results)
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
        
        # CHAT PROMPT (DEEP CITATION STYLE)
        researcher_template = f"""
        Ti je "Juristi AI", Këshilltar Ligjor i Lartë.
        {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}
        
        MJETET E TUA: {{tools}}
        
        SHEMBULL I PËRGJIGJES (Vini re saktësinë e citimit):
        
        Final Answer:
        **Analiza Ligjore:**
        Kërkesa e paditësit mbështetet në [**Ligjin për Marrëdhëniet e Detyrimeve Nr. 04/L-077, Neni 25, paragrafi 1**](doc://...), i cili përcakton qartë se "Kreditori ka të drejtë të kërkojë përmbushjen e detyrimit".
        
        **Analiza Faktike:**
        Megjithatë, faktet tregojnë se pagesa është kryer me vonesë (Burimi: Fatura Nr. 123, fq. 1).

        ---
        PËRDOR FORMATIN REACT:
        Question: ...
        Thought: ...
        Action: Një nga [{{tool_names}}]
        Action Input: ...
        Observation: ...
        ...
        Final Answer: (Këtu zbato citimin e plotë ligjor)
        
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
            facts = ""
            if p_docs:
                for r in p_docs:
                    src = r.get('source', '')
                    pg = r.get('page', 'N/A')
                    cit = f"{src}"
                    if pg and pg != 'N/A': cit += f", fq. {pg}"
                    facts += f"- {r.get('text', '')} (Burimi: {cit})\n"
            else:
                facts = "S'ka fakte specifike."
            
            l_docs = vector_store_service.query_global_knowledge_base(
                instruction[:300], 
                jurisdiction='ks'
            )
            laws = "\n".join([d.get('text', '') for d in l_docs]) if l_docs else "S'ka ligje specifike në dispozicion."

            drafting_prompt = f"""
            Ti je "Mjeshtër i Litigimit", avokat elitar në Kosovë.
            {PROTOKOLLI_I_EKSPERTIZES_LIGJORE}

            **URDHËR I STRUKTURËS (Blueprint Mandate):**
            Ndiq me përpikmëri `STRUKTURA E KËRKUAR` nga udhëzimi.

            **URDHËR I CITIMIT (Sinteza Ligjore):**
            Çdo argument ligjor DUHET të mbështetet me Nenin dhe Paragrafin përkatës.
            
            --- MATERIALET ---
            [FAKTET]: 
            {facts}
            
            [LIGJET]: 
            {laws}
            
            [RASTI]: {case_summary}
            
            [UDHËZIMI]: 
            {instruction}
            ---
            
            DETYRA: Harto draftin e plotë, profesional, me tonin e duhur dhe citime preçize ligjore.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"