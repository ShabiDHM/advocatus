# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - SUPREME COMPREHENSIVE DOSSIER ANALYSIS V50.0 (ELITE BENCHMARK • FULL CASE SAGAS)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ComprehensiveAnalysisService:
    """
    Shërbimi Suprem i Analizës Gjithëpërfshirëse të Fashikullit (V50.0 Elitë).
    Funksioni: 'Këshilltari Kryesor Ligjor / Ish-Gjyqtari i Gjykatës Supreme të Kosovës'.
    Skanon të gjithë historikun e lëndës (Polici, QPS, Psikiatri, Gjykata, Apel, Mesazhe)
    dhe zbardh të vërtetën absolute juridike, mjetet ligjore aktive (të rregullta dhe të jashtëzakonshme),
    si dhe përgjegjësinë penale të institucioneve/gjyqtarëve për shkelje me dashje (Nenet 414 & 425 KPK).
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
        
        # Kërkim vektorial RAG gjithëpërfshirës
        search_query = query_text or (
            f"Analiza e plotë supreme e fashikullit: {case_title}. "
            f"Lëmia: {case_domain}. Klienti: {client_name} ({pos}). Të gjitha shkresat: "
            f"Policia, Prokuroria, Qendra për Punë Sociale, Ekspertizat Psikiatrike/Financiare, "
            f"Aktgjykimet e Shkallës së Parë, Apeli, Vendimet e Refuzuara dhe Provat Materiale."
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
AUTORITETI DHE MISIONI YT: ISH-GJYQTARI I GJYKATËS SUPREME TË KOSOVËS
Klienti yt (**{client_name}**) ka ardhur në zyrën tënde me NJË FASHIKULL TË TËRË dokumentesh.
Ai ka kaluar nëpër seanca, ekspertiza psikiatrike, raporte sociale të QPS-së, polici, vendime gjykate dhe ankesa në Apel.

Klienti të kërkon të vërtetën e zhveshur dhe rrugën e fitores:
1. ÇFARË KA NDODHUR REALISHT GJATË GJITHË KËTIJ PROCESI?
2. KU JANË KRYER SHKELJET PROCEDURALE DHE MATERIALE NGA INSTITUCIONET APO PALA KUNDËRSHTARE?
3. CILAT MJETE LIGJORE JANË ENDE TË HAPURA? (Mjetet e Rregullta vs. Mjetet e Jashtëzakonshme).
4. NËSE AFATET GJYQËSORE KANË KALUAR APO GJYQTARËT/ZYRTARËT KANË SHKELUR LIGJIN ME DASHJE:
   - A ka bazë për KALLËZIM PENAL për 'Keqpërdorim të Detyrës Zyrtare' (Neni 414 i KPK) apo 'Marrje të Vendimit të Kundërligjshëm Gjyqësor' (Neni 425 i KPK)?
   - A ka bazë për Kallëzim Penal për 'Deklarim të Rremë' (Neni 384 KPK) ose 'Lajmërim të Rremë' (Neni 382 KPK)?
5. CILI ËSHTË MASTER PLANI TAKTIK I DREJTËSISË (HAP-PAS-HAPI)?

RREGULLAT E HEKURTA:
- Përdor ton autoritar, të ftohtë, dinjitoz dhe thellësisht profesional të Gjykatës Supreme.
- Cito me saktësi neni-për-nen ligjet e Republikës së Kosovës (KPPRK Nr. 08/L-032, KPK Nr. 06/L-074, LPK Nr. 03/L-006, LMD Nr. 04/L-077, Kushtetuta e Kosovës).
- ZERO halucinacione. Çdo konstatim mbështetet në dokumentet e fashikullit.
======================================================================

STRUKTURA E DETYRUESHME E RAPORTIT MASTER GJITHËPËRFSHIRËS:

### 1. 🏛️ DIAGNOZA EKZEKUTIVE E HISTORIKUT ("ÇFARË KA NDODHUR REALISHT?")
* **Zanafilla dhe Rrjedha e Konfliktit:** Si nisi çështja, si u ndërlikua ndërinstitucionalisht dhe ku ndodhet lënda sot.
* **Gjendja Reale Faktike e Provuar me Shkresa:** E vërteta e dokumentuar përmes provave materiale (përtej trillimeve dhe deklaratave emocionale).
* **Pozicioni dhe Legitimiteti i Klientit ({client_name}):** Pse pozicioni i tij/saj është i drejtë sipas ligjit dhe Kushtetutës.

### 2. 🔍 KRYQËZIMI FORENZIK NDËR-INSTITUCIONAL (POLICIA, QPS, PSIKIATRIA, GJYKATA)
(Analizo veprimet e secilit organ të përfshirë në fashikull):
* 👮 **Policia & Prokuroria:** A janë kryer hetime objektive, apo ka pasur denoncime të orkestruara dhe anashkalim provash shfajësuese?
* 🏢 **QPS (Qendra për Punë Sociale):** A ka qenë raporti i tyre profesional, apo ka shfaqur njëanshmëri dhe shkelje të procedurës së vlerësimit?
* 🧠 **Psikiatria Forenzike / Ekspertët:** Çfarë konstatojnë raportet mjekësore dhe a vërtetojnë kapacitetin dhe integritetin e klientit?
* ⚖️ **Gjykata Themelore & Apeli:** A janë zbatuar afatet dhe dispozitat urdhëruese (LPK/KPPRK), apo vendimet përmbajnë shkelje thelbësore?

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET VS. PROVAT REALE NË FASHIKULL
| Pretendimi / Akuza e Palës Kundërshtare | Çfarë Vërtetojnë Shkresat & Provat Reale | Vlerësimi Forenzik (I Fabrikuar / I Pabazuar / I Rrëzuar) |
| :--- | :--- | :--- |

### 4. ⚖️ HIERARKIA E MJETEVE JURIDIKE DHE STATUSI I AFATEVE (KOSOVË)
* 🟢 **Mjetet e Rregullta Juridike:** A ka vendime të padorëzuara apo afate aktive për Ankesë (15 ditë sipas LPK/KPPRK)?
* 🟡 **Mjetet e Jashtëzakonshme Juridike:** 
  - Revizioni në Gjykatën Supreme (Neni 211 i LPK-së);
  - Kërkesa për Mbrojtje të Ligjshmërisë (Neni 432 i KPPRK-së);
  - Përsëritja e Procedurës / Kthimi në Gjendje të Mëparshme (Neni 232 / Neni 129 i LPK-së);
  - Ankesa Individuale Kushtetuese në Gjykatën Kushtetuese (Neni 113.7 i Kushtetutës për cenim të Gjykatës së Drejtë - Neni 31).

### 5. 🚨 PËRGJEGJËSIA PENALE DHE DISIPLINORE PËR SHKELJE ME DASHJE (KPK NR. 06/L-074)
(Nëse konstatohen shkelje të rënda nga institucionet, gjyqtarët apo pala kundërshtare):
* 🔴 **Kallëzimi Penal ndaj Zyrtarëve / Gjyqtarëve:**
  - *Neni 414 i KPK:* Keqpërdorimi i pozitës apo autoritetit zyrtar (nëse ka favorizim apo tejkalim kompetencash);
  - *Neni 425 i KPK:* Nxjerrja e vendimeve gjyqësore të kundërligjshme (nëse gjyqtari ka shkelur ligjin me vetëdije);
* 🔴 **Kallëzimi Penal ndaj Palës Kundërshtare / Dëshmitarëve:**
  - *Neni 382 i KPK:* Lajmërimi i rremë;
  - *Neni 384 / 385 i KPK:* Deklarimi i rremë nën betim ose ekspertiza e rreme.
* 🏛️ **Denoncimi në Këshillin Gjyqësor (KGJK) / Këshillin Prokurorial (KPK):** Për inicimin e procedurës disiplinore ndaj gjyqtarit apo prokurorit.

### 6. 🎯 MASTER PLANI I HEKURT I VEPRIMIT (STRATEGJIA E DREJTËSISË)
* 🔴 **HAPI 1 (Urgjenca Procedurale - Brenda 48 Orëve):** Depozitimi i mbrojtjes, ankesave aktive apo sigurimi i provave të rrezikuara.
* 🟡 **HAPI 2 (Mjetet e Jashtëzakonshme & Bllokimi i Ekzekutimit):** Parashtrimi i kërkesës për masë të përkohshme ose pezullim të ekzekutimit.
* 🟢 **HAPI 3 (Kundërsulmi Penal dhe Institucional):** Dorëzimi i kallëzimeve penale në Prokurorinë Speciale / Themelore ndaj personave që kanë fabrikuar prova apo shkelur ligjin me dashje.

### 7. 💡 KËSHILLA EKZEKUTIVE DHE STRATEGJIKE PËR KLIENTIN ({client_name})
* Udhëzimi kryesor i Gjyqtarit Suprem se si të veprojë me maturi, të mbajë komunikimin e dokumentuar dhe të ruajë avantazhin deri në fitoren e plotë të drejtësisë.
"""