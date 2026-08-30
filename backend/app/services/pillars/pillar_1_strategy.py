# FILE: backend/app/services/pillars/pillar_1_strategy.py
# PHOENIX PROTOCOL - PILLAR 1: ROLE-AWARE FORENSIC STRATEGY V24.0 (TIMELINE INTEGRATED)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService
import logging

logger = logging.getLogger(__name__)

class Pillar1StrategyService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 1:
    - Përshtatet 100% sipas Rolit të zgjedhur:
      * PLAINTIFF (Paditës): Ndërtimi i strategjisë sulmuese, provimi i fakteve dhe fitimi i kërkesës.
      * DEFENDANT (I Paditur): Mbrojtja e hekurt, shfajësimi dhe rrëzimi i pretendimeve.
      * NEUTRAL (I Paanshëm): Vlerësim objektiv gjyqësor i të dyja palëve pa anësi.
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
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()
        
        # PHOENIX FIX: Zbulo domenin nëse nuk është dhënë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Kërko në RAG për kontekst ligjor
        search_query = query_text or f"Strategjia ligjore për çështjen: {case_title}. Klienti: {client_name}. Pozicioni: {pos}. Lëmia: {case_domain}"
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )
        
        # PHOENIX FIX: Ndërto kronologjinë e rastit
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        if pos in ["PLAINTIFF", "PADITËS", "KALLËZUES"]:
            stance_instruction = f"""
            QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR NË MBROJTJE TË PADITËSIT / KALLËZUESIT (**{client_name}**).
            - Misioni: Ndërto të gjitha provat dhe argumentet për të PROVUAR padinë/kallëzimin tonë;
            - Identifiko të gjitha shkeljet dhe dëmet e shkaktuara nga Pala e Paditur / të Dyshuarit;
            - Ndërto planin e veprimit për të fituar 100% kërkesëpadinë, dëmshpërblimin maksimal dhe masat e sigurimit.
            """
            section_1_title = f"### 1. 🏛️ ANALIZA FORENZIKE E FASHIKULLIT DHE BAZA E PADISË SË ({client_name})"
            section_5_title = f"### 5. 🎯 PLANI TAKTIK PËR FITOREN E PADISË DHE HAPAT E ARDHSHËM TË ({client_name})"

        elif pos in ["NEUTRAL", "I PAANSHËM", "GJYQTAR", "ARBITËR"]:
            stance_instruction = f"""
            QËNDRIMI STRATEGJIK: TI JE GJYQTAR / ARBITËR 100% I PAANSHËM DHE OBJEKTIV.
            - Misioni: Analizo fashikullin pa mbajtur anën e asnjërës palë;
            - Peshon argumentet dhe provat e Paditësit kundrejt atyre të të Paditurit;
            - Identifiko pikat e forta dhe dobësitë e secilës palë dhe jep një vlerësim doktrinar të drejtë sipas ligjit.
            """
            section_1_title = "### 1. 🏛️ ANALIZA OBJEKTIVE GJYQËSORE E FASHIKULLIT DHE GJENDJA FAKTIKE"
            section_5_title = "### 5. 🎯 VLERËSIMI PËRFUNDIMTAR DHE DREJTIMET PROCEDURALE TË GJYKIMIT"

        else:  # DEFENDANT
            stance_instruction = f"""
            QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR NË MBROJTJE TË TË PADITURIT / TË DYSHUARIT (**{client_name}**).
            - Misioni: Mbrojtje e hekurt e {client_name}, rrëzimi i të gjitha pretendimeve të palës kundërshtare;
            - Shfrytëzo testet laboratorike, mesazhet, prapadatimet dhe shkeljet procedurale për të rrëzuar padinë/akuzat;
            - Ndërto planin e kundërsulmit: Prapësime, Kundërpadi, Kallëzime Penale për lajmërim të rremë dhe Mjete të Jashtëzakonshme.
            """
            section_1_title = f"### 1. 🏛️ ANALIZA FORENZIKE E TË GJITHË FASHIKULLIT: ÇKA KA NDODHUR ({client_name})?"
            section_5_title = f"### 5. 🎯 ÇFARË DUHET TË BËJË ({client_name}) TASH: PLANI I VEPRIMIT DHE HAPAT PROCEDURALË"

        # PHOENIX FIX: Përdor BasePillarService me Timeline
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
Ti je "Sokrati - Krye-Strategu Procedural dhe Auditori Ligjor në Republikën e Kosovës".
DEGË E SË DREJTËS: {case_domain}
KLIENTI / PËRDORUESI: **{client_name}** | ROLI ZYRTAR NË LËNDË: **{pos}** | LËNDA: **{case_title}** | DATA: {current_date_str}

{stance_instruction}

RREGULLA TË PËRGJITHSHME:
1. Përshtat gjuhën, strategjinë dhe matricën e provave me rolin ({pos});
2. Përshtat analizën me lëminë specifike: {case_domain};
3. Analizo afatet procedurale në bazë të KRONOLOGJISË së rastit më poshtë;
4. NËSE afatet e ankimit kanë skaduar, rekomando KALLËZIM PENAL ose KËRKESË PËR RISHQYRTIM;
5. NËSE ka masa emergjente për fëmijë, rekomando VEPRIM TË MENJËHERSHËM;
6. Fëmijët trajtohen vetëm si Palë e Dëmtuar/Viktima;
7. Ndalohen kategorikisht nënshkrimet fiktive apo inicialet në fund;
8. PËRDOR VETËM ligjet dhe nenet nga KONTEKSTI LIGJOR I VERIFIKUAR;
9. MOS cito asnjë precedent që NUK gjendet në listën e verifikuar.

{base_prompt}

STRUKTURA E DETYRUESHME E PËRGJIGJES:
{section_1_title}
### 2. 🔬 MATRICA E PROVAVE MATERIALE, SHKRESORE, SHKENCORE DHE FONOGRAMEVE
### 3. 👥 IDENTIFIKIMI SHTERUES I TË GJITHË AKTORËVE DHE ROLI I TYRE NË LËNDË
### 4. 🔨 OPINIONI DHE VLERËSIMI DOKTRINAR MBI QËNDRUESHMËRINË E LËNDËS
{section_5_title}
"""