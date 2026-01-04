# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V20.0 (PROFESSIONAL BLUEPRINTS)
# 1. UPGRADE: Massively upgraded the TEMPLATE_MAP with detailed, professional legal structures.
# 2. BEHAVIOR: Provides a high-quality architectural blueprint for the "Master Litigator" AI.
# 3. STATUS: Fully aligned with the V32.1 RAG service for superior drafting performance.

import os
import io
import structlog
from typing import Optional, Dict, Any
from pymongo.database import Database
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from ..models.user import UserInDB
from .albanian_rag_service import AlbanianRAGService

logger = structlog.get_logger(__name__)

# PHOENIX V20.0: UPGRADED PROFESSIONAL BLUEPRINTS
TEMPLATE_MAP = {
    "generic": "Strukturoje si dokument juridik formal, me hyrje, zhvillim të argumentit dhe përfundim.",
    
    "padi": """
STRUKTURA E PADISË (STRICT):
1.  **KOKA E AKTIT:** (Gjykata Themelore në [Qyteti], Departamenti për Çështje Civile, Emrat e Palëve, Baza Ligjore).
2.  **HYRJE:** Përmbledhje e shkurtër e kërkesës.
3.  **GJENDJA FAKTIKE:** Përshkrim i detajuar dhe kronologjik i ngjarjeve, duke cituar provat.
4.  **BAZA LIGJORE:** Analizë e neneve specifike të ligjit që janë shkelur dhe si aplikohen ato mbi faktet.
5.  **PROPOZIM-PADIA (PETITUMI):** Lista e kërkesave të sakta dhe të numëruara që i drejtohen gjykatës (p.sh., "Të detyrohet i padituri...", "Të paguajë shpenzimet...").
    """,

    "pergjigje": """
STRUKTURA E PËRGJIGJES NË PADI (STRICT):
1.  **KOKA E AKTIT:** (Gjykata, Palët, Referenca ndaj Padisë).
2.  **DEKLARIM MBI PADINË:** Deklaratë e qartë nëse i padituri i pranon apo i kundërshton në tërësi pretendimet e padisë.
3.  **KUNDËRSHTIMET FAKTIKE:** Përgjigje pikë për pikë ndaj pretendimeve faktike të paditësit, duke paraqitur versionin e vet të ngjarjeve dhe duke cituar kundër-provat.
4.  **KUNDËRSHTIMET LIGJORE:** Argumentim se pse baza ligjore e paditësit është e gabuar ose nuk aplikohet.
5.  **PROPOZIM PËRFUNDIMTAR:** Kërkesë e qartë drejtuar gjykatës (p.sh., "Të refuzohet padia si e pabazuar...", "Të detyrohet paditësi të paguajë shpenzimet...").
    """,

    "kunderpadi": """
STRUKTURA E KUNDËRPADISË (STRICT):
1.  **KOKA E AKTIT:** (Gjykata, Palët, Referenca ndaj Padisë Kryesore).
2.  **HYRJE:** Deklaratë që ky dokument shërben si përgjigje në padi dhe njëkohësisht si kundërpadi.
3.  **FAKTET E REJA (BAZA E KUNDËRPADISË):** Përshkrim i fakteve të reja që nuk janë përmendur në padi dhe që krijojnë një bazë për kërkesën e re të kundër-paditësit.
4.  **DËMI I SHKAKTUAR:** Specifikim i dëmit material ose jomaterial që i është shkaktuar kundër-paditësit.
5.  **LIDHJA SHKAKORE:** Argumentim se si veprimet e paditësit fillestar kanë shkaktuar drejtpërdrejt dëmin e përmendur.
6.  **BAZA LIGJORE E KUNDËRPADISË:** Nenet specifike të ligjit që mbështesin kërkesën për kompensim.
7.  **PETITUMI I KUNDËRPADISË:** Kërkesë e qartë për kompensim ose veprim tjetër nga gjykata.
    """,

    "kontrate": """
STRUKTURA E KONTRATËS (STRICT):
1.  **TITULLI DHE DATA:** (p.sh., "KONTRATË PËR SHITBLERJE", lidhur më [Data]).
2.  **PALËT KONTRAKTUESE:** Identifikim i plotë i palëve (Emri, adresa, numri personal/biznesit).
3.  **PREAMBULA/OBJEKTI I KONTRATËS:** Përshkrim i qartë i qëllimit të kontratës.
4.  **NENET E KONTRATËS:**
    *   Neni 1: Të Drejtat dhe Detyrimet e Palës A.
    *   Neni 2: Të Drejtat dhe Detyrimet e Palës B.
    *   Neni 3: Çmimi, Mënyra dhe Afatet e Pagesës.
    *   Neni 4: Afatet dhe Kushtet e Dorëzimit/Përmbushjes.
    *   Neni 5: Rrethanat e Jashtëzakonshme (Forca Madhore).
    *   Neni 6: Zgjidhja e Kontratës dhe Pasojat.
5.  **ZGJIDHJA E MOSMARRËVESHJEVE:** Përcaktimi i gjykatës kompetente ose arbitrazhit.
6.  **DISPOZITAT PËRFUNDIMTARE.**
7.  **NËNSHKRIMET E PALËVE.**
    """
}

async def generate_draft(
    db: Database,
    user_id: str,
    case_id: Optional[str],
    draft_type: str,
    user_prompt: str,
) -> str:
    """
    Uses the Direct Generation Mode to write legal drafts.
    """
    logger.info(f"Initializing Drafting Service for type: {draft_type}")
    
    template_instruction = TEMPLATE_MAP.get(draft_type, TEMPLATE_MAP["generic"])

    # Combined instruction for the AI
    final_instruction = f"""
    LLOJI I DOKUMENTIT: {draft_type.upper()}
    STRUKTURA E KËRKUAR (Blueprint i Detyrueshëm): 
    {template_instruction}
    
    DETAJET SPECIFIKE NGA PËRDORUESI:
    {user_prompt}
    """
    
    try:
        agent_service = AlbanianRAGService(db)
        
        final_draft = await agent_service.generate_legal_draft(
            instruction=final_instruction,
            user_id=user_id,
            case_id=case_id
        )
        return final_draft
    except Exception as e:
        logger.error(f"Drafting service failed: {e}", exc_info=True)
        return "Gjatë hartimit të draftit ka ndodhur një gabim teknik."


def generate_objection_document(analysis_result: Dict[str, Any], case_title: str) -> bytes:
    """
    Generates a .docx file from an analysis result.
    """
    document = Document()
    style = document.styles['Normal']
    font = style.font; font.name = 'Times New Roman'; font.size = Pt(12) # type: ignore

    header = document.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("GJYKATA THEMELORE PRISHTINË\n"); run.bold = True; run.font.size = Pt(14)
    header.add_run("Departamenti i Përgjithshëm - Divizioni Civil")

    document.add_paragraph(f"LËNDA: {case_title}")
    document.add_paragraph("NR. I REFERENCËS: [Vendosni Numrin e Lëndës]")
    document.add_paragraph("_" * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph()

    document.add_paragraph("I/E Nderuar Gjykatës / Gjykatëse,")
    intro = document.add_paragraph("Në emër të palës së paditur/kundërshtuese, përmes kësaj parashtrese paraqesim: ")
    intro.add_run("KUNDËRSHTIM NDAJ PRETENDIMEVE").bold = True
    document.add_paragraph("Bazuar në analizën e provave dhe fakteve të çështjes, ne kundërshtojmë kërkesat e palës kundërshtare për arsyet e mëposhtme:")

    if analysis_result.get("contradictions"):
        document.add_heading("I. KUNDËRSHTIMET FAKTIKE DHE LIGJORE", level=1)
        for idx, contradiction in enumerate(analysis_result["contradictions"], 1):
            p = document.add_paragraph(style='List Bullet'); p.add_run(f"Pika {idx}: ").bold = True; p.add_run(contradiction)

    if analysis_result.get("discovery_targets"):
        document.add_heading("II. MUNGESA E PROVAVE MBËSHTETËSE", level=1)
        document.add_paragraph("Pala kundërshtare dështon të ofrojë prova për pretendimet e saj. Konkretisht:")
        for target in analysis_result["discovery_targets"]:
             p = document.add_paragraph(style='List Bullet'); p.add_run("Kërkohet prova: ").bold = True; p.add_run(target)

    document.add_paragraph("\nPër arsye të cekura më lart, i propozojmë Gjykatës që të refuzojë kërkesat e palës kundërshtare si të pabazuara.")
    document.add_paragraph("\n\nMe respekt,\n\n__________________________\n(Nënshkrimi i Përfaqësuesit)").alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()