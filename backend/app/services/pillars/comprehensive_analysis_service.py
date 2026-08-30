# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - COMPREHENSIVE ANALYSIS V1.0 (ONE-CLICK FULL REPORT)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ComprehensiveAnalysisService:
    """
    Shërbimi i Analizës së Plotë të Rastit — V1.0.
    Një klik = Raport i plotë forenzik me 10 seksione.
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
        
        search_query = query_text or f"Analiza e plotë e rastit: {case_title}. Lëmia: {case_domain}. Roli: {pos}. Të gjitha shkeljet, provat, nenet, precedentët, dëmet, plani i veprimit."
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

        role_guard = RoleGuardService.build_role_guard(pos, client_name)

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

{role_guard}

MISIONI: Gjenero RAPORTIN E PLOTË FORENZIK për këtë rast.

STRUKTURA E DETYRUESHME E RAPORTIT:

### 1. 📋 PËRMBLEDHJA EKZEKUTIVE
(2-3 paragrafë: çka është rasti, cilat janë shkeljet kryesore, cili është rekomandimi)

### 2. 📅 KRONOLOGJIA E SAKTË E RASTIT
(Lista e ngjarjeve me data nga dokumentet)

### 3. ⚖️ SHKELJET E IDENTIFIKUARA
(Çdo shkelje me: nenin përkatës, dokumentin referencë, palën përgjegjëse)

### 4. 🔬 MATRICA E PROVAVE
(Tabela: Prova | Burimi | Rëndësia Juridike)

### 5. 👥 AKTORËT DHE ROLLET
(Tabela: Aktori | Roli | Shkeljet)

### 6. 🏛️ BAZA STATUTORE DHE PRECEDENTËT
(Nenet + Ligjet + Precedentët e verifikuar)

### 7. 🔨 OPINIONI I GJYQTARIT SUPREM
(Vlerësimi i qëndrueshmërisë së rastit)

### 8. 💶 DËMET DHE KAMATA
(Nëse ka — me shuma nga dokumentet ose [Shuma sipas faturës])

### 9. 🎯 PLANI I VEPRIMIT
(Hapat konkretë të ardhshëm me afate)

### 10. 💡 REKOMANDIMET PËRFUNDIMTARE
(Çfarë duhet të bëjë klienti TANI)

RREGULLAT E HEKURTA:
1. BAZOHU VETËM në dokumentet e fashikullit;
2. MOS shpik asnjë nen, ligj, precedent, shumë, apo fakt;
3. Çdo pretendim duhet të ketë referencë në dokument;
4. NËSE diçka mungon, shëno qartë;
5. Përfundo raportin te pika 10 — PA ASNJË NËNSHKRIM PAS.
"""