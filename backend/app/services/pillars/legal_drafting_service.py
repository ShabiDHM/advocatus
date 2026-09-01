# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - PILLAR 6: COURT-READY LEGAL DRAFTING V30.0 (LPK & KPPRK STANDARDS)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService
import logging

logger = logging.getLogger(__name__)

class LegalDraftingService:
    """
    Modul Ekskluziv për HARTIMIN PROFESIONAL TË AKTEVE GJYQËSORE:
    - Padi Civile, Familjare (Alimentacion & Kujdestari), Kontestet e Punës & Pronësore
    - Kallëzime Penale (KPPRK & KPRK)
    - Prapësime në Padi, Kundërpadi dhe Ankesa (Apel)
    - Kontrata dhe Marrëveshje Noteriale
    - Standard i plotë gjyqësor me Dispozitiv, Petitum Ekzekutues dhe Inventar Provash
    """

    @staticmethod
    def detect_document_type(query: str) -> str:
        query_lower = (query or "").lower()
        
        if any(kw in query_lower for kw in ["kallëzim penal", "kallezim penal", "kallzim penal", "penale"]):
            return "KALLËZIM PENAL"
        elif any(kw in query_lower for kw in ["ankesë", "ankese", "ankim", "apel"]):
            return "ANKESË KUNDËR AKTGJYKIMIT"
        elif any(kw in query_lower for kw in ["kundërpadi", "kunderpadi"]):
            return "KUNDËRPADI"
        elif any(kw in query_lower for kw in ["prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"]):
            return "PËRGJIGJE NË PADI (PRAPËSIM)"
        elif any(kw in query_lower for kw in ["kontratë", "kontrate", "marrëveshje", "marreveshje"]):
            return "KONTRATË / MARRËVESHJE LIGJORE"
        elif any(kw in query_lower for kw in ["alimentacion", "kujdestari", "besim të fëmijës", "besim te femijes"]):
            return "PADI PËR KUJDESTARINË E FËMIJËS DHE ALIMENTACION"
        elif any(kw in query_lower for kw in ["kërkesëpadi", "kerkesepadi", "padi"]):
            return "PADÍ CIVILE"
        else:
            return "SHKRESË GJYQËSORE / PROVE MATERIALE"

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
        pos = (client_position or "DEFENDANT").upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        if not document_type:
            document_type = LegalDraftingService.detect_document_type(query)
        
        search_query = query_text or (
            f"Hartimi profesional i {document_type} për lëndën: {case_title}. "
            f"Faktet e provuara, nenet përkatëse, shumat monetare dhe petitumi."
        )
        
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=35
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        role_guard = RoleGuardService.build_role_guard(pos, client_name)

        base_prompt = BasePillarService.build_base_prompt(
            case_title=case_title,
            client_name=client_name,
            client_position=pos,
            current_date_str=current_date_str,
            manifest_str=manifest_str,
            context_str=context_str,
            case_domain=case_domain,
            rag_context=rag_context,
            case_rag_context=case_rag_context,
            timeline_context=timeline_context
        )

        return f"""
{base_prompt}

{role_guard}

📝 KËRKESA E AVOKATIT:
"{query}"

📄 LLOJI I DOKUMENTIT QË DUHET HARTUAR: **{document_type}**

======================================================================
STANDARDET E DETYRUESHME TË HARTIMIT SIPAS LIGJEVE TË KOSOVËS:
1. Shkresa duhet të jetë GATI PËR PROTOKOLL DHE GJYKATË (Court-Ready).
2. Parashtruesi/Klienti yt është: **{client_name}** (Mbro me forcë interesat e tij/saj).
3. Çdo fakt i përmendur duhet të lidhet me provën konkrete nga shkresat e lëndës.
4. PETITUMI (Kërkesa) duhet të jetë EKZAKTE, E QARTË dhe e formulueshme si Dispozitiv Aktgjykimi.
5. Fëmijët e mitur trajtohen gjithmonë sipas Parimit Suprem të 'Interesit Më të Mirë të Fëmijës'.
6. Nëse mungon një e dhënë (nr. personal, adresa e saktë), lëre me vendmbajtës: `[Nr. Personal: ________]` ose `[Adresa: ________]`.
======================================================================

STRUKTURA E SAKTË GJYQËSORE E DOKUMENTIT:

**GJYKATËS THEMELORE NË [QYTETI / PRISHTINË]**
**Departamenti për Çështje Civile / Familjare / Penale**

**PADITËSI / PARASHTRUESI:**
{client_name}, me vendbanim në [Vendbanimi], Rr. [Rruga], Nr. Personal [Sipas Dokumenteve],
i përfaqësuar nga Avokati [Emri i Avokatit], me autorizim në shkresa.

**KUNDËR TË PADITURIT / PALËS KUNDËRSHTARE:**
[Emri dhe Mbiemri i Palës Kundërshtare nga dokumentet], me vendbanim në [Vendbanimi].

**OBJEKTI I LËNDËS:** {document_type} — {case_title}
**VLERA E KONTESTIT:** [Shuma në EUR sipas shkresave, ose 'E papërcaktuar']
**BAZA LIGJORE:** Nenet përkatëse të legjislacionit në fuqi në Kosovë (LPK / LMD / Ligji për Familjen).

---

### I. GJENDJA FAKTIKE DHE KRONOLOGJIA
(Përshkruaj qartë dhe me rend kronologjik të gjitha faktet thelbësore të vërtetuara nga shkresat)

### II. BAZA LIGJORE DHE ARSYETIMI JURIDIK
(Lidh faktet konkrete me nenet specifike të ligjit të Kosovës, duke argumentuar pse klienti ka të drejtë)

### III. KËRKESËPADIA / PROPOZIMI PËRFUNDIMTAR (P E T I T U M I)
I propozojmë Gjykatës që pas shqyrtimit kryesor të marrë këtë:

**A K T G J Y K I M**
1. **APROVOHET** në tërësi si e bazuar kërkesëpadia e paditësit {client_name}.
2. **[DETYRIMI KONKRET I PALËS KUNDËRSHTARE]:** (p.sh. Detyrohet e paditura të lejojë kontaktet e rregullta... OSE Detyrohet i padituri të paguajë shumën prej... OSE Refuzohet padia e paditësit si e pabazuar).
3. **[SHPENZIMET E PROCEDURËS]:** Detyrohet pala kundërshtare t'i kompensojë paditësit shpenzimet e procedurës kontestimore sipas Tarifës së Odës së Avokatëve të Kosovës.

---

### INVENTARI I PROVAVE TË BASHKËNGJITURA:
1. **Prova 1:** [Emri i dokumentit / certifikatës]
2. **Prova 2:** [Transkripti i mesazheve / audio me sekonda]
3. **Prova 3:** [Dëshmi financiare / vërtetime]

**PARASHTRUESI I SHKRESËS / AVOKATI:**
_______________________
{client_name}
Data: {current_date_str}
Prishtinë, Republika e Kosovës
"""