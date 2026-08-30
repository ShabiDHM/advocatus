# FILE: backend/app/services/rag/intent_detector.py
# PHOENIX PROTOCOL - INTENT DETECTOR V1.0

import re
import logging

logger = logging.getLogger(__name__)

class IntentDetector:
    """
    Zbulon se çfarë kërkon përdoruesi:
    - FORENSIC_AUDIT: Ikona ⚖️ — Auditim forenzik i dokumentit
    - DRAFTING: Hartim i akteve zyrtare
    - PILLAR_STRATEGY: Karta 1 — Strategjia
    - PILLAR_STATUTES: Karta 2 — Baza Statutore
    - PILLAR_QUESTIONS: Karta 3 — Pyetësori
    - PILLAR_DAMAGES: Karta 4 — Dëmet
    - GENERAL_CHAT: Bisedë e përgjithshme
    """

    @staticmethod
    def detect(query: str) -> str:
        q = query.lower()
        
        # 1. FORENZIKA LIGJORE (⚖️)
        audit_keywords = [
            "forenzika ligjore", "forenzikë ligjore", "forenzike", "forenzikë",
            "direktivë forenzike", "auditim forenzik", "audito dokumentin",
            "verifiko dokumentin", "kontroll forenzik", "konsulenca e gjyqtarit suprem"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"

        # 2. HARTIM I AKTEVE
        draft_triggers = [
            "ma harto", "ma gjenero", "shkruaj aktin", "përpilo aktin",
            "harto padinë", "harto kallëzimin penal", "harto prapësimin",
            "harto ankesën", "harto kontratën"
        ]
        if any(k in q for k in draft_triggers):
            return "DRAFTING"
        
        # 3. PYETËSORI TAKTIK
        if any(k in q for k in [
            "pyetësorin taktik", "pyetësor", "pyetje taktike", "ballafaqim",
            "dëshmitarët", "marrja në pyetje", "seancë", "kundër-pyetje"
        ]):
            return "PILLAR_QUESTIONS"
        
        # 4. DËMET DHE MASAT
        if any(k in q for k in [
            "llogarit dëmet", "llogaritja e dëmit", "lmd", "kamatën ligjore",
            "masat emergjente", "dëmit material", "dëmet materiale e jomateriale"
        ]):
            return "PILLAR_DAMAGES"

        # 5. BAZA STATUTARE
        if any(k in q for k in [
            "nxirr bazën e plotë ligjore", "baza statutore dhe jurisprudenca",
            "lapsuse në shkresa", "precedentët dhe qëndrimet e gjykatës supreme"
        ]):
            return "PILLAR_STATUTES"

        # 6. STRATEGJIA
        if any(k in q for k in [
            "shtyllat strategjike të kërkesëpadisë", "strategjia dhe matrica e provave",
            "qëndrueshmërinë e lëndës", "gjendjen e lëndës",
            "çfarë më kanë bërë", "çfarë të bëj tash", "hapat e ardhshëm"
        ]):
            return "PILLAR_STRATEGY"

        return "GENERAL_CHAT"