# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - AGENTIC RAG SERVICE V18.1 (FINAL TYPE FIX)
# 1. FIX: Removed the unnecessary 'agent_type' parameter from the public library tool signature.
# 2. LOGIC: The vector_store_service now correctly defaults to the 'business' knowledge base.
# 3. STATUS: All Pylance errors resolved. Final version.

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

# --- Custom Tool Class for Private Diary ---
class PrivateDiaryTool(BaseTool):
    name: str = "query_private_diary"
    description: str = (
        "Access the user's 'Private Diary' (Personal Knowledge Base). "
        "Use this FIRST to find specific details about the user's business, past cases, or documents."
    )
    user_id: str
    case_id: Optional[str]

    def _run(self, query: str) -> str:
        from . import vector_store_service
        results = vector_store_service.query_private_diary(
            user_id=self.user_id, 
            query_text=query, 
            case_context_id=self.case_id
        )
        if not results:
            return "No private records found matching the query."
        return "\n\n".join([f"[SOURCE: {r['source']}]\n{r['content']}" for r in results])

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
    Use this to verify compliance, finding labor laws, tax codes, or official procedures.
    """
    from . import vector_store_service
    # PHOENIX FIX: Removed agent_type. The vector_store_service now defaults to 'business'.
    results = vector_store_service.query_public_library(query_text=query)
    if not results:
        return "No public records found."
    return "\n\n".join([f"[SOURCE: {r['source']}]\n{r['content']}" for r in results])


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        if DEEPSEEK_API_KEY:
            os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
            self.llm = ChatOpenAI(model=OPENROUTER_MODEL, base_url=OPENROUTER_BASE_URL, temperature=0.0, streaming=False)
        else:
            self.llm = None
        
        researcher_template = """
        You are a diligent business assistant. Answer the user's question in STANDARD Albanian.
        LINGUISTIC RULES: Interpret 'q' as 'ç' and 'e' as 'ë'. Use standard spelling in your actions and final answer.
        CRITICAL RULES:
        1. GROUNDING: Answer ONLY using information from the 'Observation'.
        2. NO HALLUCINATION: If no information is found, say "Nuk gjeta informacion në dokumente."

        You have access to these tools:
        {tools}

        Use this format:
        Question: the input question
        Thought: your thought process
        Action: one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (repeat Thought/Action/Observation)
        Thought: I have the final answer.
        Final Answer: the final answer

        Begin!
        Question: {input}
        Thought: {agent_scratchpad}
        """
        self.researcher_prompt = PromptTemplate.from_template(researcher_template)
        
    async def _get_case_summary(self, case_id: Optional[str]) -> str:
        try:
            if self.db is None or case_id is None: return ""
            case = await self.db.cases.find_one({"_id": ObjectId(case_id)}, {"case_name": 1, "description": 1, "summary": 1, "title": 1})
            if not case: return ""
            parts = [f"EMRI I PROJEKTIT: {case.get('title') or case.get('case_name')}", f"PËRSHKRIMI: {case.get('description')}", f"PËRMBLEDHJA: {case.get('summary')}"]
            return "\n".join(filter(None, parts))
        except Exception: return ""

    async def chat(
        self, 
        query: str, user_id: str, case_id: Optional[str]
    ) -> str:
        if not self.llm:
            return "Agent Executor is not initialized. Check API keys."

        private_tool_instance = PrivateDiaryTool(user_id=user_id, case_id=case_id)
        session_tools = [private_tool_instance, query_public_library_tool]

        researcher_agent = create_react_agent(self.llm, session_tools, self.researcher_prompt)
        researcher_executor = AgentExecutor(agent=researcher_agent, tools=session_tools, verbose=True, handle_parsing_errors=True)

        case_summary = await self._get_case_summary(case_id)
        enriched_input = f"User's Question: \"{query}\"\nCase Context:\n{case_summary}"
        
        try:
            # Step 1: Draft
            draft_response = await researcher_executor.ainvoke({"input": enriched_input})
            draft_answer = draft_response.get('output', "Asnjë draft nuk u gjenerua.")

            # Step 2: Critique
            critic_prompt = f"Review this draft. Is it grounded in the context? Does it use standard Albanian? If good, say 'OK'. If not, critique it.\n\nContext:{case_summary}\n\nDraft:{draft_answer}"
            critic_response = await self.llm.ainvoke(critic_prompt)
            critique = str(critic_response.content)

            if "OK" in critique and len(critique) < 10:
                return draft_answer

            # Step 3: Revise
            revision_prompt = f"Revise this draft based on the critique.\n\nDraft: {draft_answer}\nCritique: {critique}\n\nFinal Answer (in Standard Albanian):"
            final_response = await self.llm.ainvoke(revision_prompt)
            return str(final_response.content)

        except Exception as e:
            logger.error(f"Agent Chat Error: {e}", exc_info=True)
            return "Ndodhi një gabim gjatë procesimit të kërkesës nga agjenti."