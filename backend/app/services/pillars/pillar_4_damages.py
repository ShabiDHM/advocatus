# FILE: backend/app/services/pillars/pillar_4_damages.py
# PHOENIX PROTOCOL - PILLAR 4: FINANCIAL DAMAGES V21.0 (COMPACT & STRICT)

from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar4DamagesService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 4:
    - Llogaritja e dëmit material dhe jomaterial
    - Kamata ligjore 8%
    - Masat e sigurimit
    - RAG + TIMELINE + ZERO HALUCINACIONE
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
                financial_parts.append(f"   - Dëmi Real: {financial_data['damnum_emergens']} €")
            if financial_data.get("lucrum_cessans"):
                financial_parts.append(f"   - Fitimi i Humbur: {financial_data['lucrum_cessans']} €")
            if financial_data.get("moral_damage"):
                financial_parts.append(f"   - Dëmi Jomaterial: {financial_data['moral_damage']} €")
            if financial_parts:
                financial_section = f"\nTË DHËNAT FINANCIARE:\n{chr(10).join(financial_parts)}"

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

MISIONI I KARTËS 4:
1. Llogarit dëmin material dhe jomaterial në Euro (€);
2. Llogarit kamatën 8% (VETËM nëse konfirmohet nga RAG context);
3. Argumento masat e sigurimit (VETËM nga RAG context);
4. MOS shpik asnjë shumë — Nëse mungon, shëno: [Shuma sipas faturës];
5. MOS cito asnjë nen apo precedent që nuk gjendet në RAG context ose listën e verifikuar.

STRUKTURA E DETYRUESHME:
### 1. 💶 TABELA E DËMIT MATERIAL
### 2. 🧠 TABELA E DËMIT JOMATERIAL
### 3. 📈 LLOGARITJA E KAMATËS LIGJORE (8%)
### 4. 🛡️ BAZA STATUTARE PËR MASËN E SIGURISË
### 5. 📋 PËRMBLEDHJA TOTALE (€) DHE REKOMANDIMI STRATEGJIK
"""