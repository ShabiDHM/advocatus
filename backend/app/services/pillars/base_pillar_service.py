# FILE: backend/app/services/pillars/base_pillar_service.py
# PHOENIX PROTOCOL - BASE PILLAR SERVICE V45.0 (SUPREME COURT JURISPRUDENCE FOUNDATION)

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ========== DOMENET DHE FJALËT KYÇE TË JURISPRUDENCËS SË KOSOVËS ==========
DOMAIN_KEYWORDS = {
    "PENAL": [
        "kallëzim penal", "kallezim penal", "vepër penale", "veper penale", "prokurori", "prokuroria",
        "kpprk", "kprk", "kodi penal", "kodi i procedures penale", "mashtrim", "vjedhje",
        "kanosje", "kërcënim", "falsifikim", "lajmërim i rremë", "dëmtim trupor", "armëmbajtje",
        "keqpërdorim i detyrës", "korrupsion", "ekspertizë psikiatrike forenzike", "paraburgim",
        "aktakuzë", "aktakuze", "hetime", "shqyrtim fillestar", "shqyrtim kryesor"
    ],
    "FAMILJAR": [
        "bashkëshort", "bashkeshort", "divorc", "shkurorëzim", "shkurorezim", "kujdestari",
        "kujdestaria e fëmijës", "alimentacion", "ushqimim", "qps", "qendra për punë sociale",
        "raport social", "kontaktet me fëmijën", "interesi më i mirë i fëmijës", "e drejta prindërore",
        "dhunë në familje", "urdhër mbrojtje", "urdhërmbrojtje", "trashëgimi", "trashëgimtar", "testament"
    ],
    "CIVIL": [
        "kërkesëpadi", "kerkesepadi", "padi", "kundërpadi", "kunderpadi", "prapësim", "prapsim",
        "lpk", "lmd", "procedurë kontestimore", "dëmshpërblim", "demshperblim", "kontratë",
        "borxh", "detyrim", "kompensim", "dëm material", "dëm jomaterial", "masë e përkohshme",
        "sigurim i kërkesës", "përmbarim", "titull ekzekutiv", "kamata ligjore"
    ],
    "PRONËSOR": [
        "pronë", "prone", "tokë", "shtëpi", "banesë", "apartament", "kadastër", "kadaster",
        "hipotekë", "hipoteke", "posedim", "servitut", "ndërtim pa leje", "pengim posedimi",
        "uzurpim", "e drejta sendore", "bashkëpronësi", "pjesëtim i pronës"
    ],
    "PUNËS": [
        "punëtor", "punetor", "punëdhënës", "punedhenes", "pagë", "kontratë pune", "shkarkim",
        "largim nga puna", "trust", "pension", "orë shtesë", "diskriminim në punë",
        "inspektorati i punës", "marrëdhënie pune"
    ],
    "KOMERCIAL": [
        "tregtar", "kompani", "biznes", "ortakëri", "falimentim", "gjykatë komerciale",
        "gjykata komerciale", "shoqëri tregtare", "aksione", "shpk", "sha", "faturë", "fature",
        "kontratë tregtare", "furnizim", "transaksion komercial"
    ],
    "ADMINISTRATIV": [
        "administrativ", "ministri", "komunë", "leje ndërtimi", "licencë", "vendim administrativ",
        "konflikt administrativ", "inspektorat", "lppa", "shërbim civil", "rekrutim publik"
    ],
    "KUSHTETUES": [
        "kushtetues", "kushtetutë", "liri themelore", "të drejtat e njeriut", "gjykata kushtetuese",
        "proces i rregullt ligjor", "neni 31", "neni 54", "kednj", "protokolli 1"
    ]
}

# ========== LIGJET POZITIVE TË REPUBLIKËS SË KOSOVËS ==========
DOMAIN_LAWS = {
    "PENAL": [
        "Kodi i Procedurës Penale i Republikës së Kosovës (KPPRK Nr. 08/L-032)",
        "Kodi Penal i Republikës së Kosovës (KPK Nr. 06/L-074)",
        "Ligji për Bashkëpunim Juridik Ndërkombëtar në Çështjet Penale"
    ],
    "FAMILJAR": [
        "Ligji për Familjen i Kosovës (Nr. 2004/32)",
        "Ligji për Parandalimin dhe Mbrojtjen nga Dhuna në Familje (Nr. 08/L-185)",
        "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006)"
    ],
    "CIVIL": [
        "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006)",
        "Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)",
        "Ligji për Procedurën Përmbarimore (LPP Nr. 04/L-139)"
    ],
    "PRONËSOR": [
        "Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (Nr. 03/L-154)",
        "Ligji për Kadastër të Pronës së Paluajtshme (Nr. 04/L-013)",
        "Ligji për Procedurën Jashtëkontestimore (Nr. 03/L-007)"
    ],
    "PUNËS": [
        "Ligji i Punës i Republikës së Kosovës (Nr. 03/L-212)",
        "Ligji për Mbrojtjen nga Diskriminimi (Nr. 05/L-021)",
        "Ligji për Sigurinë dhe Shëndetin në Punë (Nr. 04/L-161)"
    ],
    "KOMERCIAL": [
        "Ligji për Gjykatën Komerciale (Nr. 08/L-015)",
        "Ligji për Shoqëritë Tregtare (Nr. 06/L-016)",
        "Ligji për Falimentimin (Nr. 05/L-083)"
    ],
    "ADMINISTRATIV": [
        "Ligji për Procedurën e Përgjithshme Administrative (LPPA Nr. 05/L-031)",
        "Ligji për Konfliktet Administrative (Nr. 03/L-202)"
    ],
    "KUSHTETUES": [
        "Kushtetuta e Republikës së Kosovës",
        "Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)",
        "Ligji për Gjykatën Kushtetuese të Kosovës (Nr. 03/L-121)"
    ]
}


class BasePillarService:
    """Shërbimi Bazë Universal — V45.0 me Jurisprudencën e Gjykatës Supreme të Kosovës"""

    @staticmethod
    def detect_case_domain(case_title: str = "", context_str: str = "", manifest_str: str = "") -> str:
        combined_text = f"{case_title} {context_str[:8000]} {manifest_str[:3000]}".lower()
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
🚨 RREGULLI I HEKURT I SË VËRTETËS FAKTIKE DHE PROVUAR:
1. Çdo fakt, datë, deklaratë dhe pretendim merret EKSKLUZIVISHT nga shkresat e fashikullit të lëndës.
2. Zbato legjislacionin në fuqi të Republikës së Kosovës me saktësi absolute neni-për-nen.
3. Nëse një fakt apo provë MUNGON në shkresa, thekso shprehimisht: "[E pa-dokumentuar në shkresat e administruara]".
4. ZERO halucinacione: Ndalohet rreptësisht trillimi i neneve, datave apo provave materiale.
"""
    
    @staticmethod
    def build_precedent_instruction() -> str:
        return """
⚖️ DOKTRINA DHE PRAKTIKA GJYQËSORE E KOSOVËS:
- Mbështetu në parimet udhëzuese dhe mendimet parimore të Gjykatës Supreme të Kosovës, Gjykatës së Apelit dhe Gjykatës Kushtetuese.
- Cito vendime gjyqësore vetëm kur ato pasqyrohen në shkresat e lëndës ose përbëjnë linjë të konsoliduar jurisprudenciale.
"""

    @staticmethod
    def build_supreme_judge_protocol(case_domain: str = "CIVIL") -> str:
        if case_domain == "PENAL":
            return """
🏛️ PROTOKOLLI I GJYQTARIT SUPREM (LËMI PENALE):
1. ELEMENTET E VEPRËS PENALE:
   - Analizo me imtësi figurën e veprës penale (subjekti, objekti, ana subjektive - dashja/pakujdesia, pasoja dhe lidhja shkakësore sipas KPK Nr. 06/L-074).
2. LIGJSHMËRIA E PROVAVE (Neni 257 KPPRK Nr. 08/L-032):
   - Identifiko nëse ka prova të papranueshme, të marra me shkelje të procedurës apo të drejtave të të pandehurit.
3. SHKELJET THELBËSORE TË PROCEDURËS (Neni 384 KPPRK):
   - Zbulo çdo shkelje absolute procedurale që e bën aktakuzën apo aktgjykimin të pavlefshëm.
4. ZINXHIRI I RUAJTJES DHE KUNDËRTHËNIET:
   - Kryqëzo deklaratat në polici, prokurori dhe seanca me procesverbalet zyrtare.
"""
        else:
            return """
🏛️ PROTOKOLLI I GJYQTARIT SUPREM (LËMI CIVILE / KONTIDHJE / FAMILJARE):
1. SHQYRTIMI I PETITUMIT DHE BAZËS JURIDIKE:
   - Vlerëso nëse kërkesëpadia është e qartë, e bazuar në ligj (LMD/LPK/LFK) dhe e përcaktuar me vlerë të saktë.
2. BARRA E PROVËS DHE PESHA E TYRE (Nenet 7, 8 dhe 319 të LPK Nr. 03/L-006):
   - Përcakto saktë cilës palë i takon barra e provës për çdo pretendim dhe a është arritur pragu i provueshmërisë.
3. SHKELJET E PROCEDURËS KONTESTIMORE (Neni 182 i LPK):
   - Zbulo çdo shkelje procedurale që cenon të drejtën për gjykim të drejtë dhe të rregullt.
4. EKZEKUTUESHMËRIA E KËRKESËS:
   - Analizo nëse kërkesa mund të përmbarohet pa pengesa sipas Ligjit për Procedurën Përmbarimore (LPP).
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
            logger.warning(f"⚠️ [RAG] Vector store nuk u importua: {e}")
        except Exception as e:
            logger.error(f"❌ [RAG] Gabim gjatë kërkimit vektorial: {e}")
        
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
            logger.error(f"❌ [Timeline] Gabim gjatë krijimit të kronologjisë: {e}")
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
        supreme_protocol = BasePillarService.build_supreme_judge_protocol(case_domain)
        role_guard = BasePillarService.get_role_guard(client_position, client_name)
        role_tone = BasePillarService.get_role_tone(client_position)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])
        
        return f"""
{rag_truth_rule}

{precedent_instruction}

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I LËNDËS:
LËMIA: **{case_domain}** | KLIENTI: **{client_name}** | POZICIONI: **{(client_position or 'DEFENDANT').upper()}** | TITULLI: **{case_title}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME (KOSOVË):
{laws_list}

{f"📌 KUSHTET DHE NENET E RELEVUESHME NGA BAZA E DITURISË:\n{rag_context}" if rag_context else ""}

📅 KRONOLOGJIA E DOKUMENTUAR E RASTIT:
{timeline_context if timeline_context else "Kronologjia po rindërtohet nga dokumentet e fashikullit."}

📄 SHKRESAT DHE PROVAT E LËNDËS:
{case_rag_context if case_rag_context else "Dokumentet e fashikullit të lëndës."}

📎 PASAPORTA E DOKUMENTEVE TË ADMINISTRUARA:
{manifest_str}

📎 PËRMBAJTJA E PLOTË E DOKUMENTEVE TË FASHIKULLIT:
{context_str}
"""