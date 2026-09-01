# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - COMPREHENSIVE MASTER ANALYSIS V40.0 (SUPREME COURT FORENSIC ADVISOR)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ComprehensiveAnalysisService:
    """
    Shërbimi Suprem i Analizës Forenzike të Lëndës (V40.0 Elitë).
    Funksioni: 'Këshilltari Kryesor Ligjor / Ish-Gjyqtari i Gjykatës Supreme'.
    Merr të gjithë fashikullin e lëndës (Polici, QPS, Psikiatri, Gjykata, Mesazhe)
    dhe zbardh të vërtetën absolute juridike, shkeljet ndërinstitucionale dhe planin e fitores.
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
        
        # Kërkim vektorial i thellë për të kapur të gjitha institucionet (Polici, QPS, Gjykata, Ekspertiza)
        search_query = query_text or (
            f"Analiza gjithëpërfshirëse forenzike e lëndës: {case_title}. "
            f"Klienti: {client_name} ({pos}). Të gjitha shkresat: Policia, Qendra për Punë Sociale (QPS), "
            f"Psikiatria Forenzike, Vendimet Gjyqësore, Procesverbalet, Komunikimet dhe Provat Materiale."
        )
        
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=40
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

======================================================================
AUTORITETI DHE IDENTITETI Y yt:
Ti je Këshilltari Kryesor Ligjor me përvojën e një Krye-Gjyqtari të Gjykatës Supreme.
Para teje ndodhet një fashikull i tërë me shkresa nga institucione të ndryshme:
(Raporte Policie, Vlerësime të Qendrës për Punë Sociale - QPS, Ekspertiza Psikiatrike Forenzike, Aktgjykime, Procesverbale Seancash dhe Komunikime Private).

Klienti yt (**{client_name}**) të ka besuar të gjitha shkresat dhe kërkon të dijë:
1. ÇFARË KA NDODHUR REALISHT NË KËTË LËNDË? (Të vërtetën e zhveshur nga manipulimet)
2. KU JANË SHKELUR PROCEDURAT DHE LIGJET NGA INSTITUCIONET APO PALA TJETËR?
3. CILAT JANË PROVAT TONA TË PATHYESHME DHE KU ËSHTË KURTHI I PALËS TJETËR?
4. EKZAKTËSISHT ÇFARË DUHET TË BËJË AVOKATI DHE KLIENTI TANI HAP-PAS-HAPI PËR TË FITUAR DREJTËSINË?

RREGULLAT E HEKURTA:
- Përdor ton autoritar, të qartë, dinjitoz dhe thellësisht profesional.
- Mos përdor fjalë të përgjithshme; përmend me emër dokumentet, institucionet, datat dhe provat reale.
- Zbulo menjëherë njëanshmëritë (nëse QPS apo ndonjë ekspert ka favorizuar palën tjetër pa prova).
- ZERO halucinacione. Çdo konkluzion duhet të bazohet në shkresat e administruara.
======================================================================

STRUKTURA E RAPORTIT MASTER FORENZIK:

### 1. 🏛️ DIAGNOZA EKZEKUTIVE E LËNDËS ("ÇFARË KA NDODHUR REALISHT?")
* **Sinopsisi i Konfliktit:** Si filloi çështja, si u ndërlikua ndër-institucionalisht dhe ku ndodhet lënda sot.
* **Gjendja Reale Faktike e Provuar:** Cila është e vërteta që del nga shkresat (përtej akuzave dhe deklaratave emocionale).
* **Pozicioni i Klientit ({client_name}):** Pse pozicioni i tij/saj është i drejtë ligjërisht dhe ku mbështetet.

### 2. 🔍 KRYQËZIMI FORENZIK NDËR-INSTITUCIONAL (POLICIA, QPS, PSIKIATRIA, GJYKATA)
(Analizo veprimet e secilit institucion të përfshirë):
* 👮 **Policia & Prokuroria:** A ka pasur hetime korrekte, apo denoncime të rreme/të orkestruara?
* 🏢 **Qendra për Punë Sociale (QPS):** A është raporti i tyre objektiv? A kanë zbatuar Parimin e Interesit Më të Mirë të Fëmijës, apo kanë shfaqur njëanshmëri procedurale?
* 🧠 **Psikiatria Forenzike / Ekspertët:** Çfarë konstatojnë raportet mjekësore? A mbështesin stabilitetin dhe prindërimin/aftësinë e klientit?
* ⚖️ **Gjykata Themelore:** Cilat vendime/urdhëresa janë marrë deri më sot dhe a janë zbatuar rregullat e LPK-së?

### 3. 🔬 MATRICA E TË VËRTETËS FAKTIKE VS. PRETENDIMEVE TË PALËS KUNDËRSHTARE
| Pretendimi i Palës Kundërshtare | Çfarë Vërtetojnë Shkresat & Provat Reale | Vlerësimi Forenzik (Manipulim / I Pabazuar / I Provuar) |
| :--- | :--- | :--- |

### 4. ⚖️ SHKELJET LIGJORE DHE BAZA STATUTORE E APLIKUESHME (KOSOVË)
* Nenet kyçe të legjislacionit ({case_domain}, Ligji për Familjen, LPK, Kodi Penal) që mbrojnë drejtpërdrejt {client_name}.
* Shkeljet materiale dhe procedurale të kryera nga pala kundërshtare apo institucionet.

### 5. 🔨 OPINIONI DOKTRINAR I GJYQTARIT SUPREM (VLERËSIMI I QËNDRUESHMËRISË)
* **Shanset Reale të Suksesit:** Vlerësimi i ftohtë i lëndës nëse trajtohet nga një trup gjykues i shkallës së dytë (Apeli / Gjykata Supreme).
* **Pikat e Forca të Pakontestueshme:** Cilat prova e vulosin fitoren e klientit.
* **Rreziqet dhe Dobësitë që Duhen Mbyllur:** Ku mund të tentojë të godasë pala tjetër.

### 6. 💶 ASPEKTI FINANCIAR / ALIMENTACIONI / DËMET
(Nëse aplikohet në këtë rast):
* Analiza e kërkesave financiare kundrejt të ardhurave reale dhe mundësive financiare të dokumentuara me prova bankare/vërtetime.

### 7. 🎯 MASTER PLANI I VEPRIMIT: ÇFARË DUHET TË BËSH TANI (HAPAT E HEKURT)
* 🔴 **HAPI 1 (I Menjëhershëm - Brenda 48 Orëve):** Shkresat, prapësimet, ankesat apo kërkesat për përjashtim që duhen dorëzuar menjëherë.
* 🟡 **HAPI 2 (Veprimet Administrative & Institucionale):** Kundërshtimi i raporteve të njëanshme (nëse ka raport social apo ekspertizë me shkelje, si duhet atakuar formalisht).
* 🟢 **HAPI 3 (Taktika në Seancë Gjyqësore):** Pyetjet direkte dhe provat që duhen kërkuar gjatë seancës për të çmontuar pretendimet e palës tjetër.

### 8. 💡 KËSHILLA PËRFUNDIMTARE EKZEKUTIVE PËR KLIENTIN ({client_name})
(Udhëzimi kryesor me fjalë të qarta njerëzore dhe strategjike se si të ruajë qetësinë, provat dhe avantazhin ligjor deri në përmbylljen e plotë të rastit).
"""