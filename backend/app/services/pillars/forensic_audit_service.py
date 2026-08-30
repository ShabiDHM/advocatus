# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - FORENSIC AUDIT SPECIALIST V27.0 (100% UNIVERSAL DOCUMENT AUDIT)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul i Pavarur Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (⚖️):
    - Auditim 100% UNIVERSAL i çdo dokumenti juridik
    - Draft, Padi, Kallëzim Penal, Kundërpadi, Prapësim, Ankesë, Kontratë, Marrëveshje,
      Vendim Gjykate, Aktvendim, Aktgjykim, Urdhër Mbrojtje, Ekspertizë, Raport Social,
      Procesverbal, apo çdo dokument tjetër ligjor
    - Verifikimi nen-për-nen i ligjshmërisë pozitive të Kosovës
    - Korrigjimi i lapsuseve ligjore (Contra Legem)
    - ZERO HALUCINACIONE + ZERO NËNSHKRIM FIKTIV
    """

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> tuple:
        """
        Zbulon llojin e dokumentit dhe kthen (kategoria, përshkrimi).
        """
        combined = f"{file_name} {document_text[:5000]}".lower()
        
        # Lista e gjerë e kategorive
        categories = [
            ("KALLËZIM PENAL", ["kallëzim penal", "kallezim penal", "kallzim penal"], 
             "Audito nëse kallëzimi penal është i bazuar në ligj, nëse nenet e KPRK-së dhe KPPRK-së janë të sakta, nëse kompetenca e Prokurorisë është e saktë, dhe nëse provat mbështesin pretendimet."),
            ("VENDIM GJYKATE", ["aktvendim", "aktgjykim", "vendim i gjykatës", "vendimi i gjykatës"],
             "Audito nëse vendimi është i bazuar në ligj, nëse ka shkelje procedurale, nëse ka bazë për ankim, dhe rekomando hapat e ardhshëm."),
            ("URDHËR MBROJTJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "urdhermbrojtje"],
             "Audito nëse urdhërmbrojtja është e ligjshme, nëse masat janë proporcionale, dhe nëse ka bazë për ankim."),
            ("PADI / KËRKESËPADI", ["kërkesëpadi", "kerkesepadi", "padi ", "padia"],
             "Audito nëse padia është e bazuar në ligj, nëse nenet janë të sakta, nëse petitumi është i argumentuar, dhe rekomando si ta forcosh ose si të mbrohesh."),
            ("KUNDËRPADI", ["kundërpadi", "kunderpadi"],
             "Audito nëse kundërpadia është e bazuar në ligj dhe nëse është e argumentuar si duhet."),
            ("PRAPËSIM", ["prapësim", "prapsim"],
             "Audito nëse prapësimi është i argumentuar dhe nëse ka shkelje."),
            ("ANKESË", ["ankesë", "ankese", "ankim", "apel"],
             "Audito nëse ankesa është e bazuar në shkelje reale dhe nëse është e argumentuar."),
            ("KONTRATË / MARRËVESHJE", ["kontratë", "kontrate", "marrëveshje", "marreveshje"],
             "Audito nëse kontrata është e ligjshme, nëse nenet janë të sakta, dhe nëse ka lapsuse."),
            ("EKSPERTIZË", ["ekspertizë", "ekspertize", "raport eksperti"],
             "Audito nëse ekspertiza është e bazuar në ligj, nëse metodologjia është e saktë, dhe nëse ka anësi."),
            ("RAPORT SOCIAL / QPS", ["raport social", "qps", "qendra për punë sociale", "qendra per pune sociale"],
             "Audito nëse raporti social është i njëanshëm, nëse ka shkelje, dhe nëse është në përputhje me ligjin."),
            ("PROCESVERBAL", ["procesverbal", "proces verbali"],
             "Audito nëse procesverbali ka shkelje procedurale, nëse ka prapadatime, dhe nëse është i ligjshëm."),
            ("DRAFT", [], 
             "Audito draftin — verifiko nenet, ligjet, lapsuset, dhe rekomando përmirësime para dorëzimit."),
        ]
        
        for category, keywords, _ in categories:
            if not keywords:  # DRAFT është default
                continue
            for kw in keywords:
                if kw in combined:
                    return category, categories[[c[0] for c in categories].index(category)][2]
        
        return "DRAFT", "Audito draftin — verifiko nenet, ligjet, lapsuset, dhe rekomando përmirësime para dorëzimit."

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
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str or ""
            )
        
        audit_text = document_text or context_str
        
        # PHOENIX FIX: Zbulo kategorinë dhe përshkrimin
        doc_category, category_description = ForensicAuditService.detect_document_category(audit_text)
        
        search_query = query_text or f"Auditimi forenzik i {doc_category}: {case_title}. Lëmia: {case_domain}. Verifiko nenet dhe ligjet."
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
            manifest_str=manifest_str or "",
            context_str=context_str,
            case_domain=case_domain,
            rag_context=rag_context,
            case_rag_context=case_rag_context,
            timeline_context=timeline_context
        )

        return f"""
{base_prompt}

📄 LLOJI I DOKUMENTIT PËR AUDITIM: {doc_category}

🎯 MISIONI SPECIFIK I AUDITIMIT:
{category_description}

RREGULLAT SHTESË TË AUDITIMIT:
1. Nëse dokumenti është DRAFT, fokuso në përmirësimin para dorëzimit;
2. Nëse dokumenti është VENDIM GJYKATE, fokuso në gjetjen e shkeljeve për ankim;
3. Nëse dokumenti është PADI ose KALLËZIM, fokuso në dobësitë dhe si të mbrohesh;
4. Gjithmonë verifiko çdo nen me RAG context;
5. Gjithmonë verifiko çdo precedent me listën e lejuar;
6. Përfundo raportin te pika 5 — PA ASNJË NËNSHKRIM.

{'='*60}
TEKSTI I PARAQITUR PËR AUDITIM FORENZIK:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT:
### 1. 🔍 ANALIZA E PËRGJITHSHME E DOKUMENTIT DHE NATYRA JURIDIKE (Lëmia: {case_domain})
### 2. ⚖️ VERIFIKIMI NEN PËR NEN I BAZËS LIGJORE
### 3. ⚠️ LAPSUSET LIGJORE DHE KORRIGJIMI (CONTRA LEGEM & NENET E SAKTA)
### 4. 🏛️ OPINIONI DOKTRINAR MBI QËNDRUESHMËRINË
### 5. 💡 REKOMANDIMET KONKRETE

RAPORTI PËRFUNDON TE PIKA 5. MOS SHKRUAJ ASNJË NËNSHKRIM PAS PIKËS 5.
"""