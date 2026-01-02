# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V24.3 (PERFORMANCE OPTIMIZED)
# 1. FIX: Increased iteration limits to prevent premature agent termination
# 2. ADDED: Configurable timeout parameters via environment variables
# 3. ADDED: Better error handling and verbose logging for debugging
# 4. FIX: Removed invalid request_timeout parameter from ChatOpenAI
# 5. FIX: Added proper null checking for LLM before agent creation

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
# Configurable via environment variables for flexibility
MAX_ITERATIONS = int(os.environ.get("RAG_MAX_ITERATIONS", "15"))  # Increased from 5 to 15
MAX_EXECUTION_TIME = int(os.environ.get("RAG_MAX_EXECUTION_TIME", "120"))  # 120 seconds
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "60"))  # LLM call timeout
EARLY_STOPPING_METHOD = os.environ.get("RAG_EARLY_STOPPING", "force")

logger.info(f"RAG Configuration: max_iterations={MAX_ITERATIONS}, max_execution_time={MAX_EXECUTION_TIME}s")

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
                formatted_results.append(f"[BURIMI: {source}]\n{text}")
            
            return "\n\n".join(formatted_results)
        except Exception as e:
            logger.error(f"PrivateDiaryTool error: {e}")
            return f"Gabim në aksesimin e ditarit privat: {str(e)}"

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
    try:
        results = vector_store_service.query_public_library(query_text=query)
        if not results: 
            return "Nuk u gjetën të dhëna në bibliotekën publike për kërkesën tuaj."
        
        formatted_results = []
        for r in results:
            source = r.get('source', 'Ligji_Unknown')
            text = r.get('text', '')
            formatted_results.append(f"[BURIMI: {source}]\n{text}")
        
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
        
        # PHOENIX UPGRADE: Researcher Prompt with ESCAPED Style Protocol
        researcher_template = f"""
        Ti je "Juristi AI", një asistent ligjor elitar.
        
        {STRICT_FORENSIC_RULES}
        
        {VISUAL_STYLE_PROTOCOL}

        MJETET E DISPONUESHME:
        {{tools}}
        
        STRATEGJIA E KËRKIMIT:
        1. Së pari kërko në ditarin privat për fakte specifike të rastit
        2. Pastaj kërko në bibliotekën publike për ligje të përshtatshme
        3. Kombino të dhënat dhe aplikojnë ligjet në fakte
        4. Formatizo përgjigjen sipas protokollit vizual
        
        Përdor formatin e mëposhtëm (ReAct):
        Question: Pyetja e hyrjes
        Thought: Mendo çfarë të bësh
        Action: Një nga [{{tool_names}}]
        Action Input: Inputi për veprimin
        Observation: Rezultati i veprimit (Kërko 'Nr.' të ligjit këtu)
        ... (Përsërit nëse duhet)
        Thought: Tani e di përgjigjen.
        Final Answer: Përgjigja përfundimtare duke përdorur citimet e plota të theksuara.

        SHËNIM: Mos përdor më shumë se {MAX_ITERATIONS} hapa. Nëse keni gjetur përgjigjen e plotë, ndaloni më herët.
        
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
        """Create an AgentExecutor with optimized configuration."""
        try:
            # Check if LLM is available
            if self.llm is None:
                raise ValueError("LLM is not initialized. Check API keys configuration.")
            
            agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
            executor = AgentExecutor(
                agent=agent, 
                tools=session_tools, 
                verbose=True, 
                handle_parsing_errors=True,
                max_iterations=MAX_ITERATIONS,
                max_execution_time=MAX_EXECUTION_TIME,
                early_stopping_method=EARLY_STOPPING_METHOD,
                return_intermediate_steps=False  # Set to True for debugging if needed
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
        Main chat method with improved agent execution.
        """
        if not self.llm: 
            return "Gabim: Sistemi AI nuk është konfiguruar saktë. Kontrolloni çelësat API."

        logger.info(f"Chat request - User: {user_id}, Case: {case_id}, Query: '{query[:100]}...'")
        
        try:
            # Create tools
            private_tool = PrivateDiaryTool(
                user_id=user_id, 
                case_id=case_id, 
                document_ids=document_ids
            )
            session_tools = [private_tool, query_public_library_tool]
            
            # Create executor with optimized settings
            executor = self._create_agent_executor(session_tools)
            
            # Prepare input context
            case_summary = await self._get_case_summary(case_id)
            input_text = f"""
            PYETJA: "{query}"
            JURIDIKSIONI: {jurisdiction}
            KONTEKSTI I RASTIT:
            {case_summary}
            
            UDHËZIM: Jep një përgjigje të plotë dhe të dokumentuar duke përdorur të dyja burimet.
            """
            
            logger.info(f"Executing agent with max_iterations={MAX_ITERATIONS}, max_execution_time={MAX_EXECUTION_TIME}s")
            
            # Execute the agent
            res = await executor.ainvoke({"input": input_text})
            
            # Extract and format response
            output = res.get('output', 'Nuk u gjenerua përgjigje.')
            
            # Add context note if agent was truncated
            if len(output) < 100 and "Thought" in str(res):
                output += "\n\n[SHËNIM: Kërkimi u ndal pasi arriti limitin e hapave. Ju lutem specifikoni më shumë ose thjeshtoni pyetjen tuaj.]"
            
            logger.info(f"Chat completed successfully. Response length: {len(output)} chars")
            return output
            
        except asyncio.TimeoutError:
            logger.warning(f"Agent timeout after {MAX_EXECUTION_TIME} seconds")
            return f"Kërkimi mori shumë kohë (kufiri: {MAX_EXECUTION_TIME} sekonda). Ju lutem thjeshtoni pyetjen ose provoni përsëri."
            
        except ValueError as e:
            if "LLM is not initialized" in str(e):
                return "Gabim: Sistemi AI nuk është konfiguruar. Kontrolloni çelësat API."
            logger.error(f"ValueError in chat: {str(e)}", exc_info=True)
            return f"Gabim në konfigurimin e sistemit: {str(e)[:200]}"
            
        except Exception as e:
            logger.error(f"Chat execution error: {str(e)}", exc_info=True)
            return f"Ndodhi një gabim teknik gjatë përpunimit të kërkesës tuaj: {str(e)[:200]}"

    async def generate_legal_draft(
        self,
        instruction: str,
        user_id: str,
        case_id: Optional[str]
    ) -> str:
        """
        DUAL-STREAM DRAFTING ENGINE.
        """
        if not self.llm: 
            return "Gabim i Sistemit: Modeli AI nuk është i disponueshëm."

        logger.info(f"Generating legal draft - User: {user_id}, Case: {case_id}, Instruction: '{instruction[:100]}...'")
        
        try:
            case_summary = await self._get_case_summary(case_id)
            from . import vector_store_service
            
            # 1. GET FACTS with timeout protection
            try:
                private_docs = vector_store_service.query_private_diary(
                    user_id=user_id, 
                    query_text=instruction[:300], 
                    case_context_id=case_id
                )
                facts_text = "\n\n".join([
                    f"DOKUMENTI: {d.get('text', '')} (Burimi: {d.get('source', '')})" 
                    for d in private_docs
                ]) if private_docs else "Nuk u gjetën dokumente specifike."
            except Exception as e:
                logger.error(f"Failed to fetch private documents: {e}")
                facts_text = "Nuk mund të merren dokumentet private."

            # 2. GET LAWS with timeout protection
            try:
                public_docs = vector_store_service.query_public_library(query_text=instruction[:300])
                laws_text = "\n\n".join([
                    f"LIGJI: {d.get('text', '')} (Burimi: {d.get('source', '')})" 
                    for d in public_docs
                ]) if public_docs else "Referohu parimeve të përgjithshme ligjore të Kosovës."
            except Exception as e:
                logger.error(f"Failed to fetch public laws: {e}")
                laws_text = "Nuk mund të merren ligjet publike."

            # 3. DRAFTING PROMPT (Updated to match Detailed Style)
            drafting_prompt = f"""
            Ti je Avokat Kryesor (Senior Counsel).
            
            {STRICT_FORENSIC_RULES}
            {VISUAL_STYLE_PROTOCOL}
            
            --- MATERIALET ---
            FAKTET E RASTIT:
            {facts_text}
            
            BAZA LIGJORE:
            {laws_text}
            
            INFORMACION SHTESË PËR RASTIN:
            {case_summary}
            
            --- UDHËZIMI ---
            {instruction}
            
            --- DETYRA ---
            Harto dokumentin e plotë ligjor duke:
            1. Përdorur të gjitha faktet e disponueshme
            2. Citimi i plotë i çdo ligji (Emri + Nr. + Neni)
            3. Strukturimi i qartë me tituj
            4. Përfshirja e referencave të sakta
            
            RREGULL I FORTË: Përfshi Emrin e Ligjit, Numrin, dhe Nenin në linkun e citimit Markdown.
            """
            
            # Generate draft with timeout
            response = await asyncio.wait_for(
                self.llm.ainvoke(drafting_prompt),
                timeout=LLM_TIMEOUT
            )
            
            draft_content = str(response.content)
            logger.info(f"Draft generated successfully. Length: {len(draft_content)} chars")
            return draft_content
            
        except asyncio.TimeoutError:
            logger.error(f"Draft generation timeout after {LLM_TIMEOUT} seconds")
            return f"Koha për gjenerimin e draftit ka skaduar ({LLM_TIMEOUT} sekonda). Ju lutem thjeshtoni udhëzimin ose provoni përsëri."
            
        except Exception as e:
            logger.error(f"Draft generation error: {str(e)}", exc_info=True)
            return f"Dështoi gjenerimi i draftit ligjor për shkak të: {str(e)[:200]}"