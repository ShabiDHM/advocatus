# FILE: backend/app/services/pillars/forensic_audit_service.py
# PROTOKOLLI PHOENIX - KRYE-AUDITORI SUPREM I AUTOPSISË SË DOKUMENTIT V273.0 (BALANCED HIGH-DENSITY PILLAR 3)
# GJUHË E PAZTËR JURIDIKE SHQIPE • ZERO TRUNCATION ACROSS ALL 3 PILLARS • SAKTËSI DOKTRINARE 100%

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME PËR NJË SHKRESË TË VETME (V273.0):
    - 100% I Balancuar në të 3 Shtjellat: Zero ndërprerje edhe për shkresa voluminoze 30+ faqesh.
    - Shtjella 1: Pasaporta, Palët dhe Baza Provuese (Seksionet 1, 2 dhe 3 të plota).
    - Shtjella 2: Nenet dhe Detektori i Lapsuseve (Seksionet 4 dhe 5 të plota).
    - Shtjella 3: Auditimi, Diagnoza dhe Master Plani (Seksionet 6, 7 dhe 8 të plota).
    - Saktësi Absolute: Formatim neni-për-nen dhe precedentë supremë PML/Revizion.
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
        teksti_shkreses = (document_text or context_str).strip()
        
        # Zbulim dinamik i lëmisë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=teksti_shkreses[:15000],
                manifest_str=manifest_str or ""
            )
        
        pozicioni = (client_position or "PALË NË PROCEDURË").strip().upper()
        entitetet_ligjore = ForensicAuditService.extract_legal_entities_from_text(teksti_shkreses)
        
        lemia_upper = case_domain.upper()
        termat_precedenteve = []
        if "PENAL" in lemia_upper:
            termat_precedenteve.append("Aktgjykimet PML të Kolegjit Penal")
        if any(d in lemia_upper for d in ["CIVIL", "KOMERCIAL", "PRONËSOR", "FAMILJAR", "PUNË"]):
            termat_precedenteve.append("Aktgjykimet Revizion të Kolegjit Civil dhe Komercial")
        
        orientimi_precedenteve = " dhe ".join(termat_precedenteve) or "Aktgjykimet PML dhe Revizionet"
        pyetja_kerkimore = query_text or f"{entitetet_ligjore} {case_domain} Nenet {orientimi_precedenteve} të Gjykatës Supreme"

        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",
                query_text=pyetja_kerkimore,
                n_results=25
            )
        except Exception as rag_err:
            logger.warning(f"Kërkimi i precedentëve: {rag_err}")

        protokolli_suprem = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)
        lista_ligjeve = "\n".join([f"- {ligji}" for ligji in BasePillarService.get_domain_laws(case_domain)])

        # =========================================================================
        # 🎯 PËRCAKTIMI MODULAR ME DENSITET TË BALANCUAR NË TË 3 SHTJELLAT
        # =========================================================================
        query_lower = (query_text or "").lower()

        if "shtjella 1" in query_lower or "ekzaminimi" in query_lower or "pasaporta" in query_lower:
            struktura_seksioneve = """
STRUKTURA E DETYRUESHME E SHTJELLËS 1 (GJENERO VETËM SEKSIONET 1, 2 DHE 3):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji dhe Natyra Formale e Shkresës:** (Padi, Ankesë, Aktvendim, Aktgjykim, Raport Ekspertize, Procesverbal, Kontratë, etj.).
* **Organi Nxjerrës / Titullari Procedural:** Gjykata, prokuroria, eksperti, apo autoriteti përgjegjës.
* **Numri Identifikues i Regjistrit / Shenja e Lëndës:** Numri i saktë i protokollit apo shkresës.
* **Auditimi i Afateve dhe Prekluziviteti:** A është paraqitur brenda afatit ligjor? Sa është afati i saktë për ta atakuar?

### 2. 👥 STRUKTURA E PALËVE DHE LEGJITIMITETI PROCEDURAL
* **Parashtruesi / Autori i Aktit:** Legjitimiteti aktiv dhe cilësia procedurale.
* **Pala Kundërshtare / Subjekti i Atakuar:** Legjitimiteti pasiv dhe fusha e efektit juridik.
* **Interesi Juridik i Mbrojtur:** Të drejtat që kërkohen apo cenohen në këtë akt.

### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE TË SHKRESËS
* **Faktet Kryesore të Rindërtuara:** Çfarë pretendon apo konstaton ekzaktësisht kjo shkresë.
* **Provat e Administruara në Akt:** Cilat prova materiale, shkencore apo dëshmi përmenden.
* **Boshllëqet Provuese dhe Cenueshmëria:** Çfarë provash thelbësore janë shpërfillur apo mungojnë.

Përfundo plotësisht këtë Shtjellë 1 deri te fjala e fundit e Seksionit 3!
"""
        elif "shtjella 2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower:
            struktura_seksioneve = """
STRUKTURA E DETYRUESHME E SHTJELLËS 2 (GJENERO VETËM SEKSIONET 4 DHE 5):

RREGULL I HEKURT I DENSITETIT: Në qelitë e tabelave ji i saktë, i prerë dhe i ngjeshur (2–3 fjali për qeli). Kjo garanton që Seksioni 5 të shkruhet i plotë deri në fund!

### 4. ⚖️ TABELA SHTERUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(Përzgjidh 6–8 nenet më thelbësore me formatin e plotë `Neni X i [Emri i Ligjit]` dhe precedentin përkatës Revizion ose PML):
| Dispozita dhe Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare dhe Shkelja | 🏛️ Precedenti i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET NË KUNDËRSHTIM ME LIGJIN DHE DETEKTORI I GABIMEVE
* 🔴 **Shkeljet Thelbësore të Konstatuara:** (Moskompetencë lëndore, shkelje procedurale, tejkalim i kërkesëpadisë, kontradiktë mes arsyetimit dhe dispozitivit sipas Nenit 182 LPK / KPK).
* 🔍 **Detektori i Pasaktësive dhe Lapsuseve në Shkresë (Top 3–5 lapsuset):**
  | Formulimi Aktual në Shkresë | Pasaktësia apo Lapsusi Doktrinar i Identifikuar | Formula e Saktë Ligjore e Zëvendësimit |
  | :--- | :--- | :--- |

Përfundo plotësisht këtë Shtjellë 2 deri te fjala e fundit e Seksionit 5 pa u ndërprerë kurrë!
"""
        elif "shtjella 3" in query_lower or "plani" in query_lower or "kundërshtimet" in query_lower:
            struktura_seksioneve = """
STRUKTURA E DETYRUESHME E SHTJELLËS 3 (GJENERO VETËM SEKSIONET 6, 7 DHE 8):

RREGULL I DENSITETIT: Ji i saktë, i prerë dhe kirurgjikal në formulim në mënyrë që Master Plani i Seksionit 8 të përfundojë 100% i plotë!

### 6. 🔬 AUDITIMI I KËRKESËS DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Qartësisë së Kërkesës apo Dispozitivit:** A është kërkesa e saktë, e ekzekutueshme dhe e mbështetur në normë?
* **Rreziqet Procedurale:** Pengesat që çojnë në rrëzimin, hedhjen apo prishjen e aktit në instancat më të larta ankimore.
* **Forca Ekzekutive:** A përbën titull ekzekutiv dhe si mund të pezullohet apo kundërshtohet.

### 7. 💡 DIAGNOZA KORRIGJUESE DHE REKOMANDIMET E DREJTPËRDREJTA PËR SHKRESËN
* **Vlerësimi i Qëndrueshmërisë Ligjore:** Pikat e forta dhe dobësitë fatale të kësaj shkrese.
* **Këshilla Taktike mbi Korrigjimin apo Goditjen:** Çfarë argumentesh duhen goditur dhe si neutralizohet efekti i dëmshëm.
* **Rekomandimi i Hapit Taktik:** (Ankesë, Prapësim, Padi për Anulim, Kërkesë për Masë Sigurimi, apo Kundërshtim Ekspertize).

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Veprimi brenda Afatit Prekluziv):** Veprimi i parë i detyrueshëm procedural para skadimit të afatit.
* 🟡 **HAPI 2 (Plotësimi Provues dhe Kundër-Goditja):** Masat për sigurimin e provave, kundër-ekspertizat apo parashtresat plotësuese.
* 🟢 **HAPI 3 (Mbrojtja në Organin Kompetent):** Linja përfundimtare e mbrojtjes për fitoren e plotë ligjore.
* 🏁 **Konkluzioni Përfundimtar Taktik për Shkresën:** Vlerësimi përmbyllës i forcës ligjore të aktit.

Përfundo plotësisht këtë Shtjellë 3 deri te fjala e fundit e Konkluzionit Taktik!
"""
        else:
            # Nëse është thirrje e përgjithshme monolitike
            struktura_seksioneve = """
STRUKTURA E PLOTË (8 SEKSIONET):
### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
### 2. 👥 STRUKTURA E PALËVE DHE LEGJITIMITETI PROCEDURAL
### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE
### 4. ⚖️ TABELA SHTERUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
### 5. ⚠️ GJETJET KRITIKE DHE DETEKTORI I GABIMEVE
### 6. 🔬 AUDITIMI I KËRKESËS DHE EKZEKUTUESHMËRISË
### 7. 💡 DIAGNOZA KORRIGJUESE DHE REKOMANDIMET
### 8. 🎯 MASTER PLANI I VEPRIMIT
"""

        return f"""
<konteksti_i_autopsise_forenzike_se_shkreses>
JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
REPUBLIKA E KOSOVËS • EKSPERTIZË DOKTRINARE E PROVAVE DHE MBROJTJE GJYQËSORE

MANDATI YT SUPREM:
Përpara teje ndodhet një dokument specifik gjyqësor, administrativ apo procedural për auditim të thellë doktrinar.
Detyra jote absolute është AUTOPSIA FORENZIKE E KËSAJ SHKRESE DHE DHËNIA E KËSHILLËS STRATEGJIKE.
PËRGJIGJU VETËM PËR SEKSIONET E KËRKUARA NË KËTË SHTJELLË. MOS E KALOFSH TEMËN DHE MOS GJENERO SEKSIONE TË PANEVOJSHME.
Detyra jote është të përfundosh 100% strukturën e kërkuar më poshtë pa u ndërprerë kurrë në mes!
</konteksti_i_autopsise_forenzike_se_shkreses>

{protokolli_suprem}

{mbrojtja_rolit}

📋 IDENTIFIKIMI I SHKRESËS NË AUDITIM:
{manifest_str or 'Dokument Procedural i Administruar'}
LËMIA E PËRCAKTUAR NGA SHKRESA: **{case_domain}**
POZICIONI PROCEDURAL I KLIENTIT: **{pozicioni}**
DATA E AUDITIMIT DOKTRINAR: {current_date_str}

{toni_rolit}

📚 KORNIZA LIGJORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{lista_ligjeve}

🏛️ JURISPRUDENCA DHE PRECEDENTËT SUPREMË NGA BAZA GLOBALE (Revizionet / PML):
{baza_globale if baza_globale else "Zbato legjislacionin pozitiv të Republikës së Kosovës dhe praktikat e konsoliduara të Kolegjeve të Gjykatës Supreme."}

{'='*60}
TEKSTI I PLOTË I SHKRESËS QË AUDITOHET:
{'='*60}
{teksti_shkreses}
{'='*60}

{struktura_seksioneve}
"""