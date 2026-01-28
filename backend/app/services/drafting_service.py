# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V21.1 (INTEGRITY FIX)
# 1. FIX: Added missing 'datetime' and 'timezone' imports (TS-97).
# 2. ARCHITECTURE: Maintained 'Hydra Tactic' for parallel context extraction.
# 3. STATUS: Fully type-safe and production-ready.

import os
import io
import asyncio
import structlog
from datetime import datetime, timezone # PHOENIX FIX: Added missing imports
from typing import Optional, Dict, Any, List, AsyncGenerator
from pymongo.database import Database
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from ..models.user import UserInDB
from .albanian_rag_service import AlbanianRAGService
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

TEMPLATE_MAP = {
    "generic": "Strukturoje si dokument juridik formal, me hyrje, zhvillim të argumentit dhe përfundim.",
    "padi": """STRUKTURA E PADISË (STRICT): 1. KOKA, 2. HYRJE, 3. GJENDJA FAKTIKE, 4. BAZA LIGJORE, 5. PETITUMI.""",
    "pergjigje": """STRUKTURA E PËRGJIGJES NË PADI (STRICT): 1. KOKA, 2. DEKLARIM, 3. KUNDËRSHTIMET FAKTIKE, 4. KUNDËRSHTIMET LIGJORE, 5. PROPOZIM.""",
    "kunderpadi": """STRUKTURA E KUNDËRPADISË (STRICT): 1. KOKA, 2. HYRJE, 3. FAKTET E REJA, 4. DËMI, 5. LIDHJA SHKAKORE, 6. BAZA LIGJORE, 7. PETITUMI.""",
    "kontrate": """STRUKTURA E KONTRATËS (STRICT): 1. TITULLI/DATA, 2. PALËT, 3. OBJEKTI, 4. NENET, 5. ZGJIDHJA, 6. DISPOZITAT, 7. NËNSHKRIMET."""
}

async def stream_draft_generator(
    db: Database,
    user_id: str,
    case_id: Optional[str],
    draft_type: str,
    user_prompt: str
) -> AsyncGenerator[str, None]:
    """
    PHOENIX HYDRA: Fetches context in parallel and streams the draft tokens.
    """
    logger.info(f"Hydra Stream initiated for: {draft_type}")
    
    # 1. HYDRA TACTIC: Parallel Context Gathering
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, 
                          user_id=user_id, query_text=user_prompt, n_results=6, case_context_id=case_id),
        asyncio.to_thread(vector_store_service.query_global_knowledge_base, 
                          query_text=user_prompt, n_results=3)
    ]
    
    results = await asyncio.gather(*tasks)
    case_facts = results[0]
    global_laws = results[1]
    
    # 2. PREPARE REDUCE PROMPT
    context_str = "\n".join([f"- {f['text']} (Burimi: {f['source']})" for f in case_facts])
    laws_str = "\n".join([f"- {l['text']} (Burimi: {l['source']})" for l in global_laws])
    
    template_instruction = TEMPLATE_MAP.get(draft_type, TEMPLATE_MAP["generic"])
    
    system_prompt = f"""
    Ti je 'Master Litigator AI'. Detyra jote është të hartosh një {draft_type.upper()} profesionale.
    GJUHA: SHQIP. JURISDIKSIONI: KOSOVË.
    
    STRUKTURA E KËRKUAR:
    {template_instruction}
    
    KONTEKSTI NGA RASTI:
    {context_str}
    
    BAZA LIGJORE RELEVANTE:
    {laws_str}
    
    Urdhri i përdoruesit: {user_prompt}
    """
    
    # 3. STREAMING OUTPUT
    full_content = ""
    async for token in llm_service.stream_text_async(system_prompt, "Gjenero draftin e plotë ligjor tani.", temp=0.1):
        full_content += token
        yield token

    # 4. AUTO-PERSISTENCE
    if full_content.strip() and case_id:
        try:
            db.drafting_results.insert_one({
                "case_id": case_id,
                "user_id": user_id,
                "draft_type": draft_type,
                "result_text": full_content,
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Failed to auto-persist draft: {e}")

async def generate_draft(
    db: Database,
    user_id: str,
    case_id: Optional[str],
    draft_type: str,
    user_prompt: str,
) -> str:
    """
    Legacy/Sync compatibility: Aggregates the stream into a single string.
    """
    content = []
    async for chunk in stream_draft_generator(db, user_id, case_id, draft_type, user_prompt):
        content.append(chunk)
    return "".join(content)

def generate_objection_document(analysis_result: Dict[str, Any], case_title: str) -> bytes:
    document = Document()
    style = document.styles['Normal']
    font = style.font; font.name = 'Times New Roman'; font.size = Pt(12) # type: ignore
    header = document.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("GJYKATA THEMELORE PRISHTINË\n"); run.bold = True; run.font.size = Pt(14)
    header.add_run("Departamenti i Përgjithshëm - Divizioni Civil")
    document.add_paragraph(f"LËNDA: {case_title}")
    document.add_paragraph("_" * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("\nI/E Nderuar Gjykatës,")
    intro = document.add_paragraph("Përmes kësaj parashtrese paraqesim KUNDËRSHTIM.")
    if analysis_result.get("contradictions"):
        document.add_heading("I. KUNDËRSHTIMET", level=1)
        for c in analysis_result["contradictions"]: document.add_paragraph(c, style='List Bullet')
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()