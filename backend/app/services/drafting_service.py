# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA DRAFTING V27.4 (POLYMATH DOMAIN LOGIC)
# 1. LOGIC: Replaced hardcoded Family Law logic with "Polymath" Dynamic Domain Recognition.
# 2. CODEX: Integrated Kosovo's Full Legislative Matrix (Criminal, Civil, Admin) into System Context.
# 3. ACCURACY: AI now explicitly differentiates between Procedural (LPK/KPP) and Material Law.
# 4. STATUS: Ready for Multi-Domain Operations.

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
    STRUKTURA E PADISË (CIVILE / FAMILJARE / EKONOMIKE):
    1. KOKA: Gjykata, Palët, Vlera e kontestit.
    2. TITULLI: "PADI" (E qendërzuar, Bold).
    3. BAZA JURIDIKE: Përcakto saktë ligjin material sipas natyrës së rastit.
    4. SHPJEGIMI I FAKTEVE: Analizë kronologjike.
    5. ANALIZA LIGJORE: Ndërlidhja e fakteve me nenet specifike.
    6. PETITUMI: Kërkesa e saktë (p.sh. "Të aprovohet padia...").
    7. PROVAT: Lista e dëshmive.
    """,
    
    "pergjigje": """
    STRUKTURA E PËRGJIGJES NË PADI:
    1. KOKA: Numri i lëndës, Palët.
    2. TITULLI: "PËRGJIGJE NË PADI".
    3. DEKLARIMI: Kontestimi i bazueshmërisë (Në tërësi ose pjesërisht).
    4. KUNDËR-ARGUMENTET: Përdor ligjin material për të rrëzuar pretendimet.
    5. PROPOZIMI: Refuzimi i kërkesëpadisë.
    """,
    
    "kunderpadi": """
    STRUKTURA E KUNDËRPADISË:
    1. LIDHJA: Lidhja me padinë kryesore (Connexity).
    2. PRETENDIMET E REJA: Faktet e reja që ndryshojnë gjendjen.
    3. BAZA LIGJORE: Ligji për Procedurën Kontestimore + Ligji Material.
    4. PETITUMI: Kërkesa specifike kundër paditësit.
    """,
    
    "kontrate": """
    STRUKTURA E KONTRATËS:
    1. HYRJE: Palët dhe data.
    2. NENI 1: Objekti i Kontratës.
    3. NENI X: Çmimi / Pagesa (nëse aplikohet).
    4. NENI Y: Të drejtat dhe detyrimet.
    5. NENI Z: Zgjidhja e mosmarrëveshjeve.
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
    PHOENIX HYDRA DRAFTING: Multi-Domain Contextual Generation.
    """
    logger.info(f"Hydra Drafting initiated", type=draft_type, user=user_id)
    
    # 1. HYDRA TACTIC: Parallel Context Acquisition
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
        yield "**[GABIM: Dështoi mbledhja e fakteve dhe bazës ligjore.]**"
        return
    
    # 2. CONTEXT SYNTHESIS
    facts_block = "\n".join([f"- **DOKUMENTI [{f.get('source', 'E Panjohur')}]:** {f.get('text', '')}" for f in case_facts])
    laws_block = "\n".join([f"- **LIGJI RELEVANT [{l.get('source', 'E Panjohur')}]:** {l.get('text', '')}" for l in global_laws])
    
    template_instruction = TEMPLATE_MAP.get(draft_type, TEMPLATE_MAP["generic"])
    
    # 3. THE "POLYMATH" PERSONA (Dynamic Domain Logic)
    system_prompt = f"""
    ROLI: Ti je 'Senior Legal Partner' në Kosovë. Je ekspert në të gjitha fushat ligjore.
    DETYRA: Harto dokumentin ligjor: {draft_type.upper()}.

    HAPI 1: DIAGNOSTIFIKIMI I FUSHËS (DO TË ZGJEDHËSH VETËM NJË):
    
    A. FUSHA PENALE (CRIMINAL):
       - Nëse rasti përfshin vepra penale, dhunë, vjedhje, kanosje.
       - LIGJET KRYESORE: **[Kodi Penal i Kosovës 06/L-074](doc://ligji)** dhe **[Kodi i Procedurës Penale 08/L-032](doc://ligji)**.
       
    B. FUSHA CIVILE - FAMILJARE (FAMILY):
       - Nëse rasti përfshin shkurorëzim, alimentacion, kujdestari, trashëgimi.
       - LIGJET KRYESORE: **[Ligji Nr. 2004/32 Për Familjen e Kosovës](doc://ligji)** dhe **[LPK - Ligji Nr. 03/L-006](doc://ligji)**.
       
    C. FUSHA CIVILE - DETYRIME/KONTRAKTUALE (OBLIGATIONS):
       - Nëse rasti përfshin borxhe, kontrata, dëme materiale.
       - LIGJET KRYESORE: **[Ligji Nr. 04/L-077 Për Marrëdhëniet e Detyrimeve (LMD)](doc://ligji)**.
       
    D. FUSHA ADMINISTRATIVE:
       - Nëse rasti përfshin vendime të shtetit, ministrive, komunave.
       - LIGJET KRYESORE: **[Ligji Nr. 05/L-031 Për Procedurën e Përgjithshme Administrative](doc://ligji)**.

    HAPI 2: ZBATIMI I RREPTË:
    - Mos përdor ligje penale në raste civile (përveç nëse ka elemente penale).
    - Mos përdor ligje të vjetra (UNMIK) nëse ka ligje të reja të Republikës së Kosovës.
    - Cito ligjin saktësisht me formatin vizual.

    UDHËZIME PËR FORMATIMIN VIZUAL:
    - **CITIMET LIGJORE DUHEN THEKSUAR**: Përdor gjithmonë formatin: `[Emri i Ligjit/Neni](doc://ligji)`.
    - **TITUJT**: Përdor **Bold** dhe ### Titujt.

    STRUKTURA E KËRKUAR:
    {template_instruction}
    
    KONTEKSTI I RASTIT (FAKTET NGA DOSJA):
    {facts_block}
    
    BAZA LIGJORE (SUGJERIME NGA BAZA E TË DHËNAVE):
    {laws_block}
    
    KËRKESA SHTESË E PËRDORUESIT (FOKUSI):
    {user_prompt}
    """
    
    # 4. THROTTLED TOKEN STREAMING
    full_content = ""
    try:
        async for token in llm_service.stream_text_async(system_prompt, "Filloni analizën e fushës dhe pastaj hartimin.", temp=0.2):
            full_content += token
            yield token
    except Exception as e:
        logger.error(f"Hydra Stream Generation Failed: {e}")
        yield f"\n**[GABIM KRITIK GJATË GJENERIMIT: {str(e)}]**"

    # 5. ASYNC PERSISTENCE
    if full_content.strip() and case_id:
        try:
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