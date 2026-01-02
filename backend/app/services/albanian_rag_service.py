# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V24.5 (SYNTAX FIX)
# 1. FIX: Added missing 'except' clause in generate_legal_draft.
# 2. STATUS: Syntax error resolved.

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

# --- PERFORMANCE CONFIGURATION ---
MAX_ITERATIONS = int(os.environ.get("RAG_MAX_ITERATIONS", "15"))  
MAX_EXECUTION_TIME = int(os.environ.get("RAG_MAX_EXECUTION_TIME", "120"))  
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "60"))  
EARLY_STOPPING_METHOD = os.environ.get("RAG_EARLY_STOPPING", "force")

logger.info(f"RAG Configuration: max_iterations={MAX_ITERATIONS}, max_execution_time={MAX_EXECUTION_TIME}s")

# --- THE FORENSIC CONSTITUTION (SYNCED WITH LLM_SERVICE) ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):

1. HIERARKIA E BURIMEVE (THE SOURCE HIERARCHY):
   - GLOBAL KNOWLEDGE BASE (Biblioteka Publike) = LIGJI (The Law). Përmban rregullat, nenet, dhe precedentët.
   - CASE KNOWLEDGE BASE (Ditari Privat) = FAKTET (The Facts). Përmban vetëm dokumentet e dosjes specifike.
   - URDHËR: Ti nuk guxon të shpikësh fakte. Faktet merren VETËM nga CASE KNOWLEDGE BASE.
   - URDHËR: Ti nuk guxon të shpikësh ligje. Ligjet merren VETËM nga GLOBAL KNOWLEDGE BASE.

2. ZERO HALUCINACIONE: Nëse fakti nuk ekziston në "Case Knowledge Base", shkruaj "NUK KA TË DHËNA NË DOSJE".
3. RREGULLI I HESHTJES: Nëse kemi vetëm Padinë, I Padituri "NUK KA PARAQITUR PËRGJIGJE".
4. CITIM I DETYRUESHËM: Çdo pretendim faktik ose ligjor duhet të ketë referencën (Linkun Markdown).
5. GJUHA: Shqipe Standarde Juridike.
"""

# --- THE VISUAL STYLE PROTOCOL ---
VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM PËR FINAL ANSWER):

1. **FORMATI I CITIMIT TË LIGJIT (Highlighter)**:
   - Duhet të përfshijë: Emrin e Ligjit + Numrin e Ligjit + Nenin.
   - Formati: [**{{Emri i Plotë i Ligjit}} {{Nr. i Ligjit}}, {{Neni X}}**](doc://{{Emri_i_Burimit_PDF}})

2. **FORMATI I PROVAVE**:
   - Formati: [**PROVA: {{Përshkrimi i Dokumentit}}**](doc://{{Emri_i_Dosjes}})

3. **STRUKTURA**:
   - Titujt: **BAZA LIGJORE**, **VLERËSIMI I PROVAVE**, **KONKLUZIONI**.
"""

# --- Custom Tool Class for Private Diary ---
class PrivateDiaryTool(BaseTool):
    name: str = "query_private_diary"
    description: str = (
        "CASE KNOWLEDGE BASE (FACTS). Access the user's uploaded documents/evidence. "
        "Use this for: Specific dates, names, events, contracts, or police reports inside the case."
    )
    user_id: str
    case_id: Optional[str]
    document_ids: Optional[List[str]] = None

    def _run(self, query: str) -> str:
        from . import vector_store_service
        try:
            results = vector_store_service.query_private_diary(
                user_id=self.user_id, 
                query_text=query, 
                case_context_id=self.case_id
            )
            if not results: 
                return "Nuk u gjetën të dhëna private për kërkesën tuaj."
            
            formatted_results = []
            for r in results:
                source = r.get('source', 'Unknown')
                text = r.get('text', '')
                formatted_results.append(f"[BURIMI (FACT): {source}]\n{text}")
            
            return "\n\n".join(formatted_results)
        except Exception as e:
            logger.error(f"PrivateDiaryTool error: {e}")
            return f"Gabim në aksesimin e ditarit privat: {str(e)}"

    async def _arun(self, query: str) -> str:
        return await asyncio.to_thread(self._run, query)
        
    class ArgsSchema(BaseModel):
        query: str = Field(description="The question to search for in the user's private documents.")

# --- Public Library Tool ---
class PublicLibraryInput(BaseModel):
    query: str = Field(description="The topic to search for in the public laws and business regulations.")

@tool("query_public_library", args_schema=PublicLibraryInput)
def query_public_library_tool(query: str) -> str:
    """
    GLOBAL KNOWLEDGE BASE (LAW). Access Official Laws & Business Regulations.
    Use this for: Legal Articles (Nenet), Definitions, Compliance Rules.
    """
    from . import vector_store_service
    try:
        results = vector_store_service.query_public_library(query_text=query)
        if not results: 
            return "Nuk u gjetën të dhëna në bibliotekën publike për kërkesën tuaj."
        
        formatted_results = []
        for r in results:
            source = r.get('source', 'Ligji_Unknown')
            text = r.get('text', '')
            formatted_results.append(f"[BURIMI (LAW): {source}]\n{text}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"PublicLibraryTool error: {e}")
        return f"Gabim në aksesimin e bibliotekës publike: {str(e)}"


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
            logger.info(f"LLM initialized with timeout={LLM_TIMEOUT}s")
        else:
            self.llm = None
            logger.warning("No DEEPSEEK_API_KEY found, LLM not initialized")
        
        # PHOENIX UPGRADE: Researcher Prompt with ENFORCED DUAL SOURCE LOGIC
        researcher_template = f"""
        Ti je "Juristi AI", një asistent ligjor elitar.
        
        {STRICT_FORENSIC_RULES}
        
        {VISUAL_STYLE_PROTOCOL}

        MJETET E DISPONUESHME:
        {{tools}}
        
        PROTOKOLLI I KËRKIMIT (DUAL BRAIN PROTOCOL):
        1. HAPI 1 (FACTS): Përdor 'query_private_diary' për të gjetur FAKTET e rastit.
           - Nëse nuk gjen fakte, STOP dhe thuaj "Nuk ka të dhëna në dosje".
        2. HAPI 2 (LAW): Përdor 'query_public_library' për të gjetur LIGJIN e zbatueshëm.
           - Ti duhet të gjesh Nenin specifik. Mos hamendëso ligjin.
        3. HAPI 3 (SYNTHESIS): Apliko LIGJIN mbi FAKTET.
        
        Përdor formatin e mëposhtëm (ReAct):
        Question: Pyetja e hyrjes
        Thought: Mendo çfarë të bësh (Duhet të kontrolloj Faktet pastaj Ligjin)
        Action: Një nga [{{tool_names}}]
        Action Input: Inputi për veprimin
        Observation: Rezultati i veprimit
        ... (Përsërit për Burimin tjetër)
        Thought: Tani kam edhe Faktet edhe Ligjin.
        Final Answer: Përgjigja përfundimtare e strukturuar.

        SHËNIM: Mos përdor më shumë se {MAX_ITERATIONS} hapa.
        
        Fillo!
        Question: {{input}}
        Thought: {{agent_scratchpad}}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or not case_id: 
                return "Nuk ka informacion specifik të rastit."
            try: 
                oid = ObjectId(case_id)
            except: 
                return "ID e pavlefshme e rastit."  
            
            case = await self.db.cases.find_one({"_id": oid}, {"case_name": 1, "description": 1, "summary": 1})
            if not case: 
                return "Rasti nuk u gjet."
            
            summary_parts = []
            if case.get('case_name'):
                summary_parts.append(f"EMRI I RASTIT: {case['case_name']}")
            if case.get('description'):
                summary_parts.append(f"PËRSHKRIMI: {case['description']}")
            if case.get('summary'):
                summary_parts.append(f"INFORMACION SHTESË: {case['summary']}")
                
            return "\n".join(summary_parts)
        except Exception as e:
            logger.warning(f"Case summary fetch error: {e}")
            return "Nuk mund të merret informacioni i rastit."
    
    def _create_agent_executor(self, session_tools: List) -> AgentExecutor:
        try:
            if self.llm is None:
                raise ValueError("LLM is not initialized.")
            
            agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
            executor = AgentExecutor(
                agent=agent, 
                tools=session_tools, 
                verbose=True, 
                handle_parsing_errors=True,
                max_iterations=MAX_ITERATIONS,
                max_execution_time=MAX_EXECUTION_TIME,
                early_stopping_method=EARLY_STOPPING_METHOD,
                return_intermediate_steps=False 
            )
            return executor
        except Exception as e:
            logger.error(f"Agent executor creation failed: {e}")
            raise

    async def chat(
        self, query: str, user_id: str, case_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks'
    ) -> str:
        """
        Main chat method with DUAL BRAIN enforcement.
        """
        if not self.llm: 
            return "Gabim: Sistemi AI nuk është konfiguruar saktë."

        logger.info(f"Chat request - User: {user_id}, Case: {case_id}, Query: '{query[:100]}...'")
        
        try:
            private_tool = PrivateDiaryTool(
                user_id=user_id, 
                case_id=case_id, 
                document_ids=document_ids
            )
            session_tools = [private_tool, query_public_library_tool]
            
            executor = self._create_agent_executor(session_tools)
            
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""
            PYETJA: "{query}"
            JURIDIKSIONI: {jurisdiction}
            KONTEKSTI I RASTIT (Meta-Data):
            {case_summary}
            
            URDHËR EKZEKUTIV:
            1. Kontrollo 'query_private_diary' për faktet e këtij rasti.
            2. Kontrollo 'query_public_library' për nenet ligjore.
            3. Në Final Answer, cito burimet nga të dyja.
            """
            
            res = await executor.ainvoke({"input": input_text})
            
            output = res.get('output', 'Nuk u gjenerua përgjigje.')
            
            if len(output) < 100 and "Thought" in str(res):
                output += "\n\n[SHËNIM: Kërkimi u ndal pasi arriti limitin. Ju lutem specifikoni pyetjen.]"
            
            return output
            
        except asyncio.TimeoutError:
            return f"Kërkimi mori shumë kohë. Ju lutem thjeshtoni pyetjen."
        except Exception as e:
            logger.error(f"Chat execution error: {str(e)}", exc_info=True)
            return f"Ndodhi një gabim teknik: {str(e)[:200]}"

    async def generate_legal_draft(
        self,
        instruction: str,
        user_id: str,
        case_id: Optional[str]
    ) -> str:
        """
        DUAL-STREAM DRAFTING ENGINE (Already Perfected).
        """
        if not self.llm: 
            return "Gabim i Sistemit: Modeli AI nuk është i disponueshëm."

        logger.info(f"Generating legal draft - User: {user_id}, Case: {case_id}")
        
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            # 1. GET FACTS (Case Knowledge Base)
            try:
                private_docs = vector_store_service.query_private_diary(
                    user_id=user_id, 
                    query_text=instruction[:300], 
                    case_context_id=case_id
                )
                facts_text = "\n\n".join([
                    f"DOKUMENTI (FACT): {d.get('text', '')} (Burimi: {d.get('source', '')})" 
                    for d in private_docs
                ]) if private_docs else "Nuk u gjetën dokumente specifike në dosje."
            except Exception as e:
                facts_text = "Gabim gjatë marrjes së fakteve."

            # 2. GET LAWS (Global Knowledge Base)
            try:
                public_docs = vector_store_service.query_public_library(query_text=instruction[:300])
                laws_text = "\n\n".join([
                    f"LIGJI (LAW): {d.get('text', '')} (Burimi: {d.get('source', '')})" 
                    for d in public_docs
                ]) if public_docs else "Referohu parimeve të përgjithshme ligjore."
            except Exception as e:
                # PHOENIX FIX: Added missing except clause
                laws_text = "Gabim gjatë marrjes së ligjeve."

            # 3. DRAFTING PROMPT (Synthesizer)
            drafting_prompt = f"""
            Ti je Avokat Kryesor (Senior Counsel).
            
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            
            --- MATERIALET ---
            [CASE KNOWLEDGE BASE - FAKTET]:
            {facts_text}
            
            [GLOBAL KNOWLEDGE BASE - LIGJI]:
            {laws_text}
            
            [META-DATA E RASTIT]:
            {case_summary}
            
            --- UDHËZIMI ---
            {instruction}
            
            --- DETYRA ---
            Harto dokumentin ligjor duke aplikuar LIGJIN mbi FAKTET.
            """
            
            response = await asyncio.wait_for(
                self.llm.ainvoke(drafting_prompt),
                timeout=LLM_TIMEOUT
            )
            
            return str(response.content)
            
        except asyncio.TimeoutError:
            return f"Koha skadoi. Provoni përsëri."
        except Exception as e:
            return f"Dështoi gjenerimi: {str(e)[:200]}"