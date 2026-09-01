# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME FORENSIC AUDIT SPECIALIST V50.0 (ELITE BENCHMARK • SINGLE DOCUMENT AUDIT)

import logging
import re
from typing import Dict, Any, Optional, Tuple
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (🔬):
    Konsulenca Supreme e Dokumentit të Vetëm:
    - Analizon çdo shkresë të vetme (Aktgjykim, Aktvendim, Kallëzim Penal, Padi, Prapësim, Kontratë, Urdhërmbrojtje, Ekspertizë).
    - Shpjegon në mënyrë ekzekutive se çfarë është dokumenti dhe çfarë pasojash prodhon.
    - Auditon ligjshmërinë nen-për-nen sipas legjislacionit pozitiv të Kosovës (KPPRK Nr. 08/L-032, KPK Nr. 06/L-074, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139).
    - Zbulon shkeljet 'Contra Legem', afatet prekluzive dhe ofron draft-remediimin e gatshëm për gjykatë.
    """

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> Tuple[str, str]:
        """
        Zbulon llojin e dokumentit ligjor me saktësi kirurgjikale.
        """
        combined = f"{file_name} {document_text[:8000]}".lower()
        
        categories = [
            ("AKTAKUZË / AKTAKUZE", ["aktakuzë", "aktakuze", "ngre aktakuzë", "vepër penale nga neni", "dispozitivi i aktakuzës"],
             "Audito ligjshmërinë e hetimeve, përshkrimin e figurës së veprës penale sipas KPK, provat e papranueshme (Neni 257 KPPRK) dhe bazën për HEDHJEN e aktakuzës (Neni 244-245 KPPRK)."),
            
            ("KALLËZIM PENAL", ["kallëzim penal", "kallezim penal", "kallzim penal", "parashtruesi i kallëzimit", "denoncim penal"], 
             "Audito bazueshmërinë ligjore, elementet e veprës penale sipas KPK, kompetencën e prokurorisë dhe fuqinë provuese të shkresave."),
            
            ("AKTGJYKIM / AKTVENDIM", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore", "trupi gjykues"],
             "Audito ligjshmërinë e vendimit, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), arsyetimin e mangët dhe bazën e hekurt për ANKESË."),
            
            ("ANKESË / APEL", ["ankesë", "ankese", "drejtuar gjykatës së apelit", "kundër aktgjykimit", "pikat ankimore"],
             "Audito respektimin e afatit ligjor prekluziv, forcën e pikave ankimore dhe saktësinë e kërkesës ankimore (prishje/ndryshim)."),
            
            ("URDHËR MBROJTJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "dhunë në familje", "dhune ne familje", "masat mbrojtëse"],
             "Audito proporcionalitetin e masave, afatet procedurale dhe bazueshmërinë sipas Ligjit Nr. 08/L-185 për Parandalimin dhe Mbrojtjen nga Dhuna në Familje."),
            
            ("PADI / KËRKESËPADI", ["kërkesëpadi", "kerkesepadi", "paditësi", "paditesi", "padia kundër", "petitum"],
             "Audito rregullsinë formale të padisë, kompetencën gjyqësore, qartësinë e Petitumit, legjitimimin e palëve dhe bazën statutore sipas LMD/LPK."),
            
            ("KUNDËRPADI / PRAPËSIM", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
             "Audito forcën e prapësimeve procedurale (kompetenca, parashkrimi) dhe prapësimeve materiale kundërshtuese."),
            
            ("KONTRATË / MARRËVESHJE", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese", "neni 1", "klauzolë"],
             "Audito ligjshmërinë e klauzolave sipas LMD-së, rreziqet e pavlefshmërisë absolute/relative dhe barrën e penaliteteve."),
            
            ("RAPORT SOCIAL / QPS", ["raport social", "qps", "qendra për punë sociale", "interesi më i mirë i fëmijës", "vlerësimi social"],
             "Audito objektivitetin metodologjik, mungesën e njëanshmërisë dhe përputhshmërinë me Ligjin për Familjen."),
            
            ("EKSPERTIZË FINANCIARE / TEKNIKE", ["ekspertizë", "ekspertize", "raporti i ekspertit", "eksperti financiar", "super-ekspertizë"],
             "Audito metodologjinë llogaritëse, tejkalimin e kompetencave dhe përputhjen me provat shkresore."),
            
            ("DRAFT JURIDIK / PARASHTRESË", [], 
             "Audito shkresën për saktësi neni-për-nen, qartësi formulimi, respektim afatesh dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë.")
        ]
        
        for category, keywords, desc in categories:
            if not keywords:
                continue
            for kw in keywords:
                if kw in combined:
                    return category, desc
        
        return "DRAFT JURIDIK / PARASHTRESË", "Audito shkresën për saktësi neni-për-nen, qartësi formulimi, respektim afatesh dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë."

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
        
        search_query = query_text or f"Auditimi forenzik i {doc_category}: {case_title}. Nenet e ligjit të Kosovës, shkeljet procedurale, afatet prekluzive, contra legem."
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

📄 DOKUMENTI NË AUDITIM TË VETËM: **{doc_category}**
🎯 OBJEKTIVI I KONTROLLIT: {category_description}

======================================================================
AUTORITETI YT: ISH-GJYQTARI I GJYKATËS SUPREME (KONSULENCA E DOKUMENTIT)
Përdoruesi (Avokat ose Qytetar) ka ardhur në zyrën tënde me KËTË DOKUMENT TË VETËM në dorë dhe të kërkon:
1. ÇFARË ËSHTË KY DOKUMENT DHE ÇFARË KËRKON/VENDOS EKZAKTËSISHT?
2. A ËSHTË I SAKTË APO KA SHKELJE LIGJORE DHE KURTHE?
3. CILAT NENE TË KOSOVËS JANË ZBATUAR DHE A JANË ZBATUAR DREJT? (Formatoji qartë që të verifikohen me bazën ligjore).
4. EKZAKTËSISHT ÇFARË DUHET TË BËJË KLIENTI TANI (Brenda sa ditësh dhe me çfarë shkrese)?

RREGULLAT E HEKURTA:
- Përgjigju me autoritet absolut doktrinar, qartësi kristalore dhe pa zhargon boshe.
- Përdor VETËM legjislacionin në fuqi të Republikës së Kosovës (KPPRK Nr. 08/L-032, KPK Nr. 06/L-074, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139).
- Nëse gjen shkelje ligjore flagrante, shënoje menjëherë: 🔴 **[KRITIKE - CONTRA LEGEM]**.
- ZERO halucinacione.
======================================================================

{'='*60}
TEKSTI I DOKUMENTIT NË AUDITIM:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK TË DOKUMENTIT:

### 1. 🔍 DIAGNOZA EKZEKUTIVE E DOKUMENTIT ("ÇFARË ËSHTË DHE ÇFARË VENDOSET/KËRKOHET?")
* **Lloji i Aktit Juridik:** {doc_category}
* **Organi / Gjykata & Numri i Lëndës:** (Identifiko organin lëshues, departamentin dhe numrin zyrtar të protokollit).
* **Thelbi me Fjalë të Qarta:** Përmblidh në 3-4 fjali të qarta: Kush kërkon, çfarë kërkohet, çfarë është vendosur dhe çfarë pasoje direkte ka për {client_name}.
* **Statusi i Afatit Ligjor:** (Sa ditë afat ka për reagim? Sa ditë kanë mbetur nga data e pranimit?).

### 2. ⚖️ VERIFIKIMI NEN-PËR-NEN I BAZËS LIGJORE (REPUBLIKA E KOSOVËS)
(Ndërto tabelën e saktë të verifikimit për çdo nen të përmendur ose që është dashur të zbatohet):
| Dispozita & Ligji i Zbatueshëm | Statusi i Pajtueshmërisë | Analiza Forenzike & Pasojat Juridike |
| :--- | :--- | :--- |

### 3. ⚠️ GJETJET KRITIKE, SHKELJET PROCEDURALE DHE GABIMET "CONTRA LEGEM"
* 🔴 **[KRITIKE - CONTRA LEGEM]:** Shkeljet thelbësore materiale ose procedurale (p.sh. shkelje e Nenit 384 KPPRK, tejkalim i kompetencës, mungesë legjitimiteti, prova të marra paligjshëm Neni 257 KPPRK).
* 🟡 **[Lapsuse Formale & Rreziqe Taktike]:** Gabime në shuma, mungesë vulash, emra të gabuar, mungesë autorizimi (Neni 90 LPK) ose arsyetim kontradiktor.

### 4. 🔬 AUDITIMI I PETITUMIT DHE EKZEKUTUESHMËRISË
* A është kërkesa (petenumi) e formuluar saktë dhe a ka rrezik të refuzohet nga gjyqtari?
* Në rast aktgjykimi/urdhëri: A mund të përmbarohet nga përmbaruesi privat sipas Ligjit për Procedurën Përmbarimore (LPP), apo ka pengesa ligjore?

### 5. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-FORMULIMI (REMEDIIMI)
* **Paragrafi i Saktë Ligjor:** Jep draft-formulimin e saktë se si duhet të rishkruhet kërkesa, ankesa apo prapësimi për të eliminuar gabimet e gjetura.

### 6. 🎯 UDHËZUESI I MENJËHERSHËM I VEPRIMIT: ÇFARË DUHET TË BËSH SOT
* 🔴 **HAPI 1 (Urgjencë - Brenda Afatit):** Shkresa e saktë që duhet të depozitohet (p.sh. Ankesë kundër Aktgjykimit brenda 15 ditëve, Përgjigje në Padi brenda 30 ditëve, apo Prapësim).
* 🟢 **HAPI 2 (Provat Shtesë):** Çfarë dokumenti apo prove duhet t'i bashkëngjitet kësaj shkrese për ta bërë të pathyeshme.
"""