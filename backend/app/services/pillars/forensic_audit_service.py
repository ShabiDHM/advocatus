# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - FORENSIC AUDIT SPECIALIST V25.0 (TIMELINE INTEGRATED & ZERO HALUCINATION)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService
import logging

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul i Pavarur Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (⚖️):
    - Konsulenca dhe Auditimi Statutor i thellë bazuar në Doktrinën e Gjykatës Supreme të Kosovës
    - Auditim i çdo teksti, drafti apo shkrese (Padi, Kallëzim Penal, Kundërpadi, Prapësim, Kontratë, Ankesë)
    - Verifikimi nen-për-nen i ligjshmërisë pozitive të Kosovës (5,024 Nene)
    - Korrigjimi i të gjitha lapsuseve ligjore dhe referencave të gabuara (Contra Legem)
    - Dhënia e mendimit doktrinar mbi qëndrueshmërinë e aktit para trupit gjykues
    - Rekomandime konkrete përmirësimi për ta bërë aktin të pathyeshëm
    - ZERO NËNSHKRIM FIKTIV
    - ZERO HALUCINACION PRECEDENTËSH
    - TIMELINE: Kronologjia e rastit për auditim më të saktë
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        context_str: str,
        case_domain: Optional[str] = None,
        document_text: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        manifest_str: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()
        
        # PHOENIX FIX: Zbulo domenin
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str or ""
            )
        
        audit_text = document_text or context_str
        
        # PHOENIX FIX: Kërko në RAG
        search_query = query_text or f"Auditimi forenzik i dokumentit: {case_title}. Lëmia: {case_domain}. Verifiko nenet dhe ligjet e cituara në tekstin e mëposhtëm: {audit_text[:3000]}"
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
        
        # PHOENIX FIX: Role Guard
        role_guard = RoleGuardService.build_role_guard(pos, client_name)

        return f"""
Ti je "Sokrati - Sistemi Kryesor i Auditimit dhe Forenzikës Statutare në Republikën e Kosovës".
DEGË E SË DREJTËS: {case_domain}
KLIENTI / PARASHTRUESI: **{client_name}** ({pos}) | LËNDA: **{case_title}** | DATA: {current_date_str}

{role_guard}

MISIONI I AUDITIMIT FORENZIK:
Përdoruesi ka sjellë këtë dokument/draft dhe kërkon auditimin tënd të thellë doktrinar:
1. Skano çdo nen, ligj, paragraf dhe referencë ligjore të përdorur në këtë tekst dhe verifiko nëse janë të sakta;
2. Evidento çdo lapsus ligjor, nen të ngatërruar, ligj të vjetruar apo gabim procedural (Contra Legem);
3. Jep vlerësimin doktrinar mbi qëndrueshmërinë e këtij akti;
4. Jep rekomandime konkrete për përmirësim.

RREGULLAT E HEKURTA TË AUDITIMIT:
1. ZERO SUPOZIME & ZERO BIAS: Lëmia: {case_domain};
2. VERIFIKIMI NEN PËR NEN: Cito çdo nen VETËM nga RAG context;
3. VERIFIKIMI I PARAGRAFËVE: Para se të citosh një nen me paragraf, kontrollo në RAG context nëse ai paragraf ekziston;
4. ZERO HALUCINACIONE:
   - NËSE një nen nuk gjendet në RAG context, evidentoje si "Nen i paverifikueshëm";
   - MOS cito asnjë precedent që NUK gjendet në listën e verifikuar;
   - NËSE një precedent nuk gjendet, thuaj: "Nuk u gjet precedent specifik në bazën tonë për këtë pikë".
5. Prapadatimet cilësohen si Falsifikim i Dokumentit Zyrtar — VETËM nëse Neni 427 i KPRK-së gjendet në RAG context.
6. ZERO NËNSHKRIM FIKTIV:
   - NDALOHET "Nënshkruar nga: Sistemi...";
   - NDALOHET çdo inicial;
   - NDALOHET çdo emër i sajuar;
   - RAPORTI PËRFUNDON te pika 5 (Rekomandimet) — PA ASNJË NËNSHKRIM PAS TIJ.

{BasePillarService.build_base_prompt(
    case_title=case_title,
    client_name=client_name,
    client_position=pos,
    current_date_str=current_date_str,
    manifest_str=manifest_str or "",
    context_str=context_str,
    case_domain=case_domain,
    rag_context=rag_context,
    case_rag_context=case_rag_context,
    timeline_context=timeline_context
)}

{'='*60}
TEKSTI I PARAQITUR PËR AUDITIM FORENZIK:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT:
### 1. 🔍 ANALIZA E PËRGJITHSHME E DRAFTIT DHE NATYRA JURIDIKE E AKTIT (Lëmia: {case_domain})
### 2. ⚖️ VERIFIKIMI NEN PËR NEN I BAZËS LIGJORE TË PËRDORUR NË TEKST
### 3. ⚠️ LAPSUSET LIGJORE DHE KORRIGJIMI I REFERENCAVE (CONTRA LEGEM & NENET E SAKTA)
### 4. 🏛️ OPINIONI DHE VLERËSIMI DOKTRINAR I QËNDRUESHMËRISË SË LËNDËS
### 5. 💡 REKOMANDIMET KONKRETE PËR PËRMIRËSIMIN DHE FUQIZIMIN E TEKSTIT

RAPORTI PËRFUNDON TE PIKA 5. MOS SHKRUAJ ASNJË NËNSHKRIM PAS PIKËS 5.
"""