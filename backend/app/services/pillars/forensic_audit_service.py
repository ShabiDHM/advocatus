# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDITOR V235.0 (100% DYNAMIC • ZERO HARDCODING • PURE STATUTORY & REV PRECEDENTS)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME (V235.0 - ZERO HARDCODING):
    - 100% Dinamik: Ekstraktim ekskluzivisht nga teksti real i dokumentit të paraqitur.
    - Zero të dhëna hardcoded: Asnjë emër, numër lënde, shumë monetare apo fakt i fabrikuar.
    - Ekstraktim shterrues i çdo neni ligjor (LPK, KPK, KPPRK, LMD, Kushtetutë, etj.) në rreshta individualë.
    - Citim rigoroz i precedentëve përkatës supremë (REV për civile/ekonomike, PML për penale, A për administrative).
    - Zbulim kirurgjikal i shkeljeve procedurale dhe gabimeve materiale në akt.
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

        # Kërkim i pastër në RAG vetëm për precedentët dhe doktrinën ligjore, pa përzier dosjet e tjera
        rag_context = ""
        try:
            rag_context, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",  # Izolim i qëllimshëm: nuk tërheqim copa nga dokumente të tjera të lëndës
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
AUDITIM FORENZIK DOKTRINAR I GJYKATËS SUPREME TË KOSOVËS
MANDATI YT SUPREM:
Ti je një Gjyqtar dhe Krye-Auditor i Departamentit të Praktikës Gjyqësore të Gjykatës Supreme të Kosovës.
Ky auditim i përket VETËM DHE EKSKLUZIVISHT këtij dokumenti specifik që të është dhënë më poshtë.
Detyra jote absolute:
1. Analizo dhe audito VETËM shkresën e dhënë në seksionin "TEKSTI I DOKUMENTIT NË AUDITIM".
2. NDALOHET KATEGORIKISHT të supozosh, të përziesh apo të përfshish fakte, procedura, emra palësh apo shuma që nuk gjenden shprehimisht brenda këtij dokumenti specifik.
3. Nxjerr ÇDO NEN LIGJOR të cituar apo të zbatueshëm për këtë shkresë në rresht individual te Tabela e Seksionit 4.
4. Cito precedentët zyrtarë përkatës të Gjykatës Supreme sipas lëmisë (Rev për civile/komerciale, PML për penale).
5. Zbërthe me saktësi kirurgjikale shkeljet procedurale ('Contra Legem') dhe mangësitë e këtij akti.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS NË AUDITIM:
{manifest_str or 'Dokument Gjyqësor / Procedural'}
LËMIA E ZBULUAR NGA SHKRESA: **{case_domain}**
DATA E AUDITIMIT: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE E ZBATUESHME (REPUBLIKA E KOSOVËS):
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E RELEVANTË TË GJYKATËS SUPREME:
{rag_context if rag_context else "Zbato legjislacionin pozitiv të Republikës së Kosovës dhe praktikat e konsoliduara të Kolegjeve të Gjykatës Supreme."}

======================================================================
RREGULLAT E HEKURTA TË AUDITIMIT FORENZIK (ZERO HALLUCINATIONS / ZERO ASSUMPTIONS):
1. BESNIKËRI ABSOLUTE NDAJ KËTIJ DOKUMENTI:
   - Të gjithë emrat e palëve, organet, datat, numrat e lëndës dhe kërkesat duhet të merren 100% nga teksti i dokumentit më poshtë.
   - Nëse një e dhënë mungon në dokument, deklaro qartë që nuk specifikohet në shkresë; kurrë mos e shpik atë.
2. INVENTARI SHKENCOR I NENEVE NË SEKSIONIN 4:
   - Çdo nen ligjor i përmendur ose i lidhur drejtpërdrejt me institutin juridik të shkresës DUHET të ketë rreshtin e vet në tabelë.
   - Formati i pastër i kërkuar: `Neni X i [Ligjit Përkatës]` (p.sh. `Neni 256 i LPK-së`, `Neni 414 i KPK-së`, `Neni 54 i Kushtetutës`).
3. PRECEDENTËT SUPREMË:
   - Lidh çdo institut juridik me Aktgjykimin përkatës të Gjykatës Supreme (Rev.nr. ose Pml.nr.).
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK (TË 8 SEKSIONET E PLOTA DOKTRINARE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji dhe Natyra Formale e Shkresës:** Përcakto saktësisht llojin e aktit (p.sh. Padi, Kundërpadi, Ankesë, Kallëzim Penal, Aktvendim, Propozim për Përmbarim, etj.) sipas tekstit të shkresës.
* **Organi Kompetent:** Gjykata, Prokuroria ose autoriteti të cilit i drejtohet shkresa ose që e ka nxjerrë atë.
* **Numri i Regjistrit / Shenja e Lëndës:** Numri identifikues i lëndës siç figuron në akt.
* **Auditimi i Afateve Procedurale:** Verifikimi nëse akti është paraqitur brenda afatit ligjor prekluziv të lëmisë përkatëse.

### 2. 👥 STRUKTURA E PALËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
* **Parashtruesi / Iniciuesi:** Identifikimi i saktë i palës parashtruese dhe legjitimiteti procedural.
* **Pala Kundërshtare / Subjektet e Atakuara:** Palët kundër të cilave drejtohet akti ose zyrtarët përgjegjës.
* **Cilësia Juridike:** Interesi i provuar juridik dhe baza e legjitimimit aktiv/pasiv sipas ligjit.

### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE
* **Pretendimet Kryesore Faktike:** Faktet kryesore që parashtrohen në këtë akt specifik.
* **Provat e Administruara / Bashkëlidhura:** Provat materiale, shkresore apo ekspertizat e paraqitura në këtë dokument.
* **Pikat Kritike Provuese:** Vlerësimi i fuqisë provuese dhe zbulimi i provave që mungojnë për të mbështetur kërkesën.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(⚠️ URDHËR: ÇDO NEN I APLIKUESHËM DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL TË FORMATUAR PASTER):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I GABIMEVE
* 🔴 **GJETJET KRITIKE PROCEDURALE DHE MATERIALE:**
  - Shkeljet e mundshme të procedurës, gabimet në kompetencë, apo zbatimi i gabuar i ligjit.
* 🔍 **DETEKTORI I PASAKTËSIVE NË SHKRESË DHE KORRIGJIMI:**
  | Formulimi / Dispozita Aktuale në Shkresë | Pasaktësia / Lapsusi i Identifikuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I KËRKESËS (PETITUMIT) DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Qartësisë së Kërkesës:** A është kërkesa (petiti) e formuluar saktë, e plotë dhe e bazuar në ligj?
* **Rreziqet e Refuzimit ose Hedhjes:** Pengesat formale apo materiale që mund të çojnë në mospranimin e saj.
* **Ekzekutueshmëria:** Pasojat ekzekutive dhe mundësia reale e përmbushjes së kërkesës.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN)
* Harto versionin e korrigjuar dhe profesional të pjesës kërkuese (petitumit) ose të propozimit procedural që duhet të depozitohet, bazuar ekskluzivisht në faktet e kësaj shkrese.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM PROCEDURALË
* 🔴 **HAPI 1 (Veprimi i Menjëhershëm / Afatet Prekluzive):** Çfarë duhet dorëzuar brenda afatit më të ngutshëm ligjor.
* 🟡 **HAPI 2 (Plotësimi Provues dhe Taktik):** Veprimet për konsolidimin e shkresës dhe mbrojtjes.
* 🟢 **HAPI 3 (Strategjia në Organin Kompetent):** Linja argumentuese gjatë përballjes procedurale.
"""