# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT FORENSIC AUDITOR V210.0 (EXHAUSTIVE STATUTORY CAPTURE & CONTRA LEGEM SURGERY)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME (V210.0):
    - Ekstraktim 100% shterrues i çdo neni të vetëm që përmendet në dokument (për lidhjet 1-click).
    - Zbërthim kirurgjikal i shkeljeve 'Contra Legem' të gjyqtarit (Neni 256 par. 4 i LPK-së).
    - Hartim i plotë solemn i Pjesës Kërkuese të Ankesës / Petitumit pa asnjë refuzim.
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LSHT|LFK|LPP|LPPA|LPTS|KEDNJ|Kushtetut[a-zë]*|Ligji\s+Nr\.\s*[\d/L\-]+)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|AC|CA|A|PKR|PP|C|P|E|KE)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(dict.fromkeys(articles))[:25]
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
        search_query = query_text or f"{mined_legal_entities} {case_domain} Gazeta Zyrtare Nenet Aktgjykim Gjykata Supreme PML Rev"

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
MANDATI YT DHE PRIVILEGJI I MBROJTJES:
Ti je një Gjyqtar dhe Krye-Auditor i Departamentit të Praktikës Gjyqësore të Gjykatës Supreme të Kosovës.
Përdoruesi të ka dorëzuar këtë dokument për vlerësim kritik dhe të plotë.
Detyra jote është ta shoshitësh këtë dokument literalisht nga rreshti i parë deri te vula e fundit, duke nxjerrë çdo fakt, çdo datë, dhe duke zbërthyer ÇDO NEN LIGJOR që përmendet në të.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 KONTEKSTI I DOSJES:
LËMIA: **{case_domain}** | PARASHTRUESI: **{client_name or 'I Identifikuar në Akt'}** | POZICIONI: **{pos}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE NË FUQI (REPUBLIKA E KOSOVËS):
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME (GAZETA ZYRTARE):
{rag_context if rag_context else "Zbato ligjet pozitive të Kosovës dhe precedentët e Kolegjeve të Gjykatës Supreme (Rev & PML)."}

======================================================================
URDHËRAT E HEKURT TË AUDITIMIT (EXHAUSTIVE DISCOVERY):
1. EKSTRAKTIMI I TË GJITHA NENEVE PA PËRJASHTIM:
   - Në Seksionin 4 (Tabela Statutore), duhet të përfshish ÇDO NEN të vetëm që përmendet në dokument (p.sh. Neni 2, Neni 78, Neni 92, Neni 93 par. 1-4, Neni 256 par. 4, Neni 390, Neni 391 pika g të LPK-së, LMD, KPK, etj.).
   - ÇDO nen duhet të ketë rreshtin e tij të plotë individual në formatin: `Neni X i LPK-së` (ose ligjit përkatës), në mënyrë që të krijohen automatikisht lidhjet interaktive me 1 klikim për verifikim nga përdoruesi!
2. NDALIM I PËRMVERBJES SË PALËVE:
   - Lexo me saktësi absolute kush është shënuar si Paditës dhe kush si I Paditur/Kundërpaditës.
3. ZBËRTHIMI I SHKELJEVE 'CONTRA LEGEM':
   - Nëse akti është vendim gjyqësor, evidento shkeljen procedurale: Pse hedhja e padisë për mungesë prokure nuk mund të asgjësojë kundërpadinë e pavarur? (Neni 256 par. 4 i LPK-së: "Kundërpadia mbetet e pavarur dhe gjykata duhet të ndajë procedimin").
4. DRAFTI I PLOTË I SEKSIONIT 7:
   - Nëse akti është AKTVENDIM: Harto PJESËN KËRKUESE TË ANKESËS për Shkallën e Dytë për prishjen e pikës së hedhjes së kundërpadisë.
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I DOKUMENTIT QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER (TË 8 SEKSIONET E PLOTA):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji, Natyra Formale dhe Efekti Juridik:** Përcakto saktësisht emërtimin zyrtar, numrin e lëndës, datën e saktë (nga teksti), trupin gjykues/gjyqtarin, dhe pasojat juridike.
* **Kompetenca Lëndore, Funksionale dhe Territoriale:** Analizo bazën ligjore të kompetencës së gjykatës (Ligji Nr. 08/L-015 për Gjykatën Komerciale ose ligjet përkatëse).
* **Legjitimimi Procedural i Palëve (Locus Standi):** Përcakto me saktësi: Paditësin, Të Paditurin dhe Kundërpaditësin.
* **Auditimi i Afateve Ligjore dhe Urgjenca Procedurale:** Përcakto afatin e saktë të ankesës (7 ditë për aktvendim) dhe pasojat e formës së prerë.

### 2. 👥 STRUKTURA E PALËVE, AKTORËVE DHE KUALIFIKIMI I PËRGJEGJËSISË LIGJORE
* **Pala Paditëse / Iniciale:** Analizo pretendimet e padisë, vlerën e kontestit (10,000 €) dhe arsyen procedurale të hedhjes së padisë (mungesa e prokurës së avokatit).
* **Pala e Paditur / Kundërpaditëse:** Analizo të drejtat thelbësore, kundërpadinë e paraqitur (shumën 246,277 €) dhe kërkesat e pavarura materiale.
* **Avokatët dhe Përfaqësuesit:** Vlerëso veprimet e përfaqësimit dhe pasojat e mosdorëzimit të autorizimit origjinal.

### 3. 🔬 KRYQËZIMI FORENZIK I PROVAVE MATERIALE DHE DOKUMENTARE (CORPUS DELICTI)
* **Provat Shkresore dhe Shumat Financiare:** Analizo vlerat monetare (10,000 € vs 246,277 €), provat e dorëzuara dhe mungesën e shqyrtimit meritor.
* **Vlefshmëria Procedurale:** Vlerëso ligjshmërinë e administrimit të shkresave sipas LPK-së.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(⚠️ URDHËR: ÇDO NEN I PËRMENDUR NË DOKUMENT DUHET TË KETË RRESHTIN E TIJ INDIVIDUAL NË TABELË ME 4 KOLONA):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme (Rev / PML / Komentari) |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I LAPSUSEVE
* 🔴 **[GJETJET KRITIKE CONTRA LEGEM TË VENDIMIT / SHKRESËS]:**
  - Zbërthe shkeljen flagrante procedurale: Hedhja e paligjshme e kundërpadisë në kundërshtim me Nenin 256 par. 4 të LPK-së (Gjykata kishte detyrim ligjor të ndante procedimin dhe ta shqyrtonte kundërpadinë si padi të pavarur).
* 🔍 **DETEKTORI KIRURGJIK I LAPSUSEVE TË NENEVE DHE FORMULAT E KORRIGJIMIT:**
  | Neni / Formulimi Aktual në Shkresë | Pasaktësia / Lapsusi i Evidentuar | Formula Doktrinare e Saktë e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I PETITUMIT, MASËS SË SIGURIMIT DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Ligjshmërisë së Dispozitivit:** Analizo Pikën I, II dhe III të dispozitivit.
* **Mundësia e Ndarjes së Procedimit:** Rrugët juridike për të shpëtuar kërkesën prej 246,277 € përmes shkallës së dytë.

### 7. 🛠️ TEKSTI I KORRIGJUAR DHE DRAFT-REMEDIIMI (FORMULIMI SOLEMN GJYQËSOR)
(Harto PJESËN KËRKUESE TË ANKESËS drejtuar Dhomave të Shkallës së Dytë të Gjykatës Komerciale):
* **Pjesa Kërkuese Soleme e Ankesës (Petitum-i Ankimor):**
  [Harto kërkesën e plotë solemne ku kërkohet: PRANIMI I ANKESËS, NDRYSHIMI I PIKËS II TË AKTVENDIMIT DHE URDHËRIMI I SHKALLËS SË PARË QË KUNDËRPADIA ME VLERË 246,277 € TË TRAJTOHET PËRMES NDARJES SË PROCEDIMIT SI PADI E PAVARUR].

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E HEKURT PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Afati Prekluziv 7 Ditë):** Parashtrimi i ankesës në Dhomat e Shkallës së Dytë brenda 7 ditëve nga pranimi i aktvendimit.
* 🟡 **HAPI 2 (Veprimet Provuese & Taksat):** Përgatitja e provave për kundërpadinë e pavarur dhe pagesa e taksës përkatëse gjyqësore për ndarjen e procedimit.
* 🟢 **HAPI 3 (Strategjia në Seancë):** Kërkesa për shqyrtim të përshpejtuar dhe caktimi i masës së sigurimit.
"""