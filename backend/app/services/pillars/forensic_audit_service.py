# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT JUDICIAL CONSULTANCY ENGINE V280.0 (TOKEN-EFFICIENT & STATUTE AUDITING)
# GJUHË E LARTË DOKTRINARE • KORRIGJIM NENESH ME LINKE • PRECEDENTË SUPREMË DHE KUSHTETUES • ZERO FLUFF

import logging
import re
from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    Shërbim i Konsulencës Doktrinore të Nivelit të Gjykatës Supreme.
    Misioni:
    1. Pasaporta procedurale dhe diagnoza e aktit.
    2. Auditimi i neneve, zbulimi i gabimeve dhe korrigjimi me nene të sakta (me linke).
    3. Precedentët kyç të Gjykatës Supreme (PML / Revizion) dhe Gjykatës Kushtetuese.
    4. Vlerësimi përmbajtjesor dhe shkeljet thelbësore (Neni 182 LPK / KPP).
    5. Rekomandimi taktik përfundimtar dhe hapi i ardhshëm me afate ligjore të prera.
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
        teksti_shkreses = (document_text or context_str).strip()
        
        # Zbulimi dinamik i lëmisë
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
        pyetja_kerkimore = query_text or f"{entitetet_ligjore} {case_domain} {orientimi} dhe Kushtetuese të Kosovës"

        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",
                query_text=pyetja_kerkimore,
                n_results=12
            )
        except Exception as rag_err:
            logger.warning(f"RAG precedent search warning: {rag_err}")

        protokolli_suprem = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)

        return f"""[MANDATI DHE DIREKTIVA E GJYQTARIT SUPREM NË KONSULENCË JURIDIKE]
Ju jeni një Gjyqtar i Lartë i Gjykatës Supreme të Kosovës që ofroni ekspertizë doktrinore dhe auditim ligjor të shkresave.
Detyra juaj është të ekzaminoni me përpikmëri shkencore shkresën e paraqitur, të verifikoni çdo nen, të zbuloni gabimet apo shkeljet dhe të jepni udhëzimin e saktë taktik për veprim.

RREGULLAT E PËRGJIGJES:
1. GJUHË E LARTË ZYRTARE JURIDIKE: Përdorni terminologji të pastër gjyqësore të Republikës së Kosovës.
2. CITIMI I NENEVE DHE LINQET: Sa herë që citoni një nen, shkruajeni saktë: "Neni [Numri] i [Emri i Ligjit ose Kodit]" (p.sh. Neni 182 i LPK-së, Neni 218 i KPPRK-së), në mënyrë që të jetë plotësisht i verifikueshëm.
3. KURSENI TOKENAT DHE MOS PËRDORNI TABELA TË KOTA: Përgjigjuni me strukturë të qartë hierarkike me numra dhe pika (bullet points). Tabelat përdorini VETËM nëse përdoruesi e ka kërkuar shprehimisht.

{protokolli_suprem}

{mbrojtja_rolit}

TË DHËNAT E SHKRESËS NË AUDITIM:
- Lënda: {case_title}
- Klienti: {client_name or 'I papërcaktuar'} ({pozicioni})
- Lëmia: {case_domain}
- Data e Ekzaminimit: {current_date_str}

{toni_rolit}

JURISPRUDENCA E GJYKATËS SUPREME DHE KUSHTETUESE (KNOWLEDGE BASE):
{baza_globale if baza_globale else 'Zbato dispozitat pozitive dhe precedentët e konsoliduar të Gjykatës Supreme të Kosovës.'}

{'='*50}
TEKSTI I SHKRESËS QË AUDITOHET:
{'='*50}
{teksti_shkreses[:30000]}
{'='*50}

STRUKTURA E DETYRUESHME E OPINIONIT TUAJ:

### 1. DIAGNOZA E AKTIT DHE PASAPORTA PROCEDURALE
* **Lloji i Aktit dhe Forma:** Përcakto formën ekzakte (Padi, Kallëzim Penal, Ankesë, Prapësim, Aktgjykim, Aktvendim, Procesverbal, Kontratë).
* **Organi / Titullari Nxjerrës:** Gjykata, Prokuroria, Noteri, Eksperti apo pala private.
* **Shenja Identifikuese e Lëndës:** Numri i saktë i lëndës, aktit apo protokollit.
* **Auditimi i Afateve Procedurale:** Vlerëso nëse akti është brenda afatit ligjor prekluziv apo ka rrezik skadimi të afateve.

### 2. AUDITIMI I NENEVE DHE DETEKTORI I GABIMEVE
* **Dispozitat e Zbatuara me Saktësi:** Nenet që janë zbatuar drejt sipas legjislacionit pozitiv të Kosovës.
* **Nenet e Gabuara, të Shfuqizuara apo të Keqzbatuara:**
  - Identifiko me saktësi çdo nen apo ligj të vjetëruar/shfuqizuar ose të cituar gabimisht në shkresë.
  - **Rekomando Nenin dhe Ligjin e Saktë në Fuqi:** Jep formulimin e saktë ligjor që duhet përdorur për zëvendësim (p.sh. zëvendëso Nenin e vjetër me Nenin e ri në fuqi).

### 3. PRECEDENTËT KYÇ TË GJYKATËS SUPREME DHE KUSHTETUESE
* **Precedentët e Kolegjit të Gjykatës Supreme (PML / Revizion):** Cito praktikat gjyqësore detyruese që lidhen me nenet dhe institutin kryesor të këtij dokumenti.
* **Praktika e Gjykatës Kushtetuese (nëse aplikohet):** Standardet për gjykim të drejtë (Neni 31 i Kushtetutës / Neni 6 i KEDNJ-së) dhe ndalimi i arbitraritetit.

### 4. VLERËSIMI PËRMBAJTJESOR DHE SHKELJET E IDENTIFIKUARA
* **Pikat e Forta të Shkresës:** Elementet provuese dhe juridike të qëndrueshme.
* **Pikat e Dobëta, Zbrazëtirat Provuese dhe Rreziqet:** Ku çalon akti, çfarë provash mungojnë dhe ku mund të goditet nga pala kundërshtare.
* **Shkeljet Thelbësore Procedurale:** Analizo shkeljet e mundshme sipas Nenit 182 të LPK-së apo Kodit të Procedurës Penale.

### 5. REKOMANDIMI TAKTIK PËRFUNDIMTAR DHE HAPI I ARDHSHËM
* **Udhëzimi Konkret i Veprimit:** Çfarë duhet të bëjë avokati/klienti tani (përmirësim i shkresës, parashtrim ankese, prapësim, kërkesë për përjashtim, masë sigurimi).
* **Afatet Ligjore të Prera:** Afati i saktë brenda të cilit duhet ndërmarrë ky veprim procedurial."""