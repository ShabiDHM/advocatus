# FILE: backend/app/services/pillars/pillar_4_damages.py
# PHOENIX PROTOCOL - PILLAR 4: DOMAIN-AGNOSTIC FINANCIAL DAMAGES & INJUNCTIVE RELIEF V20.0 (TIMELINE INTEGRATED)

from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar4DamagesService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 4 (100% UNIVERSAL DAMAGES & MEASURES ENGINE):
    - Zbulon automatikisht llojin e dëmit sipas lëndës
    - Tabela e llogaritjes së dëmit material real (damnum emergens) dhe fitimit të humbur (lucrum cessans)
    - Tabela e dëmit jomaterial
    - Llogaritja e kamatës ligjore vonesore prej 8% në vit
    - Baza statutare për Masat e Sigurimit
    - 100% agnostik ndaj domeneve + RAG + TIMELINE + ZERO HALUCINACIONE
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
        
        # PHOENIX FIX: Zbulo domenin
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Kërko në RAG
        search_query = query_text or f"Llogaritja e dëmshpërblimit për lëminë: {case_domain}. Dëmi material, jomaterial, kamata 8%, masat e sigurimit sipas LPK dhe KPPRK."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )
        
        # PHOENIX FIX: Ndërto kronologjinë
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        # PHOENIX FIX: Ndërto seksionin e të dhënave financiare
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
                financial_parts.append(f"   - Tarifat e Avokatisë (OAK): {financial_data['attorney_fees']} €")
            if financial_data.get("interest_start_date"):
                financial_parts.append(f"   - Data e Fillimit të Kamatës: {financial_data['interest_start_date']}")
            
            if financial_parts:
                financial_section = f"""
TË DHËNAT FINANCIARE TË IDENTIFIKUARA NGA FASHIKULLI:
{chr(10).join(financial_parts)}
"""
            else:
                financial_section = """
TË DHËNAT FINANCIARE: Nuk u identifikuan shuma specifike nga fashikulli. 
Kërko nga përdoruesi të japë shumat reale ose llogarit nga dokumentet në dispozicion.
"""

        return f"""
Ti je "Sokrati - Eksperti Financiar-Juridik dhe Gjyqtari Suprem i Dëmshpërblimeve në Kosovë".
DEGË E SË DREJTËS: {case_domain}
LËNDA: **{case_title}** | KLIENTI: **{client_name}** ({pos}) | DATA: {current_date_str}

DOKTRINA DHE GUARDRAILS UNIVERSALE TË DËMEVE NË KOSOVË:
1. PËRCAKTIMI I DËMIT SIPAS LËMISË: {case_domain}
   - Civile/Tregtare/Kontraktuale: Dëmi real (damnum emergens), Fitimi i humbur (lucrum cessans), Tarifat OAK, ekspertizat, dëmi jomaterial;
   - Marrëdhënie Pune: Pagat e papaguara, kontributet e Trustit, kamata;
   - Penale: Kërkesa Pasurore-Juridike për dëmin e shkaktuar;
   - Pronësore: Shpërblimi për shfrytëzim të paligjshëm, dëmtimi i sendit.
2. DËMI JOMATERIAL: Cenimi i nderit, dinjitetit, reputacionit, dhimbja shpirtërore, stresi.
3. KAMATA LIGJORE VONESORE: 8% në vit — VETËM nëse konfirmohet nga RAG context.
4. MASAT E SIGURISË: Neni 297 LPK / Nenet 188, 221 KPPRK — VETËM nga RAG context.
5. ZERO HALUCINACIONE:
   - MOS shpik asnjë shumë që nuk gjendet në dokumente;
   - MOS cito asnjë nen që nuk gjendet në RAG context;
   - MOS cito asnjë precedent që NUK gjendet në listën e verifikuar;
   - NËSE mungon një e dhënë, shënoje: [Shuma saktësisht sipas faturës/vërtetimit përkatës].

{financial_section}

MISIONI (KARTA 4):
Përpilo llogaritjen e plotë financiare të dëmeve, ndërto tabelat me shuma në Euro (€), llogarit kamatën prej 8% (nëse konfirmohet nga RAG), dhe argumento masat emergjente në favor të klientit **{client_name}**.

{BasePillarService.build_base_prompt(
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
)}

STRUKTURA E DETYRUESHME E PËRGJIGJES PËR KARTËN 4:
### 1. 💶 TABELA E DËMIT MATERIAL (Dëmi real pasuror, shpenzimet gjyqësore, avokatia sipas OAK, ekspertizat dhe fitimi i humbur)
### 2. 🧠 TABELA E DËMIT JOMATERIAL (Cenimi i integritetit, dinjitetit, reputacionit, dhimbja shpirtërore dhe stresi i pësuar)
### 3. 📈 LLOGARITJA E KAMATËS LIGJORE VONESORE (8% në vit sipas LMD-së nga momenti i lindjes së dëmit)
### 4. 🛡️ BAZA STATUTARE PËR MASËN E SIGURISË DHE MBROJTJES SË INTERESAVE TË KLIENTIT
### 5. 📋 PËRMBLEDHJA TOTALE E DËMSHPËRBLIMIT (€) DHE REKOMANDIMI STRATEGJIK EKZEKUTIV
"""