# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - SUPREME COURT LEGAL DRAFTING V50.0 (STRICT STATUTORY CODE SEPARATION & FLAWLESS COMMERCIAL APPEALS)

import logging
import re
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class LegalDraftingService:
    """
    MODUL UNIVERSAL I DOKTRINËS SË HARTIMIT GJYQËSOR (V50.0):
    - Ndalon kategorikisht përzierjen e ligjit penal me atë komercial/civil.
    - Harton Ankesat e Gjykatës Komerciale mbi bazën e LPK-së (Nenet 208-210 dhe Neni 256 par. 4).
    - Citon ekskluzivisht precedentët përkatës (Aktgjykimet Rev për lëmitë tregtare/civile).
    """

    @staticmethod
    def resolve_draft_target(query: str, case_domain: str = "CIVIL") -> Dict[str, str]:
        q = (query or "").lower()

        # 1. ANKESË KUNDËR AKTVENDIMIT / AKTGJYKIMIT TË GJYKATËS KOMERCIALE
        if "komercial" in case_domain.lower() or any(kw in q for kw in ["komerciale", "tregtare", "shoqëri tregtare", "sh.p.k.", "nui"]):
            if any(kw in q for kw in ["ankesë", "ankese", "ankim", "apel", "kundër aktvendimit", "kunder aktvendimit"]):
                return {
                    "document_type": "ANKESË KUNDËR AKTVENDIMIT TË GJYKATËS KOMERCIALE",
                    "organ": "GJYKATËS KOMERCIALE TË REPUBLIKËS SË KOSOVËS\nDhomat e Shkallës së Dytë — Prishtinë\n(Përmes Dhomave të Shkallës së Parë)",
                    "statutes": "Nenet 208-210 dhe Neni 256 par. 4 të Ligjit për Procedurën Kontestimore (LPK Nr. 03/L-006) në lidhje me Ligjin për Gjykatën Komerciale (Nr. 08/L-015).",
                    "precedent_type": "Kolegjit Ekonomik dhe Civil të Gjykatës Supreme të Kosovës (Aktgjykimet Rev)"
                }
            return {
                "document_type": "KËRKESËPADI TREGTARE PËR DËMSHPËRBLIM",
                "organ": "GJYKATËS KOMERCIALE TË REPUBLIKËS SË KOSOVËS\nDhoma e Shkallës së Parë — Prishtinë",
                "statutes": "Ligji për Gjykatën Komerciale (Nr. 08/L-015), Ligji për Shoqëritë Tregtare (Nr. 06/L-016), LMD dhe LPK.",
                "precedent_type": "Kolegjit Ekonomik të Gjykatës Supreme (Aktgjykimet Rev)"
            }

        # 2. KALLËZIM PENAL (VETËM NËSE ÇËSHTJA ËSHTË PENALE)
        if case_domain == "PENAL" or any(kw in q for kw in ["kallëzim penal", "kallezim penal", "denoncim penal"]):
            return {
                "document_type": "KALLËZIM PENAL",
                "organ": "PROKURORISË THEMELORE / PROKURORISË SPECIALE TË KOSOVËS",
                "statutes": "Kodi Penal i Kosovës (KPK Nr. 06/L-074) dhe Kodi i Procedurës Penale (KPPRK Nr. 08/L-032).",
                "precedent_type": "Kolegjit Penal të Gjykatës Supreme (Aktgjykimet PML)"
            }

        # 3. ANKESË CIVILE
        if any(kw in q for kw in ["ankesë", "ankese", "ankim", "apel"]):
            return {
                "document_type": "ANKESË KUNDËR AKTGJYKIMIT / AKTVENDIMIT",
                "organ": "GJYKATËS SË APELIT TË KOSOVËS\n(Përmes Gjykatës Themelore)",
                "statutes": "Nenet 176-195 dhe 208-210 të Ligjit për Procedurën Kontestimore (LPK Nr. 03/L-006).",
                "precedent_type": "Kolegjit Civil të Gjykatës Supreme të Kosovës (Aktgjykimet Rev)"
            }

        # 4. KUNDËRPADI DHE PRAPËSIM
        if any(kw in q for kw in ["kundërpadi", "kunderpadi"]):
            return {
                "document_type": "KUNDËRPADI PËR DËMSHPËRBLIM DHE KËRKESA RECIPROKE",
                "organ": "GJYKATËS KOMPETENTE KU ZHVILLOHET PROCEDURA",
                "statutes": "Neni 256 i Ligjit për Procedurën Kontestimore (LPK) dhe Ligji për Marrëdhëniet e Detyrimeve (LMD).",
                "precedent_type": "Praktikës së Gjykatës Supreme mbi Pavarësinë e Kundërpadisë (Aktgjykimet Rev)"
            }

        # 5. DEFAULT I SIGURT CIVIL
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

        search_query = query_text or f"Hartimi profesional i {doc_title} Nenet e ligjit të Kosovës Precedentët e Gjykatës Supreme Rev"
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

📚 KORNIZA STATUTORE DHE NENET E ZBATUESHME:
{statutes}

🏛️ JURISPRUDENCA PARIMORE E GJYKATËS SUPREME ({precedent_type}):
{rag_context if rag_context else "Zbato precedentët e konsoliduar të Gjykatës Supreme të Kosovës (Aktgjykimet Rev)."}

======================================================================
RREGULLAT E HEKURTA DOKTRINARE (COURT-READY STANDARD):
1. NDALIM ABSOLUT I KODIT PENAL NË ÇËSHTJE KOMERCIALE/CIVILE:
   - Ky rast është i natyrës tregtare/civile në Gjykatën Komerciale! NDALOHET KATEGORIKISHT citimi i Kodit Penal (KPK) apo Kodit të Procedurës Penale (KPPRK Nenet 380/388).
   - Ankesa kundër Aktvendimit bazohet EKSKLUZIVISHT në Nenet 208-210 dhe Nenin 256 par. 4 të LPK-së (Ligji Nr. 03/L-006) dhe Ligjin për Gjykatën Komerciale!
2. ROLET E SAKTA TË PALËVE:
   - Përdor emrat, NUI-të dhe cilësitë procedurale të sakta të palëve nga shkresat e fashikullit.
3. PETITUMI SOLEMN I ANKESËS / PADISË:
   - Kërko prishjen/ndryshimin e Pikës II të Aktvendimit dhe urdhërimin e ndarjes së procedimit për shqyrtimin e kundërpadisë në meritë.
======================================================================

{'='*60}
PROVAT DHE TEKSTI I FASHIKULLIT TË LËNDËS:
{'='*60}
{context_str}
{'='*60}

HARTO AKTIN E PLOTË ZYRTAR ME KËTË STRUKTURË FORMALE:

{competent_organ}

**PARASHTRUESI / ANKUESI:**
[Emri i plotë, adresa, NUI/Nr. Personal nga provat e dosjes]

**KUNDËR PALËS KUNDËRSHTARE:**
[Emri i plotë i palës kundërshtare, adresa, NUI nga shkresat]

**NUMRI I LËNDËS SË ATAKUAR:** [psh. KE.nr.662/2022 nga shkresat]
**LËNDA:** {doc_title}
**BAZA LIGJORE:** {statutes}

---

### I. HYRJE DHE OBJEKTI I ANKIMIT
(Përcakto saktësisht aktvendimin e atakuar, datën e tij dhe pikat që ankimohen — posaçërisht hedhja e kundërpadisë).

### II. SHKELJET PROCEDURALE DHE ZBATIMI I GABUAR I LIGJIT MATERIAL
(Zbërthe pse Gjykata e Shkallës së Parë ka bërë shkelje thelbësore të dispozitave të procedurës kontestimore sipas Nenit 182 dhe Nenit 256 par. 4 të LPK-së, duke asgjësuar kundërpadinë e pavarur pa zbatuar ndarjen e procedimit).

### III. BAZA E PRECEDENTËVE TË GJYKATËS SUPREME (AKTGJYKIMET REV)
(Cito qëndrimet parimore të Kolegjit Ekonomik/Civil të Gjykatës Supreme të Kosovës mbi të drejtën e shqyrtimit meritor të kundërpadisë).

### IV. PJESA KËRKUESE SOLEMNE (PETITUM-I ANKIMOR)
I propozojmë Gjykatës Komerciale — Dhomave të Shkallës së Dytë që të marrë këtë:

**A K T V E N D I M**
1. **PRANOHET** si e bazuar ankesa e parashtruesit...
2. **NDRYSHOHET / PRISHET** Pika II e Aktvendimit të atakuar dhe **URDHËROHET** Gjykata e Shkallës së Parë që kundërpadinë ta trajtojë përmes ndarjes së procedimit si padi të pavarur kontestimore me vlerë të plotë.

---

### V. PROVAT MBËSHTETËSE TË ANKESËS:
[Kopja e aktvendimit të atakuar, shkresat e kundërpadisë, provat e administruara].

**ANKUESI / AVOKATI:**
_______________________
{client_name}
Data: {current_date_str}
Prishtinë, Republika e Kosovës
"""