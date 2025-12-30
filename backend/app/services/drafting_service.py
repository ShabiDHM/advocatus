# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V18.1 (TYPE FIX)
# 1. FIX: Added a check for 'case_id' before passing it to the agent to satisfy strict 'str | None' typing.
# 2. STATUS: Pylance errors resolved.

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

TEMPLATE_MAP = {
    "generic": "Strukturoje si dokument juridik standard.",
    "padi": "STRUKTURA E PADISË: 1. Gjykata... 2. Palët... 3. Baza Ligjore... 4. Faktet... 5. Petitiumi...",
    "pergjigje": "STRUKTURA E PËRGJIGJES: 1. Deklarim kundërshtues... 2. Arsyetimi... 3. Propozimi...",
    "kunderpadi": "STRUKTURA E KUNDËRPADISË: 1. Baza e kundërpadisë... 2. Kërkesa...",
    "kontrate": "STRUKTURA E KONTRATËS: 1. Titulli... 2. Palët... 3. Nenet (Objekti, Çmimi, Kohëzgjatja)... 4. Nënshkrimet..."
}

async def generate_draft(
    db: Database,
    user_id: str,
    case_id: Optional[str],
    draft_type: str,
    user_prompt: str,
) -> str:
    """
    Uses the full Agentic RAG service to generate a legal or business draft.
    """
    logger.info("Initializing Agentic Drafting Service...")
    
    template_instruction = TEMPLATE_MAP.get(draft_type, TEMPLATE_MAP["generic"])

    agent_query = f"""
    DETYRA: Harto një dokument të tipit '{draft_type.upper()}'.
    STRUKTURA PËR T'U NDJEKUR: {template_instruction}
    
    UDHËZIMET E PËRDORUESIT:
    ---
    {user_prompt}
    ---
    
    Filloni me hulumtimin e informacionit të nevojshëm dhe më pas hartoni dokumentin e plotë.
    """
    
    try:
        agent_service = AlbanianRAGService(db)
        
        # PHOENIX FIX: Pass case_id only if it's not None
        final_draft = await agent_service.chat(
            query=agent_query,
            user_id=user_id,
            case_id=case_id if case_id else None
        )
        return final_draft
    except Exception as e:
        logger.error(f"Agentic drafting failed: {e}", exc_info=True)
        return "Gjatë hartimit të draftit ka ndodhur një gabim në sistemin e inteligjencës artificiale."


def generate_objection_document(analysis_result: Dict[str, Any], case_title: str) -> bytes:
    """
    (Unchanged) Generates a .docx file from an analysis result.
    """
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