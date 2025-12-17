# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V17.0 (KOSOVO JUDICIAL STYLE)
# 1. NEW: Injected "Perfect Padi" & "Perfect Response" templates based on forensic analysis.
# 2. STYLE: Enforced "A K T G J Y K I M" operative block structure.
# 3. FORMAT: Added specific header hierarchies for Lawsuits vs. Responses.

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
from .vector_store_service import query_legal_knowledge_base, query_findings_by_similarity
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- INVISIBLE INTELLIGENCE LAYER ---
STRICT_KOSOVO_CONSTRAINTS = """
*** UDHËZIME STRIKTE (STILI GJYQËSOR I KOSOVËS): ***
1. JURISDIKSIONI: VETËM REPUBLIKA E KOSOVËS.
2. STILI I SHKRIMIT: Formal, autoritativ, argumentues.
3. CITIMI I PROVAVE: Përdor formatin "Provë: [Emri i Dokumentit]" me bold, në rresht të ri ose pas paragrafit përkatës.
4. TITULLI FINAL: Çdo dokument duhet të përfundojë me dispozitivin e propozuar (Petitumin) nën titullin e ndarë me hapësira: "A K T G J Y K I M".
5. FOLJET E DISPOZITIVIT: Përdor terma urdhërorë me bold: I) APROVOHET, II) DETYROHET, III) REFUZOHET.
"""

TEMPLATE_MAP = {
    "generic": "Strukturoje si dokument juridik standard.",
    
    "padi": """
    STRUKTURA E PADISË (STRICT):
    
    1. KOKA E DOKUMENTIT (Center):
       Republika e Kosovës
       Republika Kosova-Republic of Kosovo
       Qeveria -Vlada-Government
       Ministria e Drejtësisë
       GJYKATA THEMELORE PRISHTINË (ose qyteti përkatës)
       Departamenti i Përgjithshëm – Divizioni Civil

    2. PALËT (Left Align):
       Paditëse: [Emri, Adresa e plotë]
       I padituri: [Emri, Adresa e plotë]

    3. HYRJA LIGJORE:
       "Në mbështetje të nenit [X] të [Ligjit], paditësja paraqet këtë:"
       
       P A D I  (Center, Bold, Spaced)

    4. BAZA LIGJORE: [Psh. Zgjidhja e martesës, Borxhi, etj]

    5. NARRATIVA (Faktet):
       - Shpjego rrjedhojën e ngjarjes.
       - Pas çdo fakti kyç, shto rresht: "Provë: [Dokumenti]"

    6. ARSYETIMI LIGJOR:
       - Cito nenet specifike të ligjeve të Kosovës (LPK, LPF, LMD).
       - Argumento pse kërkesa është e bazuar.

    7. DISPOZITIVI I PROPOZUAR (Center, Bold):
       A K T G J Y K I M

       I) APROVOHET kërkesë padia e paditëses [Emri].
       II) DETYROHET i padituri [Emri] që të... (psh. paguajë, lirojë pronën).
       III) OBLIGOHET i padituri t'i paguajë shpenzimet e procedurës.

    8. FUNDI:
       Vendi, Data
       Paditëse: [Emri]
    """,

    "pergjigje": """
    STRUKTURA E PËRGJIGJES NË PADI (STRICT):

    1. KOKA E AVOKATIT (Top Right/Center):
       AVOKAT – LAWYER
       [Emri i Avokatit/Firmës]
       [Adresa, Tel, Email]
       C.nr.[Numri i Lëndës]

    2. ADRESIMI:
       Për: Gjykatën Themelore në [Qyteti] - Departamenti...

    3. PALËT:
       Paditësja: [Emri, Adresa]
       I Padituri: [Emri, Adresa], të cilin e përfaqëson me autorizim av. [Emri]

    4. REFERENCA:
       Baza Juridike: [Objekti i kontestit]

    5. HYRJA PROCEDURALE:
       "Duke vepruar sipas... ushtrojmë këtë:"
       
       PËRGJIGJE NË PADI (Bold, Center)

    6. TRUPI I KUNDËRSHTIMIT:
       - "Kundërshtojmë në tërësi padinë..."
       - Argumento faktet e pasakta të paditësit.
       - Shto prova: "Provë: [Emri]".

    7. DISPOZITIVI I PROPOZUAR (Center, Bold):
       A K T G J Y K I M

       - REFUZOHET në tërësi si e pa bazuar në ligj padia e paditëses.
       - MBETET NË FUQI [Nëse ka vendim paraprak].
       - DETYROHET paditësja t'i bartë shpenzimet e procedurës.

    8. REZERVIMI:
       "Rezervojmë të drejtën e paraqitjes së provave në seancë..."

    9. FUNDI:
       Vendi, Data
       Për të paditurin, sipas autorizimit:
       Av. [Emri]
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
    key = draft_type if draft_type else "generic"
    template_instruction = TEMPLATE_MAP.get(key, TEMPLATE_MAP["generic"])
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert për legjislacionin e KOSOVËS.
    
    {STRICT_KOSOVO_CONSTRAINTS}
    
    DETYRA: Harto dokumentin juridik '{key.upper()}' duke ndjekur me përpikmëri këtë strukturë:
    {template_instruction}
    """

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

    === KONTEKSTI I RASTIT (FAKTE & PROVA) ===
    {final_context}

    === UDHËZIMI SPECIFIK I PËRDORUESIT ===
    "{sanitized_prompt}"
    
    KËRKESA: Fillo hartimin e dokumentit tani. Përdor formatimin e saktë (Bold, Center) siç u kërkua.
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