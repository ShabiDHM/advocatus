# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - FORENSIC AUDIT SPECIALIST V30.0 (RIGOROUS LEGAL COMPLIANCE & ZERO HALLUCINATION)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService
import logging

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (⚖️):
    - Auditim 100% UNIVERSAL dhe Rigoroz i çdo shkrese juridike në Kosovë.
    - Verifikimi nen-për-nen i ligjeve pozitive (LPK, KPK, KPPRK, LMD, Ligji për Familjen, etj.).
    - Zbulimi i gabimeve 'Contra Legem', shkeljeve procedurale dhe dobësive të petitumit.
    - ZERO HALUCINACIONE — Çdo vlerësim ankorohet me ligj dhe prova.
    """

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> tuple:
        """
        Zbulon automatikisht llojin e dokumentit ligjor me prioritet hierarkik.
        """
        combined = f"{file_name} {document_text[:6000]}".lower()
        
        categories = [
            ("KALLËZIM PENAL", ["kallëzim penal", "kallezim penal", "kallzim penal", "vepër penale", "veper penale"], 
             "Audito bazueshmërinë penale, elementet e veprës penale sipas KPRK, kompetencën e Prokurorisë dhe provat materiale."),
            ("AKTGJYKIM / VENDIM GJYKATE", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore"],
             "Audito ligjshmërinë e vendimit, shkeljet thelbësore procedurale (LPK/KPPRK), zbatimin e gabuar të së drejtës materiale dhe bazën për ANKESË."),
            ("URDHËR MBROJTJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "dhunë në familje", "dhune ne familje"],
             "Audito proporcionalitetin e masave mbrojtëse, afatet ligjore dhe bazueshmërinë sipas Ligjit për Mbrojtje nga Dhuna në Familje."),
            ("PADI / KËRKESËPADI", ["kërkesëpadi", "kerkesepadi", "paditësi", "paditesi", "padia kundër"],
             "Audito rregullsinë e padisë, kompetencën gjyqësore, qartësinë e Petitumit (kërkesës) dhe prapësimet e mundshme mbrojtëse."),
            ("KUNDËRPADI / PRAPËSIM", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
             "Audito forcën e prapësimeve procedurale dhe materiale, afatet e dorëzimit dhe provat kundërshtuese."),
            ("ANKESË / APEL", ["ankesë", "ankese", "drejtuar gjykatës së apelit", "kundër aktgjykimit"],
             "Audito pikat ankimore: shkeljet procedurale, vërtetimin e gabuar të gjendjes faktike dhe shkeljet materiale."),
            ("KONTRATË / MARRËVESHJE", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese"],
             "Audito ligjshmërinë e klauzolave sipas LMD-së, rreziqet e pavlefshmërisë absolute/relative dhe penalitetet."),
            ("RAPORT SOCIAL / QPS", ["raport social", "qps", "qendra për punë sociale", "interesi më i mirë i fëmijës"],
             "Audito objektivitetin e raportit social, metodologjinë dhe përputhshmërinë me Ligjin për Familjen."),
            ("EKSPERTIZË FINANCIARE / TEKNIKE", ["ekspertizë", "ekspertize", "raporti i ekspertit", "eksperti financiar"],
             "Audito metodologjinë, kufijtë e autorizimit të ekspertit dhe përputhjen me provat në shkresa."),
            ("DRAFT JURIDIK", [], 
             "Audito draftin për saktësi neni-për-nen, qartësi formulimi dhe eliminimin e lapsuseve para dorëzimit në gjykatë.")
        ]
        
        for category, keywords, desc in categories:
            if not keywords:
                continue
            for kw in keywords:
                if kw in combined:
                    return category, desc
        
        return "DRAFT JURIDIK", "Audito draftin për saktësi neni-për-nen, qartësi formulimi dhe eliminimin e lapsuseve para dorëzimit në gjykatë."

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
        
        audit_text = (document_text or context_str).strip()
        doc_category, category_description = ForensicAuditService.detect_document_category(audit_text)
        
        search_query = query_text or f"Auditimi ligjor i {doc_category}: {case_title}. Nenet e ligjit të Kosovës, shkeljet, rreziqet, afatet."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=35
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
            manifest_str=manifest_str or "",
            context_str=context_str,
            case_domain=case_domain,
            rag_context=rag_context,
            case_rag_context=case_rag_context,
            timeline_context=timeline_context
        )

        return f"""
{base_prompt}

{role_guard}

📄 KATEGORIA E DOKUMENTIT NË AUDITIM: **{doc_category}**
🎯 OBJEKTIVI SPECIFIK: {category_description}

======================================================================
UDHËZUESI I HEKURT I EKSPERTIT FORENZIK LIGJOR:
1. Ti je Auditori Kryesor Ligjor. Detyra jote është të gjesh çdo gabim, lapsus, nen të pasaktë apo shkelje procedurale.
2. MOS SHPIK asnjë nen. Përdor VETËM legjislacionin në fuqi në Republikën e Kosovës.
3. Nëse dokumenti ka shkelje "CONTRA LEGEM" (në kundërshtim me ligjin e zbatueshëm), theksoje me alarm të kuq: [KRITIKE - CONTRA LEGEM].
4. Vlerëso saktësinë e Petitumi-t (kërkesës përfundimtare) — a është i zbatueshëm nga përmbaruesi/gjykata?
======================================================================

{'='*60}
TEKSTI I PLOTË I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK TË AUDITIMIT:

### 1. 🔍 PASAPORTA E DOKUMENTIT DHE RREGULLSIA FORMALE
* **Lloji i Shkresës:** {doc_category}
* **Gjykata / Organi Kompetent:** (A është kompetente lëndorisht dhe territorialisht?)
* **Legjitimimi i Palëve:** (A janë identifikuar saktë Paditësi/I Padituri/Përfaqësuesi?)
* **Objekti dhe Vlera e Kontestit:** (A është e përcaktuar qartë vlera në EUR?)
* **Afatet Ligjore dhe Rregullsia:** (A është brenda afatit ligjor të parashikuar me ligj?)

### 2. ⚖️ VERIFIKIMI NEN-PËR-NEN I BAZËS LIGJORE
(Ndërto tabelën e verifikimit të neneve të përmendura ose që duhej të përmendeshin):
| Neni & Ligji i Përmendur | Statusi Ligjor | Analiza & Përputhshmëria |
| :--- | :--- | :--- |
| *p.sh. Neni 123 i LPK* | *I Saktë / I Pasaktë / Contra Legem* | *Shpjegimi nëse ky nen mbështet këtë kërkesë* |

### 3. ⚠️ GJETJET DHE LAPSUSET LIGJORE (CONTRA LEGEM & SHKELJET)
(Rendit të gjitha dobësitë, mangësitë ose gabimet e shkresës):
* 🔴 **[Rrezik Madhor / Contra Legem]:** Përshkrimi i gabimit që mund të rrëzojë shkresën.
* 🟡 **[Lapsus Procedural / Formal]:** Gabime teknike, formulime të paqarta ose mungesë provash referuese.

### 4. 🔬 AUDITIMI I PETITUMIT (KËRKESËS PËRFUNDIMTARE)
* A është kërkesa e qartë, e numëruar saktë dhe e ekzekutueshme?
* Çfarë rrezikon të refuzohet nga gjyqtari për shkak të formulimit të gabuar?

### 5. 🛠️ KORRIGJIMI DHE FORMULIMI I SUGJERUAR (REMEDIIMI)
* **Teksti i Korrigjuar:** Jep draft-paragrafin e saktë ligjor se si duhet të rishkruhet pjesa me gabime.
* **Hapat e Menjëhershëm:** Çfarë duhet plotësuar para se të dorëzohet shkresa në gjykatë/prokurori.
"""