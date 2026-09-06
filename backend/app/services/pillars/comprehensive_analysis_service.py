# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI I AUTOPSISË FORENZIKE ME 3 SHTJELLA MODULARE V233.0
# ZERO TRUNCATION • HIGH-DENSITY BALANCED MATRICES • SAKTËSI DOKTRINARE SUPREME (CLAUDE SONNET 4.6)

import logging
import re
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ComprehensiveAnalysisService:
    """
    SHËRBIMI I AUTOPSISË FORENZIKE ME 3 SHTJELLA TË PAVARURA (V233.0):
    - 100% I Balancuar: Çdo shtjellë gjenerohet brenda buxhetit optimal të tokenëve pa asnjë ndërprerje.
    - Shtjella 1: Fakti dhe Historiku (Seksionet 1 dhe 2 të plota).
    - Shtjella 2: Ligji dhe Shkeljet (Seksionet 3, 4 dhe Seksioni 5 i plotë 5.1 deri 5.6).
    - Shtjella 3: Strategjia dhe Plani i Veprimit (Seksionet 6, 7 dhe 8 me afate 48-orëshe).
    - Saktësia: Zero humbje e neneve, shkeljeve procedurale dhe precedentëve supremë.
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
        
        # Zbulimi i Shtjellës së Kërkuar nga Query
        target_pillar = 0
        if "SHTJELLA_1" in query_upper or "PJESA_1" in query_upper or "FAKTI DHE HISTORIKU" in query_upper or "FAKTI & HISTORIKU" in query_upper:
            target_pillar = 1
        elif "SHTJELLA_2" in query_upper or "PJESA_2" in query_upper or "LIGJI DHE SHKELJET" in query_upper or "SHKELJET & NENET" in query_upper:
            target_pillar = 2
        elif "SHTJELLA_3" in query_upper or "PJESA_3" in query_upper or "PLANI I VEPRIMIT" in query_upper or "KUNDËRSHTIMET & PLANI" in query_upper:
            target_pillar = 3

        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:15000],
                manifest_str=manifest_str or ""
            )
        
        pyetja_kerkimore = query_text or (
            f"Precedentët supremë të Gjykatës Supreme të Kosovës për lëndën: {case_title}. "
            f"Lëmia parësore: {case_domain}. Përgjegjësia penale e personave zyrtarë dhe gjyqtarëve sipas nenit 383 të Kodit Penal, "
            f"keqpërdorimi i detyrës zyrtare sipas nenit 414 të Kodit Penal, falsifikimi i dokumentit zyrtar sipas nenit 427 të Kodit Penal, "
            f"cenimi i barazisë së palëve sipas nenit 193 të Kodit Penal, ushtrimi i ndikimit sipas nenit 424 të Kodit Penal, "
            f"kompetenca e Prokurorisë Speciale, frikësimi gjatë procedurës sipas nenit 386 të Kodit Penal, "
            f"shkelja e detyrës nga avokati sipas nenit 392 të Kodit Penal, rehabilitimi ligjor sipas nenit 93 të Kodit Penal, "
            f"masat emergjente të mbrojtjes, Aktgjykimet PML dhe Revizionet e Gjykatës Supreme."
        )
        
        baza_globale, baza_lendes = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=pyetja_kerkimore,
            n_results=35
        )
        
        rrjedha_kohore = ""
        if db is not None and case_id:
            rrjedha_kohore = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)

        # Udhëzimi Modular me Balancim të Hekurt të Densitetit
        if target_pillar == 1:
            struktura_e_kerkuar = f"""
TI JE DUKE GJENERUAR EKSKLUZIVISHT:
# JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
## SHTJELLA 1: FAKTI DHE HISTORIKU (SEKSIONET 1 DHE 2)
**LËNDA:** {case_title} | **KLIENTI:** {client_name} ({pozicioni}) | **DATA:** {current_date_str}

---

### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
* **1.1 Sinteza Ekzekutive e Fashikullit:** Ndarja e 5 vijave procedurale (Tabela: Vija Procedurale | Nr. i Lëndës | Gjykata/Organi | Statusi Aktual).
* **1.2 Kronologjia e Datave dhe Ngjarjeve Reale:** Rindërtimi kronologjik i datave vendimtare (Tabela e dendur: Data | Ngjarja/Akti | Burimi në Fashikull | Vlerësimi Forenzik).
* **1.3 Gjendja Reale Faktike e Provuar:** Provat materiale shkencore të pakundërshtueshme (Testi negativ i drogës Koslabor, regjistri i komunikimeve babë-bir, ekstraktet zyrtare).

### 2. 🔍 KRYQËZIMI I AKTORËVE, INSTITUCIONEVE DHE VLERËSIMI I VEPRIMEVE
(Strukturo me emra nga dosja të 5 grupet e aktorëve: Grupi I Gjyqtarët, Grupi II Prokurorët/Policia, Grupi III Mjekët e QKUK, Grupi IV QPS & ZMV, Grupi V Pala Kundërshtare & Avokatët. Për secilin grup jep funksionin, veprat e dyshuara dhe rolin strukturor).

Përfundo plotësisht këtë Shtjellë 1 deri te fjala e fundit e Seksionit 2!
"""
        elif target_pillar == 2:
            struktura_e_kerkuar = f"""
TI JE DUKE GJENERUAR EKSKLUZIVISHT:
# JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
## SHTJELLA 2: LIGJI DHE SHKELJET (SEKSIONET 3, 4 DHE 5)
**LËNDA:** {case_title} | **KLIENTI:** {client_name} ({pozicioni}) | **DATA:** {current_date_str}

---

RREGULL I HEKURT I DENSITETIT: Në qelitë e tabelave ji i saktë, i prerë dhe i ngjeshur (2–3 fjali për qeli). Ndalohen hyrjet e përsëritura. Kjo garanton që Seksioni 5 të shkruhet i plotë deri në fund!

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET KUNDREJT PROVAVE REALE NË FASHIKULL
(Tabelë me 8–10 pikat kryesore të konfliktit të nxjerra nga dosja):
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat Reale të Fashikullit | Vlerësimi Doktrinar dhe Forca Provuese |
| :--- | :--- | :--- |

### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE E PRECEDENTËVE TË GJYKATËS SUPREME
(Tabela me 8–10 nenet kryesore të Kosovës dhe precedentët supremë PML dhe Revizion):
| Dispozita dhe Ligji i Zbatueshëm | Instituti Ligjor / Procedural | Analiza Doktrinare dhe Shkelja | 🏛️ Precedenti i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. 🚨 PËRGJEGJËSIA LIGJORE DHE KUALIFIKIMI I VEPREVE PENALE (ZERO ZBUTJE DISIPLINORE)
(Shkruaj të gjitha nën-seksionet e plota me konkluzione të prera):
* 🔴 **5.1 Gjyqtari Bujar Dobërdolani:** (Nenet 383, 414, 427, 382 të Kodit Penal — prapadatimet, shkelja e Nenit 93 të rehabilitimit, refuzimi i testit toksikologjik).
* 🔴 **5.2 Gjyqtarja Shpresa Veselaj:** (Nenet 383, 414, 382 të Kodit Penal — dëbimi arbitrar nga salla, aktgjykimi vetë-kontradiktor).
* 🔴 **5.3 Gjyqtari Sabit Sadikaj:** (Nenet 383, 414 të Kodit Penal — mbajtja e aktakuzës së manipuluar).
* 🔴 **5.4 Kolegji i Gjykatës së Apelit (Sallauka, Ajvazi, Bllaca Dula):** (Neni 383 i Kodit Penal — vërtetimi i aktvendimit duke shpërfillur provat shkencore dhe Nenin 93 KPK).
* ⚖️ **5.5 Zyrtarët Publikë, Ekspertët dhe Ndikimi Politik:** (Nazlie Bala Nenet 414/424, Bekim Dugolli Nenet 386/414, Dr. Samire Braina Nenet 387/427, Jehona Misini Nenet 250/382/414, Ibadete Rexha-Aliu, Emi Zeqiri, Myrvete Hashani-Jashari Neni 392).
* 🛑 **5.6 Pala Kundërshtare Sanije Bala:** (Kallëzimi i rremë Neni 398, Pengimi i të drejtave Neni 197, Dhuna në familje Nenet 248/250 KPK).

Përfundo plotësisht këtë Shtjellë 2 deri te fjala e fundit e Seksionit 5.6 pa u ndërprerë kurrë!
"""
        elif target_pillar == 3:
            struktura_e_kerkuar = f"""
TI JE DUKE GJENERUAR EKSKLUZIVISHT:
# JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
## SHTJELLA 3: KUNDËRSHTIMET, RREZIQET DHE PLANI I VEPRIMIT (SEKSIONET 6, 7 DHE 8)
**LËNDA:** {case_title} | **KLIENTI:** {client_name} ({pozicioni}) | **DATA:** {current_date_str}

---

### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE DHE JURISDIKSIONI I DUHUR
* 🔴 **Ndjekja Penale dhe Kompetenca e Organeve Hetuese (Prokuroria Speciale sipas Ligjit Nr. 08/L-168 / Prokuroria Themelore).**
* 🟢 **Mjetet Parësore të Degës Kryesore (Civile / Familjare):** Ankesa ndaj Aktgjykimit C.nr.5906/25, masa e sigurimit për pasaportën.
* 🟡 **Mjetet e Jashtëzakonshme dhe Kushtetuese:** Kërkesa për Mbrojtje të Ligjshmërisë, Revizioni në Gjykatën Supreme, Gjykata Kushtetuese (Nenet 31 dhe 54).

### 7. 💡 REKOMANDIMET STRATEGJIKE TË KONSULENCËS SUPREME
* **Analiza Kosto / Kohë / Efektivitet e rrugëve procedurale.**
* **Strategjia e Sulmit dhe Mbrojtjes (Plani A - Kryesor vs Plani B - Alternativ).**
* **Neutralizimi i Pretendimeve të Palës Kundërshtare.**

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM TAKTIKË
* 🔴 **HAPI 1 (Urgjenca brenda 24 deri në 48 Orëve):** Veprimet emergjente procedurale.
* 🟡 **HAPI 2 (Konsolidimi Provues dhe Goditja Procedurale):** Ekspertizat e pavarura dhe kallëzimet penale.
* 🟢 **HAPI 3 (Zhdëmtimi dhe Mbrojtja Supreme / Kushtetuese):** Paditë për kompensim dëmi (Neni 162 LMD), revizioni.
* 📊 **Tabela Përmbledhëse e Master Planit me Afate Konkrete.**
* 🏁 **Konkluzioni Doktrinar Suprem dhe Vlerësimi Final i Perspektivës Procedurale.**

Përfundo plotësisht këtë Shtjellë 3 deri te fjala e fundit!
"""
        else:
            struktura_e_kerkuar = f"""
# JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
## RAPORTI MASTER I AUTOPSISË SË THELLË DOKTRINARE DHE STRATEGJISË GJYQËSORE
**LËNDA:** {case_title} | **KLIENTI:** {client_name} ({pozicioni}) | **DATA:** {current_date_str}

Gjenero raportin e plotë duke përfshirë të 8 Seksionet në mënyrë të balancuar dhe shteruese deri te fjala e fundit e Seksionit 8.
"""

        return f"""
<konteksti_i_autopsise_forenzike_dhe_doktrines_supreme>
JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
REPUBLIKA E KOSOVËS • EKSPERTIZË DOKTRINARE E PROVAVE DHE MBROJTJE GJYQËSORE

MANDATI YT SUPREM:
Përpara teje ndodhet fashikulli i plotë i çështjes **{case_title}**.
Ti vepron si Kolegj Këshillues i Gjykatës Supreme të Kosovës.
RREGULL I HEKURT: Përgjigju VETËM në gjuhën standarde juridike të Republikës së Kosovës. Ndalohet kategorikisht përdorimi i fjalëve apo shprehjeve në gjuhën angleze.
Detyra jote është të përfundosh 100% strukturën e kërkuar më poshtë pa u ndërprerë kurrë në mes!
</konteksti_i_autopsise_forenzike_dhe_doktrines_supreme>

{mbrojtja_rolit}

📋 IDENTIFIKIMI I FASHIKULLIT DHE KLIENTIT:
TITULLI I ÇËSHTJES: **{case_title}**
KLIENTI / PARASHTRUESI: **{client_name or 'I Identifikuar në Shkresa'}**
CILËSIA PROCEDURALE: **{pozicioni}**
LËMIA PARËSORE E IDENTIFIKUAR: **{case_domain}**
DATA E AUDITIMIT DOKTRINAR: {current_date_str}

{toni_rolit}

🏛️ PRECEDENTËT SUPREMË:
{baza_globale if baza_globale else "Zbato precedentët e konsoliduar të Gjykatës Supreme të Kosovës (Revizionet dhe PML)."}

📅 KRONOLOGJIA:
{rrjedha_kohore if rrjedha_kohore else "Rindërtohet kronologjikisht nga të gjitha shkresat e fashikullit."}

📄 SHKRESAT E LËNDËS:
{baza_lendes if baza_lendes else "Fashikulli dokumentar i administruar."}

📎 PASAPORTA E DOKUMENTEVE:
{manifest_str if manifest_str else "Dokumentet e fashikullit."}

{'='*60}
FASHIKULLI I PLOTË I SHKRESAVE TË LËNDËS:
{'='*60}
{context_str}
{'='*60}

STRUKTURA E DETYRUESHME QË DUHET TË GJENEROSH TANI:
{struktura_e_kerkuar}
"""