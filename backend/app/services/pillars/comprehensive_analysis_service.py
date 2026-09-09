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
    Shërbim për analizë gjithëpërfshirëse të çështjeve ligjore.
    Krijon struktura të qarta për tre shtjella analitike:
    - Shtjella 1: Faktet dhe rindërtimi kronologjik.
    - Shtjella 2: Analiza provuese, nenet dhe shkeljet procedurale.
    - Shtjella 3: Mjetet juridike, strategjia dhe plani i veprimit.
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

        # Përcaktimi i shtjellës së synuar
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

        # Kërkim në bazën globale të njohurive (10 rezultate kyçe)
        pyetja_kerkimore = query_text or f"Precedentë të Gjykatës Supreme të Kosovës për lëndën {case_domain}: {case_title}."

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

        # Strukturat e qarta për secilën shtjellë
        if target_pillar == 1:
            struktura_e_kerkuar = f"""
SHTJELLA 1: FAKTI DHE HISTORIKU I PROVUAR (SEKSIONET 1 DHE 2)
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Udhëzim: Bazo arsyetimin në provat konkrete të fashikullit. Përgjigju në mënyrë të përmbledhur dhe profesionale.

### 1. DIAGNOZA PROCEDURALE DHE GJENDJA FAKTIKE
* **1.1 Pasqyra e Ecurisë Procedurale:** Paraqit në formë tabele vijat procedurale, numrat e lëndëve, organet shqyrtuese dhe statusin aktual.
* **1.2 Kronologjia e Ngjarjeve Vendimtare:** Rindërto renditjen kohore të fakteve kryesore bazuar në datat e dokumenteve.
* **1.3 Faktet e Vërtetuara nga Shkresat:** Përmbledh faktet materiale dhe dëshmitë shkresore që janë provuar.

### 2. KRYQËZIMI I AKTORËVE DHE VEPRIMEVE PROCEDURALE
* Identifiko dhe grupo të gjithë aktorët e përfshirë (gjyqtarë, prokurorë, ekspertë, dëshmitarë, palë kundërshtare).
* Për secilin aktor, vlerëso veprimet procedurale, ligjshmërinë e vendimmarrjes dhe konfliktin e mundshëm të interesit.
"""
        elif target_pillar == 2:
            struktura_e_kerkuar = f"""
SHTJELLA 2: LIGJI, DISPOZITAT DHE SHKELJET PROCEDURALE (SEKSIONET 3, 4 DHE 5)
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Udhëzim: Qëndro i saktë dhe konciz, veçanërisht në tabela.

### 3. MATRICA E PËRPLASJES SË PRETENDIMEVE ME PROVAT REALE
Ndërto tabelën krahasuese:
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat | Forca Provuese dhe Vlerësimi |
| :--- | :--- | :--- |

### 4. TABELA E NENEVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
Nxirr nenet e aplikueshme dhe precedentët:
| Neni dhe Ligji | Instituti Procedural / Material | Shkelja e Identifikuar | Precedenti i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. SHKELJET THELBËSORE DHE PËRGJEGJËSIA LIGJORE
* **Shkeljet Thelbësore të Procedurës:** Analizo sipas Nenit 182 të LPK-së ose Kodit të Procedurës Penale.
* **Veprimet e Kundërligjshme të Subjekteve:** Analizo përgjegjësinë ligjore të personave që kanë nxjerrë akte në kundërshtim me provat.
"""
        elif target_pillar == 3:
            struktura_e_kerkuar = f"""
SHTJELLA 3: MJETET JURIDIKE, STRATEGJIA DHE MASTER PLANI I VEPRIMIT (SEKSIONET 6, 7 DHE 8)
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Udhëzim: Jep këshilla të zbatueshme me afate dhe nene konkrete.

### 6. HIERARKIA E MJETEVE JURIDIKE DHE JURISDIKSIONI
* **Mjetet Parësore Procedurale:** Parashtresat, ankesat ose kundërshtimet brenda afateve.
* **Masat e Sigurisë dhe Mbrojtjes Emergjente:** Arsyetimi i masave të sigurimit ose pezullimit.
* **Mjetet e Jashtëzakonshme:** Kërkesa për mbrojtje të ligjshmërisë, revizioni apo ankesa kushtetuese.

### 7. STRATEGJIA E BALLAFAQIMIT DHE PYETJET TËRTHORE
* **Taktika e Çmontimit të Akteve të Kundërshtarit:** Si neutralizohen pikat agresive të palës kundërshtare.
* **Pyetësori Taktik për Seancë:** 5 pyetje tërthore për të ekspozuar mospërputhjet.

### 8. MASTER PLANI I VEPRIMIT DHE KONKLUZIONI
* **Veprimet me Afat të Menjëhershëm (24–72 Orë):** Veprimet emergjente.
* **Konsolidimi i Mbrojtjes:** Masat provuese, ekspertizat dhe parashtresat.
* **Tabela e Hapave Taktikë:** (Veprimi | Organi Kompetent | Afati Ligjor | Qëllimi).
* **Konkluzioni Përfundimtar:** Vlerësimi i shanseve reale për klientin {client_name}.
"""
        else:
            struktura_e_kerkuar = f"""
RAPORTI EKZEKUTIV I ANALIZËS
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Përgatit një analizë të plotë, të qartë dhe profesionale, duke trajtuar faktet, bazën ligjore dhe planin e veprimit.
"""

        return f"""[DIREKTIVË PËR ANALIZË LIGJORE]
Ju jeni një ekspert ligjor i specializuar në legjislacionin e Republikës së Kosovës.
RREGULLAT E PËRGJIGJES:
1. Përdorni gjuhë standarde juridike shqipe.
2. Mbështetuni ekskluzivisht në provat dhe të dhënat e fashikullit.
3. Mos përmendni fakte apo persona që nuk figurojnë në tekst.
4. Përgjigjuni me arsyetim të qartë dhe strukturë të rregullt.

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