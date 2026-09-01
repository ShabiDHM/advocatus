# FILE: backend/app/services/pillars/base_pillar_service.py
# PHOENIX PROTOCOL - BASE PILLAR SERVICE V30.0 (SUPREME COURT JURISPRUDENCE FOUNDATION)

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ========== KONSTANTET E DOMENEVE (TË ZGJERUARA) ==========
DOMAIN_KEYWORDS = {
    "PENAL": [
        "kallëzim penal", "vepër penale", "prokurori", "kpprk", "kprk",
        "mashtrim", "vjedhje", "dhunë në familje", "dhune ne familje", "kërcënim",
        "falsifikim", "lajmërim i rremë", "dëmtim trupor", "armë", "kanosje",
        "keqpërdorim i detyrës", "korrupsion", "ekspertizë psikiatrike"
    ],
    "FAMILJAR": [
        "bashkëshort", "divorc", "shkurorëzim", "kujdestari", "kujdestaria e fëmijës",
        "alimentacion", "ushqim", "qps", "qendra për punë sociale", "raport social",
        "kontaktet me fëmijën", "interesi më i mirë i fëmijës", "e drejta prindërore",
        "dhunë në familje", "urdhër mbrojtje", "trashëgimi", "testament"
    ],
    "CIVIL": [
        "kërkesëpadi", "padi", "kundërpadi", "prapësim", "lpk", "lmd",
        "dëmshpërblim", "kontratë", "borxh", "detyrim", "kompensim",
        "dëm material", "dëm jomaterial", "masë e përkohshme", "sigurim i kërkesës"
    ],
    "PRONËSOR": [
        "pronë", "tokë", "shtëpi", "banesë", "apartament", "kadastër",
        "hipotekë", "posedim", "servitut", "ndërtim", "pengim posedimi", "uzurpim"
    ],
    "PUNËS": [
        "punëtor", "punëdhënës", "pagë", "kontratë pune", "shkarkim",
        "largim nga puna", "trust", "pension", "orë shtesë", "diskriminim në punë"
    ],
    "KOMERCIAL": [
        "tregtar", "kompani", "biznes", "ortakëri", "falimentim",
        "gjykatë komerciale", "shoqëri tregtare", "aksione", "shpk", "sha"
    ],
    "ADMINISTRATIV": [
        "administrativ", "ministri", "komunë", "leje", "licencë",
        "vendim administrativ", "konflikt administrativ", "inspektorat"
    ],
    "KUSHTETUES": [
        "kushtetues", "kushtetutë", "liri themelore", "të drejtat e njeriut",
        "gjykata kushtetuese", "proces i rregullt ligjor"
    ]
}

# ========== LIGJET KRYESORE SIPAS DOMENIT NË KOSOVË ==========
DOMAIN_LAWS = {
    "FAMILJAR": ["Ligji për Familjen i Kosovës (Nr. 2004/32)", "Ligji për Mbrojtje nga Dhuna në Familje", "LPK (Nr. 03/L-006)"],
    "PENAL": ["Kodi i Procedurës Penale (KPPRK Nr. 08/L-032)", "Kodi Penal (KPRK Nr. 06/L-074)"],
    "CIVIL": ["Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006)", "Ligji për Detyrimet (LMD Nr. 04/L-077)"],
    "PRONËSOR": ["Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (Nr. 03/L-154)", "Ligji për Kadastër"],
    "PUNËS": ["Ligji i Punës i Kosovës (Nr. 03/L-212)", "Ligji për Sigurinë dhe Shëndetin në Punë"],
    "KOMERCIAL": ["Ligji për Gjykatën Komerciale (Nr. 08/L-015)", "Ligji për Shoqëritë Tregtare (Nr. 06/L-016)"],
    "ADMINISTRATIV": ["Ligji për Procedurën e Përgjithshme Administrative (LPPA)", "Ligji për Konfliktet Administrative (Nr. 03/L-202)"],
    "KUSHTETUES": ["Kushtetuta e Republikës së Kosovës", "Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)"]
}


class BasePillarService:
    """Shërbimi Bazë Universal — V30.0 me Protokollin e Gjykatës Supreme"""

    @staticmethod
    def detect_case_domain(case_title: str = "", context_str: str = "", manifest_str: str = "") -> str:
        combined_text = f"{case_title} {context_str[:6000]} {manifest_str[:2000]}".lower()
        domain_scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in combined_text)
            domain_scores[domain] = score
        
        best_domain = max(domain_scores, key=domain_scores.get)
        if domain_scores[best_domain] == 0:
            return "CIVIL"
        return best_domain

    @staticmethod
    def get_domain_laws(case_domain: str) -> List[str]:
        return DOMAIN_LAWS.get(case_domain, DOMAIN_LAWS["CIVIL"])

    @staticmethod
    def build_rag_truth_rule() -> str:
        return """
🚨 RREGULLI THELBËSOR I SË VËRTETËS FAKTIKE:
1. Faktet, datat, deklarimet dhe pretendimet merren VETËM nga shkresat e fashikullit të lëndës.
2. Zbato legjislacionin në fuqi të Republikës së Kosovës me saktësi absolute neni-për-nen.
3. Nëse një fakt apo provë MUNGON në shkresa, deklaro shprehimisht: "[E pa-dokumentuar në shkresa]".
4. ZERO halucinacione. Ndalohet kategorikisht shpikja e provave ose rrethanave të paqena.
"""
    
    @staticmethod
    def build_precedent_instruction() -> str:
        return """
⚖️ PROTOKOLLI I PRECEDENTËVE DHE VENDIMEVE GJYQËSORE:
- Cito vendimet, aktgjykimet dhe numrat e lëndëve që gjenden brenda dokumenteve të fashikullit ose në praktikën gjyqësore të verifikuar të Kosovës.
- Ndalohet shpikja e numrave fiktivë të aktgjykimeve.
"""

    @staticmethod
    def build_supreme_judge_protocol() -> str:
        return """
🏛️ PROTOKOLLI I ANALIZËS SË GJYQTARIT SUPREM:
Ti vepron me autoritetin dhe thellësinë e një Gjyqtari Suprem. Kur shqyrton fashikullin:

1. KRONOLOGJIA DHE KRYQËZIMI:
   - Rendit ngjarjet sipas datave reale dhe zbulo mospërputhjet midis deklaratave të palëve.
   
2. ANALIZA E INSTITUCIONEVE:
   - Vlerëso nëse Policia, Qendra për Punë Sociale (QPS) apo Ekspertët kanë qenë objektivë apo kanë shfaqur njëanshmëri dhe shkelje procedurale.

3. FUQIA E PROVAVE:
   - Ndaj provat vendimtare (shkresat zyrtare, audiot, mesazhet e pakontestueshme) nga thashethemet dhe pretendimet e pabazuara.

4. MBROJTJA E TË DREJTAVE TË KLIENTIT:
   - Trego saktësisht ku janë shkelur të drejtat ligjore të klientit dhe si duhet të mbrohet me forcë në seancë.
"""
    
    @staticmethod
    def get_rag_context(
        user_id: str = "",
        case_id: str = "",
        query_text: str = "",
        n_results: int = 35
    ) -> Tuple[str, str]:
        global_rag_context = ""
        case_rag_context = ""
        
        try:
            from app.services.vector_store_service import (
                query_global_knowledge_base,
                query_case_knowledge_base
            )
            
            if query_text:
                global_results = query_global_knowledge_base(query_text, n_results=n_results)
                if global_results:
                    global_parts = []
                    for res in global_results:
                        source = res.get("source", "Baza Ligjore e Kosovës")
                        text = res.get("text", "").strip()
                        if text:
                            global_parts.append(f"📌 [{source}]:\n{text}")
                    global_rag_context = "\n\n".join(global_parts)
            
            if user_id and query_text:
                case_results = query_case_knowledge_base(user_id, query_text, n_results=n_results, case_id=case_id)
                if case_results:
                    case_parts = []
                    for res in case_results:
                        source = res.get("source", "Dokument i Lëndës")
                        text = res.get("text", "").strip()
                        if text:
                            case_parts.append(f"📄 [{source}]:\n{text}")
                    case_rag_context = "\n\n".join(case_parts)
                    
        except ImportError as e:
            logger.warning(f"⚠️ [RAG] nuk u importua: {e}")
        except Exception as e:
            logger.error(f"❌ [RAG] Gabim: {e}")
        
        return global_rag_context, case_rag_context

    @staticmethod
    def get_timeline_context(db: Any, case_id: str, user_id: str = "") -> str:
        try:
            from app.services.pillars.timeline_service import TimelineService
            timeline_data = TimelineService.build_case_timeline(db, case_id, user_id)
            return TimelineService.build_timeline_prompt(timeline_data)
        except ImportError:
            return ""
        except Exception as e:
            logger.error(f"❌ [Timeline] Gabim: {e}")
            return ""

    @staticmethod
    def get_role_guard(role: str, client_name: str) -> str:
        try:
            from app.services.pillars.role_guard_service import RoleGuardService
            return RoleGuardService.build_role_guard(role, client_name)
        except ImportError:
            return ""

    @staticmethod
    def get_role_tone(role: str) -> str:
        try:
            from app.services.pillars.role_guard_service import RoleGuardService
            return RoleGuardService.get_role_specific_tone(role)
        except ImportError:
            return ""

    @staticmethod
    def build_base_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str,
        case_domain: str = "",
        rag_context: str = "",
        case_rag_context: str = "",
        timeline_context: str = ""
    ) -> str:
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        rag_truth_rule = BasePillarService.build_rag_truth_rule()
        precedent_instruction = BasePillarService.build_precedent_instruction()
        supreme_protocol = BasePillarService.build_supreme_judge_protocol()
        role_guard = BasePillarService.get_role_guard(client_position, client_name)
        role_tone = BasePillarService.get_role_tone(client_position)
        
        return f"""
{rag_truth_rule}

{precedent_instruction}

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I LËNDËS:
LËMIA: **{case_domain}** | KLIENTI: **{client_name}** | POZICIONI: **{(client_position or 'DEFENDANT').upper()}** | TITULLI: **{case_title}** | DATA: {current_date_str}

{role_tone}

📅 KRONOLOGJIA E DOKUMENTUAR E RASTIT:
{timeline_context if timeline_context else "Kronologjia po gjenerohet nga dokumentet e fashikullit."}

📚 BAZA LIGJORE DHE STATUTORE (KOSOVË):
{rag_context if rag_context else "Referencat statutore nga legjislacioni në fuqi."}

📄 SHKRESAT DHE PROVAT E LËNDËS:
{case_rag_context if case_rag_context else "Dokumentet e fashikullit të lëndës."}

📎 PASAPORTA E DOKUMENTEVE TË ADMINISTRUARA:
{manifest_str}

📎 PËRMBAJTJA E PLOTË E DOKUMENTEVE:
{context_str}
"""