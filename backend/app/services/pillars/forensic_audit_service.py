# FILE: backend/app/services/pillars/forensic_audit_service.py
# PROTOKOLLI PHOENIX - KRYE-AUDITORI SUPREM I AUTOPSISË SË DOKUMENTIT V270.0
# GJUHË E PAZTËR JURIDIKE SHQIPE (ZERO ANGLISHT) • 100% DINAMIK • ZERO HARDCODING

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ForensicAuditService:
    """
    KRYE-AUDITORI DOKTRINAR I GJYKATËS SUPREME PËR NJË SHKRESË TË VETME (V270.0):
    - 100% Dinamik, Shkencor dhe i Paanshëm: Ekstraktim ekskluzivisht nga teksti real i këtij dokumenti.
    - ZERO HARDCODING: Asnjë emër, numër lënde, shumë apo fakt i fabrikuar me dorë.
    - NDALIM I DRAFTIMIT: Nuk shkruan formularë padish; fokusohet 100% në AUTOPSINË DHE KËSHILLIMIN STRATEGJIK.
    - Verifikim me Një Klikim: Çdo dispozitë e cituar formatohet ekzaktësisht 'Neni X i [Emri i Ligjit]'.
    - Gjuha: Ekskluzivisht gjuha standarde juridike shqipe e Kosovës pa fjalë të huaja.
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
        
        # Zbulim dinamik i lëmisë nga vetë teksti i shkresës
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=teksti_shkreses[:15000],
                manifest_str=manifest_str or ""
            )
        
        pozicioni = (client_position or "PALË NË PROCEDURË").strip().upper()
        entitetet_ligjore = ForensicAuditService.extract_legal_entities_from_text(teksti_shkreses)
        
        # Përcaktimi dinamik i precedentëve përkatës (PML për penale, Revizion për civile/komerciale)
        lemia_upper = case_domain.upper()
        termat_precedenteve = []
        if "PENAL" in lemia_upper:
            termat_precedenteve.append("Aktgjykimet PML të Kolegjit Penal")
        if any(d in lemia_upper for d in ["CIVIL", "KOMERCIAL", "PRONËSOR", "FAMILJAR", "PUNË"]):
            termat_precedenteve.append("Aktgjykimet Revizion të Kolegjit Civil dhe Komercial")
        
        orientimi_precedenteve = " dhe ".join(termat_precedenteve) or "Aktgjykimet PML dhe Revizionet"
        pyetja_kerkimore = query_text or f"{entitetet_ligjore} {case_domain} Nenet {orientimi_precedenteve} të Gjykatës Supreme"

        # Izolim i plotë RAG: vetëm precedentët dhe normat ligjore për këtë akt
        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id="",  # Izolim absolut për të parandaluar ndotjen nga shkresa të tjera
                query_text=pyetja_kerkimore,
                n_results=30
            )
        except Exception as rag_err:
            logger.warning(f"Kërkimi i precedentëve: {rag_err}")

        protokolli_suprem = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)
        lista_ligjeve = "\n".join([f"- {ligji}" for ligji in BasePillarService.get_domain_laws(case_domain)])

        return f"""
<konteksti_i_autopsise_forenzike_se_shkreses>
JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
REPUBLIKA E KOSOVËS • EKSPERTIZË DOKTRINARE E PROVAVE DHE MBROJTJE GJYQËSORE

MANDATI YT SUPREM:
Përpara teje ndodhet një dokument specifik gjyqësor, administrativ apo procedural për auditim të thellë doktrinar.
Detyra jote absolute është AUTOPSIA FORENZIKE E KËSAJ SHKRESE DHE DHËNIA E KËSHILLËS STRATEGJIKE:
1. Audito VETËM DHE EKSKLUZIVISHT këtë shkresë specifike që ndodhet më poshtë në tekst.
2. NDALOHET KATEGORIKISHT HARTIMI I FORMULARËVE TË PADISË (mos shkruaj 'Gjykatës Themelore: Padi ose Ankesë'). Roli yt është të evidentosh me sy inkuizitor saktësinë, të metat, lapsuset, pasojat juridike dhe veprimin e duhur procedural.
3. Zbërthe çdo nen ligjor në formatin standard për verifikim me një klikim: `Neni X i [Emri i Ligjit]`.
4. Zbulo nëse akti vuan nga mangësi thelbësore (kontradiktë mes arsyetimit dhe dispozitivit, moskompetencë lëndore, tejkalim i afateve prekluzive, apo zbatim i gabuar i së drejtës materiale).
5. GJUHË E PAZTËR SHQIPE: Përgjigju VETËM në gjuhën standarde juridike të Republikës së Kosovës pa fjalë apo kllapa në gjuhë të huaja.
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

======================================================================
RREGULLAT E HEKURTA TË AUTOPSISË FORENZIKE (AUTOPSI E PAZTËR LIGJORE):

1. BESNIKËRI DHE SHKENCORITET NDAJ KËTIJ DOKUMENTI TË VETËM:
   - Të gjitha faktet, emrat, organet, datat dhe numrat e lëndës duhet të merren 100% nga teksti real i këtij dokumenti.
   - Nëse një e dhënë mungon në shkresë, deklaroje qartë; mos bëj kurrë supozime.

2. DETEKTORI I SHKELJEVE DHE AFATEVE LIGJORE:
   - Verifiko afatet prekluzive ligjore:
     * Aktvendimi gjyqësor: afati i ankesës 7 ditë (sipas Ligjit për Procedurën Kontestimore / Gjykatës Komerciale).
     * Aktgjykimi gjyqësor: afati i ankesës 15 ditë (sipas LPK-së ose Kodit të Procedurës Penale).
     * Përgjigja në padi (prapësimi): afati 30 ditë (LPK).
     * Vendimi administrativ: afati i konfliktit administrativ 30 ditë.
   - Verifiko nëse ka kontradiktë flagrante mes asaj që pranohet në arsyetim dhe asaj që urdhërohet në dispozitiv.

3. VERIFIKIMI ME NJË KLIKIM DHE PRECEDENTËT SUPREMË:
   - ÇDO NEN i cituar apo i zbatueshëm për këtë shkresë DUHET të shfaqet në tabelën e Seksionit 4 me formatin ekzakt:
     `Neni X i [Emri i Ligjit]` (p.sh. `Neni 182 i Ligjit për Procedurën Kontestimore`, `Neni 383 i Kodit Penal`, `Neni 31 i Kushtetutës`).
   - Lidh çdo dispozitë me precedentin përkatës të Gjykatës Supreme (Revizion ose PML).
======================================================================

{'='*60}
TEKSTI I PLOTË I SHKRESËS QË AUDITOHET:
{'='*60}
{teksti_shkreses}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK TË DOKUMENTIT (8 SEKSIONE TË PLOTA):

# JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
## AUTOPSIA DOKTRINARE DHE INTEGRITETI I SHKRESËS GJYQËSORE
**SHKRESA NË AUDITIM:** {manifest_str or 'Dokument Gjyqësor'} | **LËMIA:** {case_domain} | **DATA:** {current_date_str}

---

### 1. 🔍 PASAPORTA PROCEDURALE DHE DIAGNOZA JURIDIKE E SHKRESËS
* **Lloji dhe Natyra Formale e Shkresës:** (Padi, Ankesë, Aktvendim, Aktgjykim, Raport Ekspertize, Procesverbal, Kontratë, etj.).
* **Organi Nxjerrës / Titullari Procedural:** Gjykata, prokuroria, eksperti, apo autoriteti përgjegjës.
* **Numri Identifikues i Regjistrit / Shenja e Lëndës:** Numri i saktë i protokollit apo shkresës.
* **Auditimi i Afateve dhe Prekluziviteti:** A është nxjerrë apo paraqitur brenda afatit ligjor? Sa është afati i saktë për ta atakuar?

### 2. 👥 STRUKTURA E PALËVE DHE LEGJITIMITETI PROCEDURAL
* **Parashtruesi / Autori i Aktit:** Legjitimiteti aktiv dhe cilësia procedurale.
* **Pala Kundërshtare / Subjekti i Atakuar:** Legjitimiteti pasiv dhe fusha e efektit juridik.
* **Interesi Juridik i Mbrojtur:** Të drejtat që kërkohen apo cenohen në këtë akt.

### 3. 🔬 KRYQËZIMI FORENZIK I FAKTEVE DHE BAZËS PROVUESE TË SHKRESËS
* **Faktet Kryesore të Rindërtuara:** Çfarë pretendon apo konstaton ekzaktësisht kjo shkresë.
* **Provat e Administruara në Akt:** Cilat prova materiale, shkencore apo dëshmi përmenden.
* **Boshllëqet Provuese dhe Cenueshmëria:** Çfarë provash thelbësore janë shpërfillur apo mungojnë.

### 4. ⚖️ TABELA SHTERUESE E DISPOZITAVE DHE PRECEDENTËVE TË GJYKATËS SUPREME
(Çdo nen të citohet me formatin e plotë `Neni X i [Emri i Ligjit]` për verifikim me një klikim, me precedentin përkatës Revizion ose PML):
| Dispozita dhe Ligji Pozitiv | Instituti Procedural / Material | Analiza Doktrinare dhe Pasojat Juridike | 🏛️ Precedenti dhe Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. ⚠️ GJETJET KRITIKE, SHKELJET NË KUNDËRSHTIM ME LIGJIN DHE DETEKTORI I GABIMEVE
* 🔴 **Shkeljet Thelbësore të Konstatuara:** (Moskompetencë lëndore, shkelje procedurale, tejkalim i kërkesëpadisë, kontradiktë mes arsyetimit dhe dispozitivit).
* 🔍 **Detektori i Pasaktësive dhe Lapsuseve në Shkresë:**
  | Formulimi Aktual në Shkresë | Pasaktësia apo Lapsusi Doktrinar i Identifikuar | Formula e Saktë Ligjore e Zëvendësimit |
  | :--- | :--- | :--- |

### 6. 🔬 AUDITIMI I KËRKESËS DHE EKZEKUTUESHMËRISË
* **Vlerësimi i Qartësisë së Kërkesës apo Dispozitivit:** A është kërkesa e saktë, e ekzekutueshme dhe e mbështetur në normë?
* **Rreziqet Procedurale:** Pengesat që çojnë në rrëzimin, hedhjen apo prishjen e aktit në instancat më të larta ankimore.
* **Forca Ekzekutive:** A përbën titull ekzekutiv dhe si mund të pezullohet apo kundërshtohet.

### 7. 💡 DIAGNOZA KORRIGJUESE DHE REKOMANDIMET E DREJTPËRDREJTA PËR SHKRESËN
* **Vlerësimi i Qëndrueshmërisë Ligjore:** Pikat e forta dhe dobësitë fatale të kësaj shkrese.
* **Këshilla Taktike mbi Korrigjimin apo Goditjen:** Çfarë argumentesh duhen goditur, çfarë duhen shtuar dhe si neutralizohet efekti i dëmshëm.
* **Rekomandimi i Hapit Taktik:** A duhet të paraqitet Ankesë, Prapësim, Padi për Anulim, Kërkesë për Masë Sigurimi, apo Kundërshtim Ekspertize.

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM PROCEDURALË
* 🔴 **HAPI 1 (Urgjenca / Veprimi brenda Afatit Prekluziv):** Veprimi i parë i detyrueshëm procedural para skadimit të afatit.
* 🟡 **HAPI 2 (Plotësimi Provues dhe Kundër-Goditja):** Masat për sigurimin e provave, kundër-ekspertizat apo parashtresat plotësuese.
* 🟢 **HAPI 3 (Mbrojtja në Organin Kompetent):** Linja përfundimtare e mbrojtjes për fitoren e plotë ligjore.
"""