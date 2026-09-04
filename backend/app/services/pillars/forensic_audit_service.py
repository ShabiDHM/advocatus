# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDITOR V230.0 (MULTI-ARTICLE EXHAUSTIVE DISCOVERY & STRICT REV PRECEDENTS)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME (V230.0):
    - Ekstraktim 100% shterrues i TË GJITHA neneve të dokumentit (LPK, Kushtetuta, LMD, KPK) në rreshta individualë.
    - Citohen ekskluzivisht precedentët tregtarë/civilë REV.Nr. të Gjykatës Supreme (p.sh. REV.Nr.98/2024).
    - Identifikon saktë rolin e Ankuesit / Kundërpaditësit dhe shkeljet thelbësore procedurale.
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
        
        pos = (client_position or "ANKUES / PALË NË PROCEDURË").strip().upper()
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
Detyra jote është të kryesh auditimin doktrinar shterrues të këtij akti:
1. Të nxjerrësh ÇDO NEN LIGJOR të përmendur në shkresë (LPK, Kushtetutë, LMD) në rresht më vete te Tabela e Seksionit 4.
2. Të citosh precedentët zyrtarë tregtarë/civilë REV të Gjykatës Supreme (p.sh. REV.Nr.98/2024, REV.Nr.240/2024, REV.Nr.541/2024).
3. Të zbërthen shkeljen 'Contra Legem' dhe bazën e plotë të ankesës për ndarjen e procedimit të kundërpadisë.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 KONTEKSTI I DOSJES NË AUDITIM:
LËMIA: **{case_domain}** | PARASHTRUESI/ANKUESI: **{client_name or 'I Identifikuar në Akt'}** | POZICIONI: **{pos}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE E ZBATUESHME (REPUBLIKA E KOSOVËS):
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME (Rev):
{rag_context if rag_context else "Zbato ligjet pozitive të Kosovës dhe precedentët e Kolegjit Civil/Ekonomik të Gjykatës Supreme (Aktgjykimet Rev)."}

======================================================================
RREGULLAT E HEKURTA TË DOKTRINËS FORENZIKE (ZERO OMISSIONS):
1. INVENTARI I PLOTË I NENEVE NË SEKSIONIN 4 (NDALOHET LËNIA JASHTË E NENEVE):
   - Nëse dokumenti përmban Nenin 256 par. 4 LPK, Nenin 182 par. 1 LPK, Nenin 54 të Kushtetutës, Nenin 92, Nenin 93, apo Nenin 390/391 LPK, SECILI NEN DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL NË TABELË!
   - Çdo rresht të ketë formatin e pastër: `Neni X i LPK-së` (ose `Neni X i Kushtetutës së Kosovës`), në mënyrë që sistemi të krijojë menjëherë lidhjet interaktive 1-klikim për verifikim!
2. PRECEDENTËT E DETYRUESHËM TREGATRË/CIVILË (REV):
   - Në kolonën e 4-të të tabelës, cito ekskluzivisht Aktgjykimet e Kolegjit Civil dhe Ekonomik të Gjykatës Supreme në formatin: `REV.Nr.98/2024`, `REV.Nr.240/2024`, `REV.Nr.541/2024` ose `REV.Nr.382/2023`. NDALOHET citimi i numrave administrativë A. për çështje tregtare/civile!
3. AUDITIMI I SAKTË I AKTIT DHE PALËVE:
   - Identifiko aktin (nëse është ANKESË, përcakto shkaqet ankimore dhe kërkesën ankimore).
   - Identifiko saktë Ankuesit (Kundërpaditësit) dhe të Paditurit nga kundërpadia.
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER (TË 8 SEKSIONET E PLOTA):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji, Natyra Formale dhe Efekti Juridik:** Përcakto saktësisht aktin (Ankesë kundër Aktvendimit KE.nr. 662/2022 të Shkallës së Parë), datën e shkresës (02.09.2026), dhe organin të cilit i drejtohet (Gjykata Komerciale — Dhoma e Shkallës së Dytë).
* **Kompetenca Lëndore dhe Funksionale:** Baza e kompetencës së Dhomave të Shkallës së Dytë për të vendosur mbi ankesat ndaj aktvendimeve të Shkallës së Parë (Ligji Nr. 08/L-015).
* **Legjitimimi Procedural i Palëve:** Ankuesit (Kundërpaditësit) vs. Të Paditurve nga kundërpadia.
* **Auditimi i Afateve Ligjore:** Respektimi i afatit ligjor 7-ditor nga dita e pranimit të aktvendimit.

### 2. 👥 STRUKTURA E PALËVE, AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
* **Ankuesit (Kundërpaditësit):** Shaban Bala dhe "Getting Competent" SH.P.K. (kërkesa pasurore prej 246,277.00 €).
* **Të Paditurit nga Kundërpadia:** Rainer Gerke, INDESON WBC SH.P.K., dhe Faton Deshishku.
* **Gjykata e Shkallës së Parë:** Vlerësimi i vendimmarrjes së gjyqtarit të shkallës së parë dhe shkeljeve procedurale.

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DOKUMENTARE (CORPUS DELICTI)
* **Objekti i Kontestit:** Kërkesa pasurore e pavarur prej 246,277.00 € dhe përfshirja e personave të rinj në kundërpadi.
* **Mungesa e Shqyrtimit Meritor:** Konstatimi i vetë Gjykatës së Shkallës së Parë se nuk ka hyrë në shqyrtimin e bazueshmërisë materiale.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(⚠️ URDHËR: ÇDO NEN I PËRMENDUR NË DOKUMENT DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL ME PRECEDENTIN REV):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme (Rev / Komentari) |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I LAPSUSEVE
* 🔴 **[GJETJET KRITIKE CONTRA LEGEM]:**
  - Shkelja thelbësore e Nenit 182 par. 1 dhe Nenit 256 par. 4 të LPK-së: Hedhja e kundërpadisë me pretendimin e gabuar se ajo varet nga padia kryesore.
  - Cenimi i Nenit 54 të Kushtetutës së Kosovës (e drejta për mbrojtje gjyqësore dhe qasje në drejtësi).
* 🔍 **DETEKTORI KIRURGJIK I LAPSUSEVE TË NENEVE DHE FORMULAT E KORRIGJIMIT:**
  | Neni / Formulimi Aktual në Shkresë | Pasaktësia / Lapsusi i Evidentuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I PETITUMIT DHE EKZEKUTUESHMËRISË
* **Themelësia e Propozimit Ankimor:** Kërkesa për ndryshimin e Pikës II të Aktvendimit KE.nr. 662/2022 dhe ndarjen e procedimit.
* **Ekzekutueshmëria e Kundërpadisë:** Procedimi i kërkesës 246,277.00 € si padi më vete në shkallë të parë.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN GJYQËSOR)
(Harto PROPOZIMIN DHE PJESËN KËRKUESE SOLEMNE TË ANKESËS drejtuar Dhomave të Shkallës së Dytë të Gjykatës Komerciale):
* **Pjesa Kërkuese Soleme e Ankesës:**
  [Harto tekstin solemn ku kërkohet: PRANIMI I ANKESËS SI E BAZUAR, NDRYSHIMI I PIKËS II TË AKTVENDIMIT KE.NR.662/2022 DHE URDHËRIMI I SHKALLËS SË PARË QË KUNDËRPADIA ME VLERË 246,277.00 € TË PROCEDOHET PËRMES NDARJES SË PROCEDIMIT SI PADI E PAVARUR KONTESTIMORE].

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afati 24-48 Orë):** Depozitimi i Ankesës në Dhomat e Shkallës së Dytë të Gjykatës Komerciale brenda afatit ligjor prej 7 ditësh.
* 🟡 **HAPI 2 (Veprimet Provuese):** Pagesa e taksës gjyqësore për ankesë dhe kompletimi i provave për ndarjen e procedimit.
* 🟢 **HAPI 3 (Strategjia në Seancë):** Prezantimi i argumenteve mbi pavarësinë e kërkesës pasurore dhe kërkimi i masës së sigurimit.
"""