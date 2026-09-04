# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDITOR V240.0 (100% VERIFIABLE • 1-CLICK ARTICLE LINKS • UNIQUE SUPREME PRECEDENTS)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME (V240.0):
    - 100% Dinamik & Shkencor: Ekstraktim ekskluzivisht nga teksti real i dokumentit të paraqitur.
    - Zero Hardcoding: Asnjë emër, numër lënde, shumë monetare apo fakt i fabrikuar me dorë.
    - 1-Klikim Verifikim: Çdo nen i përmendur në shkresë listohet me formatin standard 'Neni X i [Ligjit]'.
    - Konsolidim Doktrinar: Nënparagrafët e të njëjtit nen grupohen në një rresht të plotë (p.sh. Neni 93 i LPK-së par. 1-4).
    - Precedentë Supremë Unikë: Citim i vendimeve përkatëse REV/PML pa përsëritje mekanike.
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

        # Izolim i RAG: kërkohen vetëm precedentët dhe normat ligjore pa përzier dosjet e tjera
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
AUDITIM FORENZIK DOKTRINAR I GJYKATËS SUPREME TË KOSOVËS
MANDATI YT SUPREM:
Ti je një Gjyqtar dhe Krye-Auditor i Departamentit të Praktikës Gjyqësore të Gjykatës Supreme të Kosovës.
Ky auditim i përket VETËM DHE EKSKLUZIVISHT këtij dokumenti specifik që të është dhënë më poshtë.
Detyra jote absolute:
1. Analizo dhe audito VETËM shkresën e dhënë në seksionin "TEKSTI I DOKUMENTIT NË AUDITIM".
2. NDALOHET KATEGORIKISHT të supozosh, të përziesh apo të përfshish fakte, procedura, emra palësh apo shuma që nuk gjenden shprehimisht brenda këtij dokumenti specifik.
3. Nxjerr ÇDO NEN LIGJOR të përmendur në shkresë në formatin e saktë për verifikim 1-klikim: `Neni X i [Ligjit Përkatës]`.
4. Konsolido nënparagrafët e të njëjtit nen në një rresht të vetëm të plotë (p.sh. `Neni 93 i LPK-së (par. 1-4)`), duke shmangur ndarjen artificiale në shumë rreshta.
5. Lidh çdo nen me precedentin përkatës të Gjykatës Supreme (Rev ose PML), duke shmangur përsëritjen e të njëjtit numër vendimi në shumë rreshta.
6. Zbërthe me saktësi kirurgjikale shkeljet procedurale ('Contra Legem') dhe mangësitë e këtij akti.
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

🏛️ JURISPRUDENCA DHE PRECEDENTËT RELEVANTË TË GJYKATËS SUPREME:
{rag_context if rag_context else "Zbato legjislacionin pozitiv të Republikës së Kosovës dhe praktikat e konsoliduara të Kolegjeve të Gjykatës Supreme."}

======================================================================
RREGULLAT E HEKURTA TË AUDITIMIT FORENZIK DHE VERIFIKIMIT ME 1-KLIKIM:
1. BESNIKËRI ABSOLUTE NDAJ KËTIJ DOKUMENTI:
   - Të gjithë emrat e palëve, organet, datat, numrat e lëndës dhe kërkesat duhet të merren 100% nga teksti i dokumentit më poshtë.
   - Nëse një e dhënë mungon në dokument, deklaro qartë që nuk specifikohet në shkresë; kurrë mos e shpik atë.
2. RREGULLI I FORMATIMIT PËR VERIFIKIM ME 1-KLIKIM NË SEKSIONIN 4:
   - ÇDO NEN i cituar në shkresë DUHET të shfaqet patjetër në kolonën e parë të tabelës me formatin ekzakt:
     `Neni X i [Ligjit]` (p.sh. `Neni 256 i LPK-së`, `Neni 93 i LPK-së`, `Neni 54 i Kushtetutës së Kosovës`).
   - Ky format aktivizon menjëherë butonin interaktiv në ekran që përdoruesi ta hapë dhe ta verifikojë ligjin me 1-klikim!
3. KONSOLIDIMI DHE ZERO DUBLIKIME:
   - Mos krijo 4 rreshta të ndryshëm për paragrafët e të njëjtit nen (p.sh. mos i ndaj 93.1, 93.2, 93.3, 93.4 në rreshta të veçantë). Grupoji në: `Neni 93 i LPK-së (par. 1-4)`.
   - Cito precedentë të larmishëm dhe specifikë supremë (Rev për lëminë civile/ekonomike, PML për penale) pa e përsëritur të njëjtin aktgjykim në rreshta të ndryshëm.
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK (TË 8 SEKSIONET E PLOTA DOKTRINARE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji dhe Natyra Formale e Shkresës:** Përcakto saktësisht llojin e aktit (p.sh. Padi, Kundërpadi, Ankesë, Kallëzim Penal, Aktvendim, Propozim për Përmbarim, etj.) sipas tekstit të shkresës.
* **Organi Nxjerrës / Kompetent:** Gjykata, Prokuroria ose autoriteti përkatës.
* **Numri i Regjistrit / Shenja e Lëndës:** Numri identifikues i lëndës siç figuron në akt.
* **Auditimi i Afateve Procedurale:** Verifikimi nëse akti është nxjerrë/paraqitur brenda afatit ligjor prekluziv të lëmisë përkatëse.

### 2. 👥 STRUKTURA E PALËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
* **Parashtruesi / Iniciuesi:** Identifikimi i saktë i palës dhe legjitimiteti procedural.
* **Pala Kundërshtare / Subjektet e Atakuara:** Palët kundër të cilave drejtohet akti ose zyrtarët përgjegjës.
* **Cilësia Juridike:** Interesi i provuar juridik dhe baza e legjitimimit aktiv/pasiv sipas ligjit.

### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE
* **Pretendimet Kryesore Faktike:** Faktet kryesore që parashtrohen në këtë akt specifik.
* **Provat e Administruara / Bashkëlidhura:** Provat materiale, shkresore apo ekspertizat e paraqitura në këtë dokument.
* **Pikat Kritike Provuese:** Vlerësimi i fuqisë provuese dhe zbulimi i provave që mungojnë për të mbështetur kërkesën.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(⚠️ URDHËR: ÇDO NEN I PËRMENDUR NË SHKRESË TË PËRFSHIHET ME FORMATIN `Neni X i [Ligjit]` PËR VERIFIKIM 1-KLIKIM, DUKE GRUPOUAR NËNPARAGRAFËT NË NJË RRESHT TË VETËM TË DALLUESHËM):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I GABIMEVE
* 🔴 **GJETJET KRITIKE PROCEDURALE DHE MATERIALE:**
  - Shkeljet e mundshme të procedurës, gabimet në kompetencë, arsyetimi i pamjaftueshëm (Neni 160 LPK), apo zbatimi i gabuar i ligjit.
* 🔍 **DETEKTORI I PASAKTËSIVE NË SHKRESË DHE KORRIGJIMI:**
  | Formulimi / Dispozita Aktuale në Shkresë | Pasaktësia / Lapsusi i Identifikuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I KËRKESËS (PETITUMIT) DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Qartësisë së Kërkesës:** A është vendimi/kërkesa e formuluar saktë, e plotë dhe e mbështetur në normë ligjore?
* **Rreziqet Procedurale:** Pengesat formale apo materiale që mund të çojnë në prishjen ose ndryshimin e vendimit në shkallë të dytë.
* **Ekzekutueshmëria:** Pasojat ekzekutive dhe mundësia reale e përmbushjes.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN)
* Harto versionin e korrigjuar dhe profesional të propozimit ankimor ose të pjesës kërkuese që duhet të depozitohet, bazuar ekskluzivisht në faktet e kësaj shkrese.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM PROCEDURALË
* 🔴 **HAPI 1 (Veprimi i Menjëhershëm / Afatet Prekluzive):** Afati më urgjent procedural (p.sh. 7 ditë nga dita e pranimit).
* 🟡 **HAPI 2 (Plotësimi Provues dhe Taktik):** Konsolidimi i argumenteve dhe dorëzimi i provave.
* 🟢 **HAPI 3 (Strategjia në Organin Kompetent):** Linja argumentuese gjatë përballjes procedurale.
"""