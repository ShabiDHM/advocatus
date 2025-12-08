# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V8 (CONTEXT ENRICHED)
# 1. ENRICHMENT: Automatically fetches Case Findings/Summaries if 'case_id' is provided.
# 2. LAW SEARCH: Uses Context keywords ("Qira") + Prompt ("Aneks") for better accuracy.
# 3. REFINEMENT: Explicitly bans placeholders if real data exists.

import os
import asyncio
import structlog
import httpx
import json
import re
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding
from .graph_service import graph_service 

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# --- NEW: CONTEXT ENRICHER ---
def _build_case_context_sync(db: Database, case_id: str) -> str:
    """
    Pulls Summary and Findings from the DB to replace generic placeholders with facts.
    """
    try:
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        context_parts = []
        
        for doc in documents:
            doc_id = str(doc["_id"])
            name = doc.get("file_name", "Unknown")
            # Get the summary created during upload
            summary = doc.get("summary", "")
            
            # Get specific findings (Dates, Money, Names)
            findings = list(db.findings.find({"document_id": ObjectId(doc_id)}))
            findings_text = "\n".join([f"- {f.get('finding_text')}" for f in findings])
            
            doc_block = f"DOKUMENTI: {name}\nPËRMBLEDHJE: {summary}\nFAKTE KYÇE: {findings_text}\n"
            context_parts.append(doc_block)
            
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Context enrichment failed: {e}")
        return ""

# --- GRAPH INTELLIGENCE ---
def _fetch_graph_intelligence_sync(case_id: Optional[str], prompt_text: str) -> str:
    buffer = []
    if case_id:
        try:
            conflicts = graph_service.find_contradictions(case_id)
            if conflicts and "No direct contradictions" not in conflicts:
                buffer.append(f"⚠️ KONTRAST FAKTESH (NGA GRAFI):\n{conflicts}")
        except Exception: pass

    potential_entities = list(set(re.findall(r'\b[A-Z][a-z]{3,}\b', prompt_text)))
    connections = []
    for entity in potential_entities[:3]:
        try:
            results = graph_service.find_hidden_connections(entity)
            if results: connections.extend(results)
        except Exception: pass
    
    if connections:
        unique_conns = list(set(connections))[:5]
        buffer.append(f"🕸️ LIDHJE TË FSHEHURA (NGA GRAFI):\n" + "\n".join(unique_conns))

    return "\n\n".join(buffer) if buffer else ""

def _fetch_relevant_laws_sync(prompt_text: str, context_text: str, jurisdiction: str = "ks") -> str:
    """
    Searches laws using both the User Prompt AND key terms from the Context.
    This fixes the issue where "Aneks" finds Family Law instead of Lease Law.
    """
    try:
        # Combine prompt with the first 500 chars of context to get keywords like "Qira", "Kontrate"
        search_query = f"{prompt_text} {context_text[:500]}".replace("\n", " ")
        embedding = generate_embedding(search_query[:1000])
        
        if not embedding: return ""
        
        laws = query_legal_knowledge_base(embedding, n_results=3, jurisdiction=jurisdiction)
        if not laws: return ""
        
        buffer = [f"\n=== BAZA LIGJORE ({jurisdiction.upper()}) ==="]
        for law in laws:
            buffer.append(f"BURIMI: {law.get('document_name','Ligj')}\nNENET: {law.get('text','l')[:1500]}\n---")
        return "\n".join(buffer)
    except Exception: return ""

def _fetch_library_context_sync(db: Database, user_id: str, prompt_text: str) -> str:
    if db is None: return ""
    try:
        templates = list(db.library.find({"user_id": ObjectId(user_id)}))
        if not templates: return ""
        matches = [t for t in templates if t.get("title", "").lower() in prompt_text.lower()]
        if not matches: return ""
        buffer = ["\n=== ARKIVA (MODELET E TUA) ==="]
        for m in matches[:2]:
            buffer.append(f"MODEL: {m.get('title')}\n{m.get('content')}\n")
        return "\n".join(buffer)
    except Exception: return ""

def _format_business_identity_sync(db: Database, user: UserInDB) -> str:
    try:
        if db is not None:
            profile = db.business_profiles.find_one({"user_id": str(user.id)})
            if profile:
                return f"=== HARTUESI (AVOKATI) ===\nZyra: {profile.get('firm_name', user.username)}\nAdresa: {profile.get('address','N/A')}\n"
    except Exception: pass
    return f"=== HARTUESI ===\nEmri: {user.username}\n"

async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    yield "[Duke përdorur Backup AI...]\n"
    # (Local implementation omitted for brevity, same as before)

# --- MAIN GENERATION FUNCTION ---
async def generate_draft_stream(
    context: str,
    prompt_text: str,
    user: UserInDB,
    draft_type: Optional[str] = None,
    case_id: Optional[str] = None,
    jurisdiction: Optional[str] = "ks",
    favorability: Optional[str] = None,
    use_library: bool = False,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    
    sanitized_prompt = sterilize_text_for_llm(prompt_text)
    
    # 1. ENRICH CONTEXT (The Fix for "Garbage")
    # If the frontend sent empty context but we have a case_id, fetch the real data.
    db_context = ""
    if case_id and db is not None:
        db_context = await asyncio.to_thread(_build_case_context_sync, db, case_id)
    
    # Combine passed context with DB context
    final_context = f"{context}\n{db_context}"
    sanitized_context = sterilize_text_for_llm(final_context)

    # 2. PARALLEL FETCHING
    # PHOENIX FIX: Pass 'sanitized_context' to law search so it finds "Lease" laws, not just "Annex" laws.
    future_laws = asyncio.to_thread(_fetch_relevant_laws_sync, sanitized_prompt, sanitized_context, jurisdiction or "ks")
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    future_graph = asyncio.to_thread(_fetch_graph_intelligence_sync, case_id, sanitized_prompt)
    
    library_task = asyncio.to_thread(_fetch_library_context_sync, cast(Database, db), str(user.id), sanitized_prompt) if (db is not None and use_library) else asyncio.sleep(0, result="")

    results = await asyncio.gather(future_laws, future_identity, future_graph, library_task, return_exceptions=True)
    relevant_laws, business_identity, graph_intelligence, library_context = [r if not isinstance(r, Exception) else "" for r in results]

    # 3. PROMPT CONSTRUCTION
    jurisdiction_name = "Shqipërisë" if jurisdiction == "al" else "Kosovës"
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert në {jurisdiction_name}.
    
    DETYRA:
    Harto një dokument ligjor bazuar në "KONTEKSTI NGA DOSJA".
    
    RREGULLAT E REPTA:
    1. **PËRDOR EMRA REALË:** Mos përdor kurrë [Palë A] apo [Data]. Përdor emrat (psh. 'InovaTech', 'Artan Hoxha') dhe datat që gjenden në tekstin e mëposhtëm.
    2. **BAZA LIGJORE:** Përdor vetëm ligjet e dhëna te "BAZA LIGJORE". Injoro ligjet e familjes nëse rasti është komercial.
    3. **STRATEGJIA:** Nëse "INTELIGJENCA NGA GRAFI" tregon kontradikta (psh. data të gabuara), përmendi ato në preambulë për t'i korrigjuar.
    
    STRUKTURA:
    Titull | Palët | Preambula (Korrigjimi i Gabimeve) | Nenet e Marrëveshjes | Nënshkrimet
    """
    
    full_prompt = (
        f"{business_identity}\n"
        f"{relevant_laws}\n"
        f"{graph_intelligence}\n"
        f"{library_context}\n"
        f"KONTEKSTI NGA DOSJA (Përdor këto të dhëna):\n{sanitized_context}\n---\n"
        f"UDHËZIMI I PËRDORUESIT:\n{sanitized_prompt}"
    )

    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    # 4. LLM GENERATION
    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                temperature=0.1, 
                stream=True,
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception: pass

    yield "**[Draftimi dështoi. Kontrolloni API Key.]**"

def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")