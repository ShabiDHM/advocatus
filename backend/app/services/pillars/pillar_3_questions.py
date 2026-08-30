# FILE: backend/app/services/pillars/pillar_3_questions.py
# PHOENIX PROTOCOL - PILLAR 3: ROLE-AWARE CROSS-EXAMINATION V26.0 (SPECIFIC & EVIDENCE-BASED)

from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar3QuestionsService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 3:
    - PLAINTIFF: Pyetje kirurgjike për të gozhduar të Paditurin
    - DEFENDANT: Pyetje për të ekspozuar kontradiktat
    - NEUTRAL: Pyetje gjyqësore të balancuara
    - SPECIFIKE: Pyetje me emra, data, dokumente dhe sekonda [MM:SS]
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
        witness_names: Optional[List[str]] = None,
        expert_names: Optional[List[str]] = None,
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
        
        search_query = query_text or f"Pyetësori taktik për seancë. Lëmia: {case_domain}. Roli: {pos}. Nenet procedurale për kundërshtim."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=20
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        witnesses_section = ""
        if witness_names:
            witnesses_list = "\n".join([f"   - {name}" for name in witness_names])
            witnesses_section = f"\nDËSHMITARËT:\n{witnesses_list}"
        
        experts_section = ""
        if expert_names:
            experts_list = "\n".join([f"   - {name}" for name in expert_names])
            experts_section = f"\nEKSPERTËT:\n{experts_list}"

        if pos in ["PLAINTIFF", "PADITËS", "KALLËZUES"]:
            role_goal = f"Pyetje në favor të Paditësit ({client_name}) për të provuar shkeljet."
            target_party = "TË PADITURIN / TË DYSHUARIT"
        elif pos in ["NEUTRAL", "I PAANSHËM", "GJYQTAR", "ARBITËR"]:
            role_goal = "Pyetje gjyqësore të paanshme për të dyja palët."
            target_party = "TË DYJA PALËT"
        else:
            role_goal = f"Pyetje në favor të të Paditurit ({client_name}) për të rrëzuar pretendimet."
            target_party = "PALËN KUNDËRSHTARE"

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

MISIONI DHE DREJTIMI I PYETJEVE:
{role_goal}

{witnesses_section}
{experts_section}

DIREKTIVA SPECIFIKE PËR PYETJET:
1. ÇDO pyetje duhet të përmbajë: EMRIN e personit, DATËN e ngjarjes, DOKUMENTIN referencë;
2. Nëse ka audio/video, përfshi sekondat [MM:SS] në pyetje;
3. Çdo pyetje duhet të jetë në thonjëza ("...") gati për t'u lexuar me zë;
4. Çdo pyetje duhet të lidhet me një provë konkrete nga fashikulli;
5. Nëse ka kontradikta në dokumente, pyet direkt: "Në dokumentin X thuhet Y, ndërsa ju thoni Z. Si e shpjegoni?";
6. Nëse ka prapadatime, pyet: "Pse data në këtë dokument është X, ndërsa ngjarja ka ndodhur në datën Y?";
7. MOS përdor pyetje të përgjithshme — VETËM pyetje specifike me referenca.

STRUKTURA E DETYRUESHME:
### 1. 🎯 STRATEGJIA E SALLËS PËR ROLIN ({pos})
### 2. ❓ PYETJET TAKTIKE PËR {target_party} (me emra, data, dokumente)
### 3. 🔬 PYETJET PËR EKSPERTËT (me referenca në ekspertiza)
### 4. 🏢 PYETJET PËR DËSHMITARËT (me emra specifikë)
### 5. 💡 DIREKTIVAT PËR PROCESVERBAL (me referenca ligjore nga RAG)
"""