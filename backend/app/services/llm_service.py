# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MULTILINGUAL UNLOCK
# 1. PROMPT UPDATE: Removed "STRICTLY ALBANIAN" constraint.
# 2. LOGIC: Instructs AI to match the document's language for findings.
# 3. RESULT: Works for Albanian, Serbian, English, etc. automatically.

import os
import json
import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama-3.3-70b-versatile" # Ensure we use the active model

_client: Groq | None = None

def initialize_llm_client():
    global _client
    if _client: return
    if not GROQ_API_KEY: raise ValueError("GROQ_API_KEY is not configured.")
    try:
        _client = Groq(api_key=GROQ_API_KEY)
        logger.info(f"--- [LLM Service] Groq Client Initialized for model: {GROQ_MODEL_NAME}. ---")
    except Exception as e:
        logger.critical(f"!!! CRITICAL: Failed to initialize Groq Client. Reason: {e}")
        raise

def get_llm_client() -> Groq:
    if _client is None: initialize_llm_client()
    if _client is None: raise RuntimeError("Groq client could not be initialized.")
    return _client

def generate_summary(text: str) -> str:
    llm_client = get_llm_client()
    truncated_text = text[:6000]
    # PHOENIX FIX: Dynamic Language Prompt
    prompt = f"""
    Summarize this legal document.
    - If the document is in Albanian, summarize in Albanian.
    - If the document is in Serbian/Bosnian/Croatian, summarize in that language.
    - If the document is in English, summarize in English.
    Keep it professional and concise.

    Text:
    {truncated_text}
    """
    
    try:
        completion = llm_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL_NAME,
            temperature=0.3
        )
        return completion.choices[0].message.content or "Summary unavailable."
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return "Summary unavailable."

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {"answer": "Socratic response logic is here.", "sources": []}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return [] 

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Analyzes document text to extract key legal findings.
    Auto-detects language.
    """
    llm_client = get_llm_client()
    truncated_text = text[:7500]

    system_prompt = """
    You are a precision legal analysis AI. Your task is to review a legal document and extract critical findings.
    A "finding" is a significant statement with legal implications.

    **LANGUAGE INSTRUCTION:**
    - Output the `finding_text` in the **SAME LANGUAGE** as the source document.
    - Do NOT translate the `source_text`. Keep it verbatim.

    You MUST format your response as a valid JSON object with one key: "findings". 
    The value is a list of objects with keys: "finding_text" and "source_text".

    Example JSON Structure:
    {
      "findings": [
        {
          "finding_text": "Summary of the finding in the document's language.",
          "source_text": "Exact quote from the document."
        }
      ]
    }

    If no findings are relevant, return: {"findings": []}
    """

    user_prompt = f"Here is the document text. Extract findings:\n\n---\n\n{truncated_text}"
    content = ""

    try:
        chat_completion = llm_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=GROQ_MODEL_NAME,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = chat_completion.choices[0].message.content
        if not content:
            return []
        
        response_data = json.loads(content)
        findings = response_data.get("findings", [])
        
        if isinstance(findings, list):
            return findings
        else:
            return []

    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}")
        return []
    except Exception as e:
        logger.error(f"Findings extraction error: {e}")
        return []