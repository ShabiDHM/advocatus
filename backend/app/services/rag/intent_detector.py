# FILE: backend/app/services/rag/intent_detector.py
# PHOENIX PROTOCOL - INTENT DETECTOR V4.0 (STRICT HIERARCHY & DOCUMENT ISOLATION GUARD)

import re
import logging

logger = logging.getLogger(__name__)


class IntentDetector:
    """
    Zbuluesi Qendror i Qëllimit të Përdoruesit (V4.0):
    - Hierarki e rreptë: FORENSIC_AUDIT (Auditimi i një akti të vetëm) ka prioritet absolut.
    - Zero konfuzion: Fjalët e analizës së aktit individual nuk përzihen me raportin e përgjithshëm të dosjes.
    - Rrugëtimi i saktë për hartim (DRAFTING), pyetësorë seance, dëme dhe bisedë të lirë.
    """

    @staticmethod
    def detect(query: str) -> str:
        if not query:
            return "GENERAL_CHAT"

        q = query.lower().strip()

        # 1. AUDITIMI FORENZIK I DOKUMENTIT TË VEÇANTË (IKONA ⚖️) — PRIORITET ABSOLUT
        # Nëse prompti kërkon auditim të një akti/dokumenti specifik, duhet të izolohet menjëherë këtu.
        audit_keywords = [
            "direktivë forenzike", "direktive forenzike",
            "auditimin e thellë forenzik", "auditimin e thelle forenzik",
            "auditim forenzik", "auditimi forenzik",
            "audito dokumentin", "verifiko dokumentin",
            "kontroll forenzik", "forenzikë e dokumentit", "forenzike e dokumentit",
            "konsulenca e gjyqtarit", "konsulencë gjyqësore"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"

        # 2. HARTIM I AKTEVE GJYQËSORE (DRAFTING) — Kap të gjitha lakimet e procedurës civile/penale/tregtare
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

        # 3. ANALIZA E PLOTË E GJITHË DOSJES / FASHIKULLIT (RAPORTI MASTER I RASTIT)
        # Ekzekutohet VETËM kur kërkohet qartazi analiza e gjithë dosjes/rastit si tërësi.
        comprehensive_keywords = [
            "analizo rastin", "analizo rast", "analiza e plotë e rastit", "analiza e plote e rastit",
            "analizo dosjen", "analizo fashikullin", "raporti master", "raport master",
            "raport i plotë i rastit", "analiza globale", "fashikulli i plotë"
        ]
        if any(k in q for k in comprehensive_keywords):
            return "COMPREHENSIVE_ANALYSIS"

        # 4. PYETËSORI TAKTIK PËR SEANCË
        if any(k in q for k in [
            "pyetësor", "pyetesor", "pyetje taktike", "ballafaqim",
            "dëshmitar", "deshmitar", "marrja në pyetje", "seancë", "kundër-pyetje"
        ]):
            return "PILLAR_QUESTIONS"

        # 5. LLOGARITJA E DËMIT DHE MASAT E SIGURIMIT
        if any(k in q for k in [
            "llogarit dëmet", "llogaritja e dëmit", "kamatë", "kamate", "kamata ligjore",
            "masat emergjente", "masë e sigurimit", "mase e sigurimit", "dëm material", "dëmit material"
        ]):
            return "PILLAR_DAMAGES"

        # 6. BAZA STATUTORE DHE PRECEDENTËT
        if any(k in q for k in [
            "nxirr bazën e plotë ligjore", "baza statutore", "nenet e ligjit",
            "precedentët", "precedentet", "praktika e gjykatës supreme"
        ]):
            return "PILLAR_STATUTES"

        # 7. STRATEGJIA DHE MATRICA E PROVAVE
        if any(k in q for k in [
            "strategjia", "shtyllat strategjike", "matrica e provave",
            "qëndrueshmërinë e lëndës", "hapat e ardhshëm", "plani i veprimit"
        ]):
            return "PILLAR_STRATEGY"

        return "GENERAL_CHAT"