# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - UNIVERSAL SUPREME MASTER CASE ANALYZER V150.0 (DEEP FORENSIC AUTOPSY • TRANSCRIPT INCIDENTS • ZERO HARDCODING)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ComprehensiveAnalysisService:
    """
    SHËRBIMI SUPREM I ANALIZËS GJITHËPËRFSHIRËSE DHE AUTOPSISË FORENZIKE (V150.0):
    - 100% Dinamik, Shkencor dhe Universal për çdo lëndë ligjore në Kosovë (Civil, Penal, Komercial, Administrativ).
    - ZERO Hardcoding: Asnjë emër, numër lënde, shumë apo datë e gatshme në kod.
    - Skaner i thellë i procesverbaleve: zbulon prapadatimet (antidatum), shabllonet dhe censurimin e procesverbaleve.
    - Skaner i incidenteve në sallë: zbulon kërcënimet e ekspertëve, përjashtimet arbitrare dhe dëbimet nga salla.
    - Verifikim i pavarësisë së ekspertizave kundrejt provave shkencore objektive.
    - Doktrina e Dy-Frontësisë: Zhvillon paralelisht Linjën Materiale/Civile dhe Linjën Penale të Zyrtarëve Publikë.
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
            f"Autopsia master forenzike e dosjes: {case_title}. Lëmia: {case_domain}. "
            f"Procesverbalet, prapadatimet, shkeljet procedurale, ekspertizat kontradiktore, përgjegjësia penale e zyrtarëve dhe Aktgjykimet Supreme PML Rev."
        )
        
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

        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM DOKTRINAR SUPREM DHE AUTOPSI FORENZIKE E FASHIKULLIT GJYQËSOR
MANDATI YT SI TRUPË E GJYKATËS SUPREME TË KOSOVËS:
Përpara teje ndodhet fashikulli i plotë dokumentar i çështjes **{case_title}** (Lëmia: **{case_domain}**).
Mandati yt është të kryesh një AUTOPSI FORENZIKE TË THELLË DHE TË PAANSHEM të çdo shkrese, procesverbali, vendimi dhe ekspertize të administruar në dosje.
Ti nuk duhet të mjaftohesh me narrativën sipërfaqësore të palëve, por duhet të zbulosh mekanizmin real të prapaskenës institucionale, shkeljet e ligjit dhe kontradiktat thelbësore.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 PASAPORTA E DOSJES NË AUDITIM:
LËMIA: **{case_domain}** | PARASHTRUESI: **{client_name or 'I Identifikuar në Shkresa'}** | CILËSIA PROCEDURALE: **{pos}** | TITULLI: **{case_title}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E RELEVANTË TË GJYKATËS SUPREME (PML & Rev):
{rag_context if rag_context else "Zbato legjislacionin pozitiv të Kosovës dhe praktikat e konsoliduara të Kolegjeve të Gjykatës Supreme."}

📅 KRONOLOGJIA E REVERIFIKUAR E NGJARJEVE:
{timeline_context if timeline_context else "Rindërtohet dinamikisht nga shkresat e fashikullit."}

📄 INDEKSI I DOKUMENTEVE TË FASHIKULLIT TË NGARKUAR:
{manifest_str if manifest_str else "Dokumentet e fashikullit."}

======================================================================
RREGULLAT E HEKURTA TË AUTOPSISË FORENZIKE (ZERO OMISSIONS • ZERO BLINDSPOTS):

1. AUTOPSIA E PROCESVERBALEVE DHE SHKRESAVE FORMALE (ZBULIMI I PARAFABRIKIMIT):
   - KRAHASO DATAT E SEANCAVE ME KRYERREISHTAT: Kontrollo nëse procesverbalet e seancave të datave të ndryshme mbajnë data të prapavendosura (Antidatum) ose shabllone të gatshme, çka dëshmon paragjykim dhe parafabrikim të vendimmarrjes.
   - KONTROLLO CENZURËN PROCEDURALE: Evidento nëse gjykata apo organi procedues ka refuzuar të shënojë në procesverbal denoncimet, kërkesat e palës apo kundërshtimet thelbësore.

2. SKANIMI I ZHVILLIMEVE NË SALLË TË GJYKIMIT DHE INSTITUCIONE:
   - Identifiko çdo incident procedural të dokumentuar: kërcënime ose presione verbale ndaj dëshmitarëve apo ekspertëve gjatë seancave;
   - Verifiko nëse ekspertë të caktuar janë përjashtuar arbitrarisht sapo kanë dhënë mendim profesional të pavarur, për t'u zëvendësuar me ekspertë të tjerë;
   - Verifiko nëse pala është dëbuar arbitrarisht me forcë nga salla e gjykimit për të vazhduar seancën në mungesë, duke cenuar barazinë e armëve (Neni 31 i Kushtetutës, Neni 6 i KEDNJ).

3. KRYQËZIMI I EKSPERTIZAVE ME TË DHËNAT SHKENCORE OBJEKTIVE:
   - Asnjë raport ekspertize apo konstatim mjekësor/social/financiar nuk duhet pranuar verbërisht:
     * Krahaso konstatimet e ekspertëve me analizat shkencore objektive (teste laboratorike, ekstrakte bankare, regjistrat publikë ARBK, etj.).
     * Nëse një ekspert/zyrtar ka injoruar një provë shkencore ekzistuese, ose ka pranuar në procesverbal se diagnozën/konstatimin e ka mbështetur në thënie gojore të personave të tretë apo zyrtarëve me pushtet, kualifikoje këtë si ekspertizë të rreme (Neni 387 KPRK) dhe keqpërdorim të detyrës (Neni 414 KPRK).

4. VERIFIKIMI I HISTORIKUT PENAL DHE REHABILITIMIT LIGJOR (NENI 93 KPRK):
   - Kontrollo rigorozisht nëse ndonjë vendim gjyqësor apo raport zyrtar ka përdorur si rrethanë rënduese apo bazë kufizuese ndonjë dënim të mëparshëm që ka qenë ligjërisht i shlyer (i rehabilituar). Kjo përbën shkelje thelbësore absolute sipas precedentit PML.Nr.444/2022 të Gjykatës Supreme.

5. DOKTRINA E DY-FRONTËSISË SË DETYRUAR (CIVILE & PENALE):
   - Kur fashikulli përmban indicie ose prova të veprave penale të kryera nga persona zyrtarë (gjyqtarë, prokurorë, punonjës socialë, mjekë, zyrtarë ekzekutivë), NDALOHET KATEGORIKISHT reduktimi i çështjes vetëm në një padi civile!
   - Raporti duhet të ndërtojë detyrimisht TË DYJA DIMENSIONET:
     * Fronti A (Substancial): Zgjidhja themelore e kontestit (civil, familjar, pronësor apo dëmshpërblim sipas LMD/LFK).
     * Fronti B (Penal Institucional): Kualifikimi penal i përgjegjësisë së zyrtarëve publikë për Keqpërdorim (414), Ushtrim Ndikimi (424), Pengim të Provave (382), Vendime të Paligjshme (383), Falsifikim (427), me kërkesat konkrete hetimore dhe masat emergjente (KPPRK Nenet 188 & 221).
======================================================================

{'='*60}
PËRMBAJTJA E PLOTË E TË GJITHA DOKUMENTEVE TË FASHIKULLIT:
{'='*60}
{context_str}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER TË ANALIZËS (TË 8 SEKSIONET):

### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
* **Zanafilla dhe Kronologjia e Çështjes:** Zanafilla reale faktike, sekuenca e ngjarjeve sipas datave të provuara shkresërisht.
* **Gjendja Reale Faktike e Dokumentuar:** Faktet e vërtetuara me prova materiale kundrejt pretendimeve të pavërtetuara.
* **Pozicioni, Legjitimiteti dhe Interesi Juridik i Klientit ({client_name} - {pos}):** Të drejtat thelbësore të cenuara dhe mbrojtja kushtetuese.

### 2. 🔍 KRYQËZIMI I AKTORËVE, INSTITUCIONEVE DHE ZINXHIRI I PËRGJEGJËSISË
(Zbërthe rolin, veprimet faktike, konfliktet e interesit, koordinimin e dyshuar apo shkeljet ligjore të secilit aktor: zyrtarë ekzekutivë, trupa gjykues, prokurorë, ekspertë, punonjës socialë, dhe persona privatë).

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET VS. PROVAT REALE NË FASHIKULL
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat Reale të Fashikullit | Vlerësimi Doktrinar & Forca Provuese |
| :--- | :--- | :--- |

### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE E PRECEDENTËVE SUPREMË
(⚠️ URDHËR: Çdo dispozitë e zbatueshme të përfshihet me formatin `Neni X i [Ligjit]` për verifikim 1-klikim, me precedentin përkatës të Gjykatës Supreme Rev ose PML):
| Dispozita & Ligji i Zbatueshëm | Instituti Ligjor / Procedural | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. 🚨 PËRGJEGJËSIA LIGJORE, SHKELJET 'CONTRA LEGEM' DHE AUTOPSIA E PROCEDURËS
* 🔴 **Autopsia e Procesverbaleve dhe Shkeljet Thelbësore:** (Prapadatimet, mosshënimi i deklaratave, kërcënimet në sallë, përjashtimi i ekspertëve, shkelja e rehabilitimit ligjor sipas Nenit 93 KPRK).
* ⚖️ **Kualifikimi i Dyfishtë i Përgjegjësisë:**
  - Përgjegjësia Penale e Personave Zyrtarë dhe Privatë (KPRK Nenet 414, 424, 382, 383, 386, 387, 427, 250, 248).
  - Përgjegjësia Civile dhe Dëmshpërblyese (LMD Nenet 154-200 / LFK).

### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE DHE PROGNOZA SUPREME
* 🟢 **Mjetet Urgjente dhe të Rregullta:** Masat emergjente mbrojtëse, ankesat aktive dhe afatet ligjore prekluzive.
* 🟡 **Mjetet e Jashtëzakonshme & Kushtetuese:** Procedurat pranë PSRK-së, Revizioni/PML pranë Gjykatës Supreme dhe Mbrojtja Kushtetuese (Nenet 31, 54).

### 7. 🛠️ DRAFTI I PLOTË ZYRTAR I AKTIT TË RADHËS PROCEDURALE
(Harto aktin e plotë solemn gjyqësor me fuqi të lartë goditëse, gati për depozitim zyrtar):
* Nëse fashikulli përmban shkelje penale të rënda institucionale: Harto KALLËZIMIN PENAL TË UNIFIKUAR ME KËRKESË PËR MASË EMERGJENTE MBROJTËSE DHE VEPRIME HETIMORE (drejtuar Prokurorisë kompetente).
* Nëse fashikulli përmban aktvendim/aktgjykim të padrejtë: Harto ANKESËN E BLINDUAR PROCEDURALE.
* Përfshi: Organin, Palët, Faktet e Provuara, Bazën Ligjore dhe PJESËN KËRKUESE SOLEMNE (PETITUM-IN) TË NUMËRUAR PIKË PËR PIKË.

### 8. 🎯 MASTER PLANI I VEPRIMIT: STRATEGJIA E FITORES DHE HAPAT TAKTIKË
* 🔴 **HAPI 1 (Urgjenca / Veprimi brenda 24-48 Orë):** Masa emergjente, ndalimi i rrezikut dhe depozitimi urgjent.
* 🟡 **HAPI 2 (Veprimet Hetimore, Metadata & Sekuestrimet):** Kërkesat për ekspertiza të pavarura, sekuestrimi i pajisjeve elektronike/SMIL dhe dëgjimi i dëshmitarëve kyç.
* 🟢 **HAPI 3 (Strategjia në Gjykatë & Përmbyllja):** Pyetjet ballafaquese, sigurimi i dëmshpërblimit dhe vendosja e drejtësisë meritore.
"""