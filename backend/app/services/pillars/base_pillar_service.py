# FILE: backend/app/services/pillars/base_pillar_service.py
# PHOENIX PROTOCOL - BASE PILLAR SERVICE V131.0 (STREAM-OPTIMIZED • DYNAMIC KOSOVO JURISPRUDENCE • ZERO HARDCODING)
# 100% COMPLETE CODE • BALANCED RAG DENSITY • FAST TOKEN PIPELINE

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Spirancat Institucionale për zbulim autonom të lëmisë dhe departamentit nga shkresat
INSTITUTIONAL_ANCHORS = {
    "KOMERCIALE": [
        "gjykata komerciale", "gjykatës komerciale", "dhomat e shkallës së parë", 
        "departamenti për çështje ekonomike", "shoqëri tregtare", "shoqëria tregtare", 
        "sh.p.k.", "shpk", "nui:", "aksionar", "ortak", "arbk", "kontratë tregtare",
        "falimentim", "kreditë tregtare", "faturë", "garanci bankare"
    ],
    "PENALE": [
        "prokuroria speciale", "prokurorisë speciale", "prokuroria themelore", 
        "departamenti i krimeve të rënda", "departamenti special", "departamenti i përgjithshëm penal",
        "kallëzim penal", "aktakuzë", "aktakuze", "vepër penale", 
        "paraburgim", "kpprk", "kprk", "kodi penal", "psrk", "shqyrtim fillestar"
    ],
    "ADMINISTRATIVE": [
        "konflikt administrativ", "vendim administrativ", "departamenti për çështje administrative",
        "ministria", "komuna", "inspektorati", "lppa", "prokurim publik", "oshp", "atk"
    ],
    "PUNËS": [
        "kontratë pune", "marrëdhënie pune", "shkarkim nga puna", "largim nga puna",
        "inspektorati i punës", "pagë", "paga e papaguar", "pushim vjetor"
    ],
    "FAMILJARE": [
        "shkurorëzim", "divorc", "kujdestaria e fëmijës", "alimentacion", 
        "qendra për punë sociale", "qps", "dhunë në familje", "urdhër mbrojtje", "urdher mbrojtes",
        "divizioni familjar", "besimi i fëmijëve"
    ],
    "PRONËSORE": [
        "pengim posedimi", "vërtetim pronësie", "kadastër", "kadaster", "uzurpim", 
        "e drejta sendore", "lpts", "bashkëpronësi", "servitut", "paluajtshmëri", "pjesëtim fizik"
    ],
    "KUSHTETUESE": [
        "gjykata kushtetuese", "kërkesë kushtetuese", "neni 31 i kushtetutës", 
        "neni 54 i kushtetutës", "kednj", "liri themelore", "shkelje e të drejtave të njeriut"
    ],
    "CIVILE": [
        "kërkesëpadi", "padi civile", "dëmshpërblim", "lmd", "lpk", 
        "procedurë kontestimore", "borxh", "përmbarim", "përmbarues", "divizioni civil"
    ]
}

DOMAIN_KEYWORDS = {
    "KOMERCIALE": ["tregtar", "biznes", "ortakëri", "aksione", "furnizim", "transaksion komercial"],
    "PENALE": ["mashtrim", "vjedhje", "kanosje", "kërcënim", "falsifikim", "keqpërdorim i detyrës", "korrupsion", "hetime"],
    "ADMINISTRATIVE": ["leje ndërtimi", "licencë", "shërbim civil", "rekrutim publik", "akt administrativ"],
    "PUNËS": ["punëtor", "punëdhënës", "trust", "pension", "diskriminim në punë"],
    "FAMILJARE": ["bashkëshort", "kontaktet me fëmijën", "interesi më i mirë i fëmijës", "martesë"],
    "PRONËSORE": ["pronë", "tokë", "shtëpi", "banesë", "apartament", "hipotekë", "posedim", "pjesëtim"],
    "KUSHTETUESE": ["kushtetutë", "proces i rregullt ligjor", "të drejtat e njeriut"],
    "CIVILE": ["detyrim", "kompensim", "dëm material", "dëm jomaterial", "masë e përkohshme", "kamata ligjore"]
}

STATUTORY_CORPUS = {
    "KOMERCIALE": [
        "Ligji për Gjykatën Komerciale (Nr. 08/L-015)",
        "Ligji për Shoqëritë Tregtare (Nr. 06/L-016)",
        "Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)",
        "Praktika Gjyqësore e Dhomave të Shkallës së Dytë të Gjykatës Komerciale"
    ],
    "PENALE": [
        "Kodi Penal i Republikës së Kosovës (KPK Nr. 06/L-074)",
        "Kodi i Procedurës Penale i Republikës së Kosovës (KPPRK Nr. 08/L-032)",
        "Ligji për Prokurorinë Speciale të Republikës së Kosovës (PSRK Nr. 03/L-052)",
        "Praktika Gjyqësore e Kolegjit Penal të Gjykatës Supreme të Kosovës (Aktgjykimet PML)"
    ],
    "ADMINISTRATIVE": [
        "Ligji për Procedurën e Përgjithshme Administrative (LPPA Nr. 05/L-031)",
        "Ligji për Konfliktet Administrative (Nr. 03/L-202)",
        "Ligji për Prokurimin Publik në Kosovë (Nr. 04/L-042)",
        "Praktika Gjyqësore e Kolegjit Administrativ të Gjykatës Supreme"
    ],
    "PUNËS": [
        "Ligji i Punës i Republikës së Kosovës (Nr. 03/L-212)",
        "Ligji për Mbrojtjen nga Diskriminimi (Nr. 05/L-021)",
        "Praktika e Gjykatës Supreme mbi Marrëdhëniet e Punës dhe Dëmshpërblimin"
    ],
    "FAMILJARE": [
        "Ligji për Familjen i Kosovës (Nr. 2004/32)",
        "Ligji për Parandalimin dhe Mbrojtjen nga Dhuna në Familje (Nr. 08/L-185)",
        "Kodi i Drejtësisë për të Mitur (Nr. 06/L-006)",
        "Jurisprudenca e Gjykatës Supreme në Çështjet Familjare"
    ],
    "PRONËSORE": [
        "Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (LPTS Nr. 03/L-154)",
        "Ligji për Kadastër të Pronës së Paluajtshme (Nr. 04/L-013)",
        "Ligji për Procedurën Jashtëkontestimore (Nr. 03/L-007)",
        "Praktika Gjyqësore e Gjykatës Supreme për Çështjet Pronësore dhe Posedimore"
    ],
    "KUSHTETUESE": [
        "Kushtetuta e Republikës së Kosovës (Nenet 31, 53, 54)",
        "Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)",
        "Jurisprudenca e Gjykatës Kushtetuese të Kosovës dhe GJEDNJ-së"
    ],
    "CIVILE": [
        "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006)",
        "Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)",
        "Ligji për Procedurën Përmbarimore (LPP Nr. 04/L-139)",
        "Praktika Gjyqësore e Kolegjit Civil të Gjykatës Supreme të Kosovës (Aktgjykimet Rev)"
    ]
}


class BasePillarService:
    """Shërbimi Bazë Universal — V131.0 me Zbulim Autonom Hibrid dhe RAG të Optimizuar."""

    @staticmethod
    def detect_case_domain(case_title: str = "", context_str: str = "", manifest_str: str = "") -> str:
        """
        Zbulon autonomisht lëminë kryesore nga përmbajtja reale e shkresave të fashikullit.
        Zero hardcoding: Llogarit peshat reale institucionale pa paragjykuar.
        """
        combined_text = f"{case_title} {manifest_str[:3000]} {context_str[:15000]}".lower()

        scores: Dict[str, int] = {d: 0 for d in INSTITUTIONAL_ANCHORS}

        for domain, anchors in INSTITUTIONAL_ANCHORS.items():
            for anchor in anchors:
                if anchor in combined_text:
                    scores[domain] += 3

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in combined_text:
                    scores[domain] += 1

        sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_domain, top_score = sorted_domains[0]
        second_domain, second_score = sorted_domains[1]

        if top_score == 0:
            return "CIVILE"

        # Zbulim hibrid nëse lëmia e dytë është e rëndësishme (p.sh. Penale / Civile)
        if second_score >= 6 and (second_score / top_score) >= 0.45:
            return f"{top_domain} / {second_domain}"

        return top_domain

    @staticmethod
    def get_domain_laws(case_domain: str) -> List[str]:
        collected_laws: List[str] = []
        domain_upper = (case_domain or "CIVILE").upper()

        for key, laws in STATUTORY_CORPUS.items():
            if key in domain_upper:
                for law in laws:
                    if law not in collected_laws:
                        collected_laws.append(law)

        if not collected_laws:
            collected_laws = STATUTORY_CORPUS["CIVILE"]

        return collected_laws

    @staticmethod
    def build_supreme_jurisprudence_directive(case_domain: str) -> str:
        return f"""UDHËZUES I JURISPRUDENCËS SUPREME ({case_domain}):
1. Zbatoni precedentët e konsoliduar të Gjykatës Supreme të Kosovës (Aktgjykimet PML dhe Revizionet).
2. Arsyetoni saktë normat procedurale dhe materiale të lëmisë.
3. Identifikoni shkeljet e ligjit dhe kontradiktat në aktet e administruara."""

    @staticmethod
    def get_rag_context(
        user_id: str = "",
        case_id: str = "",
        query_text: str = "",
        n_results: int = 8  # Optimizuar nga 35 në 8 për streaming të shpejtë pa ndërprerje
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
                        source = res.get("source", "Precedent Suprem")
                        text = res.get("text", "").strip()
                        if text:
                            # Kufizohet gjatësia për të mos bllokuar memorjen e transmetimit
                            global_parts.append(f"[{source}]: {text[:800]}")
                    global_rag_context = "\n\n".join(global_parts)
            
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
                            case_parts.append(f"[{source}]: {text[:800]}")
                    case_rag_context = "\n\n".join(case_parts)
                    
        except ImportError as e:
            logger.warning(f"[RAG] Vector store import error: {e}")
        except Exception as e:
            logger.error(f"[RAG] Vector query error: {e}")
        
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
            logger.error(f"[Timeline] Error: {e}")
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