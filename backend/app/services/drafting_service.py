# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V16.1 (TYPE SAFETY)
# 1. FIXED: Sanitized 'draft_type' to ensure it is always a string before dictionary lookup.
# 2. STATUS: Passing strict static analysis.

import os
import asyncio
import io
import structlog
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base, query_findings_by_similarity
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- INVISIBLE INTELLIGENCE LAYER ---
STRICT_KOSOVO_CONSTRAINTS = """
*** UDHËZIME STRIKTE (SISTEMI I KOSOVËS): ***
1. JURISDIKSIONI: VETËM REPUBLIKA E KOSOVËS.
2. NDALIM: MOS përdor kurrë ligje, gjykata apo referenca nga Republika e Shqipërisë (psh. Tiranë, Kodi Civil i Shqipërisë).
3. LIGJI: Referoju vetëm legjislacionit të Kosovës (psh. Ligji për Familjen i Kosovës, Ligji për Procedurën Kontestimore, LPK).
4. Nëse nuk e di nenin specifik të Kosovës, shkruaj: "Sipas dispozitave ligjore në fuqi në Kosovë".
5. FORMATIMI: Përdor stil formal, juridik dhe profesional.
"""

TEMPLATE_MAP = {
    "generic": "Strukturoje si dokument juridik standard.",
    "padi": """
    STRUKTURA E PADISË:
    1. Gjykata Themelore në [Qyteti]
    2. Paditësi: [Emri] vs I Padituri: [Emri]
    3. Baza Juridike: [Nenet]
    4. Vlera e Kontestit: [Shuma]
    5. Pjesa Historike (Faktet)
    6. Pjesa Arsyetuese (Pse kemi të drejtë)
    7. PETITUMI (Kërkesëpadia): "I propozoj Gjykatës të aprovojë..."
    """,
    "pergjigje": """
    STRUKTURA E PËRGJIGJES NË PADI:
    1. Gjykata Themelore në [Qyteti]
    2. Nr. i Lëndës: [Numri]
    3. DEKLARIM: Kundërshtim në tërësi i padisë.
    4. ARSYETIMI: Pse padia nuk ka bazë ligjore ose faktike.
    5. PROPOZIMI: "Të refuzohet padia si e pabazuar."
    """,
    "kunderpadi": """
    STRUKTURA E KUNDËRPADISË:
    1. Gjykata...
    2. Palët...
    3. BAZA E KUNDËRPADISË: Pse paditësi fillestar është fajtor/borxhli.
    4. KËRKESA: Dëmshkërblim ose veprim specifik.
    """,
    "kontrate": """
    STRUKTURA E KONTRATËS:
    1. TITULLI (psh. KONTRATË QIRAJE)
    2. PALËT (Emri, Nr. Personal, Adresa)
    3. Neni 1: Objekti i Kontratës
    4. Neni 2: Çmimi / Pagesa
    5. Neni 3: Kohëzgjatja
    6. Neni 4: Të Drejtat dhe Detyrimet
    7. Neni 5: Zgjidhja e Konflikteve (Gjykata Themelore [Qyteti])
    8. Nënshkrimet
    """
}

def _build_case_context_hybrid_sync(db: Database, case_id: str, user_prompt: str) -> str:
    try:
        search_query = user_prompt
        query_embedding = generate_embedding(search_query)
        if not query_embedding: return ""
        vector_findings = query_findings_by_similarity(case_id=case_id, embedding=query_embedding, n_results=10)
        direct_db_findings = list(db.findings.find({"case_id": {"$in": [ObjectId(case_id), case_id]}}))
        all_findings = {f['finding_text']: f for f in vector_findings}
        for f in direct_db_findings:
            if f.get('finding_text') and f['finding_text'] not in all_findings:
                 all_findings[f['finding_text']] = f
        if not all_findings: return ""
        context_parts = ["FAKTE TË VERIFIKUARA NGA DOSJA:"]
        for finding in all_findings.values():
            context_parts.append(f"- [{finding.get('category', 'FAKT')}]: {finding.get('finding_text', 'N/A')}")
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Hybrid context failed: {e}")
        return ""

async def _fetch_relevant_laws_async(query_text: str, jurisdiction: str = "ks") -> str:
    try:
        if not query_text or len(query_text) < 5: return ""
        embedding = generate_embedding(query_text)
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=5, jurisdiction=jurisdiction) 
        if not laws: return ""
        buffer = [f"\n=== BAZA LIGJORE ({jurisdiction.upper()}) ==="]
        for law in laws:
            buffer.append(f"DOKUMENTI: {law.get('document_name','Ligj')}\n{law.get('text','N/A')}\n---")
        return "\n".join(buffer)
    except Exception: return ""

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
    
    # PHOENIX FIX: Type Safety for Dictionary Key
    # draft_type is Optional[str], so we default to "generic" if it's None
    key = draft_type if draft_type else "generic"
    template_instruction = TEMPLATE_MAP.get(key, TEMPLATE_MAP["generic"])
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert për legjislacionin e KOSOVËS.
    
    {STRICT_KOSOVO_CONSTRAINTS}
    
    DETYRA: Harto dokumentin e kërkuar duke ndjekur këtë strukturë:
    {template_instruction}
    """

    # 2. BUILD CONTEXT
    db_context = ""
    if case_id and db is not None:
         db_context = await asyncio.to_thread(_build_case_context_hybrid_sync, db, case_id, sanitized_prompt)
         
    final_context = f"{context}\n\n{db_context}"
    rag_search_query = f"{sanitized_prompt} {final_context[:500]}" 
    
    laws, identity = await asyncio.gather(
        _fetch_relevant_laws_async(rag_search_query), 
        asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    )
    
    full_prompt = f"""
    {identity}
    {laws}

    === KONTEKSTI I RASTIT ===
    {final_context}

    === UDHËZIMI I PËRDORUESIT ===
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
    yield "**[Draftimi dështoi.]**"

def generate_objection_document(analysis_result: Dict[str, Any], case_title: str) -> bytes:
    # (Same as previous - keeping existing logic)
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