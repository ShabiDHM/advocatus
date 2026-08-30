# FILE: backend/app/services/pillars/base_pillar_service.py
# PHOENIX PROTOCOL - BASE PILLAR SERVICE V1.0 (UNIVERSAL DOMAIN DETECTION & RAG INTEGRATION)

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
        "kërkesëpadi", "padi", "kundërpadi", "prapësim", "lpк", "lmd",
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
    "PENAL": [
        "KPPRK (Ligji Nr. 08/L-032 për Procedurën Penale)",
        "KPRK (Kodi Penal i Republikës së Kosovës, Nr. 06/L-074)"
    ],
    "CIVIL": [
        "LPK (Ligji Nr. 03/L-006 për Procedurën Kontestimore)",
        "LMD (Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve)"
    ],
    "KOMERCIAL": [
        "Ligji për Gjykatën Komerciale (Nr. 08/L-015)",
        "Ligji për Shoqëritë Tregtare"
    ],
    "PRONËSOR": [
        "Ligji për Pronësinë dhe të Drejtat Tjera Sendore (Nr. 03/L-154)",
        "Ligji për Kadastër"
    ],
    "PUNËS": [
        "Ligji i Punës (Nr. 03/L-212)",
        "Ligji për Sigurime Pensionale"
    ],
    "FAMILJAR": [
        "Ligji për Familjen (Nr. 2004/32)",
        "Ligji për Trashëgiminë"
    ],
    "ADMINISTRATIV": [
        "Ligji për Konfliktet Administrative (Nr. 03/L-202)",
        "Ligji për Procedurën e Përgjithshme Administrative"
    ],
    "KUSHTETUES": [
        "Kushtetuta e Republikës së Kosovës",
        "Ligji për Gjykatën Kushtetuese"
    ]
}


class BasePillarService:
    """
    Shërbimi Bazë Universal për të 6 Shtyllat:
    - Zbulimi automatik i llojit të çështjes (case_domain)
    - Integrimi me RAG (legal_knowledge_base + user_vectors)
    - Eliminimi i halucinacioneve me verifikim nen-për-nen
    - 100% agnostik ndaj domeneve (Penal, Civil, Administrativ, etj.)
    """

    @staticmethod
    def detect_case_domain(
        case_title: str = "",
        context_str: str = "",
        manifest_str: str = ""
    ) -> str:
        """
        Zbulon automatikisht llojin e çështjes bazuar në titull, dokumente dhe manifest.
        Returns: "PENAL", "CIVIL", "KOMERCIAL", "PRONËSOR", "PUNËS", "FAMILJAR", "ADMINISTRATIV", "KUSHTETUES"
        """
        combined_text = f"{case_title} {context_str[:5000]} {manifest_str[:2000]}".lower()
        
        # Numëro sa fjalë kyçe përputhen për secilin domen
        domain_scores: Dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in combined_text)
            domain_scores[domain] = score
        
        # Kthe domenin me pikët më të larta
        best_domain = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain]
        
        if best_score == 0:
            # Default në CIVIL nëse nuk gjendet asnjë fjalë kyçe
            logger.info("⚠️ [BasePillar] Nuk u zbulua domeni specifik. Duke përdorur CIVIL si default.")
            return "CIVIL"
        
        logger.info(f"✅ [BasePillar] Domeni i zbuluar: {best_domain} (score: {best_score})")
        return best_domain

    @staticmethod
    def get_domain_laws(case_domain: str) -> List[str]:
        """Kthen ligjet përkatëse për domenin e zbuluar."""
        return DOMAIN_LAWS.get(case_domain, DOMAIN_LAWS["CIVIL"])

    @staticmethod
    def build_domain_instruction(case_domain: str) -> str:
        """Gjeneron udhëzime specifike për lëminë e çështjes."""
        laws = BasePillarService.get_domain_laws(case_domain)
        laws_str = ", ".join(laws)
        
        return f"""
DEGË E SË DREJTËS: {case_domain}
LEGJISLACIONI POZITIV I ZBATUESHËM PËR KËTË LËNDË:
{laws_str}

RREGULLAT E HEKURTA TË DOMENIT:
1. Zbato VETËM ligjet e lartpërmendura dhe nenet e tyre të verifikuara;
2. NËSE një nen nuk ekziston në bazën ligjore, thuaj: "Nuk u gjet referencë e saktë në bazën statutore për këtë pikë";
3. MOS cito asnjë ligj apo nen nga memorja — VETËM nga RAG context i ofruar;
4. Përshtat terminologjinë juridike me {case_domain};
5. Precedentët e Gjykatës Supreme zbatohen sipas lëmisë specifike.
"""

    @staticmethod
    def get_rag_context(
        user_id: str = "",
        case_id: str = "",
        query_text: str = "",
        n_results: int = 20
    ) -> Tuple[str, str]:
        """
        Kërkon në legal_knowledge_base dhe user_vectors për të marrë kontekst ligjor.
        Returns: (global_rag_context, case_rag_context)
        """
        global_rag_context = ""
        case_rag_context = ""
        
        try:
            from app.services.vector_store_service import (
                query_global_knowledge_base,
                query_case_knowledge_base
            )
            
            # 1. Kërko në bazën globale statutore
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
                    logger.info(f"✅ [RAG] U gjetën {len(global_results)} rezultate nga baza statutore.")
            
            # 2. Kërko në dokumentet e çështjes
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
                    logger.info(f"✅ [RAG] U gjetën {len(case_results)} rezultate nga dokumentet e lëndës.")
                    
        except ImportError as e:
            logger.warning(f"⚠️ [RAG] vector_store_service nuk u importua: {e}")
        except Exception as e:
            logger.error(f"❌ [RAG] Gabim gjatë kërkimit: {e}")
        
        return global_rag_context, case_rag_context

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
        case_rag_context: str = ""
    ) -> str:
        """
        Ndërton pjesën e përbashkët të prompt-it që përdoret nga të 6 shërbimet.
        """
        # Zbulo domenin nëse nuk është dhënë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        domain_instruction = BasePillarService.build_domain_instruction(case_domain)
        
        return f"""
KLIENTI / PËRDORUESI: **{client_name}** | ROLI: **{(client_position or 'DEFENDANT').upper()}** | LËNDA: **{case_title}** | DATA: {current_date_str}

{domain_instruction}

{'='*60}
KONTEKSTI LIGJOR I VERIFIKUAR NGA BAZA STATUTORE E KOSOVËS (RAG):
{'='*60}
{rag_context if rag_context else "Nuk u gjet asnjë referencë specifike në bazën statutore për këtë lëndë. Jini të kujdesshëm dhe mos citoni nene pa verifikim."}

{'='*60}
KONTEKSTI NGA DOKUMENTET E ÇËSHTJES (RAG):
{'='*60}
{case_rag_context if case_rag_context else "Nuk u gjetën dokumente shtesë në bazën e çështjes."}

{'='*60}
PASAPORTA E SHKRESAVE:
{'='*60}
{manifest_str}

{'='*60}
DOKUMENTET E PLOTA:
{'='*60}
{context_str}
"""