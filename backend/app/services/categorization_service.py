# FILE: backend/app/services/categorization_service.py
# PHOENIX PROTOCOL - CATEGORIZATION ENGINE V2.0 (INSTANT MULTI-CATEGORY HEURISTICS)

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

CATEGORY_RULES = [
    ("Vendim Gjyqësor", ["aktvendim", "aktgjykim", "në emër të popullit", "kolegji gjykues", "trupi gjykues"]),
    ("Padi / Kërkesëpadi", ["kërkesëpadi", "kerkesepadi", "paditësi", "padia kundër", "petitum"]),
    ("Kundërpadi / Prapësim", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi"]),
    ("Penale / Kallëzim", ["kallëzim penal", "kallezim penal", "aktakuzë", "aktakuze", "prokuroria", "vepër penale"]),
    ("Ankesë / Mjet Juridik", ["ankesë", "ankese", "ankim", "apel", "revizion"]),
    ("Kontratë / Marrëveshje", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese"]),
    ("Financiare / Faturë", ["faturë", "fature", "transaksion", "pagesë", "shuma prej", "kupon fiskal"]),
    ("Ekspertizë / Raport", ["ekspertizë", "ekspertize", "raport social", "qps", "procesverbal"]),
]


class CategorizationService:
    """
    Shërbimi i Kategorizimit të Shpejtë të Dokumenteve:
    - Klasifikon shkresat ligjore në kategori reale brenda 1ms.
    - Shmang etiketimin e verbër dhe përshtatet me fashikullin.
    """

    def categorize_document(self, text: str) -> str:
        if not text or len(text.strip()) < 10:
            return "Procedurale"

        sample = text[:4000].lower()

        for category_name, keywords in CATEGORY_RULES:
            if any(kw in sample for kw in keywords):
                return category_name

        return "Procedurale"


# --- INSTANCIMI GLOBAL ---
CATEGORIZATION_SERVICE = CategorizationService()