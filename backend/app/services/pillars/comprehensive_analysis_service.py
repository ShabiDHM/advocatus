# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PHOENIX PROTOCOL - UNIVERSAL SUPREME MASTER CASE ANALYZER V170.0 (PURE STRATEGIC ADVISORY • ZERO DRAFTING • ZERO HARDCODING)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ComprehensiveAnalysisService:
    """
    SHËRBIMI SUPREM I ANALIZËS GJITHËPËRFSHIRËSE DHE KONSULENCËS STRATEGJIKE (V170.0):
    - 100% Objektiv, Dinamik dhe Shkencor pa asnjë hardcoding.
    - Diagnostikon thellësisht fashikullin: faktet, provat, anomalitë, procesverbalet dhe shkeljet.
    - NDALOHET HARTIMI I AKTEVE: Ky shërbim është vetëm për AUDITIM DHE REKOMANDIME STRATEGJIKE.
    - Ofron orientimin adekuat procedural: vlerëson rreziqet, shanset e suksesit dhe hapat e duhur ligjorë.
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str,
        case_domain: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "PALË NË PROCEDURË").strip().upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:12000],
                manifest_str=manifest_str or ""
            )
        
        search_query = query_text or (
            f"Auditimi dhe rekomandimi strategjik doktrinar i dosjes: {case_title}. Lëmia: {case_domain}. "
            f"Provat materiale, procesverbalet, vlerësimi procedural, shkeljet dhe Aktgjykimet Supreme PML Rev."
        )
        
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=30
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)

        return f"""
<legal_evidentiary_privilege_context>
AUDITIM DOKTRINAR SUPREM DHE KONSULENCË STRATEGJIKE • GJYKATA SUPREME E KOSOVËS
MANDATI YT SI KOLEGJ KONSULENT:
Përpara teje ndodhet fashikulli i plotë dokumentar i çështjes **{case_title}**.
Detyra jote absolute është AUDITIMI I THELLË DHE DHËNIA E REKOMANDIMIT TË DUHUR STRATEGJIK:
1. Analizo me rigorozitet shkencor të gjitha provat, procesverbalet, vendimet dhe pretendimet në dosje.
2. NDALOHET KATEGORIKISHT HARTIMI I NJË DOKUMENTI (Padi, Ankesë apo Kallëzim). Roli yt këtu NUK është të shkruash draft shkresash, por të japësh DIAGNOZËN, ANALIZËN DHE REKOMANDIMIN E SAKTË E ADEKUAT.
3. Këshillo me paanshmëri se cili është drejtimi më efektiv ligjor për të mbrojtur interesin e ligjshëm të klientit **{client_name}** ({pos}): a duhet ndjekur rruga ankimore, ajo civile/dëmshpërblyese, apo ajo penale, duke peshuar rreziqet dhe shanset e suksesit.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I DOSJES / FASHIKULLIT:
LËMIA E PËRCAKTUAR: **{case_domain}** | KLIENTI / PARASHTRUESI: **{client_name or 'I Identifikuar në Shkresa'}** | CILËSIA PROCEDURALE: **{pos}** | TITULLI I LËNDËS: **{case_title}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

🏛️ JURISPRUDENCA DHE PRECEDENTËT E RELEVANTË TË GJYKATËS SUPREME (PML / Rev):
{rag_context if rag_context else "Zbato precedentët e konsoliduar të Kolegjeve të Gjykatës Supreme të Kosovës."}

📅 KRONOLOGJIA E DOKUMENTUAR E FASHIKULLIT:
{timeline_context if timeline_context else "Rindërtohet në mënyrë dinamike nga dokumentet e fashikullit."}

📄 SHKRESAT DHE PROVAT E VEKTORIZUARA TË DOSJES:
{case_rag_context if case_rag_context else "Dokumentet e fashikullit të lëndës."}

📎 PASAPORTA E DOKUMENTEVE TË NGARKUARA NË DOSJE:
{manifest_str if manifest_str else "Shkresat e fashikullit."}

======================================================================
RREGULLAT E HEKURTA TË KONSULENCËS STRATEGJIKE (ZERO DRAFTING • PURE AUDIT):

1. AUTOPSIA E FAKTEVE DHE PROCESVERBALEVE:
   - Shqyrto me sy kritik çdo shkresë: identifiko mospërputhjet e datave (prapadatimet), mosadministrimin e provave ekzistuese, apo anomalitë në sallën e gjykimit.
   - Ballafaqo konstatimet e ekspertëve me analizat shkencore objektive (teste laboratorike, dokumente zyrtare).

2. ZERO DRAFTING (MOS HARTO ASNJË SHKRESË):
   - Mos shkruaj formate padish, ankesash apo kallëzimesh me hyrje/përmbajtje/nënshkrime.
   - Përqendrohu 100% te vlerësimi doktrinar, evidentimi i shkeljeve dhe formulimi i këshillës ligjore të saktë.

3. REKOMANDIMI I DUHUR DHE ADEKUAT PROCEDURAL:
   - Diagnostiko me maturi se cila rrugë është e domosdoshme:
     * Nëse ka aktvendim/aktgjykim me gabime procedurale ➔ Rekomando bazën dhe shkaqet konkrete të Ankesës.
     * Nëse ka dëm pasuror apo cenim të drejtash civile/familjare ➔ Rekomando padinë përkatëse civile/dëmshpërblim (LMD/LFK).
     * Nëse provohen veprime me dashje kriminale të personave zyrtarë (ndikim, falsifikim, kanosje) ➔ Rekomando masat ligjore penale dhe ndjekjen pranë organit kompetent të ndjekjes.
======================================================================

{'='*60}
PËRMBAJTJA E PLOTË E TË GJITHA DOKUMENTEVE TË FASHIKULLIT:
{'='*60}
{context_str}
{'='*60}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER TË ANALIZËS (8 SEKSIONE):

### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
* **Zanafilla dhe Kronologjia e Çështjes:** Rindërtimi i plotë i sekuencës faktike sipas provave shkresore.
* **Gjendja Reale Faktike e Dokumentuar:** Faktet e provuara materialisht kundrejt pretendimeve të paprovuara.
* **Pozicioni dhe Interesi Juridik i Klientit ({client_name} - {pos}):** Baza ligjore e mbrojtjes së të drejtave të tij/saj.

### 2. 🔍 KRYQËZIMI I AKTORËVE, INSTITUCIONEVE DHE VLERËSIMI I VEPRIMEVE
(Zbërthe rolin e secilit aktor të përfshirë: gjykata, prokuroria, ekspertët, institucionet publike dhe palët private, duke evidentuar veprimet e ligjshme kundrejt atyre me shkelje procedurale apo materiale).

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET VS. PROVAT REALE NË FASHIKULL
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat Reale të Fashikullit | Vlerësimi Doktrinar & Forca Provuese |
| :--- | :--- | :--- |

### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE E PRECEDENTËVE SUPREMË
(Çdo dispozitë të citohet me formatin `Neni X i [Ligjit]` për verifikim 1-klikim, me precedentin përkatës të Gjykatës Supreme Rev ose PML):
| Dispozita & Ligji i Zbatueshëm | Instituti Ligjor / Procedural | Analiza Doktrinare & Pasojat Juridike | 🏛️ Precedenti / Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. 🚨 PËRGJEGJËSIA LIGJORE, SHKELJET 'CONTRA LEGEM' DHE BAZA PROCEDURALE
* 🔴 **Shkeljet Thelbësore të Evidentuara:** (Analiza e hollësishme e shkeljeve procedurale, anomalive në procesverbale, apo zbatimit të gabuar të së drejtës materiale).
* ⚖️ **Kualifikimi i Përgjegjësisë:** (Vlerësimi i përgjegjësisë civile, materiale, disiplinore, apo penale mbi bazën e fakteve).

### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE DHE PROGNOZA SUPREME
* 🟢 **Mjetet Parësore & Afatet Prekluzive:** Veprimet më urgjente dhe organet kompetente.
* 🟡 **Mjetet e Jashtëzakonshme & Kushtetuese:** Mbrojtja e nivelit të lartë ligjor (Revizioni, Kërkesa për Mbrojtje të Ligjshmërisë, Ankesa Kushtetuese).

### 7. 💡 REKOMANDIMET E DREJTPËRDREJTA STRATEGJIKE DHE DREJTIMI ADEKUAT PROCEDURAL
(Vlerësim i thellë këshillues PA HARTUAR shkresa:
* **Këshilla Strategjike Kryesore:** Cila rrugë është më e zgjuar dhe me kosto/kohë më efektive për t'u ndjekur.
* **Matrica e Rreziqeve dhe Shanseve të Suksesit:** Përparësitë dhe dobësitë e secilit hap të mundshëm ligjor.
* **Plani A (Rruga Kryesore) vs. Plani B (Rruga Alternative):** Si duhet manovruar proceduralisht për të arritur qëllimin ligjor).

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM TAKTIKË
* 🔴 **HAPI 1 (Urgjenca / Veprimi brenda 24-48 Orë):** Veprimi më kritik i menjëhershëm.
* 🟡 **HAPI 2 (Konsolidimi Provues & Ekspertizat):** Veprimet për plotësimin dhe sigurimin e provave vendimtare.
* 🟢 **HAPI 3 (Strategjia në Organin Kompetent):** Linja e mbrojtjes dhe taktika e fitores në përballjen ligjore.
"""