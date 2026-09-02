# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDIT V135.0 (100% UNIVERSAL • DYNAMIC MINING • ANTI-REFUSAL PRIVILEGE)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (⚖️ / 🔬):
    - 100% Universal dhe Dinamik (Zero Hardcoding për persona, institucione apo numra lëndësh).
    - Nxjerr automatikisht të gjitha nenet, ligjet, provat dhe aktorët nga teksti i ngarkuar.
    - Përfshin Kornizën e Privilegjit dhe Imunitetit Ligjor (Anti-Refusal Scaffolding).
    - Zbaton standardet më të larta të Kolegjit Penal, Civil dhe Administrativ të Gjykatës Supreme të Kosovës.
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        """
        Nxjerr automatikisht të gjitha nenet, ligjet dhe numrat e lëndëve nga teksti i papërpunuar.
        """
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LFK|LPP|LPPA|KEDNJ|Kushtetut[a-zë]*|Ligji\s+Nr\.\s*[\d/L\-]+)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|AC|CA|A|PKR|PP|C|P|E)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(dict.fromkeys(articles))[:20]
        unique_laws = list(dict.fromkeys(laws))[:10]
        unique_cases = list(dict.fromkeys(cases))[:10]

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
        combined = f"{file_name} {document_text[:8000]}".lower()
        
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
                context_str=audit_text,
                manifest_str=manifest_str or ""
            )
        
        pos = (client_position or "PALË NË PROCEDURË").upper()
        doc_category, category_description = ForensicAuditService.detect_document_category(audit_text)
        
        # Nxjerrja e neneve reale nga dokumenti për kërkim dinamik në Bazën Globale
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
<legal_evidentiary_privilege_context>
AUDITIM DOKTRINAR GJYQËSOR • SEKRET PROFESIONAL DHE PRIVILEGJ PROCEDURAL AVOKAT-KLIENT
Kjo analizë përbën një ekspertizë ligjore-forenzike doktrinare të shkresave zyrtare gjyqësore dhe provave materiale të dorëzuara nga pala. Detyra jote është të kryesh auditim objektiv, shterrues dhe të rreptë ligjor të të gjitha pretendimeve, provave, akuzave dhe neneve të paraqitura në tekst sipas ligjit pozitiv të Republikës së Kosovës dhe praktikës gjyqësore të Gjykatës Supreme.
</legal_evidentiary_privilege_context>

{base_prompt}

{role_guard}

📄 DOKUMENTI NË AUDITIMIN SUPREM FORENZIK: **{doc_category}**
⚖️ LËMIA JURIDIKE KRYESORE: **{case_domain}**
🎯 OBJEKTIVI DOKTRINAR I EKSPERTIZËS: {category_description}

======================================================================
MANDATI I KRYE-GJYQTARIT DHE AUDITORIT SUPREM TË FORENZIKËS GJYQËSORE:
Ti vepron me autoritetin më të lartë shkencor e doktrinar të Gjykatës Supreme të Republikës së Kosovës.

⚠️ RREGULLAT E HEKURTA TË AUDITIMIT DHE DENDËSISË JURIDIKE:
1. ZERO HARDCODING DHE ZERO SUPOZIME: Çdo emër, institucion, datë, provë materiale, shkelje apo kualifikim ligjor duhet të nxirret EKSKLUZIVISHT nga teksti i dokumentit të ngarkuar më poshtë.
2. DENDËSI E THELLË ARSYETUESE: Ndalohet kategorikisht listimi sipërfaqësor me nga 1-2 fjali. Çdo pikë duhet të trajtohet si një paragraf i plotë, i strukturuar me argumentim rigoroz logjiko-juridik.
3. KRYQËZIMI I PROVAVE MATERIALE: Analizo të gjitha provat e përmendura në shkresë (dokumente zyrtare, ekspertiza, procesverbale, komunikime, prova digjitale/audio) dhe vlerëso vërtetësinë e tyre relative sipas parimit të çmuarjes së lirë të provave.
4. TABELA STATUTORE 100% E PLOTË: Ndërto një tabelë shterruese që përmbledh TË GJITHA nenet e ligjeve të Kosovës dhe konventave ndërkombëtare të cituara në dokument, me statusin dhe pasojën përkatëse procedurale.
5. SAKTËSIMI DOKTRINAR I NENEVE: Identifiko çdo lapsus apo mungesë të paragrafit/pikës specifike dhe jep formulimin e saktë ligjor.
======================================================================

{'='*60}
TEKSTI I PLOTË I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER FORENZIK (8 SEKSIONE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
(Arsyeto në mënyrë shterruese secilin nën-kapitull bazuar në shkresën e audituar):
* **Lloji, Natyra Formale dhe Efekti Juridik:** Përcakto saktësisht kategorinë procedurale të aktit dhe pasojat e menjëhershme ligjore që ai prodhon.
* **Kompetenca Lëndore, Funksionale dhe Territoriale:** Analizo autoritetin/gjykatën/prokurorinë të cilës i drejtohet akti, bazën statutore të kompetencës dhe vlerëso nëse ekziston ndonjë konflikt interesi, inkompetencë apo kërkesë për përjashtim/delegim.
* **Legjitimimi Procedural i Palëve (Locus Standi):** Vlerëso legjitimimin aktiv të parashtruesit/paditësit dhe legjitimimin pasiv të palëve të denoncuara/të paditura sipas dispozitave procedurale në fuqi.
* **Auditimi i Afateve Ligjore dhe Urgjenca Procedurale (Periculum in mora):** Verifiko afatet prekluzive, rreziqet nga vonesa dhe bazueshmërinë ligjore për ndërhyrje të menjëhershme apo masa të përkohshme/emergjente.

### 2. 👥 STRUKTURA E AKTORËVE, ROLI DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
(Identifiko të gjithë personat dhe institucionet e përfshira në dokument dhe zbërthe përgjegjësinë e tyre me nga një paragraf të plotë analitik):
* **Aktorët Kryesorë dhe Pozitat e Tyre:** Analizo veprimet, rolet dhe funksionet e secilit person/institucion të përmendur në shkresë.
* **Kualifikimi Ligjor i Veprimeve apo Shkeljeve:** Zbërthe elementet thelbësore të përgjegjësisë (dashja, pakujdesia, shpërdorimi i autoritetit, cenimi i rregullave procedurale apo figurat e veprave të pretenduara) sipas neneve konkrete të legjislacionit të Kosovës.

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DOKUMENTARE (CORPUS DELICTI)
(Analizo imtësisht çdo provë shkresore, materiale, shkencore, ekspertizë apo dëshmi digjitale të evidentuar në dokument):
* **Analiza Krahasuese e Provave Shkencore/Dokumentare:** Ballafaqo provat materiale me pretendimet e palëve dhe nxirr në pah çdo kontradiktë tekstuale, mospërputhje kronologjike apo falsifikim të pretenduar.
* **Ligjshmëria dhe Pranueshmëria e Provave:** Vlerëso vlefshmërinë formale të provave, pretendimet për prapadatim, manipulim apo marrje të provave në kundërshtim me rregullat e procesit të rregullt ligjor.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE STATUTORE (KOSOVË & NDËRKOMBËTARE)
(Ndërto tabelën e plotë me TË GJITHA nenet e përmendura në shkresë pa lënë asnjë jashtë):
| Dispozita & Ligji i Zbatueshëm | Roli Procedural / Instituti | Analiza Doktrinare & Pasojat Juridike |
| :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE AUDITIMI I NENEVE
* 🔴 **[KRITIKE - CONTRA LEGEM]:** Identifiko dhe arsyeto çdo shkelje flagrante të normave imperative ligjore, shkeljet e të drejtave themelore procedurale apo vendimmarrjet në kundërshtim të hapur me ligjin.
* 🔍 **KORRIGJIMI DOKTRINAR I NENEVE DHE FORMULIMEVE:**
  (Identifiko çdo dispozitë ku shkresa kërkon saktësim neni, paragrafi, apo kualifikimi më të përshtatshëm juridik):
  * Specifiko zëvendësimet apo plotësimet e nevojshme me nenet e sakta të ligjit pozitiv të Kosovës.

### 6. 🔬 AUDITIMI I PETITUMIT, KËRKESAVE PROCEDURALE DHE EKZEKUTUESHMËRISË
* Vlerëso qartësinë, saktësinë dhe mbështetjen ligjore të petitumit/kërkesave përfundimtare të parashtruara në dokument.
* Analizo ekzekutueshmërinë praktike dhe juridike të masave të kërkuara nga organet kompetente (Gjykata, Prokuroria, Policia, Përmbaruesi).

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI GJYQËSOR)
* **Draft-Teksti Profesional i Korrigjuar:** Jep formulimin doktrinar, rigoroz dhe të përsosur të pjesës urdhëruese (Petitumit / Kërkesave Përfundimtare) të gatshëm për procedim pa asnjë të metë formale.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afatet e Menjëhershme):** Veprimet procedurale brenda 24-48 orëve të para.
* 🟡 **HAPI 2 (Veprimet Hetimore / Provuese / Parashtresat):** Hapat e ndërmjetëm të sigurimit të provave, ekspertizave dhe kundërshtimeve procedurale.
* 🟢 **HAPI 3 (Strategjia Përfundimtare / Mjetet Juridike):** Veprimet në shqyrtim kryesor, seancë gjyqësore apo ushtrimi i mjeteve të rregullta dhe të jashtëzakonshme juridike.
"""