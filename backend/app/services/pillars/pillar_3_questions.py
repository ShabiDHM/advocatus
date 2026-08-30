# FILE: backend/app/services/pillars/pillar_3_questions.py
# PHOENIX PROTOCOL - PILLAR 3: ROLE-AWARE CROSS-EXAMINATION SPECIALIST V24.0 (TIMELINE INTEGRATED)

from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar3QuestionsService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 3:
    - PLAINTIFF: Pyetje kirurgjike për të gozhduar të Paditurin dhe provuar dëmin/fajësinë.
    - DEFENDANT: Pyetje kirurgjike për të ekspozuar kontradiktat e Paditësit dhe rrëzuar dëshmitarët e tij.
    - NEUTRAL: Pyetje gjyqësore të balancuara për të zbardhur të vërtetën materiale.
    - 100% agnostik ndaj domeneve + RAG + TIMELINE + ZERO HALUCINACIONE
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
        
        # PHOENIX FIX: Zbulo domenin
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Kërko në RAG
        search_query = query_text or f"Pyetësori taktik për seancë gjyqësore. Lëmia: {case_domain}. Roli: {pos}. Nenet procedurale për kundërshtim dhe pyetje."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=20
        )
        
        # PHOENIX FIX: Ndërto kronologjinë
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        # PHOENIX FIX: Ndërto seksionin e dëshmitarëve (korrigjuar witness_list -> witnesses_list)
        witnesses_section = ""
        if witness_names:
            witnesses_list = "\n".join([f"   - {name}" for name in witness_names])
            witnesses_section = f"""
DËSHMITARËT E IDENTIFIKUAR NË FASHIKULL:
{witnesses_list}
"""
        
        experts_section = ""
        if expert_names:
            experts_list = "\n".join([f"   - {name}" for name in expert_names])
            experts_section = f"""
EKSPERTËT E IDENTIFIKUAR NË FASHIKULL:
{experts_list}
"""

        if pos in ["PLAINTIFF", "PADITËS", "KALLËZUES"]:
            role_goal = f"Pyetje në favor të Paditësit ({client_name}) për të provuar shkeljet, dëmet dhe mashtrimet e të Paditurit."
            target_party = "TË PADITURIN / TË DYSHUARIT"
        elif pos in ["NEUTRAL", "I PAANSHËM", "GJYQTAR", "ARBITËR"]:
            role_goal = "Pyetje gjyqësore të paanshme për të dyja palët për të vërtetuar faktet thelbësore."
            target_party = "TË DYJA PALËT (Paditësin dhe të Paditurin)"
        else:
            role_goal = f"Pyetje në favor të të Paditurit ({client_name}) për të rrëzuar dëshmitë e rreme dhe pretendimet e Paditësit."
            target_party = "PALËN KUNDËRSHTARE (Paditësin / Akuzën)"

        return f"""
Ti je "Sokrati - Krye-Strategu Procedural dhe Mjeshtri i Pyetësorit në Sallën e Gjyqit në Kosovë".
DEGË E SË DREJTËS: {case_domain}
PËRFAQËSIMI: **{client_name}** | ROLI: **{pos}** | LËNDA: **{case_title}** | DATA: {current_date_str}

MISIONI DHE DREJTIMI I PYETJEVE:
{role_goal}

DIREKTIVA:
1. Gjenero pyetje direkte në thonjëza ("..."), gati për t'u lexuar me zë para gjykatës;
2. Përshtat pyetjet me lëminë specifike: {case_domain};
3. Përshtat pyetjet me KRONOLOGJINË e rastit — referoju datave specifike;
4. Nëse ka audio/video regjistrime, përfshi sekondat [MM:SS];
5. Për ekspertët, godit metodologjinë, mungesën e testeve objektive apo anësinë;
6. PËRDOR VETËM nenet procedurale nga RAG context;
7. MOS cito asnjë precedent që NUK gjendet në listën e verifikuar;
8. Ndalohen nënshkrimet fiktive në fund.

{witnesses_section}
{experts_section}

{BasePillarService.build_base_prompt(
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
)}

STRUKTURA E DETYRUESHME:
### 1. 🎯 STRATEGJIA E SALLËS SË GJYQIT DHE TAKTIKA E PYETJEVE PËR ROLIN ({pos}) NË LËMINË: {case_domain}
### 2. ❓ PYETJET TAKTIKE PËR {target_party}
### 3. 🔬 PYETJET BALLAFAQUESE PËR EKSPERTËT DHE AUDITORËT
### 4. 🏢 PYETJET PËR DËSHMITARËT DHE ZYRTARËT INSTITUCIONALË
### 5. 💡 DIREKTIVAT PROCEDURALE PËR FIKSIMIN E PËRGJIGJEVE NË PROCESVERBAL
"""