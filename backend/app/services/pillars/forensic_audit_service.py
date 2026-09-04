# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDITOR V250.0 (PURE FORENSIC AUDIT • ZERO DRAFTING • 1-CLICK VERIFICATION • ZERO HARDCODING)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME (V250.0):
    - 100% Dinamik, Shkencor dhe i Paanshëm: Ekstraktim ekskluzivisht nga teksti real i dokumentit të paraqitur.
    - ZERO Hardcoding: Asnjë emër, numër lënde, shumë apo fakt i fabrikuar me dorë.
    - ZERO DRAFTING: Nuk shkruan asnjë draft shkrese; fokusohet 100% në AUDITIM DHE REKOMANDIME.
    - 1-Klikim Verifikim: Çdo nen i përmendur listohet me formatin standard 'Neni X i [Ligjit]'.
    - Diagnostikon saktësinë formale, mangësitë e petitumit, lapsuset dhe precedentët përkatës të Gjykatës Supreme.
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LSHT|LFK|LPP|LPPA|LPTS|KEDNJ|Kushtetut[a-zë]*|Ligji\s+Nr\.\s*[\d/L\-]+)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|REV|AC|CA|A|PKR|PP|C|P|E|KE)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(dict.fromkeys(articles))[:30]
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
                context_str=audit_text[:12000],
                manifest_str=manifest_str or ""
            )
        
        pos = (client_position or "PALË NË PROCEDURË").strip().upper()
        mined_legal_entities = ForensicAuditService.extract_legal_entities_from_text(audit_text)
        
        precedent_prefix = "PML" if case_domain.lower() in ["penale", "kallëzim penal", "krim"] else "Rev"
        search_query = query_text or f"{mined_legal_entities} {case_domain} Nenet Aktgjykimet e Gjykatës Supreme {precedent_prefix}"

        # Izolim i qëllimshëm i RAG: vetëm precedentët dhe ligjet pa ndotje nga dokumente të tjera
        rag_context = ""
        try:
            rag_context, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",  # Izolim absolut
                query_text=search_query,
                n_results=20
            )
        except Exception as rag_err:
            logger.warning(f"Forensic RAG search fallback: {rag_err}")

        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM FORENZIK DOKTRINAR I SHKRESËS • GJYKATA SUPREME E KOSOVËS
MANDATI YT SUPREM:
Përpara teje ndodhet një dokument specifik gjyqësor/procedural për auditim të thellë.
Detyra jote absolute është VLERËSIMI FORENZIK DHE DHËNIA E REKOMANDIMEVE ADEKUATE:
1. Audito VETËM DHE EKSKLUZIVISHT këtë shkresë specifike që ndodhet më poshtë në seksionin e tekstit.
2. NDALOHET KATEGORIKISHT HARTIMI I NJË DOKUMENTI (Padi, Ankesë apo Aktvendim). Roli yt këtu NUK është të prodhosh draft shkresash, por të kryesh AUTOPSINË E SHKRESËS, TË EVIDENTOSH TË METAT DHE TË JAPËSH REKOMANDIMIN E SAKTË.
3. Zbërthe çdo nen ligjor në formatin standard për verifikim 1-klikim: `Neni X i [Ligjit]`.
4. Evidento shkeljet procedurale, pasaktësitë e petitumit dhe lapsuset formale.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS NË AUDITIM:
{manifest_str or 'Dokument Gjyqësor / Procedural'}
LËMIA E PËRCAKTUAR NGA TEKSTI: **{case_domain}**
DATA E AUDITIMIT: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E RELEVANTË TË GJYKATËS SUPREME:
{rag_context if rag_context else "Zbato legjislacionin pozitiv të Republikës së Kosovës dhe praktikat e konsoliduara të Kolegjeve të Gjykatës Supreme."}

======================================================================
RREGULLAT E HEKURTA TË AUDITIMIT FORENZIK (ZERO DRAFTING • PURE AUDIT):

1. BESNIKËRI ABSOLUTE NDAJ KËTIJ DOKUMENTI TË VETËM:
   - Të gjitha faktet, emrat, organet, datat dhe numrat e lëndës duhet të merren 100% nga teksti i këtij dokumenti.
   - Nëse një element mungon në shkresë, deklaro qartë që nuk specifikohet; mos supozo asgjë.

2. ZERO DRAFTING (MOS HARTO ASNJË DOKUMENT):
   - Mos shkruaj formate padish apo ankesash gati për nënshkrim.
   - Përqendrohu te këshillimi dhe diagnoza: Çfarë gabimesh ka shkresa? Si duhet përmirësuar? Çfarë veprimi duhet ndërmarrë?

3. VERIFIKIMI ME 1-KLIKIM DHE PRECEDENTËT SUPREMË:
   - ÇDO NEN i cituar në shkresë DUHET të shfaqet në tabelën e Seksionit 4 me formatin ekzakt:
     `Neni X i [Ligjit]` (p.sh. `Neni 256 i LPK-së`, `Neni 414 i KPRK-së`, `Neni 54 i Kushtetutës`).
   - Lidh çdo institut me precedentin përkatës suprem (Rev për civile/ekonomike, PML për penale) pa përsëritje mekanike.
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK (8 SEKSIONE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji dhe Natyra Formale e Shkresës:** Përcakto saktësisht aktin sipas tekstit të tij (Padi, Kundërpadi, Ankesë, Kallëzim Penal, Aktvendim, Procesverbal, etj.).
* **Organi Nxjerrës / Kompetent:** Gjykata, prokuroria apo autoriteti përgjegjës.
* **Numri i Regjistrit / Shenja e Lëndës:** Numri identifikues i dokumentit.
* **Auditimi i Afateve Procedurale:** Verifikimi nëse akti është nxjerrë/paraqitur brenda afatit ligjor prekluziv.

### 2. 👥 STRUKTURA E PALËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
* **Parashtruesi / Iniciuesi:** Identifikimi i palës dhe legjitimiteti procedural.
* **Pala Kundërshtare / Subjektet e Atakuara:** Palët ndaj të cilave drejtohet akti.
* **Cilësia Juridike:** Interesi i provuar juridik dhe baza e legjitimimit aktiv/pasiv.

### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE
* **Pretendimet Kryesore Faktike:** Faktet kryesore të parashtruara në këtë akt specifik.
* **Provat e Administruara / Bashkëlidhura:** Provat e përmendura në këtë shkresë.
* **Pikat Kritike Provuese:** Vlerësimi i fuqisë provuese dhe boshllëqet që lë ky akt.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(Çdo nen të citohet me formatin `Neni X i [Ligjit]` për verifikim 1-klikim, me precedentin përkatës të Gjykatës Supreme Rev ose PML):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I GABIMEVE
* 🔴 **Gjetjet Kritike Procedurale dhe Materiale:** Shkeljet e procedurës, gabimet në kompetencë, apo zbatimi i gabuar i normës.
* 🔍 **Detektori i Pasaktësive dhe Lapsuseve në Shkresë:**
  | Formulimi / Dispozita Aktuale në Shkresë | Pasaktësia / Lapsusi i Identifikuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I KËRKESËS (PETITUMIT) DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Qartësisë së Kërkesës:** A është vendimi apo kërkesa e formuluar saktë dhe e mbështetur në ligj?
* **Rreziqet Procedurale:** Pengesat që mund të çojnë në rrëzimin, refuzimin apo prishjen e aktit.
* **Ekzekutueshmëria:** Pasojat ekzekutive dhe zbatueshmëria reale.

### 7. 💡 DIAGNOZA KORRIGJUESE DHE REKOMANDIMET E DREJTPËRDREJTA PËR SHKRESËN
(Konsulencë strategjike PA HARTUAR shkresa të reja:
* **Vlerësimi i Qëndrueshmërisë Ligjore të Aktit:** Pikat e forta dhe të dobëta të kësaj shkrese.
* **Këshilla Profesionale mbi Korrigjimin:** Çfarë argumentesh duhen hequr, çfarë duhen shtuar dhe si duhet riformuluar kërkesa.
* **Rekomandimi Taktik i Hapit të Radhës:** Çfarë veprimi konkret duhet ndërmarrë menjëherë ndaj këtij akti).

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afatet Prekluzive):** Çfarë duhet bërë brenda afatit më të ngutshëm ligjor.
* 🟡 **HAPI 2 (Plotësimi Provues dhe Taktik):** Hapat për konsolidimin e pozicionit proceduror.
* 🟢 **HAPI 3 (Strategjia në Organin Kompetent):** Linja argumentuese gjatë shqyrtimit të aktit.
"""