# FILE: backend/app/services/rag/intent_detector.py
# PHOENIX PROTOCOL - INTENT DETECTOR V3.0 (ROBUST MULTI-INFLECTION ALBANIAN INTENT ROUTER)

import re
import logging

logger = logging.getLogger(__name__)


class IntentDetector:
    """
    Zbuluesi Qendror i Qëllimit të Përdoruesit (V3.0):
    - COMPREHENSIVE_ANALYSIS: Butoni "Analizo Rastin" / Raporti Master i Dosjes
    - FORENSIC_AUDIT: Ikona ⚖️ / Auditimi i thellë i një dokumenti specifik
    - DRAFTING: Hartimi i çdo lloj padie, ankesa, prapësimi, kallëzimi apo kontrate
    - PILLARS: Kërkesat e veçanta (Strategjia, Pyetësori, Dëmet, Baza Ligjore)
    - GENERAL_CHAT: Pyetje të përgjithshme ligjore
    """

    @staticmethod
    def detect(query: str) -> str:
        if not query:
            return "GENERAL_CHAT"

        q = query.lower().strip()

        # 0. ANALIZA E PLOTË E DOSJES (RAPORTI MASTER I FASHIKULLIT)
        comprehensive_keywords = [
            "analizo rastin", "analizo rast", "analiza e plotë", "analiza e plote",
            "raport i plotë", "raport i plote", "analizë e plotë", "analize e plote",
            "raport forenzik", "analiza forenzike", "analiza e rastit", "analizo dosjen",
            "analizo fashikullin", "raporti master", "raport master", "analizë e thellë",
            "pasaporta procedurale"
        ]
        if any(k in q for k in comprehensive_keywords):
            return "COMPREHENSIVE_ANALYSIS"

        # 1. AUDITIMI FORENZIK I DOKUMENTIT (⚖️)
        audit_keywords = [
            "direktivë forenzike", "direktive forenzike", "auditimi forenzik", "auditim forenzik",
            "audito dokumentin", "verifiko dokumentin", "kontroll forenzik", "forenzikë e dokumentit",
            "forenzike e dokumentit", "konsulenca e gjyqtarit", "konsulencë gjyqësore"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"

        # 2. HARTIM I AKTEVE GJYQËSORE (DRAFTING) - Kap të gjitha lakimet
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