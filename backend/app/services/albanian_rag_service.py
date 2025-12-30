# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V16.1 (DB CHECK FIX)
# 1. FIX: Corrected database object truthiness check ('if self.db is not None').
# 2. LOGIC: Resolves the 'Failed to fetch case summary' error.
# 3. RESULT: The Agent can now correctly access case-specific context.

import os
import asyncio
import logging
from typing import List, Optional, Dict, Any, Type
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

# --- AGENT TOOLS ---
class PrivateDiaryInput(BaseModel):
    query: str = Field(description="The specific question or topic to search for in the user's private documents.")

@tool("query_private_diary", args_schema=PrivateDiaryInput)
def query_private_diary_tool(query: str, user_id: str, case_id: Optional[str] = None) -> List[Dict]:
    """
    Searches the user's personal and private knowledge base (their documents, cases, contracts).
    Use this first to find user-specific context, templates, or facts.
    """
    from . import vector_store_service
    return vector_store_service.query_private_diary(user_id=user_id, query_text=query, case_context_id=case_id)

class PublicLibraryInput(BaseModel):
    query: str = Field(description="The legal concept, law, or article to search for in the public legal library of Kosovo.")

@tool("query_public_library", args_schema=PublicLibraryInput)
def query_public_library_tool(query: str) -> List[Dict]:
    """
    Searches the public, shared legal knowledge base containing official laws, regulations, and precedents of Kosovo.
    Use this to verify legal facts, find specific articles, or ensure compliance.
    """
    from . import vector_store_service
    return vector_store_service.query_public_library(query_text=query, jurisdiction='ks')

# --- AGENT EXECUTOR ---

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.tools = [query_private_diary_tool, query_public_library_tool]
        
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
        
        researcher_prompt_template = """
        You are a diligent legal assistant for a law firm in Kosovo. Answer the user's question in STANDARD Albanian.
        
        LINGUISTIC RULES (Dialect & Typos):
        1. Many users type 'q' instead of 'ç' (e.g., 'qka' -> 'çka', 'qa' -> 'ça').
        2. Many users type 'e' instead of 'ë' (e.g., 'eshte' -> 'është', 'per' -> 'për').
        3. WHEN USING TOOLS: You MUST convert the user's keywords to Standard Albanian. Searching for "qka" might fail, searching for "çka" will succeed.
        
        CRITICAL RULES:
        1. GROUNDING: Answer ONLY using the information found in the 'Observation' from the tools. 
        2. NO HALLUCINATION: If the tools return no relevant information, say "Nuk gjeta informacion në dokumente." Do NOT invent facts.
        3. TYPO CORRECTION: If the user says "Rasti Perman" but you see "Rasti Përmban" or similar, use logic to infer the intent.

        You have access to the following tools:
        {tools}

        Use the following format:

        Question: the input question you must answer
        Thought: you should always think about what to do. (Normalize the user's spelling here before deciding on an Action).
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action (MUST BE IN STANDARD ALBANIAN SPELLING)
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now have enough information to draft a comprehensive answer.
        Final Answer: [A detailed answer based on Observations, written in Standard Albanian with correct ë/ç]
        
        Begin!

        Question: {input}
        Thought: {agent_scratchpad}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_prompt_template)
        
        if self.llm:
            researcher_agent = create_react_agent(self.llm, self.tools, self.researcher_prompt)
            self.researcher_executor = AgentExecutor(agent=researcher_agent, tools=self.tools, verbose=True, handle_parsing_errors=True)
        else:
            self.researcher_executor = None

    async def _get_case_summary(self, case_id: str) -> str:
        try:
            # PHOENIX FIX: Check for 'is not None' instead of truthiness on DB object
            if self.db is None: return ""
            case = await self.db.cases.find_one({"_id": ObjectId(case_id)}, {"case_name": 1, "description": 1, "summary": 1, "title": 1})
            if not case: return ""
            parts = [f"EMRI I RASTIT: {case.get('title') or case.get('case_name')}" if case.get('title') or case.get('case_name') else "",
                     f"PËRSHKRIMI: {case.get('description')}" if case.get('description') else "",
                     f"PËRMBLEDHJA AUTOMATIKE: {case.get('summary')}" if case.get('summary') else ""]
            return "\n".join(filter(None, parts))
        except Exception as e:
            logger.warning(f"Failed to fetch case summary: {e}")
            return ""

    async def chat(
        self, 
        query: str,
        user_id: str,
        case_id: str, 
        document_ids: Optional[List[str]] = None, 
        jurisdiction: str = 'ks'
    ) -> str:
        if not self.researcher_executor or not self.llm:
            return "Agent Executor nuk është inicializuar. Kontrolloni API keys."

        case_summary = await self._get_case_summary(case_id)
        
        enriched_input = f"""
        User's Question (Raw): "{query}"

        KNOWN CASE CONTEXT (Use this):
        {case_summary}
        """
        
        try:
            # --- STEP 1: RESEARCHER AGENT (DRAFT) ---
            logger.info("AGENTIC FLOW - STEP 1: DRAFTING")
            draft_response = await self.researcher_executor.ainvoke({
                "input": enriched_input,
                "user_id": user_id,
                "case_id": case_id
            })
            draft_answer = draft_response.get('output', "Asnjë draft nuk u gjenerua.")

            # --- STEP 2: CRITIC AGENT (REVIEW) ---
            logger.info("AGENTIC FLOW - STEP 2: CRITIQUE (Anti-Hallucination)")
            critic_prompt = f"""
            You are a senior legal auditor. Your ONLY job is to detect hallucinations.

            ORIGINAL QUESTION:
            {query}

            DRAFT ANSWER:
            {draft_answer}

            CONTEXT SUMMARY:
            {case_summary}

            TASK:
            1. Does the draft mention specific names (like 'Perman', 'Gashi', etc.) or specific facts that are NOT in the Context Summary or the User's Question?
            2. If the draft invents a case name (e.g., 'Rasti Perman') that does not exist in the context, flag it immediately.
            3. Did the draft interpret a typo as a proper name?

            If the draft is GROUNDED in reality (even if it says 'I don't know'), output: "OK".
            If the draft is HALLUCINATED, output: "CRITICAL: The draft mentions [X] which is not in the context. Rewrite to say you do not have information about [X]."
            """
            
            critic_response = await self.llm.ainvoke(critic_prompt)
            critique = critic_response.content if isinstance(critic_response.content, str) else ""

            if "OK" in critique and len(critique) < 10:
                return draft_answer

            # --- STEP 3: FINAL SYNTHESIS (REVISE) ---
            logger.info("AGENTIC FLOW - STEP 3: REVISION")
            revision_prompt = f"""
            You are the final author. Fix the hallucination identified by the critic.

            ORIGINAL DRAFT:
            {draft_answer}

            CRITIC'S WARNING:
            {critique}
            
            INSTRUCTION: Rewrite the answer. If you were hallucinating a name/case, remove it. 
            If you don't know the answer because the documents don't have it, explicitly say: "Në dokumentet e kësaj dosjeje nuk gjendet informacion specifik për këtë."
            
            Final Answer (in Albanian):
            """

            final_response = await self.llm.ainvoke(revision_prompt)
            final_answer = final_response.content if isinstance(final_response.content, str) else ""

            return final_answer

        except Exception as e:
            logger.error(f"Agent Chat Error: {e}", exc_info=True)
            return "Ndodhi një gabim gjatë procesimit të kërkesës nga agjenti."