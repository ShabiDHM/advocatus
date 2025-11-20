# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - LANGUAGE ENFORCEMENT FIX
# 1. PROMPT ENGINEERING: Explicitly instructs the LLM to output findings in ALBANIAN.
# 2. SYSTEM PROMPT: Added "LANGUAGE INSTRUCTION" section to override English bias.
# 3. DEFINITION: Ensures 'extract_findings_from_text' is clearly defined.

import os
import json
import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama-3.1-8b-instant" 

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
    prompt = f"Summarize this legal document in Albanian (Shqip). Keep it professional and concise.\n\nText:\n{truncated_text}"
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
    # Logic moved to deadline_service.py, kept for interface compatibility
    return [] 

# --- PHOENIX PROTOCOL: ALBANIAN LANGUAGE ENFORCEMENT ---
def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Analyzes document text to extract key legal findings.
    FORCES output in ALBANIAN.
    """
    llm_client = get_llm_client()
    truncated_text = text[:7500]

    system_prompt = """
    You are a precision legal analysis AI. Your single task is to review a legal document and extract critical findings.
    A "finding" is a significant statement with legal implications (e.g., obligations, duties, risk assignments).

    **LANGUAGE INSTRUCTION: STRICTLY ALBANIAN**
    The `finding_text` MUST be written in ALBANIAN (Shqip), regardless of the input document's language.
    The `source_text` must be the exact, verbatim text from the document (do not translate the source).

    For each finding, provide:
    1.  `finding_text`: The core statement of the finding, summarized concisely in ALBANIAN.
    2.  `source_text`: The exact, verbatim source text from the document that supports the finding.

    You MUST format your entire response as a single, valid JSON object. This object must have one key: "findings". 
    The value of "findings" must be a list of objects. Each object must have two keys: "finding_text" and "source_text".

    Example of a valid response:
    {
      "findings": [
        {
          "finding_text": "Qiramarrësit i kërkohet të dorëzojë mallrat brenda 30 ditëve.",
          "source_text": "Party A hereby agrees and covenants to deliver the aforementioned goods to Party B no later than thirty (30) calendar days..."
        }
      ]
    }

    If you find no relevant legal findings, you MUST return a JSON object with an empty list: {"findings": []}
    Do not add any commentary or introductory text outside of the JSON structure. Your entire output must be the JSON object itself.
    """

    user_prompt = f"Here is the document text. Please extract the findings:\n\n---\n\n{truncated_text}"
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
            logger.warning("--- [LLM Service] Groq API returned no content for findings extraction. ---")
            return []
        
        response_data = json.loads(content)
        findings = response_data.get("findings", [])
        
        if isinstance(findings, list):
            return findings
        else:
            logger.error(f"--- [LLM Service] Findings extraction did not return a list. Received data: {findings} ---")
            return []

    except json.JSONDecodeError as e:
        logger.error(f"--- [LLM Service] Failed to decode JSON from Groq for findings extraction: {e}. Raw content: '{content}' ---")
        return []
    except Exception as e:
        logger.error(f"--- [LLM Service] An unexpected error occurred during findings extraction: {e} ---", exc_info=True)
        return []