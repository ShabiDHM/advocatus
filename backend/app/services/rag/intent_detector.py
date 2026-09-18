# FILE: backend/app/services/rag/intent_detector.py
# PHOENIX PROTOCOL - INTENT DETECTOR V6.0 (QUERY DEPTH CLASSIFIER)
# V6.0: Shtuar QueryDepthDetector — klasifikon pyetjet faktike vs analitike.
#       Përdoret për të vendosur nëse duhet shtuar konteksti ligjor global.
# V5.0: Hequr intenti FORENSIC_AUDIT.

import re
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# QUERY DEPTH DETECTOR (V6.0)
# ═══════════════════════════════════════════════════════════════════════════

class QueryDepthDetector:
    """
    Klasifikon thellësinë e pyetjes:
    - 'factual'   → pyetje për Fakte (kush, çfarë, sa, kur, ku)
    - 'analytical'→ pyetje për Analizë Ligjore (ligjshmëri, shkelje, strategji)
    - 'unknown'   → e paqartë → default 'analytical' (për siguri)

    Përdoret për të vendosur nëse duhet të shtohet konteksti ligjor global
    kur përdoruesi ka zgjedhur një dokument specifik.
    """

    # Pyetje për FAKTE — përgjigjen e gjejmë brenda dokumentit
    FACTUAL_KEYWORDS = [
        # Pyetësorë bazë
        "kush", "çfarë", "cfare", "çka", "cka",
        "sa", "kur", "ku",
        "cila", "cili", "cilat", "cilet", "cilët",
        # Veprime ekstraktimi
        "përmbledh", "permbledh", "përmblidh", "permbli",
        "listo", "nxjerr", "trego", "tregoni",
        "cito", "citat", "citoje",
        "gjej", "kërko", "kerko",
        # Fusha specifike
        "emri", "emrat", "data", "datat",
        "adresa", "numri", "numrat",
        "sa faqe", "sa fletë", "sa flete",
        "çfarë shkruan", "cfare shkruan",
        "çfarë thotë", "cfare thote",
        # Pala / personat
        "kush është", "kush eshte",
        "kush janë", "kush jane",
    ]

    # Pyetje ANALITIKE — kërkojnë kontekst ligjor përveç fashikullit
    ANALYTICAL_KEYWORDS = [
        # Ligjshmëri / vlefshmëri
        "ligjshëm", "ligjshem", "ligjshmëri", "ligjshmeri",
        "i ligjshëm", "i paligjshëm",
        "i vlefshëm", "i pavlefshëm",
        "i saktë", "i pavërtetë",
        # Nene / ligje
        "nen", "neni", "nenet", "nenit",
        "ligj", "ligji", "ligje", "ligjit",
        "shkel", "shkelje", "shkelur",
        "kundërshton", "kundershton", "kundërshtim",
        # Analizë
        "analizo", "analizë", "analize",
        "vlerëso", "vlereso", "vlerësim", "vleresim",
        "krahaso", "krahasim", "krahasuar",
        "pse", "përse", "perse",
        # Praktikë gjyqësore
        "praktik", "praktikë", "praktike",
        "precedent", "precedentë", "precedente",
        "jurisprudenc", "gjykatës supreme", "gjykates supreme",
        # Rekomandime / strategji
        "rekomandoj", "rekomandim", "rekomandohet",
        "strategji", "strategjia", "strategjik",
        "duhet", "mund të", "mund te",
        "hapi", "hapat", "veprim", "veprimi",
        # Rreziqe / pasoja
        "rrezik", "rreziku", "rreziqet",
        "pasoj", "pasoja", "pasojat",
        "afat", "afati", "afate", "afatet",
        # Bazë ligjore
        "bazë ligjore", "baze ligjore", "baza ligjore",
        "procedur", "procedura", "procedurë",
        "kusht", "kushtet", "kushtet ligjore",
        # Të drejtat
        "të drejt", "te drejt", "drejtat",
    ]

    @staticmethod
    def detect(query: str) -> str:
        """
        Kthen:
        - 'factual'    → pyetje faktike
        - 'analytical' → pyetje analitike
        - 'unknown'    → e paqartë

        Nëse ka të dyja → 'analytical' (për siguri, shto kontekst).
        """
        if not query:
            return "unknown"

        q = query.lower().strip()

        has_factual = any(kw in q for kw in QueryDepthDetector.FACTUAL_KEYWORDS)
        has_analytical = any(kw in q for kw in QueryDepthDetector.ANALYTICAL_KEYWORDS)

        # Të dyja → prioritet analitike (më e sigurt)
        if has_analytical:
            return "analytical"

        if has_factual:
            return "factual"

        return "unknown"

    @staticmethod
    def should_fetch_global_docs(query: str, has_document_selection: bool) -> bool:
        """
        Vendos nëse duhet të shtohen dokumentet globale (baza ligjore).

        - Pa dokument të zgjedhur → GJITHMONË po (fashikulli i plotë ka nevojë për kontekst)
        - Me dokument të zgjedhur + pyetje faktike → JO (vetëm dokumenti)
        - Me dokument të zgjedhur + pyetje analitike → PO (shto bazë ligjore)
        - Me dokument të zgjedhur + pyetje e paqartë → PO (për siguri)
        """
        if not has_document_selection:
            return True

        depth = QueryDepthDetector.detect(query)

        if depth == "factual":
            logger.info(f"🎯 [QueryDepth] Factual → VETËM dokumenti (pa bazë ligjore globale)")
            return False

        if depth == "analytical":
            logger.info(f"🎯 [QueryDepth] Analytical → dokument + bazë ligjore globale")
            return True

        logger.info(f"🎯 [QueryDepth] Unknown → default në dokument + bazë ligjore globale")
        return True


# ═══════════════════════════════════════════════════════════════════════════
# INTENT DETECTOR (V5.0 — i paprekur)
# ═══════════════════════════════════════════════════════════════════════════

class IntentDetector:
    """
    Zbuluesi Qendror i Qëllimit të Përdoruesit (V5.0):
    - Zero konfuzion: Fjalët e analizës së aktit individual nuk përzihen me raportin e përgjithshëm të dosjes.
    - Rrugëtimi i saktë për hartim (DRAFTING), pyetësorë seance, dëme dhe bisedë të lirë.
    """

    @staticmethod
    def detect(query: str) -> str:
        if not query:
            return "GENERAL_CHAT"

        q = query.lower().strip()

        # 1. HARTIM I AKTEVE GJYQËSORE (DRAFTING)
        is_drafting_intent = (
            any(w in q for w in ["harto", "gjenero", "përpilo", "perpilo", "shkruaj", "drafto", "krijo"]) and
            any(w in q for w in [
                "padi", "kërkesëpadi", "kerkesepadi", "kallëzim", "kallezim", 
                "ankesë", "ankese", "ankim", "prapësim", "prapsim", "kundërpadi", 
                "kunderpadi", "kontratë", "kontrate", "shkresë", "shkrese", "akt", "draft"
            ])
        ) or any(t in q for t in [
            "ma harto", "ma gjenero", "shkruaj aktin", "përpilo aktin", 
            "harto aktin", "përgatit padinë", "përgatit ankesën"
        ])

        if is_drafting_intent:
            return "DRAFTING"

        # 2. ANALIZA E PLOTË E GJITHË DOSJES / FASHIKULLIT
        comprehensive_keywords = [
            "analizo rastin", "analizo rast", "analiza e plotë e rastit", "analiza e plote e rastit",
            "analizo dosjen", "analizo fashikullin", "raporti master", "raport master",
            "raport i plotë i rastit", "analiza globale", "fashikulli i plotë"
        ]
        if any(k in q for k in comprehensive_keywords):
            return "COMPREHENSIVE_ANALYSIS"

        # 3. PYETËSORI TAKTIK PËR SEANCË
        if any(k in q for k in [
            "pyetësor", "pyetesor", "pyetje taktike", "ballafaqim",
            "dëshmitar", "deshmitar", "marrja në pyetje", "seancë", "kundër-pyetje"
        ]):
            return "PILLAR_QUESTIONS"

        # 4. LLOGARITJA E DËMIT DHE MASAT E SIGURIMIT
        if any(k in q for k in [
            "llogarit dëmet", "llogaritja e dëmit", "kamatë", "kamate", "kamata ligjore",
            "masat emergjente", "masë e sigurimit", "mase e sigurimit", "dëm material", "dëmit material"
        ]):
            return "PILLAR_DAMAGES"

        # 5. BAZA STATUTORE DHE PRECEDENTËT
        if any(k in q for k in [
            "nxirr bazën e plotë ligjore", "baza statutore", "nenet e ligjit",
            "precedentët", "precedentet", "praktika e gjykatës supreme"
        ]):
            return "PILLAR_STATUTES"

        # 6. STRATEGJIA DHE MATRICA E PROVAVE
        if any(k in q for k in [
            "strategjia", "shtyllat strategjike", "matrica e provave",
            "qëndrueshmërinë e lëndës", "hapat e ardhshëm", "plani i veprimit"
        ]):
            return "PILLAR_STRATEGY"

        return "GENERAL_CHAT"