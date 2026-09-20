# FILE: backend/app/services/document_review/precedent_search/query_builder.py
# PHOENIX PROTOCOL - PRECEDENT QUERY BUILDER V2.1
# Krijon query semantik nga konteksti i lendes.
# V2.1: Termat tematike (whitelist) + fallback frekuence.

import re
import logging
from typing import List, Dict, Optional

from .config import (
    PRECEDENT_MAX_THEMATIC_TERMS,
    PRECEDENT_MAX_KEY_TERMS,
    PRECEDENT_MAX_TEXT_FOR_QUERY,
)
from .helpers import normalize_for_match

logger = logging.getLogger(__name__)


# ===========================================================================
# STOP WORDS (boilerplate ligjore)
# ===========================================================================

_STOP_WORDS = {
    "i", "e", "të", "te", "së", "se", "më", "me", "në", "ne", "nga",
    "për", "per", "ndaj", "tek", "ku", "ka", "pa", "brenda", "para",
    "pas", "si", "ose", "dhe", "po", "jo", "një", "nje", "çdo", "cdo",
    "këtë", "kete", "atij", "asaj", "keta", "keto", "derisa", "nuk",
    "është", "eshte", "janë", "jane", "kanë", "kane", "ishte", "ishin",
    "që", "qe", "por", "edhe", "vetëm", "vetem", "gjithashtu", "atë",
    "ate", "kjo", "ky", "këto", "këta", "kësaj", "kesaj", "këtij",
    "ketij", "prej", "mbi", "nën", "nen", "gjatë", "gjate", "kundër",
    "kunder", "sipas", "tij", "saj", "tyre", "shume", "shumë",
    # Boilerplate ligjore
    "gjykata", "gjykate", "gjykates", "gjykaten", "gjykatave",
    "gjykimi", "gjykimit", "gjykim",
    "vendimi", "vendim", "vendimit", "vendimet", "vendimeve",
    "aktgjykim", "aktgjykimi", "aktgjykimit",
    "aktvendim", "aktvendimi", "aktvendimit",
    "lenda", "lendes", "lendet", "lende",
    "pala", "pales", "palet", "pale", "palesh",
    "parashtruesi", "parashtrues", "parashtruesit",
    "themelore", "themelor", "apeli", "apelit", "apel",
    "supreme", "shkalles", "shkalle", "shkalla",
    "procedura", "procedure", "procedures", "procedural", "procedurës",
    "kontrate", "kontrata", "kontrates", "kontratës",
    "dosja", "dosje", "dosjes", "fashikulli", "fashikull", "fashikullit",
    "prokurori", "prokurorit", "prokuroria", "prokuror",
    "mbrojtesi", "mbrojtesin", "mbrojtes",
    "klienti", "klientit", "klient", "klientes",
    "avokati", "avokatit", "avokat",
    "nisur", "bazuar", "parashtruar", "parashtruara", "parashtroi",
    "dokumenti", "dokument", "dokumentet", "dokumenteve",
    "cituar", "citohet", "referuar", "referohet",
    "ndryshuar", "ndryshon", "ndryshimin", "ndryshim",
    "shkruar", "shkruan", "theksoi", "thekson", "theksuar",
    "vendosi", "vendosur", "vendos",
    "kërkoi", "kerkoi", "kërkuar", "kerkuar", "kërkesë", "kerkese",
    "pranuar", "pranimit", "pranim",
    "refuzuar", "refuzimit", "refuzim",
    "shqyrtimit", "shqyrtim", "shqyrtuar",
    "gjyqtari", "gjyqtarit", "gjyqtar", "gjyqtare",
    "nenin", "nenit", "neneve",
    "kodi", "kodit", "kod",
    "ligji", "ligjit", "ligjet", "ligjeve", "ligj",
    "paragrafi", "paragrafit", "paragraf",
    "përcaktuar", "percaktuar", "cilësuar", "cilesuar",
    "kualifikuar", "plotësuar", "plotesuar",
    "konstatuar", "konstaton", "konstatoi",
    "dëgjuar", "degjuar", "dëgjoi",
    "shpallur", "shpalli", "nis", "filluar", "filloi",
    "bërë", "bere", "bëhet", "behet",
    "dhënë", "dhene", "jep", "jepet",
    "prishur", "prishi", "prish",
    "mbajtur", "mbajti", "mbahet",
    "paraqitur", "paraqiti", "paraqitet", "paraqit",
    "ushtruar", "ushtroi", "ushtron",
    "kundërshtuar", "kundershtuar", "kundërshtoi", "kundershtoi",
    "apeluar", "apeloi", "apelon",
    "kishte", "kishin", "kish",
    "mund", "mundet", "do", "duhet", "duhej",
    "prandaj", "sepse", "megjithatë", "megjithate",
    "ndërsa", "ndersa", "tashmë", "tashme",
}


# ===========================================================================
# THEMATIC KEYWORDS WHITELIST
# ===========================================================================

THEMATIC_KEYWORDS = [
    # Dhunë familjare / urdhër mbrojtjeje
    "dhune", "dhuna", "dhunes", "dhunës", "dhunshëm", "dhunshem",
    "mbrojtje", "mbrojtjes", "mbrojtjen", "mbrojtur",
    "urdher mbrojtjeje", "urdheri i mbrojtjes",
    "familjare", "familjar", "familjes", "familjen", "familje",
    "bashkeshort", "bashkeshorti", "bashkeshortor",
    "prind", "prinderore", "prinderor",
    "kontakt", "kontakti", "kontaktit", "kontakte",
    "vizite", "vizita", "vizitat",
    "femije", "femija", "femijeve", "femijet", "femijën",
    "mitur", "mituri", "miture",
    "kujdestari", "kujdestaria", "kujdestar",
    "adoptim", "adoptimi",
    "ndarje", "ndarja",
    # Psikiatri / mjekësi / toksikologji
    "psikiatrike", "psikiatri", "psikologjik", "psikologjike",
    "diagnoze", "diagnoza", "diagnozat",
    "icd", "icd-10", "icd10",
    "toksikologji", "toksikologjike", "toksikologjik",
    "narkotike", "narkotik", "narkotikë",
    "droga", "droge", "alkool", "alkooli", "alkoolik",
    "shendetesor", "shendetesore",
    "ekspertize", "ekspertiza", "ekspertimi",
    # Procedurë penale
    "arrest", "arresti", "arrestim", "arrestimi",
    "paraburgim", "paraburgimi", "paraburguar",
    "sekuestrim", "sekuestro", "sekuestrimi", "sekuestruar", "sekuestroi",
    "kontroll", "kontrolli", "kontrolluar",
    "akuz", "akuze", "akuza", "akuzat", "akuzuar", "akuzuari",
    "kallzim", "kallzimi", "kallzuar",
    "aktakuze", "aktakuza",
    "denim", "denimi", "denuar", "denuari",
    "vjedhje", "vjedhja", "vjedhur",
    "grabitje", "grabitja", "grabitur",
    "mashtrim", "mashtrimi", "mashtruar",
    "vrasje", "vrasja", "vrare", "vrasës",
    "krim", "krimi", "kriminal", "kriminale",
    "traffikim", "traffikimi", "traffikuar",
    "armë", "arma", "armët", "armëmbajtje",
    "kundërvajtje", "kundervajtje",
    "fajësi", "fajesia", "fajtor", "fajtore",
    "pafajësi", "pafajesi", "pafajshëm", "pafajshem",
    # Procedurë civile / pronësi
    "pronesi", "pronesia", "prone", "prona",
    "pasuri", "pasuria", "pasurie", "pasuror",
    "kompensim", "kompensimi", "kompensuar",
    "demi", "demit", "dëm", "dëmi", "dëmtuar", "demtuar",
    "kontest", "kontesti", "kontestimi", "kontestuar",
    "kerkespadi", "kerkespadia", "kërkesëpadi",
    "trashgimi", "trashgimia", "trashëgimi", "trashëguar",
    "testament", "testamenti", "testamentar",
    "hipotekë", "hipoteka", "hipotekuar",
    "qiradhënie", "qiradhenie", "qira", "qiraja",
    "shitblerje", "shitblerja", "shitur", "blerje",
    "ndërtim", "ndertim", "ndërtimi", "ndërtuar",
    # Të drejtat dhe procedura
    "shkelje", "shkelja", "shkelur",
    "drejtat", "e drejta", "drejtësia",
    "gjykim i drejtë", "gjykim i drejte",
    "ankim", "ankimi", "ankuar", "ankohet",
    "rishqyrtim", "rishqyrtimi", "rishqyrtuar",
    "revizion", "revizioni", "reviduar",
    "rikthim", "rikthimi", "rikthyer",
    "ekstradim", "ekstradimi", "ekstraduar",
    "azil", "azili", "azilkërkues",
    "shtetësi", "shtetesi", "shtetas",
    "emigracion", "emigrim", "imigrim",
]


# ===========================================================================
# NXJERRJA E TERMAVE
# ===========================================================================

def _extract_thematic_terms(
    text: str,
    max_terms: int = PRECEDENT_MAX_THEMATIC_TERMS,
) -> List[str]:
    """Nxjerr termat tematike nga whitelist (radha e shfaqjes)."""
    if not text:
        return []

    snippet = text[:PRECEDENT_MAX_TEXT_FOR_QUERY].lower()
    normalized_snippet = normalize_for_match(snippet)

    found: List[str] = []
    seen: set = set()

    for keyword in THEMATIC_KEYWORDS:
        kw_norm = normalize_for_match(keyword)
        if not kw_norm or kw_norm in seen:
            continue
        if kw_norm in normalized_snippet:
            seen.add(kw_norm)
            found.append(keyword)
            if len(found) >= max_terms:
                break

    return found


def _extract_key_terms(
    text: str,
    max_terms: int = PRECEDENT_MAX_KEY_TERMS,
) -> List[str]:
    """Nxjerr termat kyc me frekuence (fallback)."""
    if not text:
        return []

    snippet = text[:PRECEDENT_MAX_TEXT_FOR_QUERY]
    words = re.findall(r'\b[a-zA-ZëËçÇ]{4,}\b', snippet)

    freq: Dict[str, int] = {}
    for w in words:
        wl = w.lower()
        if wl in _STOP_WORDS:
            continue
        freq[wl] = freq.get(wl, 0) + 1

    sorted_terms = sorted(freq.items(), key=lambda x: -x[1])
    return [t for t, _ in sorted_terms[:max_terms]]


# ===========================================================================
# PUBLIC
# ===========================================================================

def build_precedent_query(
    document_type: str = "",
    file_name: str = "",
    doc_text: str = "",
    case_type: Optional[str] = None,
) -> str:
    """Nderton query semantik per kerkim precedentesh."""
    parts: List[str] = []

    if case_type:
        ct_clean = case_type.replace("→", " ").replace("->", " ")
        ct_clean = " ".join(ct_clean.split())
        if ct_clean:
            parts.append(ct_clean)

    if document_type:
        dt = document_type.strip()
        if dt:
            parts.append(dt)

    thematic = _extract_thematic_terms(doc_text)

    if thematic:
        parts.extend(thematic)
        logger.info(
            f"🔍 [PRECEDENT] Query tematik ({len(thematic)} terma): "
            f"{thematic[:5]}..."
        )
    else:
        key_terms = _extract_key_terms(doc_text)
        parts.extend(key_terms)
        logger.info(
            f"🔍 [PRECEDENT] Query frekuence (pa terma tematikë): "
            f"{key_terms[:5]}..."
        )

    query = " ".join(p for p in parts if p).strip()

    if len(query) < 15:
        query = f"Gjykata Supreme {query}".strip()

    logger.info(f"🔍 [PRECEDENT] Query final: '{query[:200]}'")
    return query