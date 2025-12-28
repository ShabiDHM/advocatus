# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V14.3 (CONFLICT RESOLUTION)
# 1. FIX: Removed direct api_key passing to ChatOpenAI constructor to resolve Pydantic v1/v2 conflict.
# 2. LOGIC: LangChain now implicitly uses the DEEPSEEK_API_KEY environment variable.
# 3. STATUS: Resolves all Pylance errors.

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
# The Agent will now use this environment variable directly.
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
            # PHOENIX FIX: Rely on environment variables for API key to avoid Pydantic conflict.
            # LangChain's ChatOpenAI will automatically pick up the DEEPSEEK_API_KEY if we set it as OPENAI_API_KEY.
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL,
                base_url=OPENROUTER_BASE_URL,
                temperature=0.0,
                streaming=False
            )
        else:
            self.llm = None
        
        react_prompt_template = """
        Answer the user's question in Albanian. You have access to the following tools:

        {tools}

        Use the following format:

        Question: the input question you must answer
        Thought: you should always think about what to do.
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer.
        Final Answer: the final answer to the original input question in detailed, professional Albanian.
        
        Begin!

        Question: {input}
        Thought: {agent_scratchpad}
        """
        self.prompt = PromptTemplate.from_template(react_prompt_template)
        
        if self.llm:
            agent = create_react_agent(self.llm, self.tools, self.prompt)
            self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, handle_parsing_errors=True)
        else:
            self.agent_executor = None

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
        if not self.agent_executor:
            return "Agent Executor nuk është inicializuar. Kontrolloni API keys."

        case_summary = await self._get_case_summary(case_id)
        
        enriched_input = f"""
        User's Question: "{query}"

        Case Summary:
        {case_summary}
        """
        
        try:
            response = await self.agent_executor.ainvoke({
                "input": enriched_input,
                "user_id": user_id,
                "case_id": case_id
            })
            return response.get('output', "Agjenti nuk ktheu përgjigje.")
        except Exception as e:
            logger.error(f"Agent Chat Error: {e}", exc_info=True)
            return "Ndodhi një gabim gjatë procesimit të kërkesës nga agjenti."