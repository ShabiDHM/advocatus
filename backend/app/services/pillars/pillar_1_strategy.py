# FILE: backend/app/services/pillars/pillar_1_strategy.py
# PHOENIX PROTOCOL - PILLAR 1: ROLE-AWARE FORENSIC STRATEGY V25.0 (COMPACT & STRICT)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar1StrategyService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 1:
    - PLAINTIFF: Strategji sulmuese për fitore
    - DEFENDANT: Mbrojtje e hekurt
    - NEUTRAL: Vlerësim objektiv
    - RAG + TIMELINE + ZERO HALUCINACIONE
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str,
        case_domain: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        search_query = query_text or f"Strategjia ligjore për çështjen: {case_title}. Klienti: {client_name}. Pozicioni: {pos}. Lëmia: {case_domain}"
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        if pos in ["PLAINTIFF", "PADITËS", "KALLËZUES"]:
            stance_instruction = f"""
QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR I PADITËSIT (**{client_name}**).
Misioni: Provo padinë, identifiko shkeljet, maksimizo dëmshpërblimin.
"""
            section_1_title = f"### 1. 🏛️ ANALIZA FORENZIKE E FASHIKULLIT DHE BAZA E PADISË SË ({client_name})"
            section_5_title = f"### 5. 🎯 PLANI TAKTIK PËR FITOREN E PADISË DHE HAPAT E ARDHSHËM TË ({client_name})"
        elif pos in ["NEUTRAL", "I PAANSHËM", "GJYQTAR", "ARBITËR"]:
            stance_instruction = f"""
QËNDRIMI STRATEGJIK: TI JE GJYQTAR / ARBITËR 100% I PAANSHËM.
Misioni: Vlerëso objektivisht të dyja palët.
"""
            section_1_title = "### 1. 🏛️ ANALIZA OBJEKTIVE GJYQËSORE E FASHIKULLIT"
            section_5_title = "### 5. 🎯 VLERËSIMI PËRFUNDIMTAR DHE DREJTIMET PROCEDURALE"
        else:
            stance_instruction = f"""
QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR I TË PADITURIT (**{client_name}**).
Misioni: Mbrojtje e hekurt, rrëzo pretendimet, ndërto kundërsulmin.
"""
            section_1_title = f"### 1. 🏛️ ANALIZA FORENZIKE E TË GJITHË FASHIKULLIT: ÇKA KA NDODHUR ({client_name})?"
            section_5_title = f"### 5. 🎯 ÇFARË DUHET TË BËJË ({client_name}) TASH: PLANI I VEPRIMIT"

        base_prompt = BasePillarService.build_base_prompt(
            case_title=case_title,
            client_name=client_name,
            client_position=pos,
            current_date_str=current_date_str,
            manifest_str=manifest_str,
            context_str=context_str,
            case_domain=case_domain,
            rag_context=rag_context,
            case_rag_context=case_rag_context,
            timeline_context=timeline_context
        )

        return f"""
{base_prompt}

{stance_instruction}

STRUKTURA E DETYRUESHME E PËRGJIGJES:
{section_1_title}
### 2. 🔬 MATRICA E PROVAVE MATERIALE, SHKRESORE, SHKENCORE DHE FONOGRAMEVE
### 3. 👥 IDENTIFIKIMI SHTERUES I TË GJITHË AKTORËVE DHE ROLI I TYRE NË LËNDË
### 4. 🔨 OPINIONI DHE VLERËSIMI DOKTRINAR MBI QËNDRUESHMËRINË E LËNDËS
{section_5_title}
"""