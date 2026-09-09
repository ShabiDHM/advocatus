# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - FORENSIC DOCUMENT AUTOPSY PROMPT ENGINE V275.0 (STREAM-OPTIMIZED & CLEAN LEGAL PROSE)
# GJUHË E PASTËR JURIDIKE SHQIPE • SAKTËSI DOKTRINARE • ZERO TRUNCATION

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    Shërbim për analizën e dokumenteve ligjore.
    Krijon struktura të qarta për tre shtjella:
    - Shtjella 1: Pasaporta procedurale, palët dhe baza provuese.
    - Shtjella 2: Nenet e zbatueshme dhe shkeljet procedurale.
    - Shtjella 3: Auditimi i kërkesës, diagnoza dhe plani i veprimit.
    """

    @staticmethod
    def extract_legal_entities_from_text(text: str) -> str:
        if not text:
            return ""
        
        articles = re.findall(r'\b(?:Neni|Nenit|Nenin|Nenet)\s*(\d+[a-zA-Z]?)\b', text, re.IGNORECASE)
        laws = re.findall(r'\b(?:KPK|KPRK|KPPRK|LPK|LMD|LSHT|LFK|LPP|LPPA|LPTS|KEDNJ|Kushtetut[a-zë]*|Ligji\s+Nr\.\s*[\d/L\-]+)\b', text, re.IGNORECASE)
        cases = re.findall(r'\b(?:PML|Rev|REV|AC|CA|A|PKR|PP|C|P|E|KE)\.?\s*Nr\.?\s*(\d+/\d+)\b', text, re.IGNORECASE)
        
        unique_articles = list(dict.fromkeys(articles))[:15]
        unique_laws = list(dict.fromkeys(laws))[:6]
        unique_cases = list(dict.fromkeys(cases))[:6]

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
        teksti_shkreses = (document_text or context_str).strip()
        
        # Zbulim dinamik i lëmisë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=teksti_shkreses[:8000],
                manifest_str=manifest_str or ""
            )
        
        pozicioni = (client_position or "PALË NË PROCEDURË").strip().upper()
        entitetet_ligjore = ForensicAuditService.extract_legal_entities_from_text(teksti_shkreses)
        
        lemia_upper = case_domain.upper()
        termat_precedenteve = []
        if "PENAL" in lemia_upper:
            termat_precedenteve.append("Aktgjykimet PML të Kolegjit Penal")
        if any(d in lemia_upper for d in ["CIVIL", "KOMERCIAL", "PRONËSOR", "FAMILJAR", "PUNË"]):
            termat_precedenteve.append("Aktgjykimet Revizion të Kolegjit Civil")
        
        orientimi = " dhe ".join(termat_precedenteve) or "Aktgjykimet PML dhe Revizionet"
        pyetja_kerkimore = query_text or f"{entitetet_ligjore} {case_domain} {orientimi} të Gjykatës Supreme të Kosovës"

        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",
                query_text=pyetja_kerkimore,
                n_results=10
            )
        except Exception as rag_err:
            logger.warning(f"RAG precedent search warning: {rag_err}")

        protokolli_suprem = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)

        query_lower = (query_text or "").lower()

        # =========================================================================
        # STRUKTURAT E MODULARIZUARA PA TEPRICA DHE PA ZHARGON
        # =========================================================================
        if any(term in query_lower for term in ["shtjella 1", "ekzaminimi", "pasaporta"]):
            struktura_seksioneve = f"""
SHTJELLA 1: EKZAMINIMI DHE FAKTET E SHKRESËS (SEKSIONET 1, 2 DHE 3)
Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

### 1. PASAPORTA PROCEDURALE DHE DIAGNOZA E AKTIT
* **Natyra dhe Lloji i Aktit:** Përcakto formën e shkresës (Padi, Ankesë, Aktgjykim, Aktvendim, Procesverbal, Kontratë).
* **Titullari Nxjerrës:** Gjykata, organi administrativ, prokuroria apo eksperti.
* **Numri Identifikues i Lëndës:** Numri i saktë i protokollit apo shenjës gjyqësore.
* **Auditimi i Afateve:** Vlerësimi nëse akti është nxjerrë apo goditur brenda afatit ligjor prekluziv.

### 2. STRUKTURA E PALËVE DHE LEGJITIMITETI
* **Parashtruesi i Aktit:** Legjitimiteti aktiv dhe cilësia procedurale.
* **Pala Kundërshtare:** Legjitimiteti pasiv dhe fusha e efektit juridik.
* **Interesi Juridik:** Të drejtat që mbrohen apo rrezikohen nga ky akt.

### 3. KRYQËZIMI I FAKTEVE DHE BAZA PROVUESE
* **Pretendimet Kryesore:** Përmbledhje e fakteve që pretendohen në shkresë.
* **Provat e Administruara:** Provat shkresore, materiale apo ekspertizat që citohen.
* **Zbrazëtirat Provuese:** Provat thelbësore që mungojnë apo janë shpërfillur padrejtësisht.
"""
        elif any(term in query_lower for term in ["shtjella 2", "nenet", "shkeljet"]):
            struktura_seksioneve = f"""
SHTJELLA 2: NENET DHE SHKELJET PROCEDURALE (SEKSIONET 4 DHE 5)
Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

### 4. TABELA E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
Nxirr të gjitha nenet e legjislacionit pozitiv të Kosovës që lidhen drejtpërdrejt me këtë shkresë:
| Neni dhe Ligji i Kosovës | Instituti Juridik | Shkelja apo Zbatimi i Gabuar | Precedenti i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. GJETJET KRITIKE DHE SHKELJET THELBËSORE
* **Shkeljet Thelbësore të Procedurës:** Analizo shkeljet sipas Nenit 182 të LPK-së apo Kodit të Procedurës Penale (mungesa e arsyetimit, kundërthëniet, moskompetenca).
* **Tabela e Pasaktësive dhe Gabimeve Materiale në Shkresë:**
| Formulimi i Pasaktë në Shkresë | Natyra e Gabimit / Shkeljes | Formulimi i Saktë Ligjor |
| :--- | :--- | :--- |
"""
        elif any(term in query_lower for term in ["shtjella 3", "plani", "kundërshtimet"]):
            struktura_seksioneve = f"""
SHTJELLA 3: KUNDËRSHTIMET, DIAGNOZA DHE PLANI I VEPRIMIT (SEKSIONET 6, 7 DHE 8)
Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

### 6. AUDITIMI I KËRKESËS DHE FORCA EKZEKUTIVE
* **Qartësia dhe Përmbajtja e Dispozitivit:** Vlerësimi i zbatueshmërisë praktike të kërkesës.
* **Rreziqet Procedurale:** Pikat që rrezikojnë rrëzimin e aktit në shkallët më të larta të gjykimit.

### 7. DIAGNOZA KORRIGJUESE DHE REKOMANDIMET
* **Vlerësimi i Qëndrueshmërisë:** Pikat e forta dhe dobësitë e kësaj shkrese.
* **Këshilla Taktike e Goditjes:** Si të neutralizohen efektet negative përmes mjeteve ligjore (Ankesë, Prapësim, Padi për Anulim, Masë Sigurimi).

### 8. MASTER PLANI I VEPRIMIT DHE AFATET LIGJORE
* **Hapi 1 (Veprimi Emergjent):** Çfarë duhet dorëzuar brenda afatit ligjor më të afërt.
* **Hapi 2 (Plotësimi Provues):** Sigurimi i provave shtesë dhe ekspertizave.
* **Konkluzioni Përfundimtar:** Vlerësimi përmbyllës i forcës ligjore të aktit për klientin {client_name}.
"""
        else:
            struktura_seksioneve = f"""
AUTOPSIA PROCEDURALE E SHKRESËS
Lënda: {case_title} | Klienti: {client_name} ({pozicioni}) | Data: {current_date_str}

Trajto në mënyrë të qartë pasaportën procedurale, bazën ligjore dhe rekomandimet konkrete për veprim.
"""

        return f"""[DIREKTIVË PËR ANALIZË TË DOKUMENTIT LIGJOR]
Ju jeni një ekspert ligjor i specializuar në legjislacionin e Republikës së Kosovës.
RREGULLAT E PËRGJIGJES:
1. Përdorni gjuhë standarde juridike shqipe.
2. Bazo arsyetimin ekskluzivisht në tekstin e shkresës që auditohet.
3. Përgjigju në mënyrë të qartë dhe pa përsëritje të panevojshme, duke plotësuar të gjitha pikat e strukturës së kërkuar.

{protokolli_suprem}

{mbrojtja_rolit}

TË DHËNAT E SHKRESËS NË AUDITIM:
- Lënda: {case_title}
- Klienti: {client_name or 'I papërcaktuar'}
- Pozicioni: {pozicioni}
- Lëmia: {case_domain}
- Data e Auditimit: {current_date_str}

{toni_rolit}

PRECEDENTËT SUPREMË RELEVANTË:
{baza_globale if baza_globale else 'Zbato dispozitat pozitive të legjislacionit të Kosovës.'}

{'='*50}
TEKSTI I SHKRESËS QË AUDITOHET:
{'='*50}
{teksti_shkreses[:25000]}
{'='*50}

STRUKTURA E DETYRUESHME:
{struktura_seksioneve}"""