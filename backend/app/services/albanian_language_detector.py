# FILE: backend/app/services/albanian_language_detector.py
# PHOENIX PROTOCOL - MULTI-LANGUAGE ID V5.2 (INSTANT RECOGNITION FOR KOSOVO COURT DECISIONS)

import logging
import re
from typing import List
from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)


class AlbanianLanguageDetector:
    """
    Detektori Shumëgjuhësh i Dokumenteve Ligjore:
    - Optimizuar për kontekstin e Kosovës dhe rajonit.
    - Kthen kodet ISO: 'sq', 'en', 'sr', 'de', etj.
    - Shpejtësi ekzekutimi <5ms.
    """

    KOSOVO_LEGAL_MARKERS: List[str] = [
        "republika e kosovës", "gjykata themelore", "gjykata komerciale", 
        "gjykata e apelit", "gjykata supreme", "aktgjykim", "aktvendim", 
        "prokuroria", "kallëzim penal", "kundërpadi", "kunderpadi", "padi", 
        "neni", "ligji nr.", "kodi penal", "kodi i procedurës penale", 
        "gazeta zyrtare", "kontratë", "prishtinë", "prizren", "ferizaj", 
        "gjakovë", "shoqëri tregtare", "sh.p.k."
    ]

    ENGLISH_LEGAL_MARKERS: List[str] = [
        "republic of kosovo", "article", "court", "law no.", 
        "criminal code", "plaintiff", "defendant", "contract", "agreement"
    ]

    SERBIAN_LEGAL_MARKERS: List[str] = [re.escape(m) for m in [
        "republika kosova", "osnovni sud", "član", "zakon br.", 
        "krivični zakonik", "tužilac", "tuženi", "ugovor"
    ]]

    ALBANIAN_STOPWORDS: List[str] = [
        "të", "e", "i", "me", "në", "për", "nga", "që", "u", 
        "do", "ka", "një", "janë", "dhe", "apo", "ose", "si"
    ]

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Përcakton kodin e saktë të gjuhës ('sq', 'en', 'sr', etj.).
        Nëse është e paqartë, vendos 'sq'.
        """
        if not text or len(text.strip()) < 10:
            return "sq"

        text_lower = text.lower()[:5000]

        # 1. Heuristikë e menjëhershme për dokumentet e Kosovës
        albanian_matches = sum(1 for marker in cls.KOSOVO_LEGAL_MARKERS if marker in text_lower)
        if albanian_matches >= 2:
            return "sq"

        # 2. Heuristikë për Anglishten
        english_matches = sum(1 for marker in cls.ENGLISH_LEGAL_MARKERS if marker in text_lower)
        if english_matches >= 2:
            return "en"

        # 3. Kontroll statistikor me LangDetect
        try:
            langs = detect_langs(text_lower)
            if langs:
                best_lang = langs[0].lang
                if best_lang in ['sq', 'en', 'sr', 'hr', 'bs', 'de']:
                    if best_lang in ['hr', 'bs']:
                        return 'sr'
                    return best_lang
        except LangDetectException:
            pass

        # 4. Dendësia e fjalëve lidhëse shqipe
        words = text_lower.split()
        if words:
            stopword_count = sum(1 for w in words if w in cls.ALBANIAN_STOPWORDS)
            if (stopword_count / len(words)) > 0.04:
                return "sq"

        return "sq"


def detect_document_language(text: str) -> str:
    return AlbanianLanguageDetector.detect_language(text)

def is_albanian(text: str) -> bool:
    return AlbanianLanguageDetector.detect_language(text) == "sq"