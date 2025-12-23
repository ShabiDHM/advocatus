# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V17.3 (MULTI-TENANT COMPATIBILITY)
# 1. FIXED: Replaced missing imports with 'query_mixed_intelligence'.
# 2. LOGIC: Implements Dual-Brain RAG (Private Documents + Public Laws) in one call.
# 3. STATUS: Fully compatible with V20 Vector Store.

import os
import asyncio
import io
import structlog
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from pymongo.database import Database
from bson import ObjectId
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
# PHOENIX FIX: Import the new unified query function
from .vector_store_service import query_mixed_intelligence
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

STRICT_KOSOVO_CONSTRAINTS = """
*** UDHËZIME STRIKTE (SISTEMI I KOSOVËS): ***

1. JURISDIKSIONI: VETËM REPUBLIKA E KOSOVËS.
   - Ndalohet çdo referencë nga Shqipëria.

2. PREZANTIMI I LIGJEVE (E DETYRUESHME):
   - Përdor formatin: **[Emri i Nenit/Ligjit]**: "[Përmbajtja]".

3. CITIMI I PROVAVE: 
   - Përdor formatin "Provë: [[Burimi: Emri i Dokumentit]]" me bold.

4. STILI: Formal, autoritativ, argumentues.
"""

TEMPLATE_MAP = {
    "generic": "Strukturoje si dokument juridik standard.",
    "padi": "STRUKTURA E PADISË: 1. Gjykata... 2. Palët... 3. Baza Ligjore... 4. Faktet... 5. Petitiumi...",
    "pergjigje": "STRUKTURA E PËRGJIGJES: 1. Gjykata... 2. Deklarim kundërshtues... 3. Arsyetimi... 4. Propozimi...",
    "kunderpadi": "STRUKTURA E KUNDËRPADISË: 1. Gjykata... 2. Baza e kundërpadisë... 3. Kërkesa...",
    "kontrate": "STRUKTURA E KONTRATËS: 1. Titulli... 2. Palët... 3. Nenet (Objekti, Çmimi, Kohëzgjatja)... 4. Nënshkrimet..."
}

def _format_business_identity_sync(db: Database, user: UserInDB) -> str:
    try:
        if db is not None:
            profile = db.business_profiles.find_one({"user_id": str(user.id)})
            if profile: return f"=== HARTUESI ===\nZyra: {profile.get('firm_name', user.username)}\nAdresa: {profile.get('address','N/A')}\n"
    except Exception: pass
    return f"=== HARTUESI ===\nEmri: {user.username}\n"

async def generate_draft_stream(
    context: str, prompt_text: str, user: UserInDB, draft_type: Optional[str] = "generic",
    case_id: Optional[str] = None, jurisdiction: Optional[str] = "ks",
    use_library: bool = False, db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    
    sanitized_prompt = sterilize_text_for_llm(prompt_text)
    key = draft_type if draft_type else "generic"
    template_instruction = TEMPLATE_MAP.get(key, TEMPLATE_MAP["generic"])
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert për legjislacionin e KOSOVËS.
    
    {STRICT_KOSOVO_CONSTRAINTS}
    
    DETYRA: Harto dokumentin juridik '{key.upper()}' duke ndjekur me përpikmëri këtë strukturë:
    {template_instruction}
    """

    # PHOENIX FIX: Unified RAG Call (Private + Public)
    # We fetch relevant case docs AND laws in one go using the new Multi-Tenant Engine
    try:
        rag_results = await asyncio.to_thread(
            query_mixed_intelligence,
            user_id=str(user.id),
            query_text=sanitized_prompt,
            n_results=15,
            case_context_id=case_id
        )
    except Exception as e:
        logger.error(f"RAG failed: {e}")
        rag_results = []

    # Organize RAG results
    private_context = []
    public_laws = []
    
    for item in rag_results:
        text = item.get("text", "")
        source = item.get("source", "Unknown")
        type_ = item.get("type", "DATA")
        
        entry = f"--- {source} ---\n{text}"
        if type_ == "PUBLIC_LAW":
            public_laws.append(entry)
        else:
            private_context.append(entry)

    formatted_context = "\n\n".join(private_context)
    formatted_laws = "\n\n".join(public_laws)
    
    identity = await asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    
    full_prompt = f"""
    {identity}

    === BAZA LIGJORE (RELEVANTE) ===
    {formatted_laws}

    === KONTEKSTI I RASTIT (FAKTE & PROVA) ===
    {formatted_context}

    === UDHËZIMI SPECIFIK I PËRDORUESIT ===
    "{sanitized_prompt}"
    
    KËRKESA: Fillo hartimin e dokumentit tani.
    """

    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}],
                temperature=0.1, stream=True, extra_headers={"HTTP-Referer": "https://juristi.tech"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception: pass
    yield "**[Draftimi dështoi. Provoni përsëri.]**"

def generate_objection_document(analysis_result: Dict[str, Any], case_title: str) -> bytes:
    # (Identical to previous version - keeping logic for .docx generation)
    document = Document()
    style = document.styles['Normal']
    font = style.font # type: ignore
    font.name = 'Times New Roman'
    font.size = Pt(12)

    header = document.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("GJYKATA THEMELORE PRISHTINË\n")
    run.bold = True
    run.font.size = Pt(14)
    header.add_run("Departamenti i Përgjithshëm - Divizioni Civil")

    document.add_paragraph(f"LËNDA: {case_title}")
    document.add_paragraph(f"NR. I REFERENCËS: [Vendosni Numrin e Lëndës]")
    document.add_paragraph("_" * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph()

    document.add_paragraph("I/E Nderuar Gjykatës / Gjykatëse,")
    intro = document.add_paragraph("Në emër të palës së paditur/kundërshtuese, përmes kësaj parashtrese paraqesim: ")
    intro.add_run("KUNDËRSHTIM NDAJ PRETENDIMEVE").bold = True
    document.add_paragraph("Bazuar në analizën e provave dhe fakteve të çështjes, ne kundërshtojmë kërkesat e palës kundërshtare për arsyet e mëposhtme:")

    if analysis_result.get("contradictions"):
        document.add_heading("I. KUNDËRSHTIMET FAKTIKE DHE LIGJORE", level=1)
        for idx, contradiction in enumerate(analysis_result["contradictions"], 1):
            p = document.add_paragraph(style='List Bullet')
            p.add_run(f"Pika {idx}: ").bold = True
            p.add_run(contradiction)

    if analysis_result.get("discovery_targets"):
        document.add_heading("II. MUNGESA E PROVAVE MBËSHTETËSE", level=1)
        document.add_paragraph("Pala kundërshtare dështon të ofrojë prova për pretendimet e saj. Konkretisht:")
        for target in analysis_result["discovery_targets"]:
             p = document.add_paragraph(style='List Bullet')
             p.add_run("Kërkohet prova: ").bold = True
             p.add_run(target)

    if analysis_result.get("suggested_questions"):
        document.add_heading("III. ÇËSHTJE PËR T'U SQARUAR (NË SEANCË)", level=1)
        for q in analysis_result["suggested_questions"]:
             document.add_paragraph(q, style='List Bullet')

    document.add_paragraph("\nPër arsye të cekura më lart, i propozojmë Gjykatës që të refuzojë kërkesat e palës kundërshtare si të pabazuara.")
    document.add_paragraph("\n\nMe respekt,\n\n__________________________\n(Nënshkrimi i Përfaqësuesit)").alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()