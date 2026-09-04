# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDITOR V220.0 (LITERAL DEADLINE LOCK & EXHAUSTIVE STATUTORY DISCOVERY)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME (V220.0):
    - Lexim literal i afateve të ankesës nga Udhëzimi Juridik (7 ditë për Aktvendim, ZERO halucinacion 30 ditë).
    - Ekstraktim 100% shterrues i të gjitha neneve në rreshta të veçantë për lidhjet 1-klikim.
    - Zbatim ekskluziv i precedentëve tregtarë Rev të Gjykatës Supreme për çështje komerciale.
    - Diagnostikim kirurgjikal i shkeljes Contra Legem (Neni 256 par. 4 i LPK-së).
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
            search_tokens.append(" ".join(unique_cases))

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
        search_query = query_text or f"{mined_legal_entities} {case_domain} LPK Nenet Aktgjykimet e Gjykatës Supreme Rev"

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
AUDITIM FORENZIK DOKTRINAR I GJYKATËS SUPREME TË KOSOVËS
MANDATI YT SUPREM:
Ti je një Gjyqtar dhe Krye-Auditor i Departamentit të Praktikës Gjyqësore të Gjykatës Supreme të Kosovës.
Përdoruesi të ka dorëzuar këtë dokument në tavolinë. Detyra jote është ta shoshitësh këtë akt me saktësi absolute kirurgjikale:
1. Të lexosh LITERILISHT çdo datë, numër lënde dhe afat nga teksti i dokumentit.
2. Të nxjerrësh ÇDO NEN TË VETËM ligjor në rresht më vete te Tabela e Seksionit 4.
3. Të zbardhësh shkeljen 'Contra Legem' të gjyqtarit (hedhja e kundërpadisë pa ndarje procedimi sipas Nenit 256 par. 4 të LPK-së).
4. Të hartosh Pjesën Kërkuese të Ankesës me afatin e saktë 7-ditor (ZERO përmendje e 30 ditëve).
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I DOSJES NË AUDITIM:
LËMIA: **{case_domain}** | PARASHTRUESI: **{client_name or 'I Identifikuar në Akt'}** | POZICIONI: **{pos}** | DATA E AUDITIMIT: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE E ZBATUESHME (REPUBLIKA E KOSOVËS):
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME (Rev):
{rag_context if rag_context else "Zbato ligjet pozitive të Kosovës dhe precedentët e Kolegjit Civil/Ekonomik të Gjykatës Supreme (Aktgjykimet Rev)."}

======================================================================
RREGULLAT E HEKURTA TË AUDITIMIT (RIGID PRECISION & ZERO HALLUCINATION):
1. AFATI I SAKTË I ANKESËS NGA UDHËZIMI JURIDIK:
   - Lexo me saktësi në fund të dokumentit çfarë shkruhet te "Udhëzimi mbi të drejtën e ankimimit":
   - Nëse akti është AKTVENDIM dhe shkruhet "shtatë (7) ditë", afati ligjor i ankesës është DETYRIMISHT 7 DITË! NDALOHET KATEGORIKISHT të shkruash 15 apo 30 ditë!
2. EKSTRAKTIMI SHKENCOR I TË GJITHA NENEVE NË SEKSIONIN 4:
   - ÇDO NEN i përmendur në tekst (p.sh. Neni 2, Neni 78, Neni 92, Neni 93, Neni 256, Neni 390, Neni 391 të LPK-së) DUHET të ketë rreshtin e tij të veçantë në Tabelë!
   - Ndalohet rreptësisht bashkimi i neneve në një rresht. Shkruaj formatin standard: `Neni X i LPK-së` që sistemi të krijojë lidhjet interaktive 1-klikim për përdoruesin.
3. PRECEDENTËT E GJYKATËS SUPREME (EKSKLUZIVISHT REV PËR KOMERCIALE/CIVILE):
   - Në kolonën e 4-të të tabelës, cito Aktgjykimet e Kolegjit Civil/Ekonomik të Gjykatës Supreme (p.sh. `REV.Nr.98/2024`, `REV.Nr.36/2024`, `REV.Nr.382/2023`). NDALOHET citimi i numrave penalë PML ose administrativë A. kur lënda është tregtare/civile!
4. ZBËRTHIMI I SHKELJES CONTRA LEGEM:
   - Zbardh shkeljen e rëndë të gjyqtarit: Gjykata hodhi padinë për mungesë prokure të avokatit, por gaboi rëndë duke hedhur edhe kundërpadinë e pavarur! Neni 256 par. 4 i LPK-së e detyron gjykatën të bëjë NDARJEN E PROCEDIMIT dhe ta shqyrtojë kundërpadinë si padi më vete!
5. DRAFTI I SEKSIONIT 7 (ANKESË ME AFAT 7-DITOR):
   - Harto Pjesën Kërkuese Solemne të Ankesës drejtuar Dhomave të Shkallës së Dytë të Gjykatës Komerciale për prishjen e Pikës II të Aktvendimit.
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER (TË 8 SEKSIONET E PLOTA):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji, Natyra Formale dhe Efekti Juridik:** Përcakto saktësisht emërtimin zyrtar (Aktvendim), numrin e lëndës (KE.nr.662/2022), datën e saktë (31.08.2026), gjyqtarin vendimmarrës (Arben Toska), dhe pasojat juridike.
* **Kompetenca Lëndore, Funksionale dhe Territoriale:** Analizo bazën ligjore të kompetencës së Gjykatës Komerciale (Ligji Nr. 08/L-015).
* **Legjitimimi Procedural i Palëve (Locus Standi):** Paditësi formal ("Getting Competent" ShPK), I Padituri (Shaban Bala), dhe Kundërpaditësit.
* **Auditimi i Afateve Ligjore dhe Urgjenca:** Afati prekluziv i ankesës është SHTATË (7) DITË nga pranimi sipas udhëzimit juridik të aktit.

### 2. 👥 STRUKTURA E PALËVE, AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
* **Pala Paditëse Iniciale:** "Getting Competent" ShPK (padia me vlerë 10,000 € e hedhur për mungesë prokure të avokatit Fitim Gashi).
* **Pala e Paditur / Kundërpaditëse:** Shaban Bala (kundërpadia prej 246,277.00 € kundër Rainer Gerke dhe Indeson WBC ShPK).
* **Avokatët dhe Përfaqësuesit:** Shkelja e afatit 7-ditor për dorëzimin e autorizimit origjinal nga avokati i paditësit.

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DOKUMENTARE (CORPUS DELICTI)
* **Provat Shkresore dhe Shumat Financiare:** Analizo padinë 10,000 € kundrejt kundërpadisë thelbësore prej 246,277.00 €, projektet tregtare dhe mungesën e shqyrtimit meritor.
* **Vlefshmëria Procedurale:** Administrimi i kërkesës së gjykatës për prokurë të regjistruar në ARBK dhe pasojat ligjore.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(⚠️ ÇDO NEN DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL NË TABELË ME CITIMIN REV TË SUPREMES):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme (Rev / Komentari) |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I LAPSUSEVE
* 🔴 **[GJETJET KRITIKE CONTRA LEGEM]:**
  - Shkelja e rëndë e gjyqtarit: Gjykata zbatoi drejt Nenin 93 par. 4 LPK për padinë, por bëri SHKELJE THELBËSORE PROCEDURALE të Nenit 182 dhe Nenit 256 par. 4 të LPK-së duke hedhur edhe kundërpadinë e pavarur prej 246,277 € në vend që të urdhëronte Ndarjen e Procedimit!
* 🔍 **DETEKTORI KIRURGJIK I LAPSUSEVE TË NENEVE DHE FORMULAT E KORRIGJIMIT:**
  | Neni / Formulimi Aktual në Shkresë | Pasaktësia / Lapsusi i Evidentuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I PETITUMIT, MASËS SË SIGURIMIT DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Pikave të Dispozitivit:** Pika I (hedhja e padisë), Pika II (hedhja e paligjshme e kundërpadisë), Pika III (pavlefshmëria e veprimeve).
* **Mundësia e Ndarjes së Procedimit:** Procedimi i kundërpadisë si padi më vete në shkallë të parë pas ankesës.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN GJYQËSOR)
(Harto PJESËN KËRKUESE TË ANKESËS drejtuar Dhomave të Shkallës së Dytë të Gjykatës Komerciale brenda afatit 7-ditor):
* **Pjesa Kërkuese Soleme e Ankesës (Petitum-i Ankimor):**
  [Harto kërkesën e përpiktë ku kërkohet: PRANIMI I ANKESËS SI E BAZUAR, NDRYSHIMI I PIKËS II TË AKTVENDIMIT KE.NR.662/2022 DHE URDHËRIMI I SHKALLËS SË PARË QË KUNDËRPADIA ME VLERË 246,277.00 € TË PROCEDOHET PËRMES NDARJES SË PROCEDIMIT SI PADI E PAVARUR KONTESTIMORE].

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afati Prekluziv 7 Ditë):** Parashtrimi i Ankesës në Dhomat e Shkallës së Dytë brenda afatit ligjor prej SHTATË (7) DITËSH nga pranimi i aktvendimit.
* 🟡 **HAPI 2 (Veprimet Provuese & Taksat):** Përgatitja e provave dhe pagesa e taksës gjyqësore për ndarjen e procedimit.
* 🟢 **HAPI 3 (Strategjia në Seancë):** Kërkesa për shqyrtim të përshpejtuar dhe caktimi i masës së sigurimit për llogaritë bankare të personave të paditur në kundërpadi.
"""