# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDIT V140.0 (MAXIMUM JUDICIAL DENSITY • INDIVIDUAL ROW STATUTES • FORMULA REMEDIATION)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (⚖️ / 🔬):
    - 100% Universal dhe Dinamik (Zero Hardcoding).
    - Dendësi Maksimale Doktrinare: Paragrafë të thellë arsyetues të nivelit të Gjykatës Supreme.
    - Tabelë Statutore Rresht-për-Rresht (1 Nen = 1 Rresht i veçantë për verifikim interaktiv).
    - Detektori Kirurgjik i Lapsuseve me Formulë Zëvendësuese të Gatshme.
    - Draft-Remediim i Plotë Solemn Gjyqësor (Court-Ready Petitum).
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        """
        Nxjerr automatikisht nenet, ligjet dhe precedentët nga teksti për kërkim të saktë në RAG.
        """
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LFK|LPP|LPPA|KEDNJ|Kushtetut[a-zë]*|Ligji\s+Nr\.\s*[\d/L\-]+)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|AC|CA|A|PKR|PP|C|P|E)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(dict.fromkeys(articles))[:15]
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
        """
        Identifikon llojin e shkresës procedurale dhe përcakton udhëzimin e saktë doktrinar.
        """
        combined = f"{file_name} {document_text[:6000]}".lower()
        
        categories = [
            ("KALLËZIM PENAL / AKTAKUZË", ["kallëzim penal", "kallezim penal", "kallzim penal", "aktakuzë", "aktakuze", "denoncim penal", "prokuroria speciale", "prokuroria themelore", "psrk"], 
             "Audito ligjshmërinë e bazës penale, elementet e figurës së veprës penale (dashjen/fajësinë), kompetencën lëndore të prokurorisë, bazueshmërinë e kërkesave për masa emergjente mbrojtëse dhe pranueshmërinë e provave sipas KPPRK-së."),
            
            ("AKTGJYKIM / AKTVENDIM GJYKATE", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore", "gjykata e apelit", "gjykata supreme", "trupi gjykues", "kolegji"],
             "Audito ligjshmërinë dhe arsyetimin e vendimit, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), mospërputhjet arsyetim-dispozitiv, shkeljet e ligjit material dhe bazën e hekurt për mjete juridike (Ankesë / Revizion / PML)."),
            
            ("PADI / KËRKESËPADI", ["kërkesëpadi", "kerkesepadi", "paditësi", "padia kundër", "petitum", "vlera e kontestit"],
             "Audito legjitimimin aktiv/pasiv, qartësinë dhe ekzekutueshmërinë e Petitumit, kompetencën gjyqësore dhe bazën statutore sipas LMD/LPK/LPTS."),
            
            ("KUNDËRPADI / PËRGJIGJE NË PADI / PRAPËSIM", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
             "Audito forcën e prapësimeve procedurale (litispendenca, parashkrimi, res judicata, kompetenca) dhe prapësimeve materiale kundërshtuese."),
            
            ("ANKESË / APEL / REVIZION / PML", ["ankesë", "ankese", "drejtuar gjykatës së apelit", "kundër aktgjykimit", "pikat ankimore", "revizion", "kërkesë për mbrojtje të ligjshmërisë"],
             "Audito respektimin e afatit ligjor prekluziv, formulimin e pikave ankimore (procedurale, faktike, materiale) dhe formulimin e kërkesës ankimore."),
            
            ("URDHËR MBROJTJE / DHUNË NË FAMILJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "dhunë në familje", "dhune ne familje", "masat mbrojtëse"],
             "Audito proporcionalitetin e masave, afatet procedurale të veprimit emergjent dhe bazueshmërinë sipas Ligjit për Mbrojtjen nga Dhuna në Familje."),
            
            ("KONTRATË / MARRËVESHJE JURIDIKE", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese", "klauzolë", "shpk", "sha", "kontrata mbi"],
             "Audito vlefshmërinë e klauzolave sipas LMD-së, rreziqet e pavlefshmërisë absolute/relative, penalitetet, kushtet e zgjidhjes dhe juridiksionin gjyqësor."),
            
            ("RAPORT SOCIAL / EKSPERTIZË MJEKËSORE-GJYQËSORE", ["raport social", "qps", "qendra për punë sociale", "ekspertizë", "ekspertize", "raporti i ekspertit", "epikrizë", "diagnoza"],
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
        search_query = query_text or f"{mined_legal_entities} {case_domain} {doc_category}"

        rag_context, _ = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=15
        )
        
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM FORENZIK DOKTRINAR I GJYKATËS SUPREME • PRIVILEGJI I MBROJTJES DHE ANALIZËS GJYQËSORE
Ky material përbën një ekspertizë ligjore-forenzike doktrinare të shkresës zyrtare dhe provave të dorëzuara nga pala. 
Detyra jote si Krye-Auditor i Gjykatës Supreme është të kryesh një auditim të hekurt, shterrues, analitik dhe kirurgjik të këtij akti sipas legjislacionit pozitiv të Republikës së Kosovës dhe praktikës gjyqësore të Kolegjit Penal dhe Civil të Gjykatës Supreme.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS NË AUDITIM:
DOKUMENTI: **{doc_category}** | LËMIA: **{case_domain}** | PARASHTRUESI/KLIENTI: **{client_name or 'I Identifikuar në Dokument'}** | POZICIONI PROCEDURAL: **{pos}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

{f"🏛️ JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME PËR KËTË ÇËSHTJE:\n{rag_context}" if rag_context else ""}

🎯 OBJEKTIVI DOKTRINAR: {category_description}

======================================================================
URDHËR I HEKURT DOKTRINAR I KRYE-AUDITORIT TË GJYKATËS SUPREME:
1. NDALOHET KATEGORIKISHT PËRMBLEDHJA SIPËRFAQËSORE APO LISTIMI ME 1-2 FJALI! Çdo nën-kapitull kërkon PARAGRAF TË PLOTË ARSYETUES me argumentim të dendur juridiko-logjik.
2. TEK AKTORËT DHE INSTITUCIONET (Seksioni 2): Grupo personat e përfshirë sipas institucioneve dhe shkruaj një paragraf të plotë analitik për secilin grup, duke evidentuar veprimet konkrete, datat, dashjen (dolus) dhe bazën e përgjegjësisë penale/civile.
3. TEK PROVAT MATERIALE (Seksioni 3): Analizo secilën provë konkrete të fashikullit, peshën e saj shkencore kundrejt pretendimeve të kundërta dhe ligjshmërinë e administrimit.
4. TEK TABELA STATUTORE (Seksioni 4): 
   ⚠️ RREGULL ABSOLUT: NDALOHET GRUMBULLIMI I NENEVE NË NJË RRESHT TË VETËM! 
   Secili nen kryesor i cituar (nga KPK, KPPRK, Ligji për PSRK, Kushtetuta, Konventat) DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL NË TABELË, me analizën e detajuar të institutit dhe pasojës juridike.
5. TEK DETEKTORI I LAPSUSEVE DHE NENET CONTRA LEGEM (Seksioni 5): Identifiko pasaktësitë dhe jep FORMULËN E SAKTË DOKTRINARE ZËVENDËSUESE (para/pas).
6. TEK DRAFT-REMEDIIMI (Seksioni 7): Shkruaj PETITUMIN / PJESËN KËRKUESE TË PLOTË SOLEMNE GJYQËSORE, gati për t'u vulosur e dorëzuar në organin kompetent.
======================================================================

{'='*60}
TEKSTI I PLOTË I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER FORENZIK (8 SEKSIONE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
(Shkruaj një analizë të thellë me paragrafë të plotë për secilën pikë):
* **Lloji, Natyra Formale dhe Efekti Juridik:** Përcakto kategorinë formale të aktit, rëndësinë e tij procedurale dhe efektet e menjëhershme detyruese mbi organin procedues.
* **Kompetenca Lëndore, Funksionale dhe Territoriale:** Analizo me saktësi bazën ligjore të kompetencës së organit të cilit i drejtohet akti, dhe zbërthe konfliktin e interesit apo arsyetimin ligjor për skualifikimin/përjashtimin e organeve vartëse.
* **Legjitimimi Procedural i Palëve (Locus Standi):** Vlerëso legjitimimin aktiv të parashtruesit (në cilësi vetjake dhe si përfaqësues ligjor) dhe legjitimimin pasiv të të denoncuarve/të paditurve.
* **Auditimi i Afateve Ligjore dhe Urgjenca Procedurale (Periculum in mora):** Vlerëso respektimin e afateve prekluzive, rrezikun e pariparueshëm nga vonesa dhe domosdoshmërinë e masave të menjëhershme emergjente (brenda 24-48 orëve).

### 2. 👥 STRUKTURA E AKTORËVE, ROLI DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
(Identifiko të gjithë personat/institucionet dhe shkruaj nga një paragraf të dendur arsyetues për secilin grup):
* **Zyrtarët e Lartë Ekzekutivë dhe Politikë:** Analizo veprimet konkrete të ushtrimit të ndikimit (Neni 424 KPK), shtytjes (Neni 32 KPK) dhe bashkëkryerjes (Neni 31 KPK).
* **Gjyqtarët dhe Trupat Gjykues të Përfshirë:** Analizo shkeljet e pretenduara mbi nxjerrjen e vendimeve të paligjshme (Neni 383/425 KPK), shkeljen e institutit të rehabilitimit ligjor (Neni 93 KPK) dhe cenimin e parimit të barazisë së armëve në sallë.
* **Mjekët, Psikiatrët dhe Ekspertët Profesionalë:** Analizo konsumimin e veprave penale të ekspertizës së rreme (Neni 387 KPK), lëshimit të dokumenteve të rreme dhe shpërfilljes së testeve shkencore laboratorike.
* **Zyrtarët e Qendrës për Punë Sociale (QPS) dhe Mbrojtësit e Viktimave:** Analizo keqpërdorimin e autoritetit zyrtar (Neni 414 KPK), kanosjen psikologjike të të miturit (Nenet 250 & 386 KPK) dhe manipulimin e procesverbaleve.
* **Organet Hetuese dhe Prokurorët Lokalë:** Analizo fshehjen e provave digjitale shfajësuese (Neni 382 KPK) dhe ngritjen e akuzave në mungesë të elementeve të veprës.

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DOKUMENTARE (CORPUS DELICTI)
(Zbërthe fuqinë provuese dhe kontradiktat tekstuale për secilën provë kryesore me nga një paragraf analitik):
* **E Vërteta Shkencore vs. Deklarimet Verbale:** Analizo provat laboratorike/shkencore ekzistuese kundrejt raporteve mjekësore apo konstatimeve gojore të institucioneve.
* **Vetë-Kontradiktat në Shkresat dhe Vendimet Zyrtare:** Ballafaqo konstatimet tekstuale të gjykatave (arsyetimet ku pranohen faktet pozitive) kundrejt masave kufizuese në dispozitiv.
* **Provat Digjitale, Audiot dhe Komunikimet Elektronike:** Vlerëso forcën provuese të regjistrimeve audio, mesazheve dhe vizatimeve grafike si prova të lidhjes emocionale dhe të presionit psikologjik.
* **Ligjshmëria e Procesverbaleve dhe Prapadatimet (Antidatum):** Analizo dyshimet mbi parafabrikimin e datave në procesverbale gjyqësore/zyrtare dhe papranueshmërinë e provave sipas rregullave procedurale.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE STATUTORE (KOSOVË & NDËRKOMBËTARE)
(⚠️ URDHËR: ÇDO NEN DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL NË TABELË — NDALOHET GRUMBULLIMI I NENEVE! Përfshi të gjitha nenet nga KPK, KPPRK, Ligji për PSRK, Kushtetuta dhe Konventat):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Penal | Analiza Doktrinare & Pasojat Juridike të Zbatimit |
| :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I LAPSUSEVE
* 🔴 **[GJETJET KRITIKE CONTRA LEGEM]:**
  (Analizo me imtësi shkeljet më të rënda të rendit juridik, si p.sh. përdorimi i dënimeve të shlyera ligjërisht, vendimmarrja arbitrare apo mohimi i të drejtës së mbrojtjes):
  * Zbërthe arsyetimin pse këto veprime janë të pavlefshme dhe absolutisht të paligjshme.
* 🔍 **DETEKTORI KIRURGJIK I LAPSUSEVE DHE FORMULAT E KORRIGJIMIT:**
  (Tabela e saktësimit të neneve, paragrafëve dhe kualifikimeve ligjore):
  | Neni / Formulimi Aktual në Shkresë | Pasaktësia / Lapsusi i Evidentuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I PETITUMIT, KËRKESAVE PROCEDURALE DHE EKZEKUTUESHMËRISË
(Analizo në thellësi kërkesat e parashtruesit):
* **Qartësia dhe Përputhshmëria Ligjore e Kërkesave:** Vlerëso nëse kërkesat për urdhëresa emergjente, masa mbrojtëse, fillim hetimesh dhe ekspertiza plotësojnë standardet formale të ligjit.
* **Ekzekutueshmëria e Menjëhershme nga Organet Zbatuese:** Analizo mekanizmin praktik se si Policia e Kosovës dhe Prokuroria duhet t'i ekzekutojnë këto kërkesa brenda 24 orëve.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN GJYQËSOR)
(Shkruaj DRAFTIN E PLOTË TË KËRKESËS PËRFUNDIMTARE / PETITUMIT me gjuhë të hekurt të Gjykatës Supreme, gati për t'u integruar e dorëzuar në organin procedues):
* **Pjesa Kërkuese Soleme (Petitum-i i Remeduar):**
  [Shkruaj tekstin e plotë të kërkesës me të gjitha pikat e urdhërueshme të detajuara me nene dhe afate precize].

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afati 24-48 Orë):** Hapat e menjëhershëm proceduralë të deponimit dhe ekzekutimit të masave emergjente.
* 🟡 **HAPI 2 (Veprimet Hetimore & Sigurimi i Provave):** Hapat e ndërmjetëm të sigurimit të metadatave digjitale, caktimit të komisioneve të pavarura të ekspertëve dhe kërkesave për përjashtim.
* 🟢 **HAPI 3 (Strategjia në Seancë & Mjetet Juridike):** Taktika e ballafaqimit në shqyrtim kryesor, përgatitja e pyetësorit kryqëzues dhe procedimi drejt Departamentit Special.
"""