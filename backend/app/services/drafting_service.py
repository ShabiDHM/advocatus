# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA DRAFTING V27.0
# 1. HYDRA: Parallelized context acquisition optimized for 8-core execution.
# 2. STABILITY: Integrated with V68.0 Global Semaphore to prevent API starvation.
# 3. PERSONA: Hardened "Senior Legal Partner" logic with Substantive Law Priority.
# 4. STATUS: 100% Unabridged. Async-optimized.

import os
import io
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, AsyncGenerator
from pymongo.database import Database
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Preserving original project imports for system compatibility
from ..models.user import UserInDB
from .albanian_rag_service import AlbanianRAGService
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

# --- UNIVERSAL LEGAL BLUEPRINTS (MULTI-DOMAIN) ---
TEMPLATE_MAP = {
    "generic": "Harto një dokument zyrtar juridik me strukturë logjike, paragrafë të numërtuar dhe bazë ligjore të saktë.",
    
    "padi": """
    STRUKTURA E PADISË (STANDARDET E KOSOVËS):
    1. KOKA: Gjykata kompetente, Paditësi dhe i Padituri, Vlera e kontestit.
    2. TITULLI: "PADI" (E qendërzuar, Bold).
    3. IDENTIFIKIMI I BAZËS: Përcakto ligjin material (Familja, Puna, Detyrimet, etj.) nga konteksti.
    4. SHPJEGIMI I FAKTEVE: Analizë kronologjike e rrethanave të rastit.
    5. ANALIZA LIGJORE: Ndërlidhja e fakteve me nenet specifike të ligjit material.
    6. PETITUMI (KËRKESËPADIA): E hartuar me saktësi në formë urdhëri.
    7. PROVAT: Referencat në dokumentet e bashkëngjitura.
    """,
    
    "pergjigje": """
    STRUKTURA E PËRGJIGJES NË PADI:
    1. KOKA: Numri i lëndës (C.nr...), Identifikimi i palëve.
    2. TITULLI: "PËRGJIGJE NË PADI" (Bold, qendër).
    3. DEKLARIMI MBI BAZUESHMËRINË: Kontestimi i kërkesëpadisë.
    4. MBROJTJA SUBSTANTIVE: Përdor ligjin material përkatës për të rrëzuar pretendimet.
    5. PROPOZIMI: Refuzimi i padisë si të pabazuar.
    """,
    
    "kunderpadi": """
    STRUKTURA E KUNDËRPADISË:
    1. LIDHJA: Shpjegimi i lidhjes me kërkesën fillestare.
    2. PRETENDIMET E REJA: Faktet mbështetëse.
    3. BAZA LIGJORE: Nenet autorizuese.
    4. PETITUMI: Kërkesa specifike.
    """,
    
    "kontrate": """
    STRUKTURA E KONTRATËS (SIPAS LIGJIT PËR DETYRIMET):
    1. TITULLI DHE PALËT: Identifikimi i saktë i palëve kontraktuese.
    2. OBJEKTI I KONTRATËS: Përshkrim i detajuar.
    3. TË DREJTAT DHE OBLIGIMET: Detajet teknike të marrëveshjes.
    4. DISPOZITAT E FUNDIT: Kohëzgjatja dhe kompetenca gjyqësore.
    """
}

async def stream_draft_generator(
    db: Database,
    user_id: str,
    case_id: Optional[str],
    draft_type: str,
    user_prompt: str
) -> AsyncGenerator[str, None]:
    """
    PHOENIX HYDRA DRAFTING: Non-blocking context synthesis and generation.
    Utilizes parallel vector threads and throttled async LLM streaming.
    """
    logger.info(f"Hydra Drafting initiated", type=draft_type, user=user_id)
    
    # 1. HYDRA TACTIC: Parallel Context Acquisition (CPU & I/O Parallelism)
    # We use to_thread because vector queries are often blocking/synchronous drivers
    tasks = [
        asyncio.to_thread(
            vector_store_service.query_case_knowledge_base, 
            user_id=user_id, query_text=user_prompt, n_results=10, case_context_id=case_id
        ),
        asyncio.to_thread(
            vector_store_service.query_global_knowledge_base, 
            query_text=user_prompt, n_results=8
        )
    ]
    
    try:
        results = await asyncio.gather(*tasks)
        case_facts = results[0]
        global_laws = results[1]
    except Exception as e:
        logger.error(f"Hydra Context Acquisition Failed: {e}")
        yield "[GABIM: Dështoi mbledhja e fakteve dhe bazës ligjore.]"
        return
    
    # 2. CONTEXT SYNTHESIS
    facts_block = "\n".join([f"DOKUMENTI [{f.get('source', 'E Panjohur')}]: {f.get('text', '')}" for f in case_facts])
    laws_block = "\n".join([f"LIGJI RELEVANT [{l.get('source', 'E Panjohur')}]: {l.get('text', '')}" for l in global_laws])
    
    template_instruction = TEMPLATE_MAP.get(draft_type, TEMPLATE_MAP["generic"])
    
    # 3. THE PARTNER PERSONA (V68.0 ALIGNED)
    system_prompt = f"""
    ROLI: Ti je 'Senior Legal Partner' me përvojë 20-vjeçare në Gjykata e Kosovës.
    DETYRA: Harto dokumentin ligjor: {draft_type.upper()}.
    PRIORITETI: LIGJI MATERIAL (SUBSTANTIV) është thelbi i argumentit.

    UDHËZIME TË RREPTA:
    1. GJUHA: Shqipe profesionale juridike (Akademike dhe Formale).
    2. PROTOKOLLI I PLOTËSIMIT: Për çdo të dhënë që mungon, përdor VETËM: [PLOTËSO: ...].
    3. ZERO-TRUST: Përdor vetëm faktet nga 'KONTEKSTI I RASTIT' më poshtë.
    4. CITIMI: Çdo nen i cituar duhet të ndjekë formatin: [Emri i Ligjit, Neni X].

    STRUKTURA E KËRKUAR:
    {template_instruction}
    
    KONTEKSTI I RASTIT (FAKTET):
    {facts_block}
    
    BAZA LIGJORE (LIGJI MATERIAL):
    {laws_block}
    
    KËRKESA SHTESË:
    {user_prompt}
    """
    
    # 4. THROTTLED TOKEN STREAMING
    # This automatically respects the 10-call Global Semaphore in llm_service.py
    full_content = ""
    try:
        async for token in llm_service.stream_text_async(system_prompt, "Filloni hartimin e draftit tani.", temp=0.1):
            full_content += token
            yield token
    except Exception as e:
        logger.error(f"Hydra Stream Generation Failed: {e}")
        yield f"\n[GABIM KRITIK GJATË GJENERIMIT: {str(e)}]"

    # 5. ASYNC PERSISTENCE
    if full_content.strip() and case_id:
        try:
            # Wrap DB call in thread to avoid blocking loop
            await asyncio.to_thread(
                db.drafting_results.insert_one,
                {
                    "case_id": case_id,
                    "user_id": user_id,
                    "draft_type": draft_type,
                    "result_text": full_content,
                    "status": "COMPLETED",
                    "created_at": datetime.now(timezone.utc)
                }
            )
        except Exception as e:
            logger.error(f"Persistence Error: {e}")

async def generate_draft(
    db: Database,
    user_id: str,
    case_id: Optional[str],
    draft_type: str,
    user_prompt: str,
) -> str:
    """Compatibility layer for sequential processing."""
    content = []
    async for chunk in stream_draft_generator(db, user_id, case_id, draft_type, user_prompt):
        content.append(chunk)
    return "".join(content)

def generate_objection_document(analysis_result: Dict[str, Any], case_title: str) -> bytes:
    """Generates physical .docx with build integrity fix."""
    document = Document()
    style = document.styles['Normal']
    font = style.font # type: ignore
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    header = document.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("GJYKATA THEMELORE NË PRISHTINË\n")
    run.bold = True
    run.font.size = Pt(14)
    header.add_run("Departamenti përkatës sipas kompetencës lëndore")
    
    document.add_paragraph(f"LËNDA: {case_title}")
    document.add_paragraph("_" * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    document.add_paragraph("\nKUNDËRSHTIM")
    
    if analysis_result.get("contradictions"):
        document.add_heading("I. KUNDËRSHTIMET E KONSTATUARA", level=1)
        for c in analysis_result["contradictions"]:
            p = document.add_paragraph(style='List Bullet')
            p.add_run(str(c))
            
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()