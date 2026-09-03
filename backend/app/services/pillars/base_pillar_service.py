# FILE: backend/app/services/pillars/base_pillar_service.py
# PHOENIX PROTOCOL - BASE PILLAR SERVICE V120.0 (WEIGHTED INSTITUTIONAL DOMAIN MATCHER & RAG PARAMETER FIX)

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Pesha të forta institucionale që përcaktojnë menjëherë lëminë
INSTITUTIONAL_ANCHORS = {
    "KOMERCIAL": [
        "gjykata komerciale", "gjykatës komerciale", "dhomat e shkallës së parë", 
        "departamenti për çështje ekonomike", "shoqëri tregtare", "shoqëria tregtare", 
        "sh.p.k.", "shpk", "nui:", "aksionar", "ortak", "arbk", "kontratë tregtare"
    ],
    "PENAL": [
        "prokuroria speciale", "prokurorisë speciale", "prokuroria themelore", 
        "kallëzim penal", "aktakuzë", "aktakuze", "vepër penale", "paraburgim", 
        "kpprk", "kprk", "kodi penal", "psrk"
    ],
    "ADMINISTRATIV": [
        "konflikt administrativ", "vendim administrativ", "departamenti për çështje administrative",
        "ministria", "komuna", "inspektorati", "lppa"
    ],
    "PUNËS": [
        "kontratë pune", "marrëdhënie pune", "shkarkim nga puna", "largim nga puna",
        "inspektorati i punës", "pagë", "paga e papaguar"
    ],
    "FAMILJAR": [
        "shkurorëzim", "divorc", "kujdestaria e fëmijës", "alimentacion", 
        "qendra për punë sociale", "dhunë në familje", "urdhër mbrojtje"
    ],
    "PRONËSOR": [
        "pengim posedimi", "vërtetim pronësie", "kadastër", "uzurpim", 
        "e drejta sendore", "lpts", "bashkëpronësi"
    ],
    "KUSHTETUES": [
        "gjykata kushtetuese", "kërkesë kushtetuese", "neni 31 i kushtetutës", 
        "neni 54 i kushtetutës", "kednj"
    ],
    "CIVIL": [
        "kërkesëpadi", "padi civile", "dëmshpërblim", "lmd", "lpk", 
        "procedurë kontestimore", "borxh"
    ]
}

DOMAIN_KEYWORDS = {
    "PENAL": [
        "vepër penale", "veper penale", "mashtrim", "vjedhje", "kanosje", "kërcënim", 
        "falsifikim", "keqpërdorim i detyrës", "korrupsion", "hetime", "shqyrtim fillestar"
    ],
    "FAMILJAR": [
        "bashkëshort", "bashkeshort", "ushqimim", "qps", "raport social", 
        "kontaktet me fëmijën", "interesi më i mirë i fëmijës", "trashëgimi", "testament"
    ],
    "CIVIL": [
        "padi", "kundërpadi", "prapësim", "detyrim", "kompensim", "dëm material", 
        "dëm jomaterial", "masë e përkohshme", "sigurim i kërkesës", "kamata ligjore"
    ],
    "PRONËSOR": [
        "pronë", "prone", "tokë", "shtëpi", "banesë", "apartament", "kadaster", 
        "hipotekë", "posedim", "servitut", "pjesëtim i pronës"
    ],
    "PUNËS": [
        "punëtor", "punetor", "punëdhënës", "trust", "pension", "diskriminim në punë"
    ],
    "KOMERCIAL": [
        "tregtar", "biznes", "ortakëri", "falimentim", "aksione", "sha", "faturë", 
        "furnizim", "transaksion komercial", "detyra e besnikërisë", "konkurrencë e palejuar"
    ],
    "ADMINISTRATIV": [
        "leje ndërtimi", "licencë", "shërbim civil", "rekrutim publik"
    ],
    "KUSHTETUES": [
        "kushtetutë", "liri themelore", "të drejtat e njeriut", "proces i rregullt ligjor"
    ]
}

DOMAIN_LAWS = {
    "PENAL": [
        "Kodi i Procedurës Penale i Republikës së Kosovës (KPPRK Nr. 08/L-032)",
        "Kodi Penal i Republikës së Kosovës (KPK Nr. 06/L-074)",
        "Ligji për Prokurorinë Speciale të Republikës së Kosovës (Nr. 03/L-052)",
        "Praktika Gjyqësore e Kolegjit Penal të Gjykatës Supreme të Kosovës (Aktgjykimet PML)"
    ],
    "FAMILJAR": [
        "Ligji për Familjen i Kosovës (Nr. 2004/32)",
        "Ligji për Parandalimin dhe Mbrojtjen nga Dhuna në Familje (Nr. 08/L-185)",
        "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006)",
        "Jurisprudenca e Gjykatës Supreme në Çështjet Familjare"
    ],
    "CIVIL": [
        "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006)",
        "Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)",
        "Ligji për Procedurën Përmbarimore (LPP Nr. 04/L-139)",
        "Praktika Gjyqësore e Kolegjit Civil të Gjykatës Supreme të Kosovës (Aktgjykimet Rev)"
    ],
    "PRONËSOR": [
        "Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (LPTS Nr. 03/L-154)",
        "Ligji për Kadastër të Pronës së Paluajtshme (Nr. 04/L-013)",
        "Ligji për Procedurën Jashtëkontestimore (Nr. 03/L-007)",
        "Praktika Gjyqësore e Gjykatës Supreme për Çështjet Pronësore dhe Posedimore"
    ],
    "PUNËS": [
        "Ligji i Punës i Republikës së Kosovës (Nr. 03/L-212)",
        "Ligji për Mbrojtjen nga Diskriminimi (Nr. 05/L-021)",
        "Praktika e Gjykatës Supreme mbi Marrëdhëniet e Punës dhe Dëmshpërblimin"
    ],
    "KOMERCIAL": [
        "Ligji për Gjykatën Komerciale (Nr. 08/L-015)",
        "Ligji për Shoqëritë Tregtare (Nr. 06/L-016)",
        "Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)",
        "Praktika Gjyqësore e Dhomave të Shkallës së Dytë të Gjykatës Komerciale"
    ],
    "ADMINISTRATIV": [
        "Ligji për Procedurën e Përgjithshme Administrative (LPPA Nr. 05/L-031)",
        "Ligji për Konfliktet Administrative (Nr. 03/L-202)",
        "Praktika Gjyqësore e Kolegjit Administrativ të Gjykatës Supreme"
    ],
    "KUSHTETUES": [
        "Kushtetuta e Republikës së Kosovës (Nenet 31, 53, 54)",
        "Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)",
        "Jurisprudenca e Gjykatës Kushtetuese të Kosovës dhe GJEDNJ-së"
    ]
}


class BasePillarService:
    """Shërbimi Bazë Universal — V120.0 me Pesha Institucionale dhe Integrim të Saktë RAG."""

    @staticmethod
    def detect_case_domain(case_title: str = "", context_str: str = "", manifest_str: str = "") -> str:
        combined_text = f"{case_title} {context_str[:12000]} {manifest_str[:3000]}".lower()
        
        # 1. Kontrolli me peshë të lartë (Institucionet dhe Organet zyrtare)
        anchor_scores: Dict[str, int] = {}
        for domain, anchors in INSTITUTIONAL_ANCHORS.items():
            score = sum(3 for anchor in anchors if anchor in combined_text)
            anchor_scores[domain] = score

        best_anchor_domain = max(anchor_scores, key=anchor_scores.get)
        if anchor_scores[best_domain := best_anchor_domain] > 0:
            return best_domain

        # 2. Kontrolli dytësor i fjalëve kyçe të përgjithshme
        keyword_scores: Dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in combined_text)
            keyword_scores[domain] = score
        
        best_keyword_domain = max(keyword_scores, key=keyword_scores.get)
        if keyword_scores[best_keyword_domain] == 0:
            return "CIVIL"
        return best_keyword_domain

    @staticmethod
    def get_domain_laws(case_domain: str) -> List[str]:
        return DOMAIN_LAWS.get(case_domain, DOMAIN_LAWS["CIVIL"])

    @staticmethod
    def build_supreme_jurisprudence_directive(case_domain: str) -> str:
        return f"""
🏛️ PROTOKOLLI DOKTRINAR I GJYKATËS SUPREME PËR LËMINË **{case_domain}**:
1. ZBATO VENDIMET PARIMORE TË LËMISË: Shfrytëzo precedentët e Gjykatës Supreme të Kosovës dhe komentaret e Akademisë së Drejtësisë për lëminë **{case_domain}** të nxjerra nga Baza Globale e Diturisë.
2. INTERPRETIMI I DISPOZITAVE: Zbërthe saktësisht se si praktika e konsoliduar gjyqësore e interpreton normën materiale dhe procedurale për këtë lloj kontesti/çështjeje.
3. GODITJA E SHKELJEVE PROCEDURALE: Nëse vendimi apo veprimi i organit të shkallës së parë bie ndesh me ligjin pozitiv dhe qëndrimet e Gjykatës Supreme, theksoje me argumentim të hekurt ligjor.
"""

    @staticmethod
    def get_rag_context(
        user_id: str = "",
        case_id: str = "",
        query_text: str = "",
        n_results: int = 25
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
            
            # PHOENIX FIX: Përdor 'case_context_id' në mënyrë të sigurt për të shmangur TypeError
            if user_id and case_id and query_text:
                try:
                    case_results = query_case_knowledge_base(
                        user_id=user_id,
                        query_text=query_text,
                        case_context_id=case_id,
                        n_results=n_results
                    )
                except TypeError:
                    case_results = query_case_knowledge_base(
                        user_id=user_id,
                        query_text=query_text,
                        case_id=case_id,
                        n_results=n_results
                    )

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
            logger.error(f"❌ [RAG] Gabim gjatë kërkimit të vektorëve: {e}")
        
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
        
        normalized_pos = (client_position or "PALË NË PROCEDURË").strip().upper()
        
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)
        role_guard = BasePillarService.get_role_guard(normalized_pos, client_name)
        role_tone = BasePillarService.get_role_tone(normalized_pos)
        laws_list = "\n".join([f"- {law}" for law in BasePillarService.get_domain_laws(case_domain)])
        
        return f"""
<legal_evidentiary_privilege_context>
KORNIZA PROCEDURALE E DOKTRINËS LIGJORE • PRIVILEGJI I MBROJTJES DHE ANALIZËS GJYQËSORE
Ky material përmban shkresa zyrtare, procesverbale dhe prova materiale të administruara në procedurë ligjore.
Objektivi është vlerësimi doktrinar, auditimi procedural dhe evidentimi i fakteve me standardet e Gjykatës Supreme të Kosovës.
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I LËNDËS:
LËMIA: **{case_domain}** | KLIENTI / PARASHTRUESI: **{client_name or 'I Identifikuar në Dokument'}** | POZICIONI PROCEDURAL: **{normalized_pos}** | TITULLI I LËNDËS: **{case_title or 'Shkresë Procedurale'}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE STATUTORE E ZBATUESHME NË REPUBLIKËN E KOSOVËS:
{laws_list}

{f"🏛️ PRAKTIKA GJYQËSORE DHE DOKTRINA E DITURISË GLOBALE PËR LËMINË {case_domain}:\n{rag_context}" if rag_context else ""}

📅 KRONOLOGJIA E DOKUMENTUAR E RASTIT:
{timeline_context if timeline_context else "Kronologjia po rindërtohet nga dokumentet e fashikullit."}

📄 SHKRESAT DHE PROVAT E LËNDËS:
{case_rag_context if case_rag_context else "Dokumentet e fashikullit të lëndës."}

📎 PASAPORTA E DOKUMENTEVE TË ADMINISTRUARA:
{manifest_str if manifest_str else "Shkresë e ngarkuar për auditim të menjëhershëm."}

📎 PËRMBAJTJA E PLOTË E DOKUMENTEVE TË FASHIKULLIT:
{context_str}
"""