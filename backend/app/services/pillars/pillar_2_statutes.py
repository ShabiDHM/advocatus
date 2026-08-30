# FILE: backend/app/services/pillars/pillar_2_statutes.py
# PHOENIX PROTOCOL - PILLAR 2: DOMAIN-AGNOSTIC STATUTORY AUDIT V21.0 (COMPACT & STRICT)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar2StatutesService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 2:
    - Auditimi statutor nen-për-nen
    - Zbulimi i lapsuseve Contra Legem
    - Precedentët e Gjykatës Supreme (VETËM nga lista e verifikuar)
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
        
        search_query = query_text or f"Auditimi statutor për çështjen: {case_title}. Lëmia: {case_domain}. Shkeljet ligjore, nenet e zbatueshme."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=30
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

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

MISIONI I KARTËS 2:
1. FOKUSI ËSHTË EKSKLUZIVISHT STATUTOR DHE DOKTRINAR — Mos përsërit faktet e Kartës 1;
2. Evidento çdo shkelje procedurale (Contra Legem);
3. Korrigjo çdo lapsus me nenin dhe paragrafin e saktë nga RAG context;
4. Apliko VETËM precedentët nga lista e verifikuar.

STRUKTURA E DETYRUESHME E PËRGJIGJES:
### 1. 📜 MATRICA STATUTARE E APLIKUESHME (Ligjet për lëminë: {case_domain})
### 2. ⚠️ AUDITIMI I SHKELJEVE PROCEDURALE DHE LAPSUSEVE (Contra Legem & Prapadatimet)
### 3. 🏛️ PRECEDENTËT E GJYKATËS SUPREME TË ZBATUESHME (VETËM nga lista e verifikuar)
### 4. ⚖️ KUALIFIKIMI I SAKTË JURIDIK I VEPRIMEVE TË PALËVE
### 5. 💡 DIREKTIVAT STATUTORE PËR ANKESËN APO RRËZIMIN E AKTEVE
"""