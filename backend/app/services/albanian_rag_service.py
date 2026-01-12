# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - FINAL ANALYTICAL SERVICE V44.0
# 1. ENHANCEMENT (Prompting): Introduced a new, mandatory 'LEGAL ANALYSIS' section in the main 'fast_prompt'.
# 2. CORE DIRECTIVE: This new directive explicitly commands the model to not just cite a law, but to **explain its substance and relevance** to the case facts, using the information provided in the context.
# 3. RESULT: Elevates the AI's output from a precise citator to a true analytical assistant, fulfilling the final, implicit requirement of professional legal standards. Session mandate is now complete.

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

# --- PHOENIX PROFESSIONAL STANDARD V3.1 (ANALYTICAL) ---
PROTOKOLLI_PROFESIONAL = """
**URDHËRA MANDATORË PËR ANALIZË DHE CITIM:**

1.  **JURIDIKSIONI I REPUBLIKËS SË KOSOVËS (ABSOLUT):**
    *   **KUFIZIM:** Çdo analizë, referencë ligjore apo përfundim duhet të bazohet **EKSKLUZIVISHT** në legislacionin dhe kontekstin juridik të Republikës së Kosovës.
    *   **NDALIM:** **MOS** përmend kurrë ligjet e Shqipërisë apo të ndonjë shteti tjetër.

2.  **CITIMI I FAKTEVE (Nga "Baza e Lëndës"):**
    *   **RREGULL:** Çdo fjali që përmban informacion nga një dokument i rastit **DUHET** të përfundojë me një citim të saktë.
    *   **FORMATI (I PA-NEGOCIUESHËM):** `(Burimi: [Emri i Dokumentit], fq. [numri])`
    *   **SHEMBULL:** Pretendimet e paditëses janë se fëmija ndjen ankth. (Burimi: padi.pdf, fq. 2)

3.  **ANALIZA DHE CITIMI I LIGJEVE (Nga "Baza e Ligjeve"):**
    *   **RREGULLI I ANALIZËS:** Nuk mjafton vetëm të citosh një ligj. **DUHET** të shpjegosh shkurtimisht se çfarë thotë neni i cituar dhe pse ai është relevant për faktet e rastit.
    *   **FORMATI I CITIMIT (ABSOLUT):** `[**[Emri i plotë i Ligjit] Nr. [Numri], Neni [numri]**](doc://[Emri i plotë i Ligjit] Nr. [Numri], Neni [numri])`
    *   **RREGULL PËR PARAGRAFËT:** Numri i nenit dhe paragrafit (nëse ekziston) **DUHET** të jetë **IDENTIK** si në tekstin e dukshëm ashtu edhe brenda linkut `doc://`.
    *   **SHEMBULL I SAKTË I ANALIZËS DHE CITIMIT:** Kërkesa për ndryshimin e kontaktit bazohet në [**Ligji për Familjen Nr. 2004/32, Neni 145(2)**](doc://Ligji për Familjen Nr. 2004/32, Neni 145(2)), i cili lejon gjykatën të rishikojë vendimet për kontaktin nëse rrethanat kanë ndryshuar ndjeshëm.
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
            Nëse pyetja e avokatit është e përgjithshme (p.sh., "për çka bëhet fjalë?", "qka permban padia?"), përgjigja jote **DUHET** të jetë një përmbledhje analitike e dokumenteve të ofruara në këtë rast specifik. **MOS** jep kurrë përgjigje gjenerike.

            **MATERIALET PËR ANALIZË:**
            
            --- INFORMACIONI I GJETUR ---
            {context_str}
            -----------------------------

            **PYETJA E AVOKATIT:** "{query}"

            **DETYRA JOTE (HAP PAS HAPI):**
            1.  **Sintetizo Faktet:** Lexo me kujdes të gjitha materialet nga "DOKUMENTET E DOSJES" dhe strukturo përgjigjen me seksione të qarta (Pretendimet, Kundërshtimet, etj.), duke cituar faktet sipas rregullave.
            2.  **Sintetizo dhe Analizo Ligjin (URDHËR KRITIK):** Krijo një seksion të dedikuar "BAZA LIGJORE E APLIKUESHME". Për çdo nen ligjor relevant të përmendur në dokumente:
                a.  **Gjej Përmbajtjen:** Lokalizo tekstin e plotë të atij neni brenda kontekstit `[LIGJI: '...']` që të është ofruar.
                b.  **Shpjego Substancën:** Shkruaj një fjali të qartë që përmbledh çfarë thotë ai nen.
                c.  **Lidhe me Rastin:** Shpjego shkurtimisht pse ai nen është relevant për kërkesat e paditësit ose kundërshtimet e të paditurit.
                d.  **Cito Perfekt:** Përfundo shpjegimin me citimin e plotë, të theksuar dhe teknikisht të saktë sipas protokollit.

            **VERIFIKIM I DYFISHTË (PARA PËRGJIGJES FINALE):**
            *   **Kontrolli 1 (Theksimi):** A i kam vendosur dy yje (`**`) para dhe pas tekstit të çdo citimi ligjor?
            *   **Kontrolli 2 (Pariteti i Nenit):** Për çdo citim ligjor, a është numri i nenit (p.sh., `Neni 145(2)`) **EKZAKTËSISHT I NJËJTË** brenda kllapave `[]` dhe brenda linkut `doc://`?
            *   **Kontrolli 3 (Analiza):** A kam ofruar një shpjegim të qartë për **çdo** ligj të cituar, apo thjesht kam vendosur një link?

            VETËM PASI TË KESH VERIFIKUAR KËTO TRE PIKA, FORMULO PËRGJIGJEN FINALE.
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