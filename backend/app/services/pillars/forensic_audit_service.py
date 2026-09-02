# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDIT V110.0 (SURGICAL STATUTE LAPSE DETECTOR & REMEDIATION)

import logging
import re
from typing import Dict, Any, Optional, Tuple
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (🔬):
    Auditimi Kirurgjikal i Neneve dhe Zbulimi i të Gjitha Lapsuseve:
    - Skanon çdo nen të cituar dhe zbulon me përpikmëri çdo gabim numerik, ligj të pasaktë apo paragraf të mangët.
    - Ofron zëvendësimin e saktë të dispozitës për të blinduar shkresën para gjykatës dhe prokurorisë.
    """

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> Tuple[str, str]:
        combined = f"{file_name} {document_text[:8000]}".lower()
        
        categories = [
            ("AKTAKUZË / KALLËZIM PENAL", ["kallëzim penal", "kallezim penal", "kallzim penal", "aktakuzë", "aktakuze", "denoncim penal", "vepër penale"], 
             "Audito elementet konstitutive të veprës penale sipas KPK, kompetencën e PSRK-së, papranueshmërinë e provave (Neni 257 KPPRK) dhe lapsuset e neneve."),
            
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
MANDATI I KRYE-GJYQTARIT DHE AUDITORIT KIRURGJIKAL TË NENEVE:
Ti vepron me autoritetin më të lartë shkencor e doktrinar të Gjykatës Supreme të Republikës së Kosovës.

⚠️ URDHËR I HEKURT PËR MBULIMIN E TË GJITHA NENEVE DHE ZBULIMIN E LAPSUSEVE:
1. MBULIM 100% I DISPOZITAVE: Tek Seksioni 4, përfshi TË GJITHA nenet e përmendura në shkresë në tabelë (Kodi Penal, KPPRK, LPK, LMD, Kushtetuta, Konventat) pa lënë asnjë jashtë.
2. AUDITIM KIRURGJIKAL I LAPSUSEVE: Tek Seksioni 5, zbulo çdo gabim ku një nen është cituar me titull të gabuar, me numër të pasaktë apo kur mungon paragrafi përkatës, dhe jep DISPOZITËN E SAKTË për zëvendësim.
3. KRYQËZIM I PROVAVE DHE AKTORËVE: Analizo me paragrafë të plotë të gjithë aktorët dhe provat konkrete të administruara.
======================================================================

{'='*60}
TEKSTI I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER TË AUDITIMIT FORENZIK:

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE
* **Lloji dhe Natyra e Shkresës:** {doc_category}
* **Kompetenca Lëndore, Territoriale dhe Funksionale:** (Përcakto kompetencën sipas ligjeve të Kosovës dhe arsyeto konfliktet e interesit).
* **Legjitimimi i Palëve dhe Përfaqësimi:** (Legjitimimi aktiv/pasiv dhe autorizimi sipas ligjit).
* **Objekti dhe Vlera e Kontestit:** (Objekti juridik dhe interesat pasurore/penale).
* **Auditimi i Afateve & Prekluzivitetit:** (Afatet ligjore për veprim, parashkrimi dhe rreziku nga vonesa — *Periculum in mora*).

### 2. 👥 STRUKTURA E TË GJITHË AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
(Zbërthe me paragrafë të plotë të gjithë personat, gjyqtarët, prokurorët, mjekët/ekspertët dhe zyrtarët e përfshirë):
* Rendit veprimet e secilit aktor me datat përkatëse dhe kualifikimin penal/procedural (p.sh. Nenet 414, 424, 425, 387, 382 të KPK-së).

### 3. 🔬 KRYQËZIMI FORENZIK I TË GJITHA PROVAVE MATERIALE (CORPUS DELICTI)
* **Skanimi Provë-për-Provë:** Analizo secilën provë të administruar në shkresë (laboratorike, gjyqësore, procesverbale, regjistrime audio/video).
* **Matrica e Kontradiktave:** Ballafaqo mospërputhjet midis deklaratave gojore dhe provave materiale e shkencore të vërtetuara.
* **Ligjshmëria e Provave (Neni 257 KPPRK / Neni 8 LPK):** Identifiko provat e papranueshme apo të marra me shkelje procedurale.
* **Integriteti Formale dhe Prapadatimet (Antidatum/Metadata):** Zbulo prapadatimet apo manipulimet në procesverbale.

### 4. ⚖️ TABELA SHTERRUESE E TË GJITHA DISPOZITAVE STATUTORE (KOSOVË)
(Përfshi TË GJITHA nenet e përmendura në shkresë pa lënë asnjë jashtë — KPK, KPPRK, LPK, LMD, Kushtetutë, Konventa):
| Dispozita & Ligji i Zbatueshëm në Kosovë | Statusi Procedural | Analiza Doktrinare & Pasojat Juridike |
| :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE KORRIGJIMI I LAPSUSEVE STATUTORE
* 🔴 **[KRITIKE - CONTRA LEGEM]:** Shkeljet thelbësore të normave urdhëruese ligjore (shkelje e rehabilitimit ligjor Neni 93 KPK, cenim i barazisë së armëve, vendime të kundërligjshme).
* 🔍 **AUDITIMI DHE KORRIGJIMI KIRURGJIKAL I LAPSUSEVE TË NENEVE:**
  (Rendit me saktësi çdo nen të cituar me gabim dhe jep zëvendësimin e saktë):
  * ❌ **Neni me Lapsus në Shkresë:** [Numri i nenit dhe ligji siç është shkruar gabimisht]
  * ➔ **Arsyeja e Gabimit:** [Përshkrimi i pasaktësisë doktrinare apo ligjit të përdorur]
  * ✅ **Dispozita e Saktë për Zëvendësim:** [Neni dhe ligji i saktë që duhet të vihet në shkresë]

### 6. 🔬 AUDITIMI I PETITUMIT DHE EKZEKUTUESHMËRISË
* A është kërkesa e qartë, e numëruar saktë dhe e zbatueshme nga gjykata apo policia?
* A është akti i ekzekutueshëm sipas Ligjit për Procedurën Përmbarimore (LPP)?

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI GJYQËSOR)
* **Formulimi Profesional i Korrigjuar:** Rishkruaj tekstin e saktë profesional se si duhet të formulohet kërkesa, ankesa apo prapësimi.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca 24-48 Orë):** Shkresa formale që duhet depozituar menjëherë (Masë Emergjente, Ankesë, Prapësim).
* 🟡 **HAPI 2 (Veprimet Institucionale & Provat):** Kërkesat për sigurimin e provave të reja, ekspertiza të pavarura apo sekuestrime.
* 🟢 **HAPI 3 (Strategjia në Seancë / Ballafaqimi):** Pyetjet kryqëzuese (cross-examination) dhe strategjia e fitores në shqyrtim kryesor.
"""