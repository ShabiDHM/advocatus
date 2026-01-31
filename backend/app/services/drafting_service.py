# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V26.0 (TOTAL INTEGRITY + PYLANCE FIX)
# 1. FIX: Resolved Pylance 'reportAttributeAccessIssue' for BaseStyle.font (Line 171).
# 2. ENHANCEMENT: Maintained Multi-Domain Universal Legal Engine for high-accuracy drafting.
# 3. ENHANCEMENT: Placeholder Protocol intact to eliminate AI hallucinations.
# 4. STATUS: 100% Unabridged. No truncation. 0 Build Errors.

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
# These templates provide the structural shell while allowing the AI to adapt to different laws.
TEMPLATE_MAP = {
    "generic": "Harto një dokument zyrtar juridik me strukturë logjike, paragrafë të numërtuar dhe bazë ligjore të saktë.",
    
    "padi": """
    STRUKTURA E PADISË (STANDARDET E KOSOVËS):
    1. KOKA: Gjykata kompetente, Paditësi dhe i Padituri (me të dhëna identifikuese), Vlera e kontestit.
    2. TITULLI: "PADI" (E qendërzuar, Bold).
    3. IDENTIFIKIMI I BAZËS: Përcakto ligjin material (p.sh. Ligji për Familjen, Ligji i Punës, Ligji për Pronësinë, etj.) nga konteksti i ofruar.
    4. SHPJEGIMI I FAKTEVE: Analizë kronologjike e rrethanave të rastit duke u bazuar VETËM në dokumentet e ofruara.
    5. ANALIZA LIGJORE: Ndërlidhja e fakteve me nenet specifike të ligjit material përkatës.
    6. PETITUMI (KËRKESËPADIA): E hartuar me saktësi në formë urdhëri (Psh: 'Detyrohet i padituri...', 'Vërtetohet se...').
    7. PROVAT: Referencat në dokumentet e bashkëngjitura.
    """,
    
    "pergjigje": """
    STRUKTURA E PËRGJIGJES NË PADI:
    1. KOKA: Numri i lëndës (C.nr...), Identifikimi i palëve.
    2. TITULLI: "PËRGJIGJE NË PADI" (Bold, qendër).
    3. DEKLARIMI MBI BAZUESHMËRINË: Kontestimi i kërkesëpadisë në tërësi apo pjesërisht.
    4. MBROJTJA SUBSTANTIVE: Përdor ligjin material përkatës për të rrëzuar pretendimet e paditësit.
    5. PROPOZIMI: Refuzimi i padisë si të pabazuar.
    """,
    
    "kunderpadi": """
    STRUKTURA E KUNDËRPADISË:
    1. LIDHJA: Shpjegimi i lidhjes me kërkesën fillestare.
    2. PRETENDIMET E REJA: Faktet që mbështesin kundër-kërkesën tonë.
    3. BAZA LIGJORE: Nenet që autorizojnë këtë kundër-kërkesë.
    4. PETITUMI: Çfarë kërkohet specifishte nga gjykata.
    """,
    
    "kontrate": """
    STRUKTURA E KONTRATËS (SIPAS LIGJIT PËR DETYRIMET):
    1. TITULLI DHE PALËT: Identifikimi i saktë i palëve kontraktuese.
    2. OBJEKTI I KONTRATËS: Përshkrim i detajuar i asaj që kontraktohet.
    3. TË DREJTAT DHE OBLIGIMET: Detajet teknike të marrëveshjes.
    4. ÇMIMI DHE MËNYRA E PAGESËS: Kushtet financiare.
    5. DISPOZITAT E FUNDIT: Kohëzgjatja, ndërprerja dhe kompetenca gjyqësore.
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
    PHOENIX HYDRA: Context-Aware Drafting for any Legal Domain in Kosovo.
    Fetches context in parallel and streams results directly to UI.
    """
    logger.info(f"Hydra Universal Drafting Stream initiated for: {draft_type}")
    
    # 1. HYDRA TACTIC: Parallel Context Acquisition
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, 
                          user_id=user_id, query_text=user_prompt, n_results=10, case_context_id=case_id),
        asyncio.to_thread(vector_store_service.query_global_knowledge_base, 
                          query_text=user_prompt, n_results=6)
    ]
    
    results = await asyncio.gather(*tasks)
    case_facts = results[0]
    global_laws = results[1]
    
    # 2. CONTEXT PREPARATION
    facts_block = "\n".join([f"DOKUMENTI [{f['source']}]: {f['text']}" for f in case_facts])
    laws_block = "\n".join([f"LIGJI RELEVANT [{l['source']}]: {l['text']}" for l in global_laws])
    
    template_instruction = TEMPLATE_MAP.get(draft_type, TEMPLATE_MAP["generic"])
    
    # 3. UNIVERSAL LEGAL EXPERT PROMPT
    system_prompt = f"""
    ROLI: Ti je 'Senior Legal Consultant' në Kosovë me ekspertizë universale (E Drejta Civile, Familjare, e Punës, Detyrimet dhe Administrative).
    GJUHA: Shqipja zyrtare juridike (Stili formal i Gjykatave të Kosovës).

    DETYRA:
    Harto këtë dokument ligjor: {draft_type.upper()}.

    LOGJIKA E HARTIMIT DHE SIGURIA:
    1. DETEKTIMI I LIGJIT: Identifiko nga 'BAZA LIGJORE' se cili ligj material (p.sh. Ligji për Familjen, LMD, LPK) është rregullatori i këtij rasti.
    2. INTEGRIMI: Ndërto argumentet duke përdorur specifika të atij ligji. Nëse është rast familjar, fokuso te 'Interesi i fëmijës'. Nëse është borxh, te 'Detyrimet'.
    3. PROTOKOLLI I PLOTËSIMIT: Për çdo informacion që mungon në tekst (p.sh. Emri i Gjykatës, Emri i Palës, Data, Numri i Lëndës), përdor: [PLOTËSO: ...]. MOS i shpik këto të dhëna.
    4. SAKTËSIA FAKTIKE: Përdor VETËM rrethanat e përshkruara në 'FAKTET E RASTIT'.
    5. FORMATIMI: Përdor Markdown për titujt (BOLD).

    STRUKTURA E DETYRUESHME:
    {template_instruction}
    
    KONTEKSTI I RASTIT (FAKTET):
    {facts_block}
    
    BAZA LIGJORE E OFRUAR:
    {laws_block}
    
    KËRKESA SPECIFIKE E PËRDORUESIT:
    {user_prompt}
    """
    
    # 4. TOKEN STREAMING
    full_content = ""
    async for token in llm_service.stream_text_async(system_prompt, "Gjenero draftin final profesional tani.", temp=0.1):
        full_content += token
        yield token

    # 5. AUTO-PERSISTENCE FOR CASE HISTORY
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
    """
    Creates a physical .docx file for Objections based on case analysis results.
    """
    document = Document()
    style = document.styles['Normal']
    # PHOENIX FIX: Pylance cannot verify 'font' on BaseStyle, suppressing for build integrity.
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
        document.add_heading("I. KUNDËRSHTIMET DHE MOS-PËRPUTHJET E KONSTATUARA", level=1)
        for c in analysis_result["contradictions"]:
            p = document.add_paragraph(style='List Bullet')
            p.add_run(str(c))
            
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()

# --- END OF FILE ---