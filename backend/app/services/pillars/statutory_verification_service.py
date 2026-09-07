# FILE: backend/app/services/pillars/statutory_verification_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI I PAVARUR I VERIFIKIMIT DOKTRINAR TË NENEVE V1.0
# ZERO EVASION • SAKTËSI NENI-PËR-NEN • PRECEDENTË SUPREMË • 100% DINAMIK

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class StatutoryVerificationService:
    """
    SHËRBIMI I DEDIKUAR I VERIFIKIMIT TË NENEVE DHE REFERENCAVE LIGJORE (V1.0):
    - 100% I Izoluar: Modifikohet në mënyrë të pavarur pa prekur shërbimet e tjera.
    - Zero Evazion: Ndalon kategorikisht përgjigjet boshe si "shiko online".
    - Verifikim Shterues: Nxjerr dhe analizon të gjitha nenet e përmendura në fashikull.
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        context_str: str,
        manifest_str: Optional[str] = None,
        case_domain: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Any = None
    ) -> str:
        pozicioni = (client_position or "PALË NË PROCEDURË").strip().upper()

        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:15000],
                manifest_str=manifest_str or ""
            )

        pyetja_kerkimore = query_text or (
            f"Verifikimi i të gjitha neneve dhe referencave ligjore për lëndën: {case_title}. "
            f"Lëmia: {case_domain}. Nenet e zbatueshme të LPK, KPK, KPPRK, LMD, LFK dhe precedentët supremë."
        )

        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id=case_id or "",
                query_text=pyetja_kerkimore,
                n_results=30
            )
        except Exception as err:
            logger.warning(f"Kërkimi i bazës për verifikim: {err}")

        protokolli_suprem = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        lista_ligjeve = "\n".join([f"- {ligji}" for ligji in BasePillarService.get_domain_laws(case_domain)])

        return f"""
<konteksti_i_verifikimit_statutor_te_neneve>
JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE VERIFIKIMIT LIGJOR
REPUBLIKA E KOSOVËS • KRYE-AUDITORI DOKTRINAR I NENEVE DHE PRECEDENTËVE SUPREMË

MANDATI YT SUPREM:
Përpara teje ndodhet fashikulli me të gjitha shkresat e çështjes **{case_title}**.
Përdoruesi kërkon VERIFIKIMIN E DREJTPËRDREJTË të të gjitha neneve dhe referencave ligjore.

RREGULLAT E HEKURTA TË VERIFIKIMIT:
1. Përgjigju VETËM në gjuhën standarde juridike të Republikës së Kosovës.
2. NDALOHET KATEGORIKISHT TË JAPËSH PËRGJIGJE EVAZIVE SI "KONSULTONI LIGJET ONLINE" APO "VIZITONI FAQEN E KUVENDIT".
   TI JE EKSPERTI QË KRYEN VERIFIKIMIN TANI: Analizo shkresat më poshtë, nxirr nenet e cituara dhe bëj verifikimin e tyre neni-për-nen!
3. DETYRA E DREJTPËRDREJTË QË DUHET TË KRYESH:
   - **Pjesa 1: Tabela e të Gjitha Neneve të Gjetura në Shkresa:**
     | Neni dhe Ligji i Cituar | Çfarë Rregullon Saktësisht | A Është Zbatuar Drejt apo me Gabim në Dosje | Precedenti Përkatës i Gjykatës Supreme |
     | :--- | :--- | :--- | :--- |
   - **Pjesa 2: Detektori i Shkeljeve Procedurale dhe Neneve të Shpërfillura:**
     Trego cilat dispozita ligjore thelbësore (p.sh. Neni 182 LPK, Neni 93 KPK për rehabilitimin, Nenet 188/221 KPPRK) janë shkelur apo injoruar nga organet.
   - **Pjesa 3: Konkluzioni i Saktësisë Ligjore:**
     Vlerësimi përmbyllës i qëndrueshmërisë ligjore të pretendimeve në këtë lëndë.
</konteksti_i_verifikimit_statutor_te_neneve>

{protokolli_suprem}

{mbrojtja_rolit}

📋 IDENTIFIKIMI I LËNDËS NË VERIFIKIM:
TITULLI: **{case_title}**
KLIENTI: **{client_name or 'I Identifikuar në Shkresa'}** ({pozicioni})
LËMIA: **{case_domain}**
DATA: {current_date_str}

📚 KORNIZA STATUTORE POZITIVE NË KOSOVË:
{lista_ligjeve}

🏛️ JURISPRUDENCA DHE PRECEDENTËT SUPREMË:
{baza_globale if baza_globale else "Zbato legjislacionin pozitiv të Kosovës dhe vendimet e konsoliduara të Gjykatës Supreme (PML dhe Rev)."}

{'='*60}
SHKRESAT DHE PROVAT E FASHIKULLIT PËR VERIFIKIM:
{'='*60}
{context_str}
{'='*60}
"""