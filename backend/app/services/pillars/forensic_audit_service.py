# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDIT V80.0 (DENSE LEGAL REASONING • ZERO FLUFF)

import logging
import re
from typing import Dict, Any, Optional, Tuple
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (🔬):
    Auditimi Suprem i Nivelit Gjyqësor të Dokumentit:
    - Analizë e thellë, e dendur dhe e padiskutueshme doktrinare.
    - Zbulim kirurgjikal i shkeljeve procedurale, ligjshmërisë së provave dhe gabimeve Contra Legem.
    - Zero tekst mbushës — Çdo fjali bart peshë juridike dhe statutore të Kosovës.
    """

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> Tuple[str, str]:
        combined = f"{file_name} {document_text[:8000]}".lower()
        
        categories = [
            ("AKTAKUZË / KALLËZIM PENAL", ["kallëzim penal", "kallezim penal", "kallzim penal", "aktakuzë", "aktakuze", "denoncim penal", "vepër penale"], 
             "Audito elementet konstitutive të figurës së veprës penale sipas KPK, ligjshmërinë e hetimeve, kompetencën e prokurorisë (Themelore/Speciale) dhe papranueshmërinë e provave (Neni 257 KPPRK)."),
            
            ("AKTGJYKIM / AKTVENDIM GJYKATE", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore", "trupi gjykues", "kolegji"],
             "Audito ligjshmërinë dhe arsyetimin e vendimit, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), mospërputhjet midis arsyetimit dhe dispozitivit dhe bazën e hekurt për ANKESË."),
            
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
        
        search_query = query_text or f"Auditimi forenzik suprem i {doc_category}: {case_title}. Lëmia: {case_domain}. Nenet e ligjit të Kosovës, shkeljet thelbësore procedurale, contra legem, papranueshmëria e provave."
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
MANDATI I KRYE-GJYQTARIT DHE EKSPERTIT TË FORENZIKËS GJYQËSORE:
Ti vepron me nivelin më të lartë të analizës juridiko-shkencore të Gjykatës Supreme të Republikës së Kosovës.

⚠️ RREGULLAT E HEKURTA TË DENDËSISË DHE PROFESIONALIZMIT:
1. ZERO TEKST MBUSHËS: Ndalohen fjalitë e përgjithshme dhe deklaratat sipërfaqësore. Çdo paragraf duhet të mbajë arsyetim të thellë, dispozita ligjore ekzakte dhe peshë provuese.
2. ANALIZË SHKATËRRUESE E PROVAVE DHE AKTORËVE: Ekstrakto nga teksti të gjithë personat/institucionet dhe provat materiale konkrete, duke i kryqëzuar ato kirurgjikisht.
3. IDENTIFIKIMI I SHKELJEVE 'CONTRA LEGEM': Zbulo çdo zbatim të gabuar të së drejtës materiale, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK) dhe provat e papranueshme (Neni 257 KPPRK).
4. SAKTSIA STATUTORE: Çdo nen duhet të analizohet në lidhje me pasojën direkte procedurale për klientin ({client_name}).
======================================================================

{'='*60}
TEKSTI I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER TË AUDITIMIT FORENZIK:

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE
* **Lloji dhe Natyra e Shkresës:** {doc_category}
* **Kompetenca Lëndore, Territoriale dhe Funksionale:** (Përcakto saktë nëse organi/gjykata është kompetente sipas ligjeve pozitive të Kosovës dhe a ka konflikt interesi apo papërshtatshmëri ligjore).
* **Legjitimimi i Palëve:** (Vlerësimi i legjitimimit aktiv dhe pasiv, autorizimit të përfaqësimit dhe cilësive procedurale).
* **Objekti dhe Vlera e Kontestit:** (Përcaktimi i saktë i objektit dhe interesit juridik).
* **Auditimi i Afateve & Prekluzivitetit:** (Verifikimi rigoroz i afateve ligjore për veprim, parashkrimit penal/civil dhe rrezikut nga vonesa — *Periculum in mora*).

### 2. 👥 STRUKTURA E AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË
(Analizo veprimet e secilit aktor të përfshirë në shkresë):
* Zbërthe rolet e palëve, gjyqtarëve, prokurorëve, ekspertëve apo zyrtarëve publikë të përmendur.
* Përcakto saktë nëse veprimet e tyre përbëjnë veprimtari të ligjshme, tejkalim kompetence, shkelje disiplinore, apo konsumojnë elemente të veprave penale (p.sh. Nenet 414, 425, 387, 382 të KPK-së).

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DISKREPANCAT
* **Analiza e Provave Shkresore & Laboratorike:** Analizo fuqinë provuese të secilit dokument të administruar.
* **Matrica e Kontradiktave:** Ballafaqo pretendimet gojore/subjektive me provat e vërtetuara materiale dhe shkencore.
* **Ligjshmëria e Provave (Neni 257 KPPRK / Neni 8 LPK):** Identifiko nëse ka prova të papranueshme, të marra në mënyrë të paligjshme ose nën presion/mashtrim.
* **Integriteti i Formës dhe Prapadatimet (Antidatum/Metadata):** Vlerëso nëse aktet përmbajnë manipulime formale, prapadatime apo mungesë elementesh thelbësore.

### 4. ⚖️ VERIFIKIMI NEN-PËR-NEN I DISPOZITAVE STATUTORE (KOSOVË)
(Ndërto tabelën shterruese të verifikimit për të gjitha dispozitat e ligjit të zbatueshëm për lëminë **{case_domain}**):
| Dispozita & Ligji i Zbatueshëm | Statusi Procedural | Analiza Doktrinare & Pasojat Juridike |
| :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE DHE SHKELJET "CONTRA LEGEM"
* 🔴 **[KRITIKE - CONTRA LEGEM]:** Shkeljet flagrante të normave urdhëruese ligjore (p.sh. zbatim i ligjit të shfuqizuar, shkelje e rehabilitimit ligjor, cenim i parimit të barazisë së armëve, mohim i të drejtës së mbrojtjes).
* 🟡 **[Lapsuse Formale & Dobësi Taktike]:** Mangësi në arsyetim, mos-përputhje mes dispozitivit dhe arsyetimit, gabime teknike në shuma apo emra.

### 6. 🔬 AUDITIMI I PETITUMIT DHE EKZEKUTUESHMËRISË
* A është kërkesa (petenumi) e qartë, e numëruar saktë dhe në harmoni me të drejtën materiale?
* A përmban kërkesa të pazbatueshme apo formulime që rrezikojnë refuzimin nga trupi gjykues?
* A është akti i ekzekutueshëm nga përmbaruesi privat sipas Ligjit për Procedurën Përmbarimore (LPP)?

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI GJYQËSOR)
* **Formulimi Profesional i Korrigjuar:** Rishkruaj saktë paragrafin, dispozitivin apo pikat ankimore me gabime, gati për t'u integruar në shkresën zyrtare.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Veprimi i Menjëhershëm - Brenda Afatit):** Shkresa formale që duhet depozituar (Ankesë, Prapësim, Kallëzim Penal, Kërkesë për Masë Emergjente).
* 🟡 **HAPI 2 (Veprimet Institucionale & Provat):** Kërkesat për sigurimin e provave të reja, ekspertiza të pavarura apo përjashtim të personave në konflikt interesi.
* 🟢 **HAPI 3 (Strategjia në Seancë / Ballafaqimi):** Taktika e përfaqësimit, pyetjet kryqëzuese dhe pikat e pathyeshme mbrojtëse për fitoren e lëndës.
"""