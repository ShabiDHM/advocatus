# FILE: backend/app/services/pillars/pillar_4_damages.py
# PHOENIX PROTOCOL - PILLAR 4: FINANCIAL DAMAGES V22.0 (REAL AMOUNTS & SPECIFIC CALCULATION)

from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar4DamagesService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 4:
    - Llogaritja e dëmit material dhe jomaterial me shuma REALE nga dokumentet
    - Kamata ligjore 8% e llogaritur saktësisht
    - Masat e sigurimit specifike për rastin
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
        financial_data: Optional[Dict[str, Any]] = None,
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
        
        search_query = query_text or f"Llogaritja e dëmshpërblimit për lëminë: {case_domain}. Dëmi material, jomaterial, kamata 8%, masat e sigurimit."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        financial_section = ""
        if financial_data:
            financial_parts = []
            if financial_data.get("damnum_emergens"):
                financial_parts.append(f"   - Dëmi Real Pasuror: {financial_data['damnum_emergens']} €")
            if financial_data.get("lucrum_cessans"):
                financial_parts.append(f"   - Fitimi i Humbur: {financial_data['lucrum_cessans']} €")
            if financial_data.get("unpaid_salaries"):
                financial_parts.append(f"   - Pagat e Papaguara: {financial_data['unpaid_salaries']} €")
            if financial_data.get("moral_damage"):
                financial_parts.append(f"   - Dëmi Jomaterial: {financial_data['moral_damage']} €")
            if financial_data.get("expert_fees"):
                financial_parts.append(f"   - Shpenzimet e Ekspertizave: {financial_data['expert_fees']} €")
            if financial_data.get("attorney_fees"):
                financial_parts.append(f"   - Tarifat e Avokatisë: {financial_data['attorney_fees']} €")
            if financial_data.get("interest_start_date"):
                financial_parts.append(f"   - Data e Fillimit të Kamatës: {financial_data['interest_start_date']}")
            if financial_parts:
                financial_section = f"""
TË DHËNAT FINANCIARE NGA FASHIKULLI:
{chr(10).join(financial_parts)}
"""
        else:
            financial_section = """
TË DHËNAT FINANCIARE: Nuk u identifikuan shuma specifike nga fashikulli.
DUHET të kërkosh shuma nga dokumentet:
- Faturat e avokatit
- Shpenzimet e ekspertizave
- Pagat e humbura (nëse ka)
- Dëmi jomaterial (vlerëso sipas intensitetit)
NËSE shuma nuk gjendet në dokument, SHËNO: [Shuma sipas faturës/vërtetimit]
MOS shpik asnjë shumë.
"""

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

{financial_section}

MISIONI I KARTËS 4 (SPECIFIK):
1. LLOGARIT dëmin material me shuma REALE nga dokumentet e fashikullit;
2. LLOGARIT dëmin jomaterial me vlerësime të arsyetuara (jo formula të përgjithshme);
3. LLOGARIT kamatën 8% nga DATA E SAKTË e lindjes së dëmit deri sot ({current_date_str});
4. LLOGARIT çdo zë të dëmit VEÇ E VEÇ me tabelë të plotë;
5. Propozo MASA TË SIGURIMIT specifike për këtë rast (jo të përgjithshme).

RREGULLAT E HEKURTA:
1. MOS shpik asnjë shumë që nuk gjendet në dokumente;
2. NËSE shuma mungon, shëno: [Shuma sipas faturës/vërtetimit përkatës];
3. Çdo shumë duhet të ketë BURIMIN (cili dokument e vërteton);
4. Kamata llogaritet nga data e saktë e çdo dëmi veç e veç;
5. MOS përdor formula të përgjithshme — bëj llogaritje reale.

STRUKTURA E DETYRUESHME:
### 1. 💶 TABELA E DËMIT MATERIAL (me burim për çdo shumë)
### 2. 🧠 TABELA E DËMIT JOMATERIAL (me arsyetim për çdo zë)
### 3. 📈 LLOGARITJA E SAKTË E KAMATËS 8% (nga data e lindjes së dëmit)
### 4. 🛡️ MASAT E SIGURIMIT SPECIFIKE PËR KËTË RAST
### 5. 📋 PËRMBLEDHJA TOTALE DHE REKOMANDIMI STRATEGJIK
"""