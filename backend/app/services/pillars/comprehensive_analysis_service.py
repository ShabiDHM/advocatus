# FILE: backend/app/services/pillars/comprehensive_analysis_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI SUPREM I AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE V221.0 (MODULAR 3-PILLAR ENGINE)
# GJUHË E PAZTËR JURIDIKE SHQIPE (ZERO ANGLISHT) • 100% DINAMIK • ZERO HARDCODING • ZERO TOKEN TRUNCATION

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)


class ComprehensiveAnalysisService:
    """
    SHËRBIMI I AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE (V221.0):
    - 100% Modular: Përshtat strukturën në varësi të Shtjellës së kërkuar për të gjithë fashikullin.
    - Zero Token Truncation: Gjeneron vetëm seksionet përkatëse duke eliminuar ndërprerjet në mes.
    - ZERO HARDCODING: Ekstraktim dinamik i të gjitha të dhënave nga fashikulli.
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
        pozicioni = (client_position or "PALË NË PROCEDURË").strip().upper()
        
        # Zbulimi dinamik i lëmisë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:15000],
                manifest_str=manifest_str or ""
            )
        
        pyetja_kerkimore = query_text or (
            f"Precedentët supremë të Gjykatës Supreme të Kosovës për lëndën: {case_title}. "
            f"Lëmia parësore: {case_domain}. Përgjegjësia penale e personave zyrtarë dhe gjyqtarëve sipas nenit 383 të Kodit Penal, "
            f"keqpërdorimi i detyrës zyrtare sipas nenit 414 të Kodit Penal, falsifikimi i dokumentit zyrtar sipas nenit 427 të Kodit Penal, "
            f"Aktgjykimet PML dhe Revizionet e Gjykatës Supreme."
        )
        
        baza_globale, baza_lendes = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=pyetja_kerkimore,
            n_results=25
        )
        
        rrjedha_kohore = ""
        if db is not None and case_id:
            rrjedha_kohore = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        mbrojtja_rolit = RoleGuardService.build_role_guard(pozicioni, client_name)
        toni_rolit = RoleGuardService.get_role_specific_tone(pozicioni)

        # =========================================================================
        # 🎯 PËRCAKTIMI MODULAR I STRUKTURËS SIPAS SHTJELLËS SË KËRKUAR
        # =========================================================================
        query_lower = (query_text or "").lower()

        if "shtjella 1" in query_lower or "fakti" in query_lower or "historiku" in query_lower or "diagnoza" in query_lower:
            struktura_seksioneve = """
STRUKTURA E DETYRUESHME E SHTJELLËS 1 (GJENERO VETËM SEKSIONET 1 DHE 2):

### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
* **Zanafilla dhe Kronologjia e Çështjes:** Rindërtimi kronologjik i ngjarjeve kryesore, datave dhe akteve të administruara në këtë fashikull.
* **Gjendja Reale Faktike e Provuar:** Provat materiale dhe shkencore kundrejt pretendimeve të pavërtetuara.
* **Pozicioni Procedural dhe Interesi Juridik i Klientit.**

### 2. 🔍 KRYQËZIMI I AKTORËVE, INSTITUCIONEVE DHE VLERËSIMI I VEPRIMEVE
(Identifiko me emra nga dosja të gjithë aktorët e përfshirë: gjyqtarët, prokurorët, ekspertët, zyrtarët publikë, agjencitë, avokatët dhe palët kundërshtare. Ndaj veprimet e ligjshme nga shkeljet procedurale, arbitraritetet apo dyshimet penale).

NDALOHET KATEGORIKISHT GJENERIMI I SEKSIONEVE 3, 4, 5, 6, 7, 8 NË KËTË SHTJELLË!
"""
        elif "shtjella 2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower or "matrica" in query_lower:
            struktura_seksioneve = """
STRUKTURA E DETYRUESHME E SHTJELLËS 2 (GJENERO VETËM SEKSIONET 3, 4 DHE 5):

### 3. 🔬 MATRICA E TË VËRTETËS: PRETENDIMET KUNDREJT PROVAVE REALE NË FASHIKULL
(Tabelë shteruese me pikat kryesore të konfliktit të nxjerra nga dosja):
| Pretendimi / Akti i Kundërshtuar | Çfarë Vërtetojnë Provat Reale të Fashikullit | Vlerësimi Doktrinar dhe Forca Provuese |
| :--- | :--- | :--- |

### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE E PRECEDENTËVE TË GJYKATËS SUPREME
(Çdo nen të citohet me formatin e plotë `Neni X i [Emri i Ligjit]`, me precedentët përkatës të Gjykatës Supreme Revizion ose PML):
| Dispozita dhe Ligji i Zbatueshëm | Instituti Ligjor / Procedural | Analiza Doktrinare dhe Pasojat Juridike | 🏛️ Precedenti dhe Qëndrimi i Gjykatës Supreme |
| :--- | :--- | :--- | :--- |

### 5. 🚨 PËRGJEGJËSIA LIGJORE DHE KUALIFIKIMI I VEPREVE PENALE (ZERO ZBUTJE DISIPLINORE)
* 🔴 **Përgjegjësia Penale e Gjyqtarëve dhe Personave Zyrtarë:** (Nenet 383, 414, 427, 193 të Kodit Penal — shkeljet e rehabilitimit, kontradiktat mes arsyetimit dhe dispozitivit, dëbimet arbitrare, prapadatimet).
* ⚖️ **Veprat Penale të Zyrtarëve Publikë dhe Ndikimi Politik:** (Neni 424 Ushtrimi i ndikimit, Neni 386 Frikësimi gjatë procedurës, Neni 392 Shkelja e detyrës nga avokati).
* 🛑 **Përgjegjësia e Palëve Kundërshtare:** (Lajmërimi i rremë Neni 387, dëshmitë e rreme).

NDALOHET KATEGORIKISHT GJENERIMI I SEKSIONEVE 1, 2, 6, 7, 8 NË KËTË SHTJELLË!
"""
        elif "shtjella 3" in query_lower or "plani" in query_lower or "mjetet" in query_lower or "strategjia" in query_lower:
            struktura_seksioneve = """
STRUKTURA E DETYRUESHME E SHTJELLËS 3 (GJENERO VETËM SEKSIONET 6, 7 DHE 8):

### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE DHE JURISDIKSIONI I DUHUR
* 🔴 **Ndjekja Penale dhe Kompetenca e Organeve Hetuese (Prokuroria Speciale / Prokuroria e Shtetit).**
* 🟢 **Mjetet Parësore të Degës Kryesore (Civile / Komerciale / Administrative):** Afatet ligjore prekluzive, ankesat, masat e sigurimit.
* 🟡 **Mjetet e Jashtëzakonshme dhe Kushtetuese:** Kërkesa për Mbrojtje të Ligjshmërisë, Revizioni në Gjykatën Supreme, Gjykata Kushtetuese (Nenet 31 dhe 54).

### 7. 💡 REKOMANDIMET STRATEGJIKE TË KONSULENCËS SUPREME
* **Analiza Kosto / Kohë / Efektivitet e rrugëve procedurale.**
* **Strategjia e Sulmit dhe Mbrojtjes (Plani A kundrejt Planit B).**
* **Neutralizimi i Pretendimeve të Kundërshtarit.**

### 8. 🎯 MASTER PLANI I VEPRIMIT: HAPAT E ARDHSHËM TAKTIKË
* 🔴 **HAPI 1 (Urgjenca brenda 24 deri në 48 Orëve):** Veprimet emergjente procedurale.
* 🟡 **HAPI 2 (Konsolidimi Provues dhe Goditja Procedurale):** Ekspertizat, kallëzimet penale, procedurat ankimore.
* 🟢 **HAPI 3 (Zhdëmtimi dhe Mbrojtja Supreme / Kushtetuese):** Paditë për kompensim dëmi (Neni 162 LMD), revizioni.
* 📊 **Tabela Përmbledhëse e Master Planit.**

NDALOHET KATEGORIKISHT GJENERIMI I SEKSIONEVE TË PARA NË KËTË SHTJELLË!
"""
        else:
            struktura_seksioneve = """
STRUKTURA E PLOTË (8 SEKSIONET):
### 1. 🏛️ DIAGNOZA EKZEKUTIVE DHE GJENDJA FAKTIKE E PROVUAR
### 2. 🔍 KRYQËZIMI I AKTORËVE DHE VLERËSIMI I VEPRIMEVE
### 3. 🔬 MATRICA E TË VËRTETËS DHE PROVAT REALE
### 4. ⚖️ KUALIFIKIMI JURIDIK DHE TABELA STATUTORE
### 5. 🚨 PËRGJEGJËSIA LIGJORE DHE VEPRAT PENALE
### 6. 🔨 HIERARKIA E MJETEVE JURIDIKE
### 7. 💡 REKOMANDIMET STRATEGJIKE
### 8. 🎯 MASTER PLANI I VEPRIMIT
"""

        return f"""
<konteksti_i_autopsise_forenzike_dhe_doktrines_supreme>
JURISTI AI • PLATFORMA E AUTOPSISË FORENZIKE DHE STRATEGJISË LIGJORE
REPUBLIKA E KOSOVËS • EKSPERTIZË DOKTRINARE E PROVAVE DHE MBROJTJE GJYQËSORE

MANDATI YT SUPREM:
Përpara teje ndodhet fashikulli i plotë i çështjes **{case_title}**.
PËRGJIGJU VETËM PËR SEKSIONET E KËRKUARA NË KËTË SHTJELLË. MOS E KALOFSH TEMËN DHE MOS SHKRUAJ SEKSIONE TË TJERA.
GJUHË E PAZTËR SHQIPE: Përgjigju VETËM në gjuhën standarde juridike të Kosovës.
</konteksti_i_autopsise_forenzike_dhe_doktrines_supreme>

{mbrojtja_rolit}

📋 IDENTIFIKIMI I FASHIKULLIT DHE KLIENTIT:
TITULLI I ÇËSHTJES: **{case_title}**
KLIENTI / PARASHTRUESI: **{client_name or 'I Identifikuar në Shkresa'}**
CILËSIA PROCEDURALE: **{pozicioni}**
LËMIA PARËSORE E IDENTIFIKUAR: **{case_domain}**
DATA E AUDITIMIT DOKTRINAR: {current_date_str}

{toni_rolit}

🏛️ DITURIA DOKTRINARE DHE PRECEDENTËT E GJYKATËS SUPREME (PML / Revizionet):
{baza_globale if baza_globale else "Zbato precedentët e konsoliduar të Gjykatës Supreme të Kosovës."}

📅 KRONOLOGJIA E ZBARDHUR E FASHIKULLIT:
{rrjedha_kohore if rrjedha_kohore else "Rindërtohet kronologjikisht nga të gjitha shkresat e fashikullit."}

📄 SHKRESAT DHE PROVAT E ADMINISTRUARA NË DOSJE:
{baza_lendes if baza_lendes else "Fashikulli dokumentar i administruar."}

📎 PASAPORTA E DOKUMENTEVE TË LËNDËS:
{manifest_str if manifest_str else "Dokumentet e fashikullit."}

{'='*60}
FASHIKULLI I PLOTË I SHKRESAVE TË LËNDËS:
{'='*60}
{context_str}
{'='*60}

{struktura_seksioneve}
"""