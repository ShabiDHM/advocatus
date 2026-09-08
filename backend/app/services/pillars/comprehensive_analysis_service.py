# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - COMPREHENSIVE FORENSIC AUTOPSY ENGINE V235.0 (STREAM-OPTIMIZED & ZERO HARDCODING)
# GJUHË E PASTËR JURIDIKE SHQIPE • DINAMIKE PËR ÇDO LËNDË • ZERO TRUNCATION

import logging
import re
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ComprehensiveAnalysisService:
    """
    MOTORI I AUTOPSISË FORENZIKE ME 3 SHTJELLA TË PAVARURA (V235.0):
    - I Optimizuar për Streaming: Pa ndërprerje, pa timeout, dhe pa tejkalim token-ash.
    - Zero Hardcoding: Nxjerr emrat, gjyqtarët, provat dhe nenet EKSKLUZIVISHT nga fashikulli real.
    - Shtjella 1: Fakti dhe Rindërtimi Kronologjik i Ngjarjeve (Seksionet 1 dhe 2).
    - Shtjella 2: Analiza Provuese, Tabela e Neneve dhe Shkeljet Procedurale (Seksionet 3, 4 dhe 5).
    - Shtjella 3: Mjetet Juridike, Strategjia e Seancës dhe Plani i Veprimit (Seksionet 6, 7 dhe 8).
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
        pozicioni = (client_position or "PALË NË PROCEDURË").strip().upper()
        query_upper = (query_text or "").upper()
        
        # Përcaktimi i Shtjellës së Synuar
        target_pillar = 0
        if any(term in query_upper for term in ["SHTJELLA_1", "PJESA_1", "FAKTI DHE HISTORIKU", "FAKTI & HISTORIKU"]):
            target_pillar = 1
        elif any(term in query_upper for term in ["SHTJELLA_2", "PJESA_2", "LIGJI DHE SHKELJET", "SHKELJET & NENET"]):
            target_pillar = 2
        elif any(term in query_upper for term in ["SHTJELLA_3", "PJESA_3", "PLANI I VEPRIMIT", "KUNDËRSHTIMET & PLANI", "KUNDËRSHTIMET, RREZIQET"]):
            target_pillar = 3

        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:8000],
                manifest_str=manifest_str or ""
            )

        # Kërkim preciz në RAG (10 rezultate kyçe në vend të 35 për të parandaluar ndërprerjen)
        pyetja_kerkimore = query_text or f"Precedentët supremë të Gjykatës Supreme të Kosovës (Revizionet dhe PML) për lëndën {case_domain}: {case_title}."
        
        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id=case_id or "",
                query_text=pyetja_kerkimore,
                n_results=10
            )
        except Exception as rag_err:
            logger.warning(f"RAG lookup warning: {rag_err}")

        rrjedha_kohore = ""
        if db is not None and case_id:
            try:
                rrjedha_kohore = BasePillarService.get_timeline_context(
                    db=db,
                    case_id=case_id,
                    user_id=user_id or ""
                )
            except Exception:
                pass

        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)

        # =========================================================================
        # STRUKTURAT E QARTA DHE TË BALANCUARA PËR SECILËN SHTJELLË
        # =========================================================================
        if target_pillar == 1:
            struktura_e_kerkuar = f"""
SHTJELLA 1: FAKTI DHE HISTORIKU I PROVUAR (SEKSIONET 1 DHE 2)
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Udhëzim: Bazo arsyetimin rreptësisht në provat konkrete të fashikullit. Përgjigju në mënyrë të përmbledhur e profesionale.

### 1. DIAGNOZA PROCEDURALE DHE GJENDJA FAKTIKE
* **1.1 Pasqyra e Ecurisë Procedurale:** Paraqit në formë tabele vijat procedurale, numrat e lëndëve, organet shqyrtuese dhe statusin aktual.
* **1.2 Kronologjia e Ngjarjeve Vendimtare:** Rindërto renditjen kohore të fakteve kryesore bazuar në datat e dokumenteve dhe shkresave të administruara.
* **1.3 Faktet e Vërtetuara nga Shkresat:** Përmbledh faktet materiale dhe dëshmitë shkresore që janë provuar pa dyshim.

### 2. KRYQËZIMI I AKTORËVE DHE VEPRIMEVE PROCEDURALE
* Identifiko dhe grupo të gjithë aktorët e përfshirë në këtë çështje (Gjyqtarët, Prokurorët, Ekspertët, Dëshmitarët dhe Palët Kundërshtare).
* Për secilin aktor të evidentuar në dosje, vlerëso veprimet procedurale, ligjshmërinë e vendimmarrjes dhe konfliktin e mundshëm të interesit.
"""
        elif target_pillar == 2:
            struktura_e_kerkuar = f"""
SHTJELLA 2: LIGJI, DISPOZITAT DHE SHKELJET PROCEDURALE (SEKSIONET 3, 4 DHE 5)
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Udhëzim: Qëndro i saktë dhe konciz në qelitë e tabelave (2–3 fjali për qeli) për të garantuar rrjedhje të plotë pa u ndërprerë.

### 3. MATRICA E PËRPLASJES SË PRETENDIMEVE ME PROVAT REALE
Ndërto tabelën krahasuese midis pretendimeve të palës kundërshtare dhe asaj që vërtetojnë provat materiale:
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat e Fashikullit | Forca Provuese dhe Vlerësimi Doktrinar |
| :--- | :--- | :--- |

### 4. TABELA E NENEVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
Nxirr të gjitha nenet e aplikueshme të legjislacionit pozitiv të Kosovës dhe precedentët përkatës:
| Neni dhe Ligji i Zbatueshëm | Instituti Procedural / Material | Shkelja e Identifikuar | 🏛️ Precedenti i Gjykatës Supreme (PML / Rev) |
| :--- | :--- | :--- | :--- |

### 5. SHKELJET THELBËSORE DHE PËRGJEGJËSIA LIGJORE
* **Shkeljet Thelbësore të Procedurës:** Analizo shkeljet sipas Nenit 182 të LPK-së ose Kodit të Procedurës Penale (mungesa e arsyetimit, kundërthëniet, shkelja e barazisë së armëve).
* **Veprimet e Kundërligjshme të Subjekteve:** Analizo përgjegjësinë ligjore të personave që kanë nxjerrë akte në kundërshtim me provat materiale apo kompetencën ligjore.
"""
        elif target_pillar == 3:
            struktura_e_kerkuar = f"""
SHTJELLA 3: MJETET JURIDIKE, STRATEGJIA DHE MASTER PLANI I VEPRIMIT (SEKSIONET 6, 7 DHE 8)
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Udhëzim: Jep këshilla taktike të zbatueshme drejtpërdrejt në procedurë gjyqësore, me afate dhe nene konkrete.

### 6. HIERARKIA E MJETEVE JURIDIKE DHE JURISDIKSIONI
* **Mjetet Parësore Procedurale:** Parashtresat, ankesat ose kundërshtimet brenda afateve ligjore prekluzive.
* **Masat e Sigurisë dhe Mbrojtjes Emergjente:** Arsyetimi i masave të sigurimit ose pezullimit të ekzekutimit të aktit.
* **Mjetet e Jashtëzakonshme:** Kërkesa për mbrojtje të ligjshmërisë, revizioni apo ankesa kushtetuese.

### 7. STRATEGJIA E BALLAFAQIMIT DHE PYETJET TËRTHORE
* **Taktika e Çmontimit të Akteve të Kundërshtarit:** Si neutralizohen pikat më agresive të palës përballë.
* **Pyetësori Taktik për Seancë:** 5 pyetje tërthore kryesore për të ekspozuar mospërputhjet në seancë dëgjimore.

### 8. MASTER PLANI I VEPRIMIT DHE KONKLUZIONI
* **Veprimet me Afat të Menjëhershëm (24–72 Orë):** Veprimet emergjente procedurale.
* **Konsolidimi i Mbrojtjes:** Masat plotësuese provuese, ekspertizat dhe parashtresat kryesore.
* **Tabela e Hapave Taktikë:** (Veprimi | Organi Kompetent | Afati Ligjor | Qëllimi).
* **Konkluzioni Përfundimtar:** Vlerësimi përmbyllës i shanseve reale të suksesit ligjor për klientin {client_name}.
"""
        else:
            struktura_e_kerkuar = f"""
RAPORTI EKZEKUTIV I AUTOPSISË FORENZIKE
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Përgatit autopsinë e plotë në mënyrë të qartë, të balancuar dhe profesionale, duke trajtuar faktet, bazën ligjore dhe planin e veprimit.
"""

        return f"""[DIREKTIVË E EKSPERTIZËS FORENZIKE • JURISTI AI]
Ju jeni Konsulenca Supreme e Ekspertizës Forenzike dhe Procedurale për Republikën e Kosovës.
RREGULLAT E PËRGJIGJES:
1. Përdorni gjuhë standarde juridike të Kosovës (pa fjalë të huaja të panevojshme).
2. Mbështetuni EKSKLUZIVISHT në provat, emrat dhe të dhënat reale që gjenden në fashikullin e kësaj lënde.
3. Ndalohet përmendja e personave apo fakteve nga lëndë të tjera që nuk figurojnë në tekstin e mëposhtëm.
4. Përgjigjuni me arsyetim të prerë, të dendur dhe të strukturuar bukur me tituj dhe pika.

{mbrojtja_rolit}

TË DHËNAT E ÇËSHTJES:
- Titulli: {case_title}
- Klienti: {client_name or 'I papërcaktuar'}
- Pozicioni: {pozicioni}
- Lëmia: {case_domain}
- Data e Analizës: {current_date_str}

{toni_rolit}

BURIMI I PRECEDENTËVE DHE DOKUMENTET:
{baza_globale if baza_globale else 'Zbato precedentët e konsoliduar të Gjykatës Supreme të Kosovës.'}

{rrjedha_kohore if rrjedha_kohore else ''}

{'='*50}
PËRMBAJTJA E FASHIKULLIT TË LËNDËS:
{'='*50}
{context_str[:35000]}
{'='*50}

STRUKTURA QË DUHET TË GJENERONI:
{struktura_e_kerkuar}"""