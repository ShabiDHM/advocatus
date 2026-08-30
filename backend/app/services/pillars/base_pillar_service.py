# FILE: backend/app/services/pillars/base_pillar_service.py
# PHOENIX PROTOCOL - BASE PILLAR SERVICE V6.0 (SUPREME JUDGE PROTOCOL)

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ========== KONSTANTET E DOMENEVE ==========
DOMAIN_KEYWORDS = {
    "PENAL": [
        "kallëzim penal", "vepër penale", "prokurori", "kpprk", "kprk",
        "mashtrim", "vjedhje", "dhunë", "kërcënim", "falsifikim",
        "lajmërim i rremë", "dëmtim i rëndë trupor", "armë", "drogë",
        "trafikim", "korrupsion", "shpëlarje parash"
    ],
    "CIVIL": [
        "kërkesëpadi", "padi", "kundërpadi", "prapësim", "lpk", "lmd",
        "dëmshpërblim", "kontratë", "borxh", "detyrim", "kompensim",
        "dëm material", "dëm jomaterial", "shkelje e kontratës"
    ],
    "KOMERCIAL": [
        "tregtar", "kompani", "biznes", "ortakëri", "falimentim",
        "gjykatë komerciale", "shoqëri tregtare", "aksion", "pjesëmarrje"
    ],
    "PRONËSOR": [
        "pronë", "tokë", "shtëpi", "apartament", "kadastër",
        "hipotekë", "posedim", "servitut", "ndërtim pa leje"
    ],
    "PUNËS": [
        "punëtor", "punëdhënës", "pagë", "kontratë pune", "shkarkim",
        "largim nga puna", "trust", "pension", "sigurim shëndetësor"
    ],
    "FAMILJAR": [
        "bashkëshort", "divorc", "kujdestari", "birësim", "ushqim",
        "familje", "fëmijë", "trashëgimi", "testament"
    ],
    "ADMINISTRATIV": [
        "administrativ", "ministri", "komunë", "leje", "licencë",
        "vendim administrativ", "konflikt administrativ", "institucion publik"
    ],
    "KUSHTETUES": [
        "kushtetues", "kushtetutë", "liri themelore", "të drejtat e njeriut",
        "diskriminim", "barazi", "gjykata kushtetuese"
    ]
}

# ========== LIGJET SIPAS DOMENIT ==========
DOMAIN_LAWS = {
    "PENAL": ["KPPRK (Nr. 08/L-032)", "KPRK (Nr. 06/L-074)"],
    "CIVIL": ["LPK (Nr. 03/L-006)", "LMD (Nr. 04/L-077)"],
    "KOMERCIAL": ["Ligji për Gjykatën Komerciale (Nr. 08/L-015)", "Ligji për Shoqëritë Tregtare"],
    "PRONËSOR": ["Ligji për Pronësinë (Nr. 03/L-154)", "Ligji për Kadastër"],
    "PUNËS": ["Ligji i Punës (Nr. 03/L-212)", "Ligji për Sigurime Pensionale"],
    "FAMILJAR": ["Ligji për Familjen (Nr. 2004/32)", "Ligji për Trashëgiminë"],
    "ADMINISTRATIV": ["Ligji për Konfliktet Administrative (Nr. 03/L-202)", "LPA"],
    "KUSHTETUES": ["Kushtetuta e Kosovës", "Ligji për Gjykatën Kushtetuese"]
}

# ========== PRECEDENTËT E VERIFIKUAR ==========
VERIFIED_PRECEDENTS = [
    "PML.nr.682/2024",
    "PML.nr.429/2025",
    "Rev.nr.240/2024",
    "Rev.Nr.541/2024",
    "PML.Nr.185/2025"
]


class BasePillarService:
    """Shërbimi Bazë Universal — V6.0 me Protokollin e Gjyqtarit Suprem"""

    @staticmethod
    def detect_case_domain(case_title: str = "", context_str: str = "", manifest_str: str = "") -> str:
        combined_text = f"{case_title} {context_str[:5000]} {manifest_str[:2000]}".lower()
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
🚨 RREGULLI ABSOLUT #0 — BURIMI I VETËM I SË VËRTETËS:
Ti je "Sokrati" — Gjyqtar Suprem i Kosovës. Ti NUK ke asnjë njohuri ligjore përveç RAG context.

1. NËSE një nen, ligj, precedent NUK gjendet në RAG context — NUK ekziston për ty;
2. TI JE I DETYRUAR të përdorësh VETËM atë që është në RAG context;
3. TI JE I DETYRUAR të thuash "Nuk u gjet në bazën tonë" nëse diçka mungon;
4. HALucinacioni është i NDALUAR KATEGORIKISHT.
"""
    
    @staticmethod
    def build_precedent_instruction() -> str:
        precedents_str = ", ".join(VERIFIED_PRECEDENTS)
        return f"""
🚨 RREGULLI ABSOLUT #1 — PRECEDENTËT E LEJUAR:
VETËM këto: {precedents_str}
NËSE një precedent NUK është në listë — NDALOHET ta citoni.
"""

    @staticmethod
    def build_verification_instruction() -> str:
        return """
🚨 RREGULLI ABSOLUT #2 — VERIFIKIMI I NENEVE:
Kontrollo në RAG context para se të citosh ndonjë Nen ose paragraf.
"""

    @staticmethod
    def build_supreme_judge_protocol() -> str:
        """
        PHOENIX FIX V6.0: Protokolli i plotë i Gjyqtarit Suprem.
        """
        return """
🚨 RREGULLI ABSOLUT #3 — PROTOKOLLI I GJYQTARIT SUPREM:
Ti je Gjyqtari më me përvojë i Gjykatës Supreme të Kosovës. Fashikulli është në tavolinën tënde.

NDIQ KËTË PROTOKOLL SAKTËSISHT:

📋 HAPI 1 — LEXO ÇDO DOKUMENT NË REND KRONOLOGJIK:
- Renditi të gjitha shkresat sipas datës
- Lexo nga më e vjetra te më e reja
- Shëno: datën, dokumentin, palët, vendimin
- Kërko: Rrjedhën kohore të ngjarjeve

📋 HAPI 2 — KRAHASO DATAT DHE DOKUMENTET:
- A përputhen datat në procesverbale me seancat?
- A ka dokumente me data të njëjta por përmbajtje të ndryshme?
- A ka nënshkrime që mungojnë?
- A ka vula që nuk përputhen?
- A ka numra lëndësh që nuk korrespondojnë?
- Kërko: Prapadatime, falsifikime, mospërputhje

📋 HAPI 3 — VERIFIKO LIGJSHMËRINË E ÇDO VENDIMI:
- A është vendimi i bazuar në ligjin e saktë?
- A janë cituar nenet e sakta?
- A janë respektuar afatet?
- A u dëgjuan të dyja palët?
- A u vlerësuan të gjitha provat?
- Kërko: Shkelje procedurale, zbatim të gabuar, injorim provash

📋 HAPI 4 — KONTROLLO PROVAT:
- A u administruan të gjitha provat materiale?
- A u vlerësuan provat shkencore?
- A u morën parasysh provat shfajësuese?
- A ka prova që u refuzuan pa arsye?
- Kërko: Prova të injoruara, prova të manipuluara, ekspertiza të njëanshme

📋 HAPI 5 — IDENTIFIKO VEPRIMET PENALE:
- A ka elemente të falsifikimit? (Neni 427 KPRK)
- A ka keqpërdorim të pozitës? (Neni 414 KPRK)
- A ka ushtrim të ndikimit? (Neni 424 KPRK)
- A ka shkelje të rehabilitimit? (Neni 96 KPRK)
- A ka nxjerrje të kundërligjshme vendimesh? (Neni 425 KPRK)
- Kërko: Çdo veprim që përbën vepër penale

📋 HAPI 6 — VLERËSO QËNDRUESHMËRINË:
- A qëndron ky vendim para trupit gjykues?
- A ka bazë për ankim?
- A ka bazë për kallëzim penal?
- Cilat janë shkeljet më të rënda?

📋 HAPI 7 — JEP OPINIONIN PËRFUNDIMTAR:
- Përmbledh shkeljet e gjetura
- Kualifiko ligjërisht çdo shkelje
- Rekomando hapat e ardhshëm
- Trego çfarë duhet të bëjë pala

BAZOHU VETËM në atë që sheh në dokumente — MOS supozo asgjë.
"""
    
    @staticmethod
    def get_rag_context(
        user_id: str = "",
        case_id: str = "",
        query_text: str = "",
        n_results: int = 20
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
                        source = res.get("source", "Burim ligjor")
                        text = res.get("text", "").strip()
                        if text:
                            global_parts.append(f"📌 {source}:\n{text}")
                    global_rag_context = "\n\n".join(global_parts)
            
            if user_id and query_text:
                case_results = query_case_knowledge_base(user_id, query_text, n_results=n_results, case_id=case_id)
                if case_results:
                    case_parts = []
                    for res in case_results:
                        source = res.get("source", "Dokument i lëndës")
                        text = res.get("text", "").strip()
                        if text:
                            case_parts.append(f"📄 {source}:\n{text}")
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
        verification_instruction = BasePillarService.build_verification_instruction()
        supreme_protocol = BasePillarService.build_supreme_judge_protocol()
        role_guard = BasePillarService.get_role_guard(client_position, client_name)
        role_tone = BasePillarService.get_role_tone(client_position)
        
        return f"""
{rag_truth_rule}

{precedent_instruction}

{verification_instruction}

{supreme_protocol}

{role_guard}

📋 KONTEKSTI I LËNDËS:
DEGË: {case_domain} | KLIENTI: **{client_name}** | ROLI: **{(client_position or 'DEFENDANT').upper()}** | LËNDA: **{case_title}** | DATA: {current_date_str}

{role_tone}

📅 KRONOLOGJIA E RASTIT:
{timeline_context if timeline_context else "Nuk u ndërtua kronologjia."}

📚 RAG — BAZA STATUTORE (BURIMI YT I VETËM):
{rag_context if rag_context else "Nuk u gjet asnjë referencë në bazën statutore."}

📄 RAG — DOKUMENTET E ÇËSHTJES:
{case_rag_context if case_rag_context else "Nuk u gjetën dokumente shtesë."}

📎 PASAPORTA E SHKRESAVE:
{manifest_str}

📎 DOKUMENTET E PLOTA:
{context_str}
"""