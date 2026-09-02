# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDIT V185.0 (100% DYNAMIC PARTIES • CLEAN SYNTAX)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (⚖️ / 🔬):
    - 100% Universal dhe Dinamik: Përshtatet plotësisht me lëminë (Penale, Komerciale, Civile, etj.).
    - Struktura e Aktorëve Dinamike: Analizon vetëm palët reale (Paditësit vs. Të Paditurit ose I Dëmtuari vs. Të Dyshuarit).
    - Korrigjimi i Numrave të Neneve dhe integrimi i Precedentëve të Gjykatës Supreme (PML & Rev).
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LSHT|LFK|LPP|LPPA|LPTS|KEDNJ|Kushtetut[a-zë]*|Ligji\s+Nr\.\s*[\d/L\-]+)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|AC|CA|A|PKR|PP|C|P|E)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(dict.fromkeys(articles))[:20]
        unique_laws = list(dict.fromkeys(laws))[:8]
        unique_cases = list(dict.fromkeys(cases))[:8]

        search_tokens = []
        if unique_articles:
            search_tokens.append(" ".join([f"Neni {a}" for a in unique_articles]))
        if unique_laws:
            search_tokens.append(" ".join(unique_laws))
        if unique_cases:
            search_tokens.append(" ".join([f"Rasti {c}" for c in unique_cases]))

        return " ".join(search_tokens)

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> Tuple[str, str]:
        combined = f"{file_name} {document_text[:6000]}".lower()
        
        categories = [
            ("PADI / KËRKESËPADI (GJYKATA KOMERCIALE)", ["gjykata komerciale", "çështje ekonomike", "shoqëri tregtare", "sh.p.k.", "nui:", "konkurrencë e palejuar", "detyra e besnikërisë", "përjashtimi i ortakut"],
             "Audito ligjshmërinë e kërkesëpadisë tregtare, bazën e dëmshpërblimit sipas LSHT dhe LMD, llogaritjen e kamatëvonesës 8%, dhe themelësinë e masës së sigurimit sipas LPK-së."),

            ("KALLËZIM PENAL / AKTAKUZË", ["kallëzim penal", "kallezim penal", "kallzim penal", "aktakuzë", "aktakuze", "denoncim penal", "prokuroria speciale", "prokuroria themelore", "psrk"], 
             "Audito ligjshmërinë e bazës penale, elementet e figurës së veprës penale (dashjen/fajësinë), kompetencën lëndore të prokurorisë, bazueshmërinë e kërkesave për masa emergjente mbrojtëse dhe pranueshmërinë e provave sipas KPPRK-së dhe praktikës PML."),
            
            ("AKTGJYKIM / AKTVENDIM GJYKATE", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore", "gjykata e apelit", "gjykata supreme", "trupi gjykues", "kolegji"],
             "Audito ligjshmërinë dhe arsyetimin e vendimit, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), mospërputhjet arsyetim-dispozitiv, shkeljet e ligjit material dhe bazën e hekurt për mjete juridike (Ankesë / Revizion / PML)."),
            
            ("PADI / KËRKESËPADI CIVILE", ["kërkesëpadi", "kerkesepadi", "paditësi", "padia kundër", "petitum", "vlera e kontestit"],
             "Audito legjitimimin aktiv/pasiv, qartësinë dhe ekzekutueshmërinë e Petitumit, kompetencën gjyqësore dhe bazën statutore sipas LMD/LPK/LPTS dhe praktikës Rev."),
            
            ("KUNDËRPADI / PËRGJIGJE NË PADI / PRAPËSIM", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
             "Audito forcën e prapësimeve procedurale (litispendenca, parashkrimi, res judicata, kompetenca) dhe prapësimeve materiale kundërshtuese."),
            
            ("ANKESË / APEL / REVIZION / PML", ["ankesë", "ankese", "drejtuar gjykatës së apelit", "kundër aktgjykimit", "pikat ankimore", "revizion", "kërkesë për mbrojtje të ligjshmërisë"],
             "Audito respektimin e afatit ligjor prekluziv, formulimin e pikave ankimore (procedurale, faktike, materiale) dhe formulimin e kërkesës ankimore sipas precedentëve të Supremes."),
            
            ("URDHËR MBROJTJE / DHUNË NË FAMILJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "dhunë në familje", "dhune ne familje", "masat mbrojtëse"],
             "Audito proporcionalitetin e masave, afatet procedurale të veprimit emergjent dhe bazueshmërinë sipas Ligjit për Mbrojtjen nga Dhuna në Familje."),
            
            ("KONTRATË / MARRËVESHJE JURIDIKE", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese", "klauzolë", "shpk", "sha", "kontrata mbi"],
             "Audito vlefshmërinë e klauzolave sipas LMD-së, rreziqet e pavlefshmërisë absolute/relative, penalitetet, kushtet e zgjidhjes dhe juridiksionin gjyqësor."),
            
            ("RAPORT SOCIAL / EKSPERTIZË", ["raport social", "qps", "qendra për punë sociale", "ekspertizë", "ekspertize", "raporti i ekspertit", "epikrizë", "diagnoza"],
             "Audito metodologjinë, mungesën e njëanshmërisë, integritetin shkencor, tejkalimin e kompetencave dhe përputhjen me provat materiale."),
            
            ("SHKRESË PROCEDURALE / PARASHTRESË", [], 
             "Audito shkresën për saktësi neni-për-nen, qartësi të kërkesës, respektim të afateve procedurale dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë.")
        ]
        
        for category, keywords, desc in categories:
            if not keywords:
                continue
            for kw in keywords:
                if kw in combined:
                    return category, desc
        
        return "SHKRESË PROCEDURALE / PARASHTRESË", "Audito shkresën për saktësi neni-për-nen, qartësi të kërkesës, respektim të afateve procedurale dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë."

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
        audit_text = (document_text or context_str).strip()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=audit_text[:10000],
                manifest_str=manifest_str or ""
            )
        
        pos = (client_position or "PALË NË PROCEDURË / PARASHTRUES").strip().upper()
        doc_category, category_description = ForensicAuditService.detect_document_category(audit_text)
        
        mined_legal_entities = ForensicAuditService.extract_legal_entities_from_text(audit_text)
        search_query = query_text or f"{mined_legal_entities} {case_domain} {doc_category} Gazeta Zyrtare Nenet Aktgjykim Gjykata Supreme PML Rev"

        rag_context, _ = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )
        
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM FORENZIK DOKTRINAR I GJYKATËS SUPREME • PRIVILEGJI I MBROJTJES DHE ANALIZËS GJYQËSORE
Ky material përbën një ekspertizë ligjore-forenzike doktrinare të shkresës zyrtare dhe provave të dorëzuara nga pala për lëminë **{case_domain}**. 
Detyra jote si Krye-Auditor i Gjykatës Supreme është të kryesh një auditim të hekurt, shterrues, analitik dhe kirurgjik të këtij akti duke zbatuar legjislacionin pozitiv të Republikës së Kosovës dhe PRECEDENTËT E KONSOLIDUAR TË GJYKATËS SUPREME (Aktgjykimet PML & Rev).
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS NË AUDITIM:
DOKUMENTI: **{doc_category}** | LËMIA: **{case_domain}** | PARASHTRUESI/KLIENTI: **{client_name or 'I Identifikuar në Dokument'}** | POZICIONI PROCEDURAL: **{pos}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

🏛️ JURISPRUDENCA PARIMORE DHE TEKSTI I LIGJEVE NË FUQI (GAZETA ZYRTARE E KOSOVËS):
{rag_context if rag_context else "Zbato tekstin pozitiv të Gazetës Zyrtare dhe precedentët parimorë të Kolegjit Penal dhe Civil të Gjykatës Supreme të Kosovës."}

🎯 OBJEKTIVI DOKTRINAR: {category_description}

======================================================================
URDHËR I HEKURT DOKTRINAR I KRYE-AUDITORIT TË GJYKATËS SUPREME:
1. PËRSHTATJA E PLOTË ME LËMINË ({case_domain}): 
   - Nëse çështja është Komerciale/Civile, analizo kontratat, faturat, dëmshpërblimin, përjashtimin e ortakut, kamatëvonesën 8% dhe masën e sigurimit (LPK/LMD/LSHT).
   - Nëse çështja është Penale, analizo veprat, hetimet dhe përgjegjësinë penale (KPK/KPPRK).
2. ZERO HEADINGS STATIKE: Tek Aktorët dhe Palët (Seksioni 2), grupo dhe analizo VETËM palët reale që ekzistojnë në dokument (Paditësit vs. Të Paditurit / I Dëmtuari vs. Të Dyshuarit). Ndalohet shkrimi i nën-titujve për institucione që nuk janë pjesë e lëndës!
3. KORRIGJIMI I NUMRIT TË NENIT: Verifiko çdo nen me ligjin pozitiv në fuqi. Nëse autori ka gabuar numrin e nenit, korrigjoje menjëherë në Seksionin 5!
4. PRECEDENTËT E SUPREMES: Cito precedentët përkatës (Aktgjykimet Rev për çështje civile/tregtare, Aktgjykimet PML për çështje penale).
5. TABELA STATUTORE ME 4 KOLONA: Çdo nen me rreshtin e tij individual: `Dispozita & Ligji` | `Instituti Ligjor` | `Analiza Doktrinare & Pasojat` | `🏛️ Precedenti / Qëndrimi i Gjykatës Supreme`.
6. DRAFT-REMEDIIMI: Shkruaj PETITUMIN / PJESËN KËRKUESE TË PLOTË SOLEMNE GJYQËSORE përkatëse për atë gjykatë/organ.
======================================================================

{'='*60}
TEKSTI I PLOTË I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER FORENZIK (8 SEKSIONE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
(Shkruaj një analizë të thellë me paragrafë të plotë doktrinarë):
* **Lloji, Natyra Formale dhe Efekti Juridik:** Përcakto kategorinë formale të aktit, rëndësinë e tij procedurale dhe pasojat ligjore.
* **Kompetenca Lëndore, Funksionale dhe Territoriale:** Analizo me saktësi bazën ligjore të kompetencës së gjykatës/organit të cilit i drejtohet akti (p.sh. Gjykata Komerciale sipas Ligjit Nr. 08/L-015, Gjykata Themelore, apo PSRK).
* **Legjitimimi Procedural i Palëve (Locus Standi):** Vlerëso legjitimimin aktiv të paditësve/parashtruesve dhe legjitimimin pasiv të të paditurve/të denoncuarve.
* **Auditimi i Afateve Ligjore dhe Urgjenca Procedurale (Periculum in mora):** Vlerëso afatet ligjore, rrezikun e pariparueshëm nga vonesa dhe themelësinë e kërkesës për Masë të Sigurimit / Masa Emergjente.

### 2. 👥 STRUKTURA E PALËVE, AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
(Identifiko të gjitha palët reale të këtij dokumenti dhe analizo përgjegjësinë me nga një paragraf të plotë):
* **Paditësit / Parashtruesit e Shkresës:** Analizo të drejtat e tyre të cenuara, raportin juridik/kontraktor dhe legjitimimin për të kërkuar dëmshpërblim apo mbrojtje.
* **Të Paditurit / Palët Kundërshtare:** Analizo shkeljet konkrete ligjore, kontraktore apo administrative (p.sh. shkelja e detyrës së besnikërisë Neni 258 LSHT, ushtrimi i konkurrencës së palejuar Neni 259 LSHT, tjetërsimi i fondeve, mospërmbushja e detyrimit, apo veprat e pretenduara).
* **Personat e Tjerë Përgjegjës / Përfaqësuesit:** Analizo përgjegjësinë solidare të drejtorëve, administratorëve apo subjekteve të ndërlidhura.

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DOKUMENTARE (CORPUS DELICTI)
(Zbërthe fuqinë provuese për secilën provë të administruar në shkresë me nga një paragraf analitik):
* **Provat Financiare, Kontratat dhe Faturat:** Analizo faturat zyrtare, marrëveshjet kontraktore, ekstraktet e ARBK-së, ekstraktet bankare dhe vlerën e dëmit të pretenduar.
* **Vërtetësia dhe Konsistenca e Dokumentacionit:** Vlerëso përputhjen mes provave shkresore dhe kërkesave të parashtruara në petitum.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(⚠️ URDHËR: ÇDO NEN DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL NË TABELË — Përfshi kolonën e 4-të me Aktgjykimin/Doktrinën e Gjykatës Supreme):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme (Rev / PML / Komentari) |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I LAPSUSEVE
* 🔴 **[GJETJET KRITIKE CONTRA LEGEM]:**
  (Analizo shkeljet më flagrante ligjore dhe kontraktore të evidentuara në shkresë):
  * Zbërthe arsyetimin pse këto veprime përbëjnë shkelje të rëndë të rendit juridik dhe bazë për dëmshpërblim/sanksionim.
* 🔍 **DETEKTORI KIRURGJIK I LAPSUSEVE TË NENEVE DHE FORMULAT E KORRIGJIMIT:**
  (Krahaso nenet e cituara në shkresë me tekstin real të Gazetës Zyrtare të Kosovës. Nëse ka ndonjë lapsus në numër neni apo paragraf, jep korrigjimin e saktë):
  | Neni / Formulimi Aktual në Shkresë | Pasaktësia / Lapsusi i Evidentuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I PETITUMIT, MASËS SË SIGURIMIT DHE EKZEKUTUESHMËRISË
(Analizo në thellësi kërkesat e padisë/shkresës):
* **Qartësia dhe Përputhshmëria Ligjore e Petitumit:** Vlerëso nëse kërkesa për dëmshpërblim, përjashtim ortaku, kamatëvonesë 8% dhe shpenzime procedurale është formuluar saktë.
* **Themelësia dhe Ekzekutueshmëria e Masës së Sigurimit:** Analizo kushtet e Nenit 297/298 të LPK-së (rreziku real i tjetërsimit, bllokimi i llogarive bankare).

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN GJYQËSOR)
(Shkruaj DRAFTIN E PLOTË TË PETITUMIT TË KORRIGJUAR drejtuar organit/gjykatës kompetente me format solemn gjyqësor):
* **Pjesa Kërkuese Soleme (Petitum-i i Remeduar):**
  [Shkruaj tekstin e plotë të aktgjykimit të propozuar me të gjitha pikat e urdhërueshme të detajuara me shuma, përqindje kamate dhe masa konkrete sigurimi].

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afati 24-48 Orë):** Depozitimi i kërkesës për Masë Sigurimi dhe bllokimi i xhirollogarive bankare.
* 🟡 **HAPI 2 (Veprimet Provuese & Sigurimi Financiar):** Verifikimi i llogarive bankare, ekspertiza financiare dhe sigurimi i pasurive të të paditurve.
* 🟢 **HAPI 3 (Strategjia në Seancë & Përmbyllja):** Përfaqësimi në seancën përgatitore dhe shqyrtim kryesor në gjykatë.
"""