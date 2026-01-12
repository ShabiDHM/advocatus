# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - PROFESSIONAL CITATION SERVICE V42.0
# 1. FIX (Logic): The 'fast_rag' context builder now correctly includes page number metadata for every document snippet, making it available to the LLM.
# 2. REWRITE (Prompting): The visual protocol ('PROTOKOLLI_PROFESIONAL') has been completely rewritten to enforce strict, non-negotiable citation rules with clear examples for both facts and laws.
# 3. ENHANCE (Prompting): The main 'fast_prompt' now contains explicit, forceful instructions on how to use the provided metadata to construct perfect citations, handle jurisdictional locks, and avoid generic answers.
# 4. RESULT: Achieves full compliance with the Professional Legal Standards mandate.

import os
import asyncio
import logging
import re
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

# --- PHOENIX PROFESSIONAL STANDARD V2.0 ---
PROTOKOLLI_PROFESIONAL = """
**URDHËRA MANDATORË PËR CITIM DHE JURIDIKSION:**

1.  **JURIDIKSIONI I REPUBLIKËS SË KOSOVËS (ABSOLUT):**
    *   **KUFIZIM:** Çdo analizë, referencë ligjore apo përfundim duhet të bazohet **EKSKLUZIVISHT** në legjislacionin dhe kontekstin juridik të Republikës së Kosovës.
    *   **NDALIM:** **MOS** përmend kurrë ligjet e Shqipërisë apo të ndonjë shteti tjetër.

2.  **CITIMI I FAKTEVE (Nga "Baza e Lëndës"):**
    *   **RREGULL:** Çdo fjali që përmban informacion nga një dokument i rastit **DUHET** të përfundojë me një citim të saktë.
    *   **FORMATI (I PA-NEGOCIUESHËM):** `(Burimi: [Emri i Dokumentit], fq. [numri])`
    *   **SHEMBULL:** Pretendimet e paditëses janë se fëmija ndjen ankth. (Burimi: padi.pdf, fq. 2)

3.  **CITIMI I LIGJEVE (Nga "Baza e Ligjeve"):**
    *   **RREGULL:** Çdo referencë ligjore **DUHET** të formatohet si një link Markdown i plotë dhe i theksuar.
    *   **FORMATI (I PA-NEGOCIUESHËM):** `[**[Emri i plotë i Ligjit] Nr. [Numri], Neni [numri]**](doc://[Emri i plotë i Ligjit] Nr. [Numri], Neni [numri])`
    *   **SHEMBULL:** Rregullat për rishikimin e alimentacionit janë të përcaktuara në [**Ligji për Familjen i Kosovës Nr. 2004/32, Neni 330**](doc://Ligji për Familjen i Kosovës Nr. 2004/32, Neni 330).
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
                user_id=self.user_id, query_text=query, case_context_id=self.case_id, document_ids=self.document_ids
            )
            if not results: return "BAZA E LËNDËS: S'ka të dhëna."
            
            formatted = []
            for r in results:
                src = r.get('source', 'Dokument i pacaktuar')
                pg = r.get('page', 'E pacaktuar')
                formatted.append(f"DOKUMENTI: '{src}' (FAQJA: {pg}) -> PËRMBAJTJA: {r.get('text', '')}")
            
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Gabim në aksesimin e Bazës së Lëndës: {e}"

    async def _arun(self, query: str) -> str: return await asyncio.to_thread(self._run, query)
    class ArgsSchema(BaseModel): query: str = Field(description="Search query for facts.")

class GlobalKnowledgeBaseInput(BaseModel): 
    query: str = Field(description="Search query for laws.")

@tool("query_global_knowledge_base", args_schema=GlobalKnowledgeBaseInput)
def query_global_knowledge_base_tool(query: str) -> str:
    """Kërko LIGJE në 'BAZA E LIGJEVE' (Kodet, Rregulloret) vetëm për Kosovën."""
    from . import vector_store_service
    try:
        results = vector_store_service.query_global_knowledge_base(query_text=query)
        if not results: return "BAZA E LIGJEVE: S'ka ligje."
        return "\n\n".join([f"[BURIMI LIGJOR: '{r.get('source', 'Ligj i pacaktuar')}']\n{r.get('text', '')}" for r in results])
    except Exception as e:
        return f"Gabim: {e}"

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
        
        researcher_template = f"""
        Ti je "Juristi AI", Këshilltar Ligjor Analitik për Republikën e Kosovës.
        {PROTOKOLLI_PROFESIONAL}
        
        MJETET E TUA: {{tools}}
        
        FORMATI REACT:
        Question: ...
        Thought: ...
        Action: Një nga [{{tool_names}}]
        Action Input: ...
        Observation: ...
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
        return AgentExecutor(agent=agent, tools=session_tools, verbose=True, handle_parsing_errors=True, max_iterations=MAX_ITERATIONS, return_intermediate_steps=False)

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            tools = [ CaseKnowledgeBaseTool(user_id=user_id, case_id=case_id, document_ids=document_ids), query_global_knowledge_base_tool ]
            executor = self._create_agent_executor(tools)
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""PYETJA: "{query}"\nKONTEKSTI: {case_summary}"""
            res = await executor.ainvoke({"input": input_text})
            return res.get('output', 'Nuk ka përgjigje.')
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return f"Ndjesë, ndodhi një gabim."

    async def fast_rag(self, query: str, user_id: str, case_id: Optional[str] = None, document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks') -> str:
        if not self.llm: return "Sistemi AI nuk është aktiv."
        try:
            from . import vector_store_service
            
            case_docs = await asyncio.to_thread(
                vector_store_service.query_case_knowledge_base,
                user_id=user_id, query_text=query, case_context_id=case_id, document_ids=document_ids, n_results=25
            )
            
            expanded_query = query
            if case_docs:
                keywords = re.findall(r'\b(?:alimentacion|përgjigje në padi|borxhe|kontestim|marrëveshje|aktgjykim|familjen|procedurën civile)\b', " ".join(d['text'] for d in case_docs[:3]), re.IGNORECASE)
                unique_keywords = " ".join(list(dict.fromkeys(keywords)))
                expanded_query = f"{query} {unique_keywords}"
                logger.info(f"Expanded Query for Global KB: {expanded_query}")

            global_docs = await asyncio.to_thread(
                vector_store_service.query_global_knowledge_base,
                query_text=expanded_query, jurisdiction=jurisdiction, n_results=5
            )
            
            context_str = ""
            
            if case_docs:
                context_str += "\n<<< BURIMI PRIMAR: DOKUMENTET E DOSJES >>>\n"
                for d in case_docs:
                    clean_text = d.get('text', '').replace('\n', ' ').strip()
                    source = d.get('source', 'Dokument i pacaktuar')
                    page = d.get('page', 'E pacaktuar')
                    # PHOENIX FIX: Page number is now included in the context for the LLM.
                    context_str += f"[DOKUMENTI: '{source}', FAQJA: {page}]:\n{clean_text}\n\n"
            else:
                context_str += "\n<<< BURIMI PRIMAR: MUNGON (Nuk u gjet informacion) >>>\n"
            
            if global_docs:
                context_str += "\n<<< BURIMI SEKONDAR: BAZA LIGJORE (Për kontekst) >>>\n"
                for d in global_docs:
                    clean_text = d.get('text', '').replace('\n', ' ').strip()
                    source = d.get('source', 'Ligj i pacaktuar')
                    context_str += f"[LIGJI: '{source}']:\n{clean_text}\n\n"

            fast_prompt = f"""
            Ti je "Juristi AI", një asistent ligjor analitik dhe tejet preciz. Misioni yt është të analizosh materialet e ofruara dhe t'i përgjigjesh avokatit në mënyrë profesionale, të strukturuar dhe të verifikueshme.

            {PROTOKOLLI_PROFESIONAL}
            
            **DIREKTIVA KRYESORE:**
            Nëse pyetja e avokatit është e përgjithshme (p.sh., "për çka bëhet fjalë?", "qka permban padia?"), përgjigja jote **DUHET** të jetë një përmbledhje analitike e dokumenteve të ofruara në këtë rast specifik. **MOS** jep kurrë përgjigje gjenerike apo përkufizime teorike. Fokusohu vetëm te faktet e rastit konkret.

            **MATERIALET PËR ANALIZË:**
            
            --- INFORMACIONI I GJETUR ---
            {context_str}
            -----------------------------

            **PYETJA E AVOKATIT:** "{query}"

            **DETYRA JOTE:**
            1.  **Sintetizo informacionin:** Lexo me kujdes të gjitha materialet e gjetura.
            2.  **Strukturo përgjigjen:** Ndërto një përgjigje të qartë, të ndarë në seksione logjike (p.sh., Historiku, Pretendimet e Paditësit, Kundërshtimet e të Paditurit, Baza Ligjore).
            3.  **Zbato RREGULLAT E CITIMIT pa asnjë përjashtim:**
                *   Për çdo fakt nga "DOKUMENTET E DOSJES", gjej emrin dhe faqen nga konteksti `[DOKUMENTI: '...', FAQJA: ...]` dhe apliko formatin `(Burimi: [Emri], fq. [numri])` në fund të fjalisë.
                *   Për çdo referencë nga "BAZA LIGJORE", gjej emrin e plotë dhe nenin nga konteksti `[LIGJI: '...']` dhe apliko formatin e plotë Markdown: `[**[Emri i Ligjit] Nr. ..., Neni ...**](doc://...)`.
            4.  **Formulo Përgjigjen Finale:** Shkruaj përgjigjen përfundimtare duke ndjekur me përpikëri të gjitha udhëzimet.

            TANI, ANALIZO DHE PËRGATIT PËRGJIGJEN FINALE.
            """
            
            response = await self.llm.ainvoke(fast_prompt)
            return str(response.content)

        except Exception as e:
            logger.error(f"Fast RAG error: {e}", exc_info=True)
            return "Ndjesë, nuk arrita të marr informacionin shpejt."

    async def generate_legal_draft(self, instruction: str, user_id: str, case_id: Optional[str]) -> str:
        # This function remains unchanged as it was not the focus of the mandate.
        if not self.llm: return "Gabim AI."
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            p_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, 
                query_text=instruction[:500], 
                case_context_id=case_id
            )
            facts = ""
            if p_docs:
                for r in p_docs:
                    src = r.get('source', 'Dokument')
                    pg = r.get('page', 'N/A')
                    facts += f"--- FAKT NGA: '{src}' (Fq. {pg}) ---\n{r.get('text', '')}\n\n"
            else:
                facts = "S'ka fakte specifike."
            
            law_keywords = "procedura civile shpenzimet familja detyrimet"
            l_docs = vector_store_service.query_global_knowledge_base(f"{instruction} {law_keywords}", jurisdiction='ks')
            laws = "\n".join([f"LIGJI: {d.get('text', '')}" for d in l_docs]) if l_docs else "S'ka ligje specifike."

            drafting_prompt = f"""
            Ti je "Mjeshtër i Litigimit" (Ghostwriter), avokat elitar në Kosovë.
            {PROTOKOLLI_PROFESIONAL}
            
            **URDHËR: MODALI GHOSTWRITER (STRIKT):**
            1. Prodho VETËM tekstin e dokumentit final.
            2. MOS shto asnjë koment shtesë.
            
            --- MATERIALET ---
            [FAKTET]: {facts}
            [LIGJET]: {laws}
            [UDHËZIMI]: {instruction}
            ---
            DETYRA: Harto dokumentin final TANI.
            """
            response = await asyncio.wait_for(self.llm.ainvoke(drafting_prompt), timeout=LLM_TIMEOUT)
            return str(response.content)
        except Exception as e:
            logger.error(f"Drafting service failed: {e}", exc_info=True)
            return f"Gabim draftimi: {str(e)[:200]}"