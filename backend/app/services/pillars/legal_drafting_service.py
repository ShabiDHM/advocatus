# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - SUPREME COURT LEGAL DRAFTING V45.0 (USER-INTENT DRIVEN • ZERO MISROUTING)

import logging
import re
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class LegalDraftingService:
    """
    MODUL UNIVERSAL PËR HARTIMIN E AKTEVE GJYQËSORE DHE PROCEDURALE:
    - 100% i orientuar nga kërkesa e përdoruesit (User Query).
    - Shmang gabimet e rënda ku kërkesa civile përfundon si kallëzim penal.
    - Format solemn, shkencor dhe gati për dorëzim zyrtar (Court-Ready).
    """

    @staticmethod
    def resolve_draft_target(query: str, case_domain: str = "CIVIL") -> Dict[str, str]:
        """
        Përcakton saktësisht llojin e aktit dhe organin kompetent duke u bazuar
        në kërkesën konkrete të përdoruesit, pa mbivendosur domain-e të gabuara.
        """
        q = (query or "").lower()

        # 1. KALLËZIM PENAL / DENONCIM (VETËM NËSE KËRKOHET SHPREHIMISHT PENALE)
        if any(kw in q for kw in ["kallëzim penal", "kallezim penal", "kallzim penal", "denoncim penal"]):
            return {
                "document_type": "KALLËZIM PENAL",
                "organ": "PROKURORISË THEMELORE / PROKURORISË SPECIALE TË KOSOVËS",
                "statutes": "Kodi Penal i Kosovës (KPK Nr. 06/L-074) dhe Kodi i Procedurës Penale (KPPRK Nr. 08/L-032).",
                "precedent_type": "Kolegjit Penal të Gjykatës Supreme (Aktgjykimet PML)"
            }

        # 2. ANKESË KUNDËR AKTVENDIMIT / AKTGJYKIMIT
        if any(kw in q for kw in ["ankesë", "ankese", "ankim", "apel", "kundër aktvendimit", "kunder aktvendimit"]):
            organ_name = "GJYKATËS SË APELIT TË KOSOVËS" if "komercial" not in case_domain.lower() else "GJYKATËS KOMERCIALE TË KOSOVËS — Dhomat e Shkallës së Dytë"
            return {
                "document_type": "ANKESË KUNDËR AKTVENDIMIT / AKTGJYKIMIT",
                "organ": f"{organ_name}\n(përmes Gjykatës së Shkallës së Parë)",
                "statutes": "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006) dhe Ligji për Gjykatën Komerciale (Nr. 08/L-015).",
                "precedent_type": "Qëndrimeve Parimore të Kolegjit Civil të Gjykatës Supreme (Aktgjykimet Rev)"
            }

        # 3. KUNDËRPADI
        if any(kw in q for kw in ["kundërpadi", "kunderpadi"]):
            return {
                "document_type": "KUNDËRPADI PËR DËMSHPËRBLIM DHE KËRKESA RECIPROKE",
                "organ": "GJYKATËS KOMPETENTE KU ZHVILLOHET PROCEDURA SIPAS PADISË",
                "statutes": "Neni 256 i Ligjit për Procedurën Kontestimore (LPK) dhe Ligji për Marrëdhëniet e Detyrimeve (LMD).",
                "precedent_type": "Praktikës së Gjykatës Supreme mbi Pavarësinë e Kundërpadisë"
            }

        # 4. MASË SIGURIMI
        if any(kw in q for kw in ["masë e sigurimit", "mase e sigurimit", "sigurim të kërkesës", "bllokim"]):
            return {
                "document_type": "PROPOZIM PËR CAKTIMIN E MASËS SË SIGURIMIT",
                "organ": "GJYKATËS KOMPETENTE TË ÇËSHTJES",
                "statutes": "Nenet 297, 298 dhe 300 të Ligjit për Procedurën Kontestimore (LPK Nr. 03/L-006).",
                "precedent_type": "Gjykatës Supreme mbi Kushtet e Rrezikut dhe Periculum in Mora"
            }

        # 5. PADI / KËRKESËPADI TREGTARE (GJYKATA KOMERCIALE)
        if any(kw in q for kw in ["komerciale", "tregtare", "shoqëri tregtare", "aksionar", "ortak", "sh.p.k."]) or case_domain == "KOMERCIAL":
            return {
                "document_type": "KËRKESËPADI TREGTARE PËR DËMSHPËRBLIM",
                "organ": "GJYKATËS KOMERCIALE TË REPUBLIKËS SË KOSOVËS\nDhoma e Shkallës së Parë — Prishtinë",
                "statutes": "Ligji për Gjykatën Komerciale (Nr. 08/L-015), Ligji për Shoqëritë Tregtare (Nr. 06/L-016), LMD dhe LPK.",
                "precedent_type": "Kolegjit Ekonomik të Gjykatës Supreme (Aktgjykimet Rev)"
            }

        # 6. PADI CIVILE (DEFAULT I SIGURT PËR DËME, KONTRATA DHE DETYRIME)
        return {
            "document_type": "KËRKESËPADI CIVILE PËR DËMSHPËRBLIM",
            "organ": "GJYKATËS THEMELORE NË PRISHTINË\nDepartamenti Civil",
            "statutes": "Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077) dhe Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006).",
            "precedent_type": "Kolegjit Civil të Gjykatës Supreme (Aktgjykimet Rev)"
        }

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str,
        query: str,
        case_domain: Optional[str] = None,
        document_type: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "PARASHTRUES").strip().upper()
        target_info = LegalDraftingService.resolve_draft_target(query, case_domain or "CIVIL")
        doc_title = target_info["document_type"]
        competent_organ = target_info["organ"]
        statutes = target_info["statutes"]
        precedent_type = target_info["precedent_type"]

        search_query = query_text or f"Hartimi profesional i {doc_title} Nenet e ligjit të Kosovës Precedentët e Gjykatës Supreme Rev PML"
        rag_context, _ = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=15
        )

        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)

        return f"""
<legal_evidentiary_privilege_context>
HARTIM PROFESIONAL DHE SOLEMN I AKTIT LIGJOR • PRIVILEGJI I AVOKATISË
Detyra jote si Avokat Kryesor dhe Ekspert i Hartimit Procedural është të përpilosh këtë akt zyrtar ({doc_title}) me saktësi absolute kirurgjikale, gati për nënshkrim dhe protokollim në:
{competent_organ}
</legal_evidentiary_privilege_context>

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS QË PO HARTOHET:
AKTI ZYRTAR: **{doc_title}** | ORGANIT: **{competent_organ}**
PARASHTRUESI/KLIENTI: **{client_name or 'I Identifikuar në Dosje'}** | POZICIONI: **{pos}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE:
{statutes}

🏛️ JURISPRUDENCA PARIMORE E GJYKATËS SUPREME ({precedent_type}):
{rag_context if rag_context else "Zbato precedentët e konsoliduar të Gjykatës Supreme të Kosovës."}

======================================================================
RREGULLAT E HEKURTA TË HARTIMIT (COURT-READY STANDARD):
1. PËRPUTHJE RIGOROZE ME KËRKESËN E PËRDORUESIT:
   - Nëse përdoruesi kërkoi Padi Civile/Dëmshpërblim, harto PADI CIVILE për dëmshpërblim! Ndalohet rreptësisht kthimi i kërkesës civile në kallëzim penal apo dërgimi në PSRK pa kërkesë të shprehur!
2. ROLET E SAKTA TË PALËVE (ZERO INVERSION):
   - Përdor emrat, adresat, dhe cilësitë procedurale të sakta të palëve siç figurojnë në provat e dosjes.
3. PETITUMI SOLEMN DHE EKZAKT:
   - Pjesa kërkuese (Petitum-i) duhet të jetë e plotë, e ndarë me pika të numëruara (1, 2, 3), me shuma monetare të sakta në EUR, kamatëvonesë ligjore (8%), dhe shpenzime procedurale.
======================================================================

{'='*60}
PROVAT DHE TEKSTI I FASHIKULLIT TË LËNDËS:
{'='*60}
{context_str}
{'='*60}

HARTO AKTIN E PLOTË ZYRTAR ME KËTË STRUKTURË FORMALE:

{competent_organ}

**PARASHTRUESI / PADITËSI:**
[Emri i plotë, adresa, NUI/Nr. Personal nga provat e dosjes]

**KUNDËR TË PADITURIT / PALËS KUNDËRSHTARE:**
[Emri i plotë i palës kundërshtare, adresa, cilësia nga provat]

**LËNDA:** {doc_title}
**VLERA E KONTESTIT:** [Shuma përkatëse në EUR sipas provave]
**BAZA LIGJORE:** {statutes}

---

### I. PËRMBLEDHJE E FAKTEVE DHE BAZA E PREDIKIMIT
(Përshkruaj rrjedhën faktike, raportin juridik mes palëve, veprimet e kundërligjshme dhe dëmin e shkaktuar).

### II. BAZA STATUTORE DHE PRECEDENTËT E GJYKATËS SUPREME
(Zbërthe nenet ligjore dhe cito qëndrimet parimore të Gjykatës Supreme të Kosovës që mbështesin kërkesën).

### III. KËRKESA PËR MASË SIGURIMI (NËSE APLIKOHET)
(Arsyeto rrezikun e tjetërsimit të pasurisë dhe bazën sipas LPK-së).

### IV. PETITUMI / PJESA KËRKUESE SOLEMNE
I propozojmë organit kompetent që të marrë këtë:

**V E N D I M / A K T G J Y K I M**
1. **APROVOHET** kërkesa e parashtruesit...
2. **OBLIGOHET** pala kundërshtare që të paguajë shumën prej [Shuma €] me kamatë ligjore prej 8%...
3. **OBLIGOHET** pala kundërshtare të paguajë shpenzimet procedurale.

---

### V. INVENTARI I PROVAVE SHKRESORE:
[Listo të gjitha provat konkrete nga dosja që mbështesin kërkesën].

**PARASHTRUESI / AVOKATI:**
_______________________
{client_name}
Data: {current_date_str}
Prishtinë, Republika e Kosovës
"""