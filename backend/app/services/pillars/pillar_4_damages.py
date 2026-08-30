# FILE: backend/app/services/pillars/pillar_4_damages.py
# PHOENIX PROTOCOL - PILLAR 4: DOMAIN-AGNOSTIC FINANCIAL DAMAGES & INJUNCTIVE RELIEF V19.0 (RAG INTEGRATED)

from typing import Dict, Any, Optional, List
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class Pillar4DamagesService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 4 (100% UNIVERSAL DAMAGES & MEASURES ENGINE):
    - Zbulon automatikisht llojin e dëmit sipas lëndës (Dëm Kontraktual, Dëmtim Pasurie, Dëm Moral/Jomaterial, Pagat e Prapambetura, Kërkesë Pasurore-Juridike Penale)
    - Tabela e llogaritjes së dëmit material real (damnum emergens) dhe fitimit të humbur (lucrum cessans) sipas LMD-së
    - Tabela e dëmit jomaterial (cenim nderi, personaliteti, reputacioni profesional, dhimbje shpirtërore, stres)
    - Llogaritja e kamatës ligjore vonesore prej 8% në vit
    - Baza statutare për Masat e Sigurimit (Neni 297 LPK / Neni 188/221 KPPRK / Masat e Përkohshme Komerciale)
    - 100% agnostik ndaj domeneve + RAG integration për zero halucinacione
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
        case_id: Optional[str] = None
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()
        
        # PHOENIX FIX: Zbulo domenin nëse nuk është dhënë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Kërko në RAG për nenet e dëmshpërblimit dhe masave të sigurimit
        search_query = query_text or f"Llogaritja e dëmshpërblimit për lëminë: {case_domain}. Dëmi material, jomaterial, kamata 8%, masat e sigurimit sipas LPK dhe KPPRK."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=25
        )

        # PHOENIX FIX: Ndërto seksionin e të dhënave financiare në mënyrë dinamike
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
   - Në çështje Civile/Tregtare/Kontraktuale: Dëmi real pasuror (damnum emergens), Fitimi i humbur (lucrum cessans), Tarifat e avokatisë sipas OAK, shpenzimet e ekspertizave dhe dëmi jomaterial;
   - Në çështje të Marrëdhënies së Punës: Pagat e papaguara mujore, kontributet e papaguara të Trustit, kamata dhe dëmi për prishje të paarsyeshme të kontratës;
   - Në çështje Penale: Kërkesa Pasurore-Juridike për dëmin e shkaktuar nga vepra penale;
   - Në çështje Pronësore/Sendore: Shpërblimi për shfrytëzim të paligjshëm të pronës, dëmtimi i sendit apo vlera reale e tregut.
   - PËRDOR VETËM nenet nga KONTEKSTI LIGJOR I VERIFIKUAR më poshtë.
2. DËMI JOMATERIAL:
   - Cenimi i nderit, dinjitetit, autoritetit moral/profesional, reputacionit të biznesit, dhimbja shpirtërore, stresi dhe trauma emocionale.
   - Baza ligjore: VETËM nenet e LMD-së që gjenden në RAG context.
3. KAMATA LIGJORE VONESORE:
   - Aplikohet kamata ligjore vonesore prej 8% në vit nga momenti i lindjes së secilit detyrim / dëmtim deri në pagesën definitive.
   - VETËM nëse kjo normë gjendet në RAG context.
4. MASAT E SIGURISË DHE MBROJTJES SË KËRKESËS:
   - Në Procedurë Civile/Tregtare: Masa e Sigurimit të Kërkesëpadisë — VETËM sipas neneve nga RAG context;
   - Në Procedurë Penale: Masat e veçanta mbrojtëse / urdhrat ndalues — VETËM sipas neneve nga RAG context;
   - Në Procedurë Përmbarimore: Masat e përkohshme të sigurimit të kërkesës.
5. ZERO HALUCINACIONE:
   - MOS shpik asnjë shumë që nuk gjendet në dokumente;
   - MOS cito asnjë nen që nuk gjendet në RAG context;
   - NËSE mungon një e dhënë, shënoje: [Shuma saktësisht sipas faturës/vërtetimit përkatës].

{financial_section}

MISIONI (KARTA 4):
Përpilo llogaritjen e plotë financiare të dëmeve të bazuara në shkresat e fashikullit, ndërto tabelat e qarta me shuma në Euro (€), llogarit kamatën prej 8% (nëse konfirmohet nga RAG) dhe argumento masat emergjente mbrojtëse në favor të klientit tonë **{client_name}**.

{'='*60}
KONTEKSTI LIGJOR I VERIFIKUAR NGA BAZA STATUTORE E KOSOVËS (RAG):
{'='*60}
{rag_context if rag_context else "Nuk u gjet asnjë referencë specifike në bazën statutore. Përdor vetëm parime të përgjithshme të dëmshpërblimit."}

{'='*60}
KONTEKSTI NGA DOKUMENTET E ÇËSHTJES (RAG):
{'='*60}
{case_rag_context if case_rag_context else "Nuk u gjetën dokumente shtesë në bazën e çështjes."}

{'='*60}
PASAPORTA E SHKRESAVE DHE DOKUMENTET:
{'='*60}
{manifest_str}
{context_str}

STRUKTURA E DETYRUESHME E PËRGJIGJES PËR KARTËN 4:
### 1. 💶 TABELA E DËMIT MATERIAL (Dëmi real pasuror, shpenzimet gjyqësore, avokatia sipas OAK, ekspertizat dhe fitimi i humbur)
### 2. 🧠 TABELA E DËMIT JOMATERIAL (Cenimi i integritetit, dinjitetit, reputacionit, dhimbja shpirtërore dhe stresi i pësuar)
### 3. 📈 LLOGARITJA E KAMATËS LIGJORE VONESORE (8% në vit sipas LMD-së nga momenti i lindjes së dëmit)
### 4. 🛡️ BAZA STATUTARE PËR MASËN E SIGURISË DHE MBROJTJES SË INTERESAVE TË KLIENTIT
### 5. 📋 PËRMBLEDHJA TOTALE E DËMSHPËRBLIMIT (€) DHE REKOMANDIMI STRATEGJIK EKZEKUTIV
"""