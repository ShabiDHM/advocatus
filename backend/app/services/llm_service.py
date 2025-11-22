# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - HYBRID ENGINE (Groq + Local Ollama)
# 1. ROUTER: Summaries -> Local Llama3 (Free). Findings -> Groq (High IQ).
# 2. FALLBACK: If Local LLM fails, auto-switch to Groq.
# 3. COST: Reduces API usage by ~60%.

import os
import json
import logging
import httpx
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama-3.3-70b-versatile" 

# Local LLM Config (Internal Docker Network)
OLLAMA_URL = "http://local-llm:11434/api/generate"
LOCAL_MODEL_NAME = "llama3"

_client: Groq | None = None

def initialize_llm_client():
    global _client
    if _client: return
    if not GROQ_API_KEY: 
        # We don't raise error yet, allowing local-only mode if needed
        logger.warning("GROQ_API_KEY not set. Cloud features will fail.")
        return
    try:
        _client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.critical(f"Failed to initialize Groq Client: {e}")

def get_llm_client() -> Groq:
    if _client is None: initialize_llm_client()
    if _client is None: raise RuntimeError("Groq client unavailable.")
    return _client

# --- LOCAL LLM ENGINE (The Free Brain) ---
def _call_local_llm(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama instance.
    Returns the generated text or raises an exception on failure.
    """
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": 4096 
            }
        }
        
        # 30s timeout should be enough for a summary
        with httpx.Client(timeout=45.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
            
    except Exception as e:
        logger.warning(f"⚠️ Local LLM Failed (Switching to Cloud): {e}")
        raise e

# --- HYBRID FUNCTIONS ---

def generate_summary(text: str) -> str:
    """
    HYBRID STRATEGY: 
    1. Try Local LLM (Free)
    2. Fallback to Groq (Paid)
    """
    truncated_text = text[:6000]
    
    prompt = f"""
    You are a professional legal assistant.
    Summarize the following legal document in a concise, professional manner.
    
    CRITICAL INSTRUCTION:
    - If the text is Albanian, write the summary in Albanian.
    - If the text is English, write the summary in English.
    - If the text is Serbian, write the summary in Serbian.
    
    Document Text:
    {truncated_text}
    """
    
    # ATTEMPT 1: LOCAL BRAIN (Free)
    try:
        logger.info("🤖 routing to Local LLM (Llama3)...")
        summary = _call_local_llm(prompt)
        if summary:
            logger.info("✅ Local LLM Success.")
            return summary
    except Exception:
        pass # Fall through to Cloud

    # ATTEMPT 2: CLOUD BRAIN (Paid)
    try:
        logger.info("☁️ Routing to Groq Cloud (Fallback)...")
        llm_client = get_llm_client()
        completion = llm_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL_NAME,
            temperature=0.3
        )
        return completion.choices[0].message.content or "Summary unavailable."
    except Exception as e:
        logger.error(f"❌ All LLMs failed for summary: {e}")
        return "Summary unavailable."

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    STRATEGY: Always use Cloud (Groq) for Findings.
    Reasoning: Extracting JSON Findings requires high precision (Smart IQ).
    Local 8B models often mess up the JSON format.
    """
    llm_client = get_llm_client()
    truncated_text = text[:7500]

    system_prompt = """
    You are a precision legal analysis AI. Your task is to review a legal document and extract critical findings.
    
    **LANGUAGE INSTRUCTION:**
    - Output the `finding_text` in the **SAME LANGUAGE** as the source document.
    - Do NOT translate the `source_text`. Keep it verbatim.

    You MUST format your response as a valid JSON object with one key: "findings". 
    The value is a list of objects with keys: "finding_text" and "source_text".

    Example: {"findings": [{"finding_text": "...", "source_text": "..."}]}
    """

    user_prompt = f"Extract findings from:\n\n{truncated_text}"

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
        if not content: return []
        
        response_data = json.loads(content)
        return response_data.get("findings", []) or []

    except Exception as e:
        logger.error(f"Findings extraction error: {e}")
        return []

# Legacy stubs
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {"answer": "Socratic response logic.", "sources": []}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []