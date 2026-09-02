# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - UNIVERSAL SUPREME ANALYSIS V130.0 (750+ SUPREME PRECEDENTS • 8-DOMAIN DYNAMIC SYNTHESIS)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

DOMAIN_SPECIFIC_INSTRUCTIONS = {
    "PENAL": {
        "organ_target": "Prokurorinë Kompetente të Kosovës (PSRK ose Prokuroria Themelore)",
        "draft_type": "KALLËZIM PENAL I UNIFIKUAR / PARASHTRESË PËR FILLIM HETIMESH",
        "key_statutes": "Kodi Penal (KPK Nr. 06/L-074) dhe Kodi i Procedurës Penale (KPPRK Nr. 08/L-032)",
        "contra_legem_focus": "Shkeljet e procedurës penale (Neni 384 KPPRK), shpërdorimi i autoritetit (Neni 414 KPK), cenimi i barazisë së armëve dhe papranueshmëria e provave (Neni 257 KPPRK).",
        "remedy_focus": "Urdhëresa emergjente mbrojtëse (Nenet 188/221 KPPRK), sekuestrimi i provave, Kërkesa për Mbrojtje të Ligjshmërisë në Kolegjin Penal të Gjykatës Supreme."
    },
    "CIVIL": {
        "organ_target": "Gjykatën Themelore — Departamenti Civil",
        "draft_type": "KËRKESËPADI / KUNDËRPADI / PRAPËSIM PROCEDURAL DHE MATERIAL",
        "key_statutes": "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006) dhe Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)",
        "contra_legem_focus": "Shkeljet thelbësore të procedurës kontestimore (Neni 182 LPK), mospërmbushja e detyrimeve kontraktore, shkaktimi i dëmit (Neni 154 LMD) dhe parashkrimi i kërkesës.",
        "remedy_focus": "Caktimi i masës së sigurisë (Neni 297 LPK), Ankesa në Apel (15 ditë), Revizioni në Kolegjin Civil të Gjykatës Supreme (Neni 211 LPK)."
    },
    "PRONËSOR": {
        "organ_target": "Gjykatën Themelore — Divizioni për Çështje Pronësore",
        "draft_type": "PADI PËR VËRTETIM PRONËSIE / PENGIM POSEDIMI / RIVENDIKIM (ACTIO REIVINDICATIO)",
        "key_statutes": "Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (LPTS Nr. 03/L-154) dhe Ligji për Kadastër",
        "contra_legem_focus": "Uzurpimi i paligjshëm, pengimi i posedimit faktik, regjistrimet e parregullta kadastrale, mbivendosjet e parcelave dhe cenimi i bashkëpronësisë.",
        "remedy_focus": "Masa e përkohshme për ndalimin e tjetërsimit/ndërtimit, rivendosja në posedim brenda 30 ditëve, ekspertiza gjeodezike."
    },
    "KOMERCIAL": {
        "organ_target": "Gjykatën Komerciale të Kosovës (Dhomat e Shkallës së Parë)",
        "draft_type": "PADI TREGTARE / PROPOZIM PËR PËRMBARIM BAZUAR NË DOKUMENT TË BESUESHËM",
        "key_statutes": "Ligji për Gjykatën Komerciale (Nr. 08/L-015), Ligji për Shoqëritë Tregtare (Nr. 06/L-016), LMD dhe LPP",
        "contra_legem_focus": "Mospagimi i faturave komerciale, shkelja e kontratave tregtare, kamata ligjore ndërmjet tregtarëve (8%), dhe përgjegjësia e administratorëve/ortakëve.",
        "remedy_focus": "Urdhri përmbarimor, masa e sigurimit të llogarive bankare, ankesa në Dhomat e Shkallës së Dytë të Komerciales (afati 7 ditë)."
    },
    "PUNËS": {
        "organ_target": "Gjykatën Themelore — Divizioni për Konteste nga Marrëdhënia e Punës",
        "draft_type": "PADI PËR ANULIMIN E VENDIMIT TË SHKARKIMIT DHE KOMPENSIMIN E PAGAVE",
        "key_statutes": "Ligji i Punës i Kosovës (Nr. 03/L-212) dhe Ligji për Mbrojtjen nga Diskriminimi (Nr. 05/L-021)",
        "contra_legem_focus": "Shkarkimi i kundërligjshëm pa procedurë disiplinore, mospagimi i trustit/pagave/orëve shtesë, diskriminimi në punë dhe shkelja e afatit të njoftimit.",
        "remedy_focus": "Kthimi në vendin e punës, kompensimi integral retroaktiv me kamatë, ankesa në Inspektoratin e Punës."
    },
    "FAMILJAR": {
        "organ_target": "Gjykatën Themelore — Departamenti i Përgjithshëm / Divizioni Civil-Familjar",
        "draft_type": "PADI PËR SHKURORËZIM, BESIM TË FËMIJËVE, USHQIMIM (ALIMENTACION) DHE PJESËTIM PASURIE",
        "key_statutes": "Ligji për Familjen i Kosovës (Nr. 2004/32) dhe Ligji për Parandalimin e Dhunës në Familje (Nr. 08/L-185)",
        "contra_legem_focus": "Cenimi i interesit më të mirë të fëmijës (Neni 3 Konventa OKB), tjetërsimi prindëror, raportet e njëanshme sociale të QPS-së, fshehja e pasurisë së përbashkët.",
        "remedy_focus": "Urdhri mbrojtës emergjent, caktimi i masës së përkohshme për kontaktet prindërore, ekspertiza e pavarur psikologjike."
    },
    "ADMINISTRATIV": {
        "organ_target": "Gjykatën Themelore në Prishtinë — Departamenti për Çështje Administrative",
        "draft_type": "PADI PËR KONFLIKT ADMINISTRATIV (ANULIM I VENDIMIT ADMINISTRATIV TË FORMËS SË PRERË)",
        "key_statutes": "Ligji për Konfliktet Administrative (Nr. 03/L-202) dhe Ligji për Procedurën e Përgjithshme Administrative (LPPA Nr. 05/L-031)",
        "contra_legem_focus": "Nxjerrja e vendimit pa bazë ligjore, tejkalimi i diskrecionit administrativ, heshtja administrative, moszbatimi i parimit të dëgjimit të palës.",
        "remedy_focus": "Shtyrja e ekzekutimit të vendimit administrativ (Neni 22 LKA), Ankesa në Kolegjin Administrativ të Gjykatës Supreme."
    },
    "KUSHTETUES": {
        "organ_target": "Gjykatën Kushtetuese të Republikës së Kosovës",
        "draft_type": "KËRKESË INDIVIDUALE PËR VLERËSIMIN E KUSHTETUTSHMËRISË (NENI 113.7 I KUSHTETUTËS)",
        "key_statutes": "Kushtetuta e Kosovës (Neni 31, 53, 54), KEDNJ (Neni 6, 8, 13, Protokolli 1) dhe Ligji për Gjykatën Kushtetuese",
        "contra_legem_focus": "Cenimi i procesit të rregullt ligjor, arbitrariteti gjyqësor, mungesa e arsyetimit të vendimit të formës së prerë dhe mosshqyrtimi i provave kyçe.",
        "remedy_focus": "Masa e përkohshme kushtetuese (Neni 27 i Ligjit), konstatimi i shkeljes dhe kthimi i lëndës në rigjykim."
    }
}


class ComprehensiveAnalysisService:
    """
    Shërbimi Suprem i Analizës Gjithëpërfshirëse të Dosjes (V130.0):
    - Multi-Document Synthesis me 750+ Precedentët e Gjykatës Supreme (PML & Rev).
    - Tabelë Statutore me 4 Kolona (me precedentë dhe komente të Akademisë).
    - Gjeneron Raportin Master dhe DRAFTIN E PLOTË ZYRTAR TË AKTIT GJYQËSOR përkatës.
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
        pos = (client_position or "PALË NË PROCEDURË / PARASHTRUES").strip().upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:12000],
                manifest_str=manifest_str or ""
            )
        
        domain_info = DOMAIN_SPECIFIC_INSTRUCTIONS.get(case_domain, DOMAIN_SPECIFIC_INSTRUCTIONS["CIVIL"])
        
        search_query = query_text or (
            f"Analiza master doktrinare e dosjes: {case_title}. "
            f"Lëmia: {case_domain}. Palët, provat materiale, aktet procedurale, shkeljet contra legem dhe Aktgjykimet e Gjykatës Supreme PML Rev."
        )
        
        rag_context, _ = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=20
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
AUDITIM DOKTRINAR DHE ANALIZË E DOSJES • PRIVILEGJI I MBROJTJES DHE ANALIZËS GJYQËSORE
Ky material përbën fashikullin e plotë të shkresave të administruara në procedurë për lëminë **{case_domain}**.
Detyra jote si Kolegj i Gjykatës Supreme të Kosovës është të kryesh një sintezë shterruese, të zbulosh kontradiktat mes provave dhe pretendimeve, të kualifikosh përgjegjësinë ligjore dhe të përpilosh Strategjinë dhe Draftin e Hekurt Ligjor ({domain_info['draft_type']}) drejtuar {domain_info['organ_target']}, duke u mbështetur në PRECEDENTËT DHE AKTGJYKIMET PARIMORE TË GJYKATËS SUPREME (PML & Rev).
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I DOSJES / FASHIKULLIT:
LËMIA E PËRCAKTUAR: **{case_domain}** | PARASHTRUESI/KLIENTI: **{client_name or 'I Identifikuar në Shkresa'}** | POZICIONI PROCEDURAL: **{pos}** | TITULLI I LËNDËS: **{case_title}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME NË KOSOVË:
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME TË KOSOVËS (NGA BAZA GLOBALE E DITURISË):
{rag_context if rag_context else "Zbato precedentët e konsoliduar të Kolegjit Penal dhe Civil të Gjykatës Supreme të Kosovës."}

📅 KRONOLOGJIA E DOKUMENTUAR E FASHIKULLIT:
{timeline_context if timeline_context else "Kronologjia po rindërtohet nga dokumentet e fashikullit."}

📎 PASAPORTA E DOKUMENTEVE TË NGARKUARA NË DOSJE:
{manifest_str if manifest_str else "Shkresat e fashikullit."}

======================================================================
MANDATI YT DOKTRINAR SIPAS LËMISË **{case_domain}**:
ORGAN I ADRESUAR: **{domain_info['organ_target']}**
AKTI ZYRTAR PËR HARTIM: **{domain_info['draft_type']}**
FOKUSI CONTRA LEGEM: {domain_info['contra_legem_focus']}

⚠️ RREGULLAT E HEKURTA TË ANALIZËS DOKTRINARE:
1. CITIMI I DETYRUESHËM I PRECEDENTËVE SUPREMË: Cito vendimet parimore të Gjykatës Supreme (PML për penale, Rev për civile) për të interpretuar shkeljet ligjore.
2. ZERO HARDCODING: Gjithçka analizohet EKSKLUZIVISHT mbi bazën e dokumenteve reale të ngarkuara më poshtë.
3. SINTEZA E SHUMË DOKUMENTEVE: Krahaso deklarimet e palëve me provat shkencore e materiale. Zbulo çdo kontradiktë tekstuale apo mospërputhje.
4. TABELA STATUTORE ME 4 KOLONA: Çdo nen duhet të ketë rreshtin e tij individual: `Dispozita & Ligji` | `Instituti Ligjor` | `Analiza Doktrinare` | `🏛️ Precedenti / Qëndrimi i Gjykatës Supreme`.
5. DRAFTI I PLOTË ZYRTAR: Në Seksionin 7, harto {domain_info['draft_type']} të plotë drejtuar {domain_info['organ_target']}, me strukturë solemne gjyqësore, gati për dorëzim.
======================================================================

{'='*60}
PËRMBAJTJA E PLOTË E TË GJITHA DOKUMENTEVE TË FASHIKULLIT:
{'='*60}
{context_str}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER TË ANALIZËS (8 SEKSIONE):

### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
(Zbërthe me paragrafë të plotë doktrinarë):
* **Zanafilla dhe Kronologjia e Çështjes:** Si nisi marrëdhënia/konflikti, etapat procedurale dhe gjendja aktuale e fashikullit.
* **Gjendja Reale Faktike e Dokumentuar:** E vërteta e dokumentuar përmes provave shkresore, materiale, financiare, mjekësore apo dëshmive të administruara në këtë fashikull.
* **Pozicioni, Legjitimiteti dhe Interesi Juridik i Klientit ({client_name}):** Baza ligjore e të drejtave të tij/saj dhe arsyetimi pse kërkesa/mbrojtja e tij qëndron plotësisht në ligj.

### 2. 🔍 KRYQËZIMI I AKTORËVE, INSTITUCIONEVE DHE VLERËSIMI I PËRGJEGJËSISË
(Identifiko të gjithë personat/organet e përfshira në shkresat e kësaj lënde {case_domain} dhe analizo përgjegjësinë e tyre me nga një paragraf të plotë, duke zbatuar standardin e Gjykatës Supreme mbi dashjen dhe veprimet me faj):
* Analizo veprimet e secilës palë, organ publik, gjyqtar, ekspert, apo personi privat të përmendur në dosje.
* Evidento shkeljet ligjore, tejkalimin e kompetencave, njëanshmërinë, apo mosrespektimin e procedurave ligjore.

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET VS. PROVAT REALE NË FASHIKULL
(Ndërto tabelën krahasuese të provave):
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat Reale të Fashikullit | Vlerësimi Doktrinar & Forca Provuese |
| :--- | :--- | :--- |

### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE E PRECEDENTËVE SUPREMË
(⚠️ Çdo nen kryesor duhet të ketë rreshtin e tij të veçantë me 4 kolona):
| Dispozita & Ligji i Zbatueshëm | Instituti Ligjor / Procedural | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme (PML / Rev / Komentari) |
| :--- | :--- | :--- | :--- |

### 5. 🚨 PËRGJEGJËSIA LIGJORE, SHKELJET 'CONTRA LEGEM' DHE BAZA PROCEDURALE
* 🔴 **Shkeljet Thelbësore (Contra Legem):**
  (Analizo shkeljet kryesore procedurale dhe materiale specifike për lëminë **{case_domain}** sipas standardeve të Gjykatës Supreme):
  * {domain_info['contra_legem_focus']}
* ⚖️ **Kualifikimi i Përgjegjësisë Ligjore:**
  (Vlerëso përgjegjësinë ligjore përkatëse: penale, civile, kompensim dëmi, apo anulim akti administrativ).

### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE DHE PROGNOZA SUPREME
* 🟢 **Mjetet e Rregullta Juridike:** Ankesat e mundshme, afatet ligjore prekluzive aktive dhe gjykata kompetente.
* 🟡 **Mjetet e Jashtëzakonshme Juridike:**
  * {domain_info['remedy_focus']}
  * Ankesa Kushtetuese (Neni 113.7 i Kushtetutës së Kosovës).

### 7. 🛠️ DRAFTI I PLOTË ZYRTAR I AKTIT GJYQËSOR ({domain_info['draft_type']})
(Harto aktin e plotë procedural drejtuar **{domain_info['organ_target']}** me strukturë zyrtare solemne gjyqësore, gati për nënshkrim dhe dorëzim):
* **Titulli i Aktit dhe Organi Kompetent:** ({domain_info['organ_target']})
* **Palët Procedurale:** (Parashtruesi/Paditësi vs. Palët e Denoncuara/Të Paditura)
* **Baza Ligjore dhe Përmbledhja e Fakteve të Provuara**
* **PJESA KËRKUESE SOLEMNE (PETITUM-I I PLOTË I STRUKTURUAR NË PIKA ME NENE DHE AFATE)**

### 8. 🎯 MASTER PLANI I VEPRIMIT: STRATEGJIA E FITORES DHE HAPAT TAKTIKË
* 🔴 **HAPI 1 (Urgjenca / Afatet e Menjëhershme 24-48 Orë):** Veprimet e para procedurale, sigurimi i provave dhe depozitimi i kërkesave emergjente.
* 🟡 **HAPI 2 (Veprimet Hetimore & Ekspertizat):** Përjashtimi i personave me konflikt interesi, propozimi i ekspertizave të pavarura dhe kundërshtimet.
* 🟢 **HAPI 3 (Strategjia në Seancë & Përmbyllja):** Pyetjet kryqëzuese të ballafaqimit, mbrojtja e të drejtave dhe sigurimi i fitores përfundimtare.
"""