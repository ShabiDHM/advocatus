# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V15.0 (REFLECTION PATTERN)
# 1. ARCHITECTURE: Implemented a two-step "Reflection" (Critique & Revise) workflow.
# 2. STEP 1 (Researcher Agent): The existing agent now produces a 'Draft Answer'.
# 3. STEP 2 (Critic Agent): A new LLM call critiques the draft for flaws.
# 4. FINAL OUTPUT: A final LLM call synthesizes the original query, draft, and critique into a polished, high-quality answer.

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
        Answer the user's question in Albanian. You have access to the following tools:

        {tools}

        Use the following format:

        Question: the input question you must answer
        Thought: you should always think about what to do.
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now have enough information to draft a comprehensive answer.
        Final Answer: [A detailed, well-structured draft of the answer in professional Albanian based on the observations]
        
        Begin!

        Question: {input}
        Thought: {agent_scratchpad}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_prompt_template)
        
        if self.llm:
            researcher_agent = create_react_agent(self.llm, self.tools, self.researcher_prompt)
            self.researcher_executor = AgentExecutor(agent=researcher_agent, tools=self.tools, verbose=True, handle_parsing_errors="Check your output and make sure it conforms to the format.")
        else:
            self.researcher_executor = None

    async def _get_case_summary(self, case_id: str) -> str:
        try:
            if not self.db: return ""
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
        Original User Question: "{query}"

        Case Summary Context:
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
            logger.info("AGENTIC FLOW - STEP 2: CRITIQUE")
            critic_prompt = f"""
            You are a senior legal partner reviewing a draft from a junior associate.
            Your task is to critique the draft for accuracy, completeness, and clarity. Be harsh but fair.
            Provide a bulleted list of suggestions for improvement. If the draft is perfect, simply state "Drafti është i saktë dhe i plotë."

            ORIGINAL QUESTION:
            ---
            {query}
            ---

            ASSOCIATE'S DRAFT:
            ---
            {draft_answer}
            ---

            Your critique (in Albanian):
            """
            
            critic_response = await self.llm.ainvoke(critic_prompt)
            critique = critic_response.content if isinstance(critic_response.content, str) else ""

            # --- STEP 3: FINAL SYNTHESIS (REVISE) ---
            logger.info("AGENTIC FLOW - STEP 3: REVISION")
            revision_prompt = f"""
            You are the final author. Your task is to revise the original draft based on the senior partner's critique.
            Produce a final, polished, and professional answer in Albanian.

            ORIGINAL QUESTION:
            ---
            {query}
            ---

            ORIGINAL DRAFT:
            ---
            {draft_answer}
            ---

            SENIOR PARTNER'S CRITIQUE:
            ---
            {critique}
            ---
            
            Your final, revised, and comprehensive answer in Albanian:
            """

            final_response = await self.llm.ainvoke(revision_prompt)
            final_answer = final_response.content if isinstance(final_response.content, str) else ""

            return final_answer

        except Exception as e:
            logger.error(f"Agent Chat Error: {e}", exc_info=True)
            return "Ndodhi një gabim gjatë procesimit të kërkesës nga agjenti."