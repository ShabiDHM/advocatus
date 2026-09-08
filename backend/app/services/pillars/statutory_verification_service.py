# FILE: backend/app/services/pillars/statutory_verification_service.py
# PHOENIX PROTOCOL - STATUTORY & PRECEDENT VERIFIER ENGINE V2.0 (STREAM-OPTIMIZED • ZERO TRUNCATION)
# 100% COMPLETE CODE • GJUHË E PASTËR JURIDIKE SHQIPE • SAKTËSI NENI-PËR-NEN

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class StatutoryVerificationService:
    """
    SHËRBIMI I VERIFIKIMIT DOKTRINAR TË NENEVE DHE PRECEDENTËVE (V2.0):
    - I Optimizuar për Streaming: Pa ndërprerje dhe me përgjigje të menjëhershme.
    - Saktësi Neni-për-Nen: Analizon çdo dispozitë të aplikueshme në Republikën e Kosovës.
    - Zero Hardcoding: Përshtatet plotësisht me çdo lloj lënde gjyqësore.
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
                context_str=context_str[:8000],
                manifest_str=manifest_str or ""
            )

        pyetja_kerkimore = query_text or f"Verifikimi i neneve dhe precedentëve të Gjykatës Supreme për lëndën {case_domain}: {case_title}."

        baza_globale = ""
        try:
            baza_globale, _ = BasePillarService.get_rag_context(
                user_id=user_id or "",
                case_id=case_id or "",
                query_text=pyetja_kerkimore,
                n_results=8
            )
        except Exception as err:
            logger.warning(f"RAG lookup warning: {err}")

        protokolli_suprem = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        lista_ligjeve = "\n".join([f"- {ligji}" for ligji in BasePillarService.get_domain_laws(case_domain)])

        return f"""[VERIFIKIMI DOKTRINAR I NENEVE DHE REFERENCAVE LIGJORE • JURISTI AI]
Ju jeni Eksperti Suprem i Verifikimit Statutor dhe Precedentëve të Gjykatës Supreme të Kosovës.
MANDATI:
Kryeni verifikimin e drejtpërdrejtë, neni-për-nen, të të gjitha dispozitave ligjore që lidhen me këtë çështje ({case_domain}).

RREGULLAT E PËRGJIGJES:
1. Përdorni gjuhë standarde administrative-juridike të Kosovës.
2. Jepni analizë të plotë e të saktë neni-për-nen, pa përgjigje evazive.
3. Bazo arsyetimin në ligjet pozitive dhe precedentët përkatës të Kolegjeve të Gjykatës Supreme (PML dhe Revizion).

{protokolli_suprem}

{mbrojtja_rolit}

TË DHËNAT E LËNDËS NË VERIFIKIM:
- Çështja: {case_title}
- Klienti: {client_name or 'I Identifikuar në Shkresa'} ({pozicioni})
- Lëmia: {case_domain}
- Data e Verifikimit: {current_date_str}

KORNIZA STATUTORE E APLIKUESHME:
{lista_ligjeve}

PRECEDENTËT SUPREMË:
{baza_globale if baza_globale else "Zbato legjislacionin pozitiv të Kosovës dhe praktikat e konsoliduara të Gjykatës Supreme."}

{'='*50}
SHKRESAT DHE PROVAT E FASHIKULLIT:
{'='*50}
{context_str[:25000]}
{'='*50}

STRUKTURA E DETYRUESHME E VERIFIKIMIT:

### 1. TABELA E TË GJITHA DISPOZITAVE LIGJORE TË DOKUMENTUARA
| Neni dhe Ligji i Kosovës | Instituti Juridik që Rregullon | A Është Zbatuar Drejt apo me Shkelje | 🏛️ Precedenti i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 2. DETEKTORI I SHKELJEVE PROCEDURALE DHE DISPOZITAVE TË SHPËRFILLURA
* Analizo shkeljet e ligjit material dhe atij procedural (p.sh. Neni 182 LPK / Nenet e Kodit të Procedurës Penale).
* Identifiko normat imperative që janë anashkaluar nga organi shqyrtues apo pala kundërshtare.

### 3. KONKLUZIONI I QËNDRUESHMËRISË STATUTORE
Vlerësimi përmbyllës doktrinar mbi bazueshmërinë e pretendimeve ligjore për klientin {client_name}."""