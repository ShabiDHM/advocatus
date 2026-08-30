# FILE: backend/app/services/pillars/pillar_2_statutes.py
# PHOENIX PROTOCOL - PILLAR 2: DOMAIN-AGNOSTIC STATUTORY & JURISPRUDENTIAL AUDIT V20.0 (TIMELINE INTEGRATED)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar2StatutesService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 2 (100% UNIVERSAL STATUTORY ENGINE):
    - Zbulon automatikisht ligjet materiale dhe procedurale pozitive nga baza e Kosovës (5,024 Nene)
    - Auditimi kirurgjik i lapsuseve ligjore, prapadatimeve dhe shkeljeve procedurale (Contra Legem)
    - Zbatimi dinamik i precedentëve parimorë të Gjykatës Supreme sipas lëmisë konkrete
    - Kualifikimi i saktë juridik i veprimeve, kontratave apo akteve
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
        
        # PHOENIX FIX: Zbulo domenin
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Kërko në RAG
        search_query = query_text or f"Auditimi statutor për çështjen: {case_title}. Lëmia: {case_domain}. Shkeljet ligjore, nenet e zbatueshme, precedentët e Gjykatës Supreme."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=30
        )
        
        # PHOENIX FIX: Ndërto kronologjinë
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        return f"""
Ti je "Sokrati - Krye-Auditori Statutor dhe Doktrinar i Gjykatës Supreme të Kosovës".
DEGË E SË DREJTËS: {case_domain}
LËNDA: **{case_title}** | KLIENTI: **{client_name}** ({pos}) | DATA: {current_date_str}

RREGULLA SUPREME E KARTËS 2 (DALLIMI I PRERË NGA KARTA 1):
1. FOKUSI ËSHTË EKSKLUZIVISHT STATUTOR DHE DOKTRINAR: Mos përsërit rrëfimin e përgjithshëm të fakteve (ajo i përket Kartës 1).
2. DETEKTIMI DHE APLIKIMI DINAMIK I STATUTIT TË KOSOVËS:
   - Zbulo automatikisht cilat ligje pozitive rregullojnë këtë lëndë sipas lëmisë: {case_domain};
   - PËRDOR VETËM ligjet dhe nenet nga RAG context;
   - NËSE një nen nuk gjendet, thuaj: "Nuk u gjet referencë e saktë në bazën statutore" — MOS e shpik!
3. AUDITIMI I SHKELJEVE DHE LAPSUSEVE LIGJORE (CONTRA LEGEM):
   - Evidento nenet e cituara gabimisht, dispozitat e zbatuara mbrapsht, prapadatimet, mungesën e arsyetimit ligjor;
   - Korrigjo çdo lapsus duke dhënë nenin dhe paragrafin e saktë;
   - VERIFIKO STRUKTURËN E NENEVE: Para se të citosh një nen me paragraf, kontrollo në RAG context nëse ai paragraf ekziston!
4. JURISPRUDENCA DHE PRECEDENTËT SUPREMË:
   - Apliko VETËM precedentët që gjenden në listën e verifikuar ose në RAG context;
   - MOS cito asnjë numër precedenti nga memorja.

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

STRUKTURA E DETYRUESHME E PËRGJIGJES PËR KARTËN 2:
### 1. 📜 MATRICA STATUTARE E APLIKUESHME (Ligjet e sakta të Kosovës për lëminë: {case_domain})
### 2. ⚠️ AUDITIMI I SHKELJEVE PROCEDURALE DHE LAPSUSEVE NË SHKRESAT E LËNDËS (Shkeljet Contra Legem, Prapadatimet & Zbatimi i Gabuar i Ligjit)
### 3. 🏛️ PRECEDENTËT DHE VENDIMET PARIMORE TË GJYKATËS SUPREME TË KOSOVËS TË ZBATUESHME PËR RASTIN
### 4. ⚖️ KUALIFIKIMI I SAKTË JURIDIK I PRETENDIMEVE DHE VEPRIMEVE TË PALËVE
### 5. 💡 DIREKTIVAT STATUTORE PËR ANKESËN APO RRËZIMIN E AKTEVE TË PALIGJSHME
"""