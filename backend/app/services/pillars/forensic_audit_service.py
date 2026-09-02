# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDIT V130.0 (DYNAMIC STATUTE MINING & SUPREME BENCHMARK)

import logging
import re
from typing import Dict, Any, Optional, Tuple
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (🔬):
    - Nxjerr automatikisht të gjitha nenet, ligjet dhe numrat e lëndëve nga teksti i dokumentit.
    - Tërheq me saktësi kirurgjikale nga Baza Globale vendimet e Gjykatës Supreme dhe komentarin e Akademisë.
    - Prodhon Akt-Ekspertizë të plotë doktrinare me thellësi supreme gjyqësore.
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        """
        Nxjerr automatikisht të gjitha nenet dhe precedentët nga teksti për kërkim të saktë në RAG.
        """
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LFK|LPP|LPPA|KEDNJ|Kushtetut[a-zë]*)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|AC|CA|A|PKR)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(set(articles))[:15]
        unique_laws = list(set(laws))[:8]
        unique_cases = list(set(cases))[:6]

        search_tokens = []
        if unique_articles:
            search_tokens.append(" ".join([f"Neni {a}" for a in unique_articles]))
        if unique_laws:
            search_tokens.append(" ".join(unique_laws))
        if unique_cases:
            search_tokens.append(" ".join([f"PML {c}" for c in unique_cases]))

        return " ".join(search_tokens)

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> Tuple[str, str]:
        combined = f"{file_name} {document_text[:8000]}".lower()
        
        categories = [
            ("AKTAKUZË / KALLËZIM PENAL", ["kallëzim penal", "kallezim penal", "kallzim penal", "aktakuzë", "aktakuze", "denoncim penal", "vepër penale"], 
             "Audito në thellësi maksimale figurën e veprës penale, ligjshmërinë e hetimeve, kompetencën e PSRK-së dhe papranueshmërinë e provave sipas Nenit 257 të KPPRK-së."),
            
            ("AKTGJYKIM / AKTVENDIM GJYKATE", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore", "trupi gjykues", "kolegji"],
             "Audito ligjshmërinë dhe arsyetimin e vendimit, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), mospërputhjet arsyetim-dispozitiv dhe bazën e hekurt për ANKESË."),
            
            ("PADI / KËRKESËPADI", ["kërkesëpadi", "kerkesepadi", "paditësi", "padia kundër", "petitum", "vlera e kontestit"],
             "Audito legjitimimin aktiv/pasiv, qartësinë e Petitumit, kompetencën gjyqësore dhe bazën statutore sipas LMD/LPK/LPTS."),
            
            ("KUNDËRPADI / PËRGJIGJE NË PADI", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
             "Audito forcën e prapësimeve procedurale (litispendenca, parashkrimi, kompetenca) dhe prapësimeve materiale kundërshtuese."),
            
            ("ANKESË / APEL", ["ankesë", "ankese", "drejtuar gjykatës së apelit", "kundër aktgjykimit", "pikat ankimore"],
             "Audito respektimin e afatit ligjor prekluziv, pikat ankimore (procedurale, faktike, materiale) dhe formulimin e kërkesës ankimore."),
            
            ("URDHËR MBROJTJE / DHUNË NË FAMILJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "dhunë në familje", "dhune ne familje", "masat mbrojtëse"],
             "Audito proporcionalitetin e masave, afatet procedurale dhe bazueshmërinë sipas Ligjit Nr. 08/L-185 për Parandalimin dhe Mbrojtjen nga Dhuna në Familje."),
            
            ("KONTRATË / MARRËVESHJE BIZNESI", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese", "klauzolë", "shpk", "sha"],
             "Audito vlefshmërinë e klauzolave sipas LMD-së, rreziqet e pavlefshmërisë absolute/relative, penalitetet dhe juridiksionin e Gjykatës Komerciale."),
            
            ("RAPORT SOCIAL / EKSPERTIZË", ["raport social", "qps", "qendra për punë sociale", "ekspertizë", "ekspertize", "raporti i ekspertit"],
             "Audito metodologjinë, mungesën e njëanshmërisë, tejkalimin e kompetencave dhe përputhjen me provat shkencore e materiale."),
            
            ("DRAFT JURIDIK / PARASHTRESË", [], 
             "Audito shkresën për saktësi neni-për-nen, qartësi formulimi, respektim afatesh dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë.")
        ]
        
        for category, keywords, desc in categories:
            if not keywords:
                continue
            for kw in keywords:
                if kw in combined:
                    return category, desc
        
        return "DRAFT JURIDIK / PARASHTRESË", "Audito shkresën për saktësi neni-për-nen, qartësi formulimi, respektim afatesh dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë."

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
        pos = (client_position or "DEFENDANT").upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str or ""
            )
        
        audit_text = (document_text or context_str).strip()
        doc_category, category_description = ForensicAuditService.detect_document_category(audit_text)
        
        # Nxjerrja e neneve reale nga dokumenti për kërkim të saktë në Bazën Globale
        mined_legal_entities = ForensicAuditService.extract_legal_entities_from_text(audit_text)
        search_query = query_text or f"{mined_legal_entities} {case_domain} {doc_category} {case_title}"

        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=35
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
            manifest_str=manifest_str or "",
            context_str=context_str,
            case_domain=case_domain,
            rag_context=rag_context,
            case_rag_context=case_rag_context,
            timeline_context=timeline_context
        )

        return f"""
{base_prompt}

{role_guard}

📄 DOKUMENTI NË AUDITIMIN SUPREM FORENZIK: **{doc_category}**
⚖️ LËMIA JURIDIKE: **{case_domain}**
🎯 OBJEKTIVI DOKTRINAR: {category_description}

======================================================================
MANDATI I KRYE-GJYQTARIT DHE AUDITORIT SUPREM TË FORENZIKËS GJYQËSORE:
Ti vepron me autoritetin më të lartë doktrinar të Gjykatës Supreme të Republikës së Kosovës.

⚠️ URDHËR I HEKURT PËR FORMATIN E ARSYETIMIT DHE DENDËSINË JURIDIKE:
1. NDALOHET LISTIMI SIPËRFAQËSOR ME NGA 1 FJALI! Çdo gjetje duhet të shkruhet si PARAGRAF I PLOTË DHE I DENDUR ARSYETUES.
2. TEK AKTORËT DHE INSTITUCIONET: Shkruaj një paragraf të zgjeruar për secilin grup ku analizon veprimet konkrete, datat, provat që i implikojnë dhe dispozitat e ligjit.
3. TEK PROVAT MATERIALE: Analizo të gjitha provat konkrete të administruara (nga Prova A-1 deri te D-1) dhe shpjego peshën e tyre provuese shkencore e ligjore.
4. TEK TABELA STATUTORE: Ndërto një tabelë të gjerë me TË GJITHA nenet e përmendura (KPK, KPPRK, LPK, Kushtetuta, Konventat) me analizë të thellë të pasojës procedurale.
5. TEK KORRIGJIMI I NENEVE: Identifiko çdo pasaktësi doktrinare dhe jep zëvendësimin e saktë me nen dhe ligj.
======================================================================

{'='*60}
TEKSTI I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER FORENZIK:

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
(Shkruaj një arsyetim të plotë e të detajuar për secilën pikë):
* **Lloji dhe Natyra e Aktit:** {doc_category} — Analizo natyrën formale dhe efektin juridik të shkresës.
* **Kompetenca Lëndore, Territoriale dhe Funksionale:** Përcakto pse kompetenca i takon PSRK-së sipas Ligjit Nr. 03/L-052 (Neni 9) dhe arsyeto papërshtatshmërinë ligjore dhe konfliktin e interesit të Prokurorisë Themelore.
* **Legjitimimi Procedural i Palëve:** Vlerëso legjitimimin aktiv dhe pasiv të {client_name} dhe palëve të tjera sipas ligjeve procedurale të Kosovës.
* **Auditimi i Afateve & Urgjenca Procedurale (Periculum in mora):** Analizo afatet ligjore prekluzive, rrezikun e pariparueshëm psikofizik dhe domosdoshmërinë e veprimit brenda 24 orëve.

### 2. 👥 STRUKTURA E TË GJITHË AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
(Zbërthe me nga një paragraf të plotë dhe të arsyetuar për secilin grup aktorësh):
* **Zyrtarët e Lartë Ekzekutivë (Ministria e Drejtësisë):** Analizo veprimet konkrete të ushtrimit të ndikimit (Neni 424 KPK), shtytjes (Neni 32 KPK) dhe bashkëkryerjes në keqpërdorim detyre (Nenet 31 & 414 KPK).
* **Trupat Gjykues dhe Gjyqtarët e Përfshirë:** Analizo shkeljet e pretenduara mbi nxjerrjen e vendimeve të kundërligjshme (Neni 425 KPK), shkeljen e rehabilitimit ligjor (Neni 93 KPK), parafabrikimin procedural dhe dëbimin nga salla.
* **Mjekët dhe Ekspertët e Psikiatrisë Forenzike:** Analizo bazueshmërinë e diagnozave kundrejt provave laboratorike dhe konsumimin e veprave penale të ekspertizës së rreme (Neni 387 KPK) dhe falsifikimit (Neni 427 KPK).
* **Zyrtarët e Qendrës për Punë Sociale (QPS):** Analizo veprimet e njëanshme, marrjen e deklaratave nën kontroll fizik dhe kanosjen psikologjike të fëmijës (Nenet 250, 386 & 414 KPK).
* **Organet e Ndjekjes dhe Hetuesit Policorë:** Analizo fshehjen e provave shfajësuese digjitale (Neni 382 KPK) dhe cenimin e barazisë së armëve (Neni 193 KPK).

### 3. 🔬 KRYQËZIMI FORENZIK I TË GJITHA PROVAVE MATERIALE (CORPUS DELICTI)
(Analizo me imtësi fuqinë provuese të secilës provë konkrete të fashikullit):
* **Trekëndëshi i Falsifikimit Mjekësor vs. E Vërteta Shkencore:** Analizo Certifikatën Toksikologjike të Laboratorit "Koslabor" (Prova A-1) me rezultat 100% Negativ kundrejt raporteve gojore të QKUK-së.
* **Vetë-Kontradikta Gjyqësore:** Analizo Faqen 4 të Aktgjykimit C.nr. 5906/25 (Prova A-3) ku konstatohet mungesa e refuzimit nga fëmija, kundrejt masës së izolimit në QPS.
* **Provat Digjitale, Audiot dhe Mesazhet:** Analizo regjistrimin audio (Prova B-7), vizatimin dhe mesazhet e lidhjes afektive atë-bir (Prova B-6).
* **Ligjshmëria e Provave dhe Prapadatimet:** Analizo procesverbalet me kryerreshta të prapadatuar "19.01.2024" (Prova C-1) dhe papranueshmërinë e provave sipas Nenit 257 të KPPRK-së.

### 4. ⚖️ TABELA SHTERRUESE E TË GJITHA DISPOZITAVE STATUTORE (KOSOVË)
(Përfshi TË GJITHA nenet e përmendura në shkresë në një tabelë të gjerë me analizë doktrinare):
| Dispozita & Ligji i Zbatueshëm në Kosovë | Statusi Procedural | Analiza Doktrinare & Pasojat Juridike |
| :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE AUDITIMI I NENEVE
* 🔴 **[KRITIKE - CONTRA LEGEM]:** Analizo shkeljet flagrante të ligjit (p.sh. përdorimi i dënimit të shlyer në kundërshtim me Nenin 93 të KPK-së, marrja e vendimeve të pambështetura në prova).
* 🔍 **KORRIGJIMI DOKTRINAR I NENEVE DHE FORMULIMEVE:**
  (Identifiko me saktësi çdo dispozitë ku kërkohet saktësim ose specifikim paragrafi për ta blinduar shkresën para gjykatës):
  * Shpjego qartë cilat nene duhet të plotësohen me paragrafët përkatës të ligjit pozitiv të Kosovës.

### 6. 🔬 AUDITIMI I PETITUMIT DHE EKZEKUTUESHMËRISË
* Analizo qartësinë e kërkesës për masa emergjente mbrojtëse (Nenet 188 & 221 të KPPRK-së).
* Vlerëso a është kërkesa e ekzekutueshme menjëherë nga Policia e Kosovës brenda 24 orëve.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI GJYQËSOR)
* **Draft-Teksti Profesional i Korrigjuar:** Jep formulimin e plotë e të saktë të kërkesës përfundimtare gati për t'u integruar në aktin procedural.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca 24-48 Orë):** Depozitimi i kërkesës për urdhëresë emergjente mbrojtëse në PSRK dhe ekzekutimi policor.
* 🟡 **HAPI 2 (Veprimet Institucionale & Provat):** Caktimi i ekspertizës së pavarur psikologjike/psikiatrike dhe sekuestrimi i metadatave kompjuterike.
* 🟢 **HAPI 3 (Strategjia në Seancë / Ballafaqimi):** Përgatitja e pyetjeve kryqëzuese (cross-examination) dhe procedimi i aktakuzës në Departamentin Special.
"""