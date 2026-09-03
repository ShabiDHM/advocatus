# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - UNIVERSAL SUPREME MASTER CASE ANALYZER V140.0 (100% ROLE-ADAPTIVE • ZERO HARDCODING)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ComprehensiveAnalysisService:
    """
    SHËRBIMI SUPREM I ANALIZËS GJITHËPËRFSHIRËSE TË DOSJES (V140.0):
    - Sintezë shterruese e të gjithë fashikullit me precedentët e Gjykatës Supreme (PML & Rev).
    - Përshtatje dinamike me pozicionin real të klientit (Paditës, I Paditur, Kundërpaditës, I Dëmtuar).
    - Zbulon kontradiktat mes provave materiale dhe pretendimeve gojore.
    - Harton automatikisht aktin e saktë procedural të radhës (Padi, Përgjigje në Padi, Kundërpadi, apo Ankesë).
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
        pos = (client_position or "PALË NË PROCEDURË").strip().upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:12000],
                manifest_str=manifest_str or ""
            )
        
        search_query = query_text or (
            f"Analiza master doktrinare e dosjes: {case_title}. "
            f"Lëmia: {case_domain}. Palët, provat materiale, aktet procedurale, shkeljet contra legem dhe Aktgjykimet e Gjykatës Supreme PML Rev."
        )
        
        # PHOENIX FIX: Tërhiqen të dyja: dituria globale statutore dhe shkresat e lëndës
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM DOKTRINAR SUPREM DHE ANALIZË E DOSJES • PRIVILEGJI I MBROJTJES DHE ANALIZËS GJYQËSORE
MANDATI YT SI TRUPË E GJYKATËS SUPREME:
Përpara teje ndodhet fashikulli i plotë i lëndës **{case_title}** për lëminë **{case_domain}**.
Detyra jote si Kolegj Konsulent i Gjykatës Supreme të Kosovës është të kryesh një autopsi ligjore të kësaj dosjeje:
1. Të kryqëzosh të gjitha provat materiale kundrejt pretendimeve të palëve për të zbuluar kontradiktat.
2. Të kualifikosh përgjegjësinë ligjore dhe shkeljet thelbësore 'Contra Legem'.
3. Të formulosh Strategjinë e Fitores dhe Draftin e Hekurt Procedural të radhës, të përshtatur rigorozisht me interesin ligjor të klientit **{client_name}** ({pos}), duke u bazuar në PRECEDENTËT E GJYKATËS SUPREME (Rev & PML).
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I DOSJES / FASHIKULLIT:
LËMIA: **{case_domain}** | KLIENTI / PARASHTRUESI: **{client_name or 'I Identifikuar në Shkresa'}** | POZICIONI PROCEDURAL: **{pos}** | TITULLI: **{case_title}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME NË KOSOVË:
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME TË KOSOVËS (NGA BAZA GLOBALE E DITURISË):
{rag_context if rag_context else "Zbato precedentët e konsoliduar të Kolegjit Penal dhe Civil të Gjykatës Supreme të Kosovës."}

📅 KRONOLOGJIA E DOKUMENTUAR E FASHIKULLIT:
{timeline_context if timeline_context else "Kronologjia po rindërtohet nga dokumentet e fashikullit."}

📄 SHKRESAT DHE PROVAT E VEKTORIZUARA TË DOSJES:
{case_rag_context if case_rag_context else "Dokumentet e fashikullit të lëndës."}

📎 PASAPORTA E DOKUMENTEVE TË NGARKUARA NË DOSJE:
{manifest_str if manifest_str else "Shkresat e fashikullit."}

======================================================================
RREGULLAT E HEKURTA TË ANALIZËS DOKTRINARE TË DOSJES:
1. PËRSHTATJE RIGOROZE ME POZICIONIN E KLIENTIT ({pos}):
   - Nëse klienti është I PADITUR: Mbrojtja duhet të ndërtojë PRAPËSIMET procedurale/materiale dhe KUNDËRPADINË. Ndalohet ta trajtosh klientin e paditur sikur po ngre padi fillestare!
   - Nëse dosja përmban një AKTVENDIM ose AKTGJYKIM të padrejtë të gjykatës: Hapi kryesor në Seksionin 7 duhet të jetë **ANKESA** drejtuar shkallës më të lartë gjyqësore!
   - Nëse klienti është PADITËS / I DËMTUAR: Ndërto Kërkesëpadinë, Masën e Sigurimit apo Kallëzimin Penal përkatës.
2. CITIMI I DETYRUESHËM I PRECEDENTËVE TË GJYKATËS SUPREME:
   - Te çdo shkelje dhe te tabela statutore, cito qëndrimet e Kolegjeve të Gjykatës Supreme (Aktgjykimet Rev për civile/tregtare, Aktgjykimet PML për penale).
3. MATRICA KRAHASUESE E TË VËRTETËS:
   - Përball fjalët gojore të palëve me provat e forta shkresore (kontrata, fatura, ekstrakte bankare, ARBK, raporte ekspertize).
4. DRAFTI I PLOTË I SEKSIONIT 7:
   - Shkruaj aktin e plotë procedural solemn gati për dorëzim zyrtar (Court-Ready), me të gjitha pikat kërkuese (Petitum-in) të detajuara.
======================================================================

{'='*60}
PËRMBAJTJA E PLOTË E TË GJITHA DOKUMENTEVE TË FASHIKULLIT:
{'='*60}
{context_str}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER TË ANALIZËS (8 SEKSIONE):

### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
* **Zanafilla dhe Kronologjia e Çështjes:** Si lindi marrëdhënia juridike, konfliktet dhe gjendja procedurale aktuale e dosjes.
* **Gjendja Reale Faktike e Dokumentuar:** Faktet e vërtetuara shkresërisht kundrejt pretendimeve të pavërtetuara.
* **Pozicioni, Legjitimiteti dhe Interesi Juridik i Klientit ({client_name} - {pos}):** Përcaktimi i saktë i të drejtave thelbësore të tij/saj.

### 2. 🔍 KRYQËZIMI I AKTORËVE, INSTITUCIONEVE DHE VLERËSIMI I PËRGJEGJËSISË
(Zbërthe rolin, veprimet me faj apo shkeljet ligjore të secilit aktor, institucion apo gjyqtari të përfshirë në fashikull).

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET VS. PROVAT REALE NË FASHIKULL
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat Reale të Fashikullit | Vlerësimi Doktrinar & Forca Provuese |
| :--- | :--- | :--- |

### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE E PRECEDENTËVE SUPREMË
| Dispozita & Ligji i Zbatueshëm | Instituti Ligjor / Procedural | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme (PML / Rev / Komentari) |
| :--- | :--- | :--- | :--- |

### 5. 🚨 PËRGJEGJËSIA LIGJORE, SHKELJET 'CONTRA LEGEM' DHE BAZA PROCEDURALE
* 🔴 **Shkeljet Thelbësore (Contra Legem):** (Zbërthe shkeljet e rënda procedurale dhe materiale të evidentuara në fashikull).
* ⚖️ **Kualifikimi i Përgjegjësisë:** (Përcakto përgjegjësinë ligjore: civile, dëmshpërblim, penale, apo administrative).

### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE DHE PROGNOZA SUPREME
* 🟢 **Mjetet e Rregullta Juridike:** Afatet prekluzive aktive dhe organet kompetente.
* 🟡 **Mjetet e Jashtëzakonshme Juridike:** Revizioni, Kërkesa për Mbrojtje të Ligjshmërisë, apo Ankesa Kushtetuese (Neni 113.7).

### 7. 🛠️ DRAFTI I PLOTË ZYRTAR I AKTIT TË RADHËS PROCEDURALE
(Harto aktin e plotë solemn të përshtatur me nevojën reale të dosjes: ANKESË nëse goditet vendim gjyqësor, PËRGJIGJE NË PADI / KUNDËRPADI nëse klienti është i paditur, apo PADI / KALLËZIM nëse kërkohet fillimi i procedurës):
* **Organi Kompetent dhe Palët Procedurale**
* **Lënda dhe Vlera e Kontestit (nëse ka)**
* **Baza Ligjore dhe Arsyetimi i Fakteve**
* **PJESA KËRKUESE SOLEMNE (PETITUM-I I DETARUAR ME PONTË TË NUMËRUARA)**

### 8. 🎯 MASTER PLANI I VEPRIMIT: STRATEGJIA E FITORES DHE HAPAT TAKTIKË
* 🔴 **HAPI 1 (Urgjenca / Veprimi brenda 24-48 Orë):** Veprimi më kritik procedural (ankesa, prapësimi, sigurimi i provave).
* 🟡 **HAPI 2 (Veprimet Hetimore & Ekspertizat):** Përgatitja e provave materiale dhe propozimi i ekspertizave.
* 🟢 **HAPI 3 (Strategjia në Seancë & Përmbyllja):** Pyetjet kyçe dhe taktika e fitores në gjykatë.
"""