# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME COURT SINGLE-DOCUMENT FORENSIC AUDITOR V260.0 (100% DYNAMIC • 1-CLICK CITATIONS • ZERO HARDCODING)

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME PËR NJË SHKRESË TË VETME (V260.0):
    - 100% Dinamik, Shkencor dhe i Paanshëm: Ekstraktim ekskluzivisht nga teksti real i këtij dokumenti.
    - ZERO HARDCODING: Asnjë emër, numër lënde, shumë apo fakt i fabrikuar me dorë.
    - ZERO DRAFTING: Nuk shkruan draft shkrese; fokusohet 100% në AUTOPSINË DHE KËSHILLIMIN STRATEGJIK.
    - 1-Klikim Verifikim: Çdo dispozitë e cituar formatohet ekzaktësisht 'Neni X i [Ligjit]'.
    - Diagnostikon saktësinë formale, afatet prekluzive, lapsuset dhe precedentët supremë (Rev dhe PML).
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
        
        # Zbulim dinamik i lëmisë nga vetë teksti i shkresës
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=audit_text[:15000],
                manifest_str=manifest_str or ""
            )
        
        pos = (client_position or "PALË NË PROCEDURË").strip().upper()
        mined_legal_entities = ForensicAuditService.extract_legal_entities_from_text(audit_text)
        
        # Përcaktimi dinamik i precedentëve përkatës (PML për penale, Rev për civile/komerciale)
        domain_upper = case_domain.upper()
        precedent_terms = []
        if "PENAL" in domain_upper:
            precedent_terms.append("Aktgjykimet PML të Kolegjit Penal")
        if any(d in domain_upper for d in ["CIVIL", "KOMERCIAL", "PRONËSOR", "FAMILJAR", "PUNË"]):
            precedent_terms.append("Aktgjykimet Rev të Kolegjit Civil dhe Komercial")
        
        precedents_hint = " dhe ".join(precedent_terms) or "Aktgjykimet PML dhe Rev"
        search_query = query_text or f"{mined_legal_entities} {case_domain} Nenet {precedents_hint} Gjykatës Supreme"

        # Izolim i plotë RAG: vetëm precedentët dhe normat ligjore për këtë akt
        rag_context = ""
        try:
            rag_context, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",  # Izolim absolut për të parandaluar ndotjen nga shkresa të tjera
                query_text=search_query,
                n_results=30
            )
        except Exception as rag_err:
            logger.warning(f"Forensic RAG search fallback: {rag_err}")

        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM FORENZIK DOKTRINAR I SHKRESËS • KOLEGJI KONSULENT I GJYKATËS SUPREME TË KOSOVËS
MANDATI YT SUPREM:
Përpara teje ndodhet një dokument specifik gjyqësor, administrativ apo procedural për auditim të thellë doktrinar.
Detyra jote absolute është AUTOPSIA FORENZIKE E KËSAJ SHKRESE DHE DHËNIA E KËSHILLËS STRATEGJIKE:
1. Audito VETËM DHE EKSKLUZIVISHT këtë shkresë specifike që ndodhet më poshtë në tekst.
2. NDALOHET KATEGORIKISHT HARTIMI I NJË SHKRESE FORMALE (mos shkruaj 'Gjykatës Themelore: Padi/Ankesë'). Roli yt është të evidentosh me sy inkuizitor saktësinë, të metat, lapsuset, pasojat juridike dhe veprimin e duhur procedural.
3. Zbërthe çdo nen ligjor në formatin standard për verifikim të menjëhershëm: `Neni X i [Ligjit]`.
4. Zbulo nëse akti vuan nga mangësi thelbësore (kontradiktë arsyetim-dispozitiv, moskompetencë, tejkalim i afateve prekluzive, apo zbatim i gabuar i së drejtës materiale).
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS NË AUDITIM:
{manifest_str or 'Dokument Procedural i Administruar'}
LËMIA E PËRCAKTUAR NGA SHKRESA: **{case_domain}**
POZICIONI PROCEDURAL I KLIENTIT: **{pos}**
DATA E AUDITIMIT: {current_date_str}

{role_tone}

📚 KORNIZA STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E RELEVANTË NGA BAZA GLOBALE (Rev / PML):
{rag_context if rag_context else "Zbato legjislacionin pozitiv të Republikës së Kosovës dhe praktikat e konsoliduara të Kolegjeve të Gjykatës Supreme."}

======================================================================
RREGULLAT E HEKURTA TË AUDITIMIT FORENZIK (ZERO DRAFTING • PURE AUDIT):

1. BESNIKËRI DHE SHKENCORITET NDAJ KËTIJ DOKUMENTI TË VETËM:
   - Të gjitha faktet, emrat, organet, datat dhe numrat e lëndës duhet të merren 100% nga teksti real i këtij dokumenti.
   - Nëse një e dhënë mungon në shkresë, deklaroje qartë; mos bëj kurrë supozime.

2. DETEKTORI I SHKELJEVE 'CONTRA LEGEM' DHE AFATEVE:
   - Verifiko afatet prekluzive ligjore:
     * Aktvendimi gjyqësor: afati i ankesës 7 ditë (LPK / Gjykata Komerciale).
     * Aktgjykimi gjyqësor: afati i ankesës 15 ditë (LPK / KPPRK).
     * Përgjigja në padi: afati 30 ditë (LPK).
     * Vendimi administrativ: afati i konfliktit administrativ 30 ditë (LKA).
   - Verifiko nëse ka kontradiktë flagrante mes asaj që pranohet në arsyetim dhe asaj që urdhërohet në dispozitiv.

3. VERIFIKIMI 1-KLIKIM DHE PRECEDENTËT SUPREMË:
   - ÇDO NEN i cituar apo i zbatueshëm për këtë shkresë DUHET të shfaqet në tabelën e Seksionit 4 me formatin ekzakt:
     `Neni X i [Ligjit]` (p.sh. `Neni 182 i LPK-së`, `Neni 383 i KPRK-së`, `Neni 31 i Kushtetutës`).
   - Lidh çdo dispozitë me precedentin përkatës të Gjykatës Supreme (Rev ose PML).
======================================================================

{'='*60}
TEKSTI I PLOTË DHE I PAPREKUR I SHKRESËS QË AUDITOHET:
{'='*60}
{audit_text}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK TË DOKUMENTIT (8 SEKSIONE):

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji dhe Natyra Formale e Shkresës:** (Padi, Ankesë, Aktvendim, Aktgjykim, Raport Ekspertize, Procesverbal, Kontratë, etj.).
* **Organi Nxjerrës / Titullari Procedural:** Gjykata, prokuroria, eksperti, apo autoriteti përgjegjës.
* **Numri Identifikues i Regjistrit / Shenja e Lëndës:** Numri i saktë i protokollit apo shkresës.
* **Auditimi i Afateve dhe Prekluziviteti:** A është nxjerrë/paraqitur brenda afatit ligjor? Sa është afati për ta atakuar?

### 2. 👥 STRUKTURA E PALËVE DHE LEGJITIMITETI PROCEDURAL
* **Parashtruesi / Autori i Aktit:** Legjitimiteti aktiv dhe cilësia procedurale.
* **Pala Kundërshtare / Subjekti i Atakuar:** Legjitimiteti pasiv dhe fusha e efektit juridik.
* **Interesi Juridik i Mbrojtur:** Të drejtat që kërkohen apo cenohen në këtë akt.

### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE TË SHKRESËS
* **Faktet Kryesore të Rindërtuara:** Çfarë pretendon apo konstaton ekzaktësisht kjo shkresë.
* **Provat e Administruara në Akt:** Cilat prova materiale, shkencore apo dëshmi përmenden.
* **Boshllëqet Provuese dhe Cenueshmëria:** Çfarë provash thelbësore janë shpërfillur apo mungojnë.

### 4. ⚖️ TABELA SHTERRUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(Çdo nen të citohet me formatin `Neni X i [Ligjit]` për verifikim 1-klikim, me precedentin përkatës Rev ose PML):
| Dispozita & Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET 'CONTRA LEGEM' DHE DETEKTORI I GABIMEVE
* 🔴 **Shkeljet Thelbësore të Konstatuara:** (Moskompetencë, shkelje procedurale, tejkalim kërkese, kontradiktë arsyetim-dispozitiv).
* 🔍 **Detektori i Pasaktësive dhe Lapsuseve në Shkresë:**
  | Formulimi / Paragrafi Aktual në Shkresë | Pasaktësia / Lapsusi Doktrinar i Identifikuar | Formula e Saktë Ligjore e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I KËRKESËS (PETITUMIT) DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Qartësisë së Kërkesës apo Dispozitivit:** A është kërkesa e saktë, e ekzekutueshme dhe e mbështetur në normë?
* **Rreziqet Procedurale:** Pengesat që çojnë në rrëzimin, hedhjen apo prishjen e aktit në instancat më të larta.
* **Forca Ekzekutive:** A përbën titull ekzekutiv dhe si mund të pezullohet apo kundërshtohet.

### 7. 💡 DIAGNOZA KORRIGJUESE DHE REKOMANDIMET E DREJTPËRDREJTA PËR SHKRESËN
* **Vlerësimi i Qëndrueshmërisë Ligjore:** Pikat e forta dhe dobësitë fatale të kësaj shkrese.
* **Këshilla Taktike mbi Korrigjimin / Sulmin:** Çfarë argumentesh duhen goditur, çfarë duhen shtuar dhe si neutralizohet efekti i dëmshëm.
* **Rekomandimi i Hapit Taktik:** A duhet të paraqitet Ankesë, Prapësim, Padi për Anulim, Kërkesë për Masë Sigurimi, apo Kundërshtim Ekspertize.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Veprimi brenda Afatit Prekluziv):** Veprimi i parë i detyrueshëm procedural para skadimit të afatit.
* 🟡 **HAPI 2 (Plotësimi Provues dhe Kundër-Sulmi):** Masat për sigurimin e provave, kundër-ekspertizat apo parashtresat plotësuese.
* 🟢 **HAPI 3 (Mbrojtja në Organin Kompetent):** Linja përfundimtare e mbrojtjes për fitoren e plotë ligjore.
"""