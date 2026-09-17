# FILE: backend/app/services/synthesis_service.py
# PHOENIX PROTOCOL - SYNTHESIS SERVICE V3.8
# V3.8: Shtuar:
#   - Guardrail #1b: Prompt strikt format + afate
#   - Guardrail #2b: Regex për akronime + çifte (Neni X + Ligji)
#   - Guardrail #5: Verifikim i atribuimit (Neni X i LMDHF vs Neni X i KPRK)
#   - Guardrail #5b: Detektim i kontradiktave të afateve
# V3.7: Guardrails anti-halucinacion + FAST_SEARCH_MODEL
# V3.6: Dual case type detection.

import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Set, Generator, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from bson import ObjectId

from app.services.llm.llm_client import (
    _call_llm,
    _get_sync_client,
    _prepare_system_prompt,
    _sanitize_and_disambiguate_prompt,
    _get_provider_routing_payload,
    _get_api_key,
    FAST_SEARCH_MODEL,
)
from app.services.defendant_group_extractor import (
    get_defendant_group_extractor,
)

logger = logging.getLogger(__name__)


SYNTHESIS_COLLECTION = "case_synthesis"
EXTRACTION_COLLECTION = "case_extractions"
CROSS_REF_COLLECTION = "case_cross_references"

MAX_DIGEST_CHARS = 130_000
MAX_ENTITIES_PER_DOC = 60
MAX_ARTICLE_DESCRIPTIONS = 250
STREAM_BATCH_CHARS = 30
STREAM_BATCH_INTERVAL_SEC = 0.15

LAW_CONTEXT_WINDOW = 8000

SIMILARITY_THRESHOLD = 0.75
SIMILARITY_BOOST_FIRST_WORD = 0.15
SIMILARITY_AMBIGUITY_GAP = 0.05
INSTITUTION_CONTEXT_WINDOW = 300

CASE_TYPE_SCAN_CHARS_PER_DOC = 10000
CASE_TYPE_MAX_DOCS = 25


# ────────────────────────────────────────────────────────────────────────────
# LAW DETECTION
# ────────────────────────────────────────────────────────────────────────────

LAW_WITH_NUMBER_PATTERN = re.compile(
    r'\b('
    r'Ligji\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r'(?:\s+për\s+[^\n(]+?)?'
    r'|'
    r'(?:KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF|KPK)\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r')',
    re.IGNORECASE
)

LAW_ABBREVIATION_PATTERN = re.compile(
    r'\b(KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF|KPK|Kushtetuta)\b',
    re.IGNORECASE
)


# ────────────────────────────────────────────────────────────────────────────
# ARTICLE PATTERNS
# ────────────────────────────────────────────────────────────────────────────

SINGLE_ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*)'
    r'((?:\s*,?\s*par\.?\s*\d+(?:\s*(?:dhe|,)\s*\d+)*)?)'
    r'((?:\s+(?:i|të|te|e|së)\s+[A-ZËÇ][a-zA-ZëçËÇ\-]+(?:-[a-zëç]+)?)*)'
    r'(?:\s*[—\-:]\s*([^\n;•]+?))?'
    r'(?=\s*[;\.\n]|\s*$|\s+[A-ZËÇ][a-zëç]+\s+(?:nuk|ka|i|e)\s)',
    re.IGNORECASE | re.UNICODE,
)

MULTI_ARTICLE_PATTERN = re.compile(
    r'\bNenet\s+'
    r'(\d+(?:[\.\/]\d+)*)'
    r'((?:\s*,\s*\d+(?:[\.\/]\d+)*)*)'
    r'((?:\s+dhe\s+\d+(?:[\.\/]\d+)*)?)'
    r'(?:\s*[—\-:]\s*([^\n;•]+?))?'
    r'(?=\s*[;\.\n]|\s*$|•)',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# V3.8 — GUARDRAIL #2b: Regex për ekstraktim deterministik
# ═══════════════════════════════════════════════════════════════════════════

LAW_NUMBER_PATTERN = re.compile(
    r'\b(\d{2}\s*\/\s*[A-Za-z]\s*-\s*\d{2,4})\b',
    re.IGNORECASE,
)

VERIFIED_ARTICLE_PATTERN = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)'
    r'(?:\s*,?\s*par(?:\.|agrafi|agrafit)?\s*(\d+))?',
    re.IGNORECASE | re.UNICODE,
)

# V3.8: Pattern për çifte (Neni X i LIGJI)
CITATION_WITH_LAW_PATTERN = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)'
    r'(?:\s*,?\s*par(?:\.|agrafi|agrafit)?\s*(\d+))?'
    r'\s+(?:i|të|te|e|së)\s+'
    r'([A-ZËÇ][A-Za-zëçËÇ0-9\-]{2,25}|KPRK|KPK|KPPRK|LPK|LMD|LMDHF)',
    re.IGNORECASE | re.UNICODE,
)

# V3.8: Pattern për datat (për detektimin e kontradiktave)
DATE_PATTERN = re.compile(
    r'\b(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})\b'
)

# V3.8: Pattern për afatet
DEADLINE_PATTERN = re.compile(
    r'\bafat[ie]?\s+(?:për\s+\w+\s+)?(?:është|prej|prej\s+)?\s*'
    r'(\d+)\s*(dit[ëe]?|muaj|jav[ëe]?|vjet)',
    re.IGNORECASE | re.UNICODE
)


def _extract_verified_citations_from_documents(
    db,
    case_id: str
) -> Dict[str, Any]:
    """
    GUARDRAIL #2 (V3.8): Ekstraktim deterministik i citimeve.

    Returns:
        {
            "laws": [...],                    # unike
            "articles": [...],                 # unike (me metadata)
            "article_law_pairs": [...],        # V3.8: [(article, law), ...]
            "by_document": {...},              # doc_id → articles
            "document_laws": {...},            # V3.8: doc_id → laws
            "total_laws": N,
            "total_articles": M,
            "total_pairs": P,
        }
    """
    laws: Set[str] = set()
    articles_by_doc: Dict[str, List[str]] = defaultdict(list)
    document_laws: Dict[str, Set[str]] = defaultdict(set)
    all_articles: List[Dict[str, Any]] = []
    article_law_pairs: Set[Tuple[str, str]] = set()

    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        query = {
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
            "status": {"$ne": "DELETED"},
        }

        cursor = db.documents.find(
            query,
            {"_id": 1, "file_name": 1, "content": 1, "extracted_text": 1, "text": 1},
        )

        for doc in cursor:
            text = (
                doc.get("content")
                or doc.get("extracted_text")
                or doc.get("text")
                or ""
            )
            if not text:
                continue

            doc_id = str(doc["_id"])
            doc_name = doc.get("file_name", "")

            # ═══ Ligjet me numër (03/L-182) ═══
            for match in LAW_NUMBER_PATTERN.finditer(text):
                law_num = match.group(1).replace(" ", "")
                laws.add(law_num)
                document_laws[doc_id].add(law_num)

            # ═══ V3.8: Akronimet e ligjeve ═══
            for match in LAW_ABBREVIATION_PATTERN.finditer(text):
                abbr = match.group(1)
                if abbr.lower() == "kushtetuta":
                    laws.add("Kushtetuta")
                    document_laws[doc_id].add("Kushtetuta")
                else:
                    abbr_up = abbr.upper()
                    laws.add(abbr_up)
                    document_laws[doc_id].add(abbr_up)

            # ═══ Nenet (të vetme) ═══
            for match in VERIFIED_ARTICLE_PATTERN.finditer(text):
                article_num = match.group(1)
                paragraph = match.group(2)
                all_articles.append({
                    "number": article_num,
                    "paragraph": paragraph,
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                })
                articles_by_doc[doc_id].append(article_num)

            # ═══ V3.8: Çiftet (Neni X i LIGJI) ═══
            for match in CITATION_WITH_LAW_PATTERN.finditer(text):
                article_num = match.group(1)
                law = match.group(3).upper()
                article_law_pairs.add((article_num, law))

    except Exception as e:
        logger.warning(f"⚠️ [GUARDRAIL #2] extraction failed: {e}")

    # Dedupe nenet
    seen: Set[Tuple[str, Optional[str]]] = set()
    unique_articles: List[Dict[str, Any]] = []
    for art in all_articles:
        key = (art["number"], art["paragraph"])
        if key in seen:
            continue
        seen.add(key)
        unique_articles.append(art)

    return {
        "laws": sorted(laws),
        "articles": unique_articles,
        "article_law_pairs": sorted(article_law_pairs),
        "by_document": dict(articles_by_doc),
        "document_laws": {k: sorted(v) for k, v in document_laws.items()},
        "total_laws": len(laws),
        "total_articles": len(unique_articles),
        "total_pairs": len(article_law_pairs),
    }
# ────────────────────────────────────────────────────────────────────────────
# STRICT RULES
# ────────────────────────────────────────────────────────────────────────────

STRICT_RULES = """
⚠️ RREGULLA TË PAFEKSIONUESHME:

1. PËRDOR VETËM EMRAT, INSTITUCIONET DHE DATAT QË SHFAQEN NË TË DHËNAT 
   E MËSIPËRME. NUK lejohet të shpikësh emra, institucione, data ose 
   tituj që nuk janë në digest.

2. NUK SHKURTO OSE NDRYSHO EMRAT:
   - Emri i plotë duhet të shfaqet saktësisht siç është në digest.
   - NUK lejohet shkurtim, kombinim, ose ndryshim i emrave.
   - NUK lejohet dyfishimi i fjalëve (p.sh. "Naim Naim Qelaj").
   - NËSE emri nuk gjendet në digest, MOS E PËRDOR.

3. INSTITUCIONET E SAKTA (të dhëna në digest):
   - Për ÇDO person, cito VETËM institucionin që shfaqet në digest.
   - NUK shkëmbe institucionet ndërmjet personave.

4. NËSE DIGEST-i përmban "DOKUMENTI KRYESOR", fokusohu KRYESISHT në atë.

5. ⚠️ RREGULL ABSOLUT PËR NENET E LIGJEVE (KRITIKE):
   - Seksioni "🔒 CITIMET E VËRTETUARA (REGEX)" është BURIMI I VETËM 
     I SË VËRTETËS për citimet.
   - PËRDOR VETËM ligjet dhe nenet që shfaqen në atë seksion.
   - ÇDO ligj/nen që NUK është aty → KONSIDEROHET HALUDINACION.
   - NUK LEJOHET të ndryshosh numrin e ligjit (03/L-182 ≠ 06/L-006).
   - NUK LEJOHET të shpikësh emra ligjesh (LMDHF, KPK, etj.) që nuk 
     shfaqen në listën e ligjeve të verifikuara.
   - NENET: nëse neni shfaqet VETËM si numër, shkruaj VETËM 
     "Neni X i [Ligjit]" — PA shpikje përshkrimi.
   - NUK LEJOHET "[numri]", "[Ligji i panjohur]", "[i panjohur]", 
     "(i panjohur)", "[N/A]".

6. ⚠️ FORMATI I NENEVE (KRITIKE):
   - Shkruaj "Neni X" ose "Neni X, par. Y" — KURRË "Neni X.Y".
   - Shembull i saktë:
        ✅ "Neni 1 i LMDHF"
        ✅ "Neni 1, par. 2 i LMDHF"
        ✅ "Neni 248 i KPRK"
   - Shembull i GABUAR:
        ❌ "Neni 1.2 i LMDHF"
        ❌ "Neni 248 i LMDHF" (nëse 248 nuk është në LMDHF)
   - NËSE dyshon → shkruaj VETËM numrin, pa përshkrim.

7. ⚠️ PËRSHKRIMET E NENEVE:
   - NËSE digest-i etiketon përshkrimin si "kontekst dokumenti" → NUK 
     është përshkrim zyrtar → shkruaj VETËM "Neni X i [Ligjit]".
   - NËSE digest-i etiketon si "përshkrim zyrtar" → përdore fjalë për fjalë.
   - KURRË mos shpik "Rregullat për procedurat e veçanta" ose 
     përshkrime gjenerike.

8. ⚠️ AFATET PROCEDURALE (KRITIKE):
   - Cito afatin VETËM me burim: "Sipas [dokumenti/neni], afati është X".
   - NËSE dokumentet kanë afate të ndryshme → listoji TË GJITHA me burime.
   - NUK LEJOHET kontradiktë brenda raportit (p.sh. 6 muaj në një 
     seksion dhe 8 ditë në tjetrin).
   - Afatet e njohura nga dokumentet: 8 ditë ankim, 12 muaj urdhër 
     mbrojtjeje, 7 ditë ekspertizë psikiatrike, 10 ditë refuzim kërkese.
   - NËSE nuk gjendet afat → shkruaj "Afati: kontrollo manualisht".

9. ⚠️ LLOJI I LËNDËS:
   - NËSE digest-i përmban "🎯 LLOJI I LËNDËS", përdore atë lloj në 
     të gjithë raportin — MOS e ndrysho.

10. ⚠️ STATUSI I DOKUMENTIT:
    - NËSE dokumenti përmban "KËSHILLË JURIDIKE" ose "afat ankimi" 
      → NUK është i plotfuqishëm.
    - MOS e etiketо si "i plotfuqishëm" pa bazë në tekst.
"""


# ────────────────────────────────────────────────────────────────────────────
# SECTION PROMPTS
# ────────────────────────────────────────────────────────────────────────────

SECTION_PROMPTS = {
    "executive_summary": {
        "title": "PASQYRA EKZEKUTIVE",
        "max_tokens": 1500,
        "prompt": """Ti je jurist i lartë në Kosovë. Bazuar në digest-in,
harto PASQYRËN EKZEKUTIVE në 5-7 paragrafë.

DETYRA:
- IDENTIFIKO LLOJIN KRYESOR të lëndës (nga seksioni "🎯 LLOJI I LËNDËS")
  NËSE lloji është i dyfishtë, përshkruaj të DYJA fazat e evolucionit.
- Palët kryesore me rolet e sakta
- Objekti i kontestit
- Pretendimet kryesore
- Gjendja aktuale procedurale
- Jurisprudenca relevante e Gjykatës Supreme
- Rezultati i mundshëm

⚠️ AFATET:
- Cito afatin VETËM me burim: "Sipas [dokumenti], afati është X ditë/muaj".
- NËSE ka afate të ndryshme → listoji TË GJITHA me burime.
- KURRË mos shkruaj "afati është 6 muaj" pa treguar se në cilin 
  dokument shfaqet.

""" + STRICT_RULES,
    },

    "chronology": {
        "title": "KRONOLOGJIA E NGJARJEVE",
        "max_tokens": 2200,
        "prompt": """Ti je jurist kronolog. Bazuar në DATAT dhe dokumentet,
harto KRONOLOGJINË E DETAJUAR.

DETYRA:
- Rendit ngjarjet sipas datës
- Për çdo ngjarje: data, akti, palët, rëndësia
- Shëno afatet procedurale VETËM nëse shfaqen në dokument
- Refero dokumentin specifik
- NËSE lënda ka fazë civile + penale, dalloji fazat në kronologji

FORMATI:
[Data] — [Ngjarja] — [Rëndësia] — [Referenca dokumenti]

⚠️ KURRË mos shpik datë që nuk shfaqet në dokumentet.

""" + STRICT_RULES,
    },

    "parties_and_roles": {
        "title": "PALËT DHE ROLET",
        "max_tokens": 3000,
        "prompt": """Ti je jurist proceduralist. Bazuar në ekstraktimet,
harto listën e plotë të PALËVE DHE PERSONAVE KYÇ.

DETYRA:
- Palët ndërgjyqëse (VETËM personat që NUK janë në grupet e të pandehurve)
- TË PANDËHURIT: NËSE digest-i përmban "GRUPET E TË PANDËHURVE",
  listoji TË GJITHË sipas grupeve, ME NUMRIN, EMRI DHE ROLI.
- Përfaqësuesit ligjorë (avokatët) — ME KUIDES:
    * VETËM personat me titull "avokat/avokate"
    * NUK lejohet klasifikimi i punonjësve socialë si avokatë.
- Zyrtarët gjyqësorë — ME INSTITUCIONIN E SAKTË
- Ekspertët
- Dëshmitarët e mundshëm
- Organizatat/institucionet

⚠️ TERMINOLOGJIA varet nga LLOJI I LËNDËS (shih seksionin 🎯).
⚠️ DEDUP: NËSE një emër shfaqet si "Elda" dhe "Elda Bala", 
bashkoji në formën e plotë.

""" + STRICT_RULES,
    },

    "legal_framework": {
        "title": "KUADRI LIGJOR DHE NENET",
        "max_tokens": 2600,
        "prompt": """Ti je jurist ekspert në legjislacionin e Kosovës. Bazuar në 
digest-in, harto KUADRIN LIGJOR.

⚠️ RREGULL ABSOLUT (GUARDRAIL #1):
- Seksioni "🔒 CITIMET E VËRTETUARA (REGEX)" është BURIMI I VETËM 
  I SË VËRTETËS.
- PËRDOR VETËM ligjet dhe nenet që shfaqen në atë seksion.
- ÇDO ligj/nen që nuk është aty do të fshihet nga Guardrail #4.
- NUK LEJOHET të ndryshosh numrin e ligjit (03/L-182 ≠ 06/L-006).
- NUK LEJOHET të shpikësh akronime ligjesh (LMDHF, KPK) që nuk janë 
  në listën e ligjeve të verifikuara.
- FORMATI: "Neni X" ose "Neni X, par. Y" — KURRË "Neni X.Y".
- NËSE neni shfaqet VETËM si numër, shkruaj VETËM:
    "Neni X i [Ligjit]"
  PA shpikje përshkrimi.

DETYRA:
- Ligjet kryesore me numra (VETËM ato në digest)
- Nenet sipas ligjit të saktë (VETËM ato në digest)
- Jurisprudenca e Gjykatës Supreme
- Hierarkia e burimeve

""" + STRICT_RULES,
    },

    "key_findings_contradictions": {
        "title": "FAKTET KYÇE DHE KUNDËRSHTITË",
        "max_tokens": 2400,
        "prompt": """Ti je jurist analitik. Identifiko FAKTET KYÇE dhe KUNDËRSHTITË.

DETYRA:
A. FAKTET KYÇE (8-12)
B. KUNDËRSHTITË
C. PROVAT

⚠️ NUK LEJOHET të krijosh fakte ose kontradikta që nuk gjenden në digest.

""" + STRICT_RULES,
    },

    "recommendations": {
        "title": "REKOMANDIMET DHE HAPAT KONKRET TË VEPRIMIT",
        "max_tokens": 3000,
        "prompt": """Ti je jurist strategjik me përvojë dekadash në Gjykatën Supreme 
të Kosovës. Bazuar në digest-in, harto ANALIZËN E DEFEKTEVE PROCEDURALE 
dhe REKOMANDIMIN STRATEGJIK për klientin.

DETYRA:

A. DEFEKTET PROCEDURALE DHE MATERIALE
   - Listo ÇDO defekt të identifikuar në fashikull
   - Për secilin: cito nenet e shkelura + dokumentin ku gjendet
   - Klasifiko: defekt procedural / shkelje e ligjit material / konflikt interesi

B. VLERËSIMI I OPSIONEVE LIGJORE
   Analizo VETËM opsionet që kanë bazë në fashikullin e dhënë.

C. REKOMANDIMI PËRFUNDIMTAR
   ▶ VEPRIMI KRYESOR
   ▶ ARSYEJA
   ▶ HAPAT KONKRET (1, 2, 3, ...)
   ▶ AFATET KRITIKE: listo VETËM ato që shfaqen në dokumentet
   ▶ RREZIQET

⚠️ RREGULLA KRITIKE PËR AFATET:
- Cito VETËM afate që shfaqen në digest (dokumentet e fashikullit).
- NËSE dokumenti përmend "8 ditë ankim" → citoje saktësisht.
- NËSE dokumenti NUK përmend afat → shkruaj "Afati: kontrollo manualisht".
- NUK LEJOHET të shpikësh afate nga ligji i përgjithshëm.

""" + STRICT_RULES,
    },
}


# ────────────────────────────────────────────────────────────────────────────
# CANONICAL ENTITIES
# ────────────────────────────────────────────────────────────────────────────

class CanonicalEntities:
    def __init__(self):
        self.persons: Dict[str, Dict[str, Any]] = {}
        self.organizations: Dict[str, Dict[str, Any]] = {}
        self.case_numbers: Set[str] = set()

    def add_person(self, name, role=None, institution=None):
        if not name or len(name.strip()) < 3:
            return
        name = _dedup_adjacent_words(name.strip())
        key = name.lower()
        if key not in self.persons:
            self.persons[key] = {
                "canonical": name,
                "variants": set(),
                "roles": set(),
                "institutions": set(),
            }
        entry = self.persons[key]
        entry["variants"].add(name)
        if role:
            entry["roles"].add(role.strip())
        if institution:
            entry["institutions"].add(institution.strip())

    def add_organization(self, name):
        if not name or len(name.strip()) < 3:
            return
        key = name.strip().lower()
        if key not in self.organizations:
            self.organizations[key] = {
                "canonical": name.strip(),
                "variants": set(),
            }
        self.organizations[key]["variants"].add(name.strip())

    def add_case_number(self, case_number):
        if case_number and len(case_number.strip()) >= 3:
            self.case_numbers.add(case_number.strip())

    def get_all_person_keys(self):
        return list(self.persons.keys())

    def get_person(self, key):
        return self.persons.get(key)

    def stats(self):
        return {
            "persons": len(self.persons),
            "organizations": len(self.organizations),
            "case_numbers": len(self.case_numbers),
        }


# ────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────

def _dedup_adjacent_words(text: str) -> str:
    if not text:
        return text
    words = text.split()
    if len(words) < 2:
        return text
    result: List[str] = [words[0]]
    for i in range(1, len(words)):
        prev_lower = result[-1].lower().strip(".,;:")
        curr_lower = words[i].lower().strip(".,;:")
        if prev_lower == curr_lower:
            continue
        result.append(words[i])
    return " ".join(result)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _similarity_with_boost(a: str, b: str) -> float:
    base = _similarity(a, b)
    a_parts = a.strip().split()
    b_parts = b.strip().split()
    if a_parts and b_parts and a_parts[0].lower() == b_parts[0].lower():
        return min(1.0, base + SIMILARITY_BOOST_FIRST_WORD)
    return base


def _normalize_for_match(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(
        r'\b(gjyqtari|gjyqtarja|prokurori|prokurorja|avokati|avokatja|'
        r'dr\.?|prof\.?|mr\.?|znj\.?|z\.?|m\.sc\.?)\b',
        '',
        text,
    )
    text = re.sub(r'[.,;:\(\)\[\]"\']', '', text)
    text = " ".join(text.split())
    return text.strip()


def _is_known_entity(name, canonical):
    if not name:
        return (False, None, None)
    key = name.strip().lower()
    if key in canonical.persons:
        return (True, key, canonical.persons[key])
    normalized = _normalize_for_match(name)
    if normalized in canonical.persons:
        return (True, normalized, canonical.persons[normalized])
    return (False, None, None)


def _stream_section_sync(system_prompt, user_content, temperature=0.1):
    if not _get_api_key():
        return
    full_sys = _prepare_system_prompt(system_prompt)
    sanitized = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()
    try:
        stream = client.chat.completions.create(
            model=FAST_SEARCH_MODEL,
            messages=[
                {"role": "system", "content": full_sys},
                {"role": "user", "content": sanitized},
            ],
            temperature=temperature,
            max_tokens=8192,
            stream=True,
            extra_body=_get_provider_routing_payload(),
        )
        for chunk in stream:
            if not chunk or not hasattr(chunk, "choices") or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content
    except Exception as e:
        logger.error(f"❌ [SYNTHESIS] Sync streaming error: {e}")
        raise


# ────────────────────────────────────────────────────────────────────────────
# CASE TYPE PATTERNS
# ────────────────────────────────────────────────────────────────────────────

CASE_TYPE_PATTERNS = {
    "Kërkesë për Urdhër Mbrojtjeje": {
        "patterns": [
            r"urdh[eë]r\s+mbrojtj?eje",
            r"urdh[eë]r\s+mbrojt[eë]s",
            r"dhun[eë]\s+n[eë]\s+familje",
            r"mbrojtje\s+nga\s+dhuna\s+n[eë]\s+familje",
            r"LMDHF",
            r"ligj[i]?\s*nr\.?\s*0[48]\s*[\/\-]?\s*L[-\s]*1[28]5",
            r"pal[eë]\s+e\s+mbrojtur",
            r"pal[eë]\s+p[eë]rgjegj[eë]se",
            r"masa\s+t[eë]\s+mbrojtjes",
        ],
        "weight": 3.0,
    },
    "Çështje Familjare": {
        "patterns": [
            r"kujdestari",
            r"bashk[eë]short",
            r"divorc",
            r"ushqim(?:i)?\s+fëmij[eë]s",
            r"alimentacion",
            r"marr[eë]dh[eë]nie\s+familjare",
        ],
        "weight": 2.5,
    },
    "Kallëzim Penal": {
        "patterns": [
            r"kall[eë]zim\s+penal",
            r"aktakuz[eë]\b",
            r"vep[eë]r\s+penale",
            r"prokuror(?:i|ia|in)",
            r"i\s+pandehur",
            r"e\s+pandehur",
        ],
        "weight": 2.0,
    },
    "Padi Civile": {
        "patterns": [
            r"k[eë]rkes[eë]padi",
            r"padit[eë]s(?:i|ja|in)",
            r"\be\s+paditura\b",
            r"\bi\s+padituri\b",
            r"petitum",
        ],
        "weight": 2.0,
    },
    "Procedurë Administrative": {
        "patterns": [
            r"ankes[eë]\s+administrative",
            r"organ(?:i)?\s+administrativ",
            r"procedur[eë]\s+administrative",
        ],
        "weight": 2.0,
    },
}


CASE_TYPE_FAMILIES = {
    "civil_family": {
        "label": "Kërkesë për Urdhër Mbrojtjeje",
        "filename_keywords": [
            "mbrojtje", "mbrojtjes", "mbrojtës", "mbrojtes",
            "urdher_mbrojtje", "urdhermbrojtje",
            "dhune", "dhunë", "dhuna",
            "familje", "familjar",
            "shkurorëzim", "divorc", "kujdestari",
        ],
    },
    "penal_family": {
        "label": "Procedurë Penale",
        "filename_keywords": [
            "aktakuz", "aktakuze",
            "kallzim", "kallëzim",
            "hedhje_akuz", "hedhjes_se_akuz",
            "penale", "penal",
            "prokuror",
            "pandehur", "padisur",
        ],
    },
}
# ────────────────────────────────────────────────────────────────────────────
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class SynthesisService:
    """
    V3.8 — Guardrails anti-halucinacion + FAST_SEARCH_MODEL.
    """

    def __init__(self, db):
        self.db = db
        self.defendant_extractor = get_defendant_group_extractor(db)

    # ────────────────────────────────────────────────────────────────────
    # GUARDRAIL #5 — Verifikim i Atribuimit (Neni + Ligji)
    # ────────────────────────────────────────────────────────────────────

    def _verify_attribution_word_by_word(
        self,
        output_text: str,
        verified_citations: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        GUARDRAIL #5 (V3.8): Kontrollon që çdo citim "Neni X i LIGJI"
        të ketë ÇIFTIN e vërtetë në dokumentet.

        Shembull gabimi që kapet:
            LLM: "Neni 248 i LMDHF"
            Dokumentet: "Neni 248 i KPRK" dhe "Neni 44 i LMDHF"
            → 248 nuk është kurrë me LMDHF → HALLUCINIM
        """
        if not output_text:
            return {
                "verified": [],
                "unverified": [],
                "hallucination_rate": 0.0,
            }

        article_law_pairs = set(
            tuple(p) for p in verified_citations.get("article_law_pairs", [])
        )

        # Nëse skemi pairs → nuk mund të verifikojmë atribuimin → skip
        if not article_law_pairs:
            return {
                "verified": [],
                "unverified": [],
                "hallucination_rate": 0.0,
                "warning": "no_pairs_available",
            }

        verified: List[Dict[str, Any]] = []
        unverified: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str]] = set()

        for match in CITATION_WITH_LAW_PATTERN.finditer(output_text):
            article_num = match.group(1)
            paragraph = match.group(2)
            law = match.group(3).upper()

            # Normalizo emrin e ligjit
            law_normalized = law.strip()

            key = (article_num, law_normalized)
            if key in seen:
                continue
            seen.add(key)

            entry = {
                "article": article_num,
                "paragraph": paragraph,
                "law": law_normalized,
                "raw": match.group(0).strip(),
            }

            # Verifiko: a ekziston ÇIFTI (article, law) në dokumente?
            # Kontrollo me disa variante të mundshme të emrit të ligjit
            found = False
            for pair_art, pair_law in article_law_pairs:
                if pair_art != article_num:
                    continue
                # Krahaso emrin e ligjit (case-insensitive, normalized)
                if pair_law.upper() == law_normalized:
                    found = True
                    break
                # Nëse ligji është shkruar si numër dhe citimi si akronim
                if law_normalized in pair_law.upper() or pair_law.upper() in law_normalized:
                    found = True
                    break

            if found:
                verified.append(entry)
            else:
                unverified.append(entry)

        total = len(verified) + len(unverified)
        hallucination_rate = (
            round(len(unverified) / max(1, total) * 100, 1) if total > 0 else 0.0
        )

        return {
            "verified": verified,
            "unverified": unverified,
            "total_attributions": total,
            "hallucination_rate": hallucination_rate,
        }

    # ────────────────────────────────────────────────────────────────────
    # GUARDRAIL #5b — Detektim i Kontradiktave të Afateve
    # ────────────────────────────────────────────────────────────────────

    def _detect_deadline_contradictions(
        self,
        output_text: str,
    ) -> Dict[str, Any]:
        """
        GUARDRAIL #5b (V3.8): Detekton afate të ndryshme për të njëjtin veprim.

        Shembull kontradikte:
            Pasqyra: "afati është 6 muaj"
            Rekomandimet: "afati është 8 ditë"
            → KONTRADIKTË (i njëjti raport)
        """
        if not output_text:
            return {
                "deadlines_found": [],
                "contradictions": [],
            }

        # Gjej të gjitha afatet me kontekst
        deadlines: List[Dict[str, Any]] = []

        for match in DEADLINE_PATTERN.finditer(output_text):
            num = int(match.group(1))
            unit = match.group(2).lower().strip("ëe")

            # Normalizo njësinë
            if unit.startswith("dit"):
                unit_normalized = "ditë"
            elif unit.startswith("muaj"):
                unit_normalized = "muaj"
            elif unit.startswith("jav"):
                unit_normalized = "javë"
            elif unit.startswith("vjet"):
                unit_normalized = "vjet"
            else:
                unit_normalized = unit

            deadlines.append({
                "num": num,
                "unit": unit_normalized,
                "raw": match.group(0).strip(),
                "position": match.start(),
            })

        # Kontrollo kontradikta:
        # Nëse ka të njëjtën njësi por numra të ndryshëm → kontradiktë
        # (Heuristikë: 2 afate me unit të njëjtë por numra të ndryshëm)
        contradictions: List[Dict[str, Any]] = []
        by_unit: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for d in deadlines:
            by_unit[d["unit"]].append(d)

        for unit, items in by_unit.items():
            if len(items) < 2:
                continue
            unique_nums = set(item["num"] for item in items)
            if len(unique_nums) > 1:
                contradictions.append({
                    "unit": unit,
                    "values": sorted(unique_nums),
                    "count": len(items),
                    "examples": [item["raw"] for item in items[:3]],
                })

        return {
            "deadlines_found": deadlines,
            "contradictions": contradictions,
        }

    # ────────────────────────────────────────────────────────────────────
    # GUARDRAIL #4 — Citation Checker (fjalë-për-fjalë, vetëm numrat)
    # ────────────────────────────────────────────────────────────────────

    def _verify_citations_word_by_word(
        self,
        output_text: str,
        doc_articles_available: Set[str],
    ) -> Dict[str, Any]:
        if not output_text:
            return {
                "verified": [],
                "unverified": [],
                "total_articles_output": 0,
                "hallucination_rate": 0.0,
            }

        verified: List[str] = []
        unverified: List[str] = []
        seen: Set[str] = set()

        for match in VERIFIED_ARTICLE_PATTERN.finditer(output_text):
            num = match.group(1)
            if num in seen:
                continue
            seen.add(num)

            if num in doc_articles_available:
                verified.append(num)
            else:
                unverified.append(num)

        total = len(seen)
        hallucination_rate = (
            round(len(unverified) / max(1, total) * 100, 1) if total > 0 else 0.0
        )

        return {
            "verified": sorted(verified),
            "unverified": sorted(unverified),
            "total_articles_output": total,
            "hallucination_rate": hallucination_rate,
        }

    # ────────────────────────────────────────────────────────────────────
    # GUARDRAIL #3 — Verifikim i Dyfishtë (LLM Correction)
    # ────────────────────────────────────────────────────────────────────

    def _correct_citations_with_llm(
        self,
        output_text: str,
        checker_report: Dict[str, Any],
        attribution_report: Dict[str, Any],
        verified_citations: Dict[str, Any],
    ) -> str:
        """
        GUARDRAIL #3 (V3.8): LLM pastron output-in duke hequr:
        - Nene që nuk ekzistojnë (checker_report)
        - Çifte të gabuara Neni+Ligji (attribution_report)
        """
        unverified_articles = checker_report.get("unverified", [])
        unverified_attrs = attribution_report.get("unverified", [])

        if not unverified_articles and not unverified_attrs:
            return output_text

        laws_list = ", ".join(verified_citations.get("laws", [])) or "asnjë"
        articles_list = ", ".join(
            f"Neni {a['number']}" for a in verified_citations.get("articles", [])[:50]
        ) or "asnjë"

        # Lista e çifteve të vërteta (maks 50)
        pairs_list = " | ".join(
            f"Neni {a} i {l}" for a, l in verified_citations.get("article_law_pairs", [])[:50]
        ) or "asnjë"

        issues = []
        if unverified_articles:
            issues.append(
                "NENET QË NUK EKZISTOJNË NË FASHIKULL:\n" +
                "\n".join(f"  ❌ Neni {n}" for n in unverified_articles)
            )
        if unverified_attrs:
            issues.append(
                "ÇIFTET E GABUARA (Neni + Ligji):\n" +
                "\n".join(
                    f"  ❌ {a['raw']} (kombinim i palejuar)" for a in unverified_attrs
                )
            )

        system_prompt = """Ti je "Verifikues i Saktësisë Ligjore" në Gjykatën Supreme të Kosovës.

DETYRA: Pastron output-in duke:
1. Fshirë citimet e neneve që NUK ekzistojnë në dokumente.
2. Fshirë çiftet e gabuara (Neni X i LIGJI) që nuk shfaqen në dokumente.

RREGULLA ABSOLUTE:
1. Fshij ÇDO nen që shfaqet në "NENET QË NUK EKZISTOJNË".
2. Fshij ÇDO citim që shfaqet në "ÇIFTET E GABUARA".
3. Ruaj vetëm citimet e vërteta që ekzistojnë në dokumente.
4. NUK LEJOHET të shtosh nene të re.
5. Ruaj strukturën, titujt, formatimin markdown.
6. NUK shpjego — kthe VETËM tekstin e pastruar."""

        user_content = f"""BURIMI I SË VËRTETËS:
- Ligjet e verifikuara: {laws_list}
- Nenet e verifikuara: {articles_list}
- Çiftet e vërteta (Neni X i Ligji): {pairs_list}

───────────────────────────────────────────────────────

PROBLEMET E ZBULUARA:
{chr(10).join(issues)}

───────────────────────────────────────────────────────

OUTPUT-I QË DUHET PASTRUAR:
{output_text}

───────────────────────────────────────────────────────

Kthe tekstin e pastruar (pa gabime citimesh):"""

        try:
            corrected = _call_llm(
                system_prompt=system_prompt,
                user_content=user_content,
                json_mode=False,
                temperature=0.0,
                model=FAST_SEARCH_MODEL,
            )
            return corrected or output_text
        except Exception as e:
            logger.warning(f"⚠️ [GUARDRAIL #3] LLM correction failed: {e}")
            return output_text

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — synthesize
    # ────────────────────────────────────────────────────────────────────

    def synthesize(
        self,
        case_id: str,
        user_id: str = "",
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        case = self._load_case(case_id)
        extractions = self._load_extractions(case_id)
        xrefs = self._load_cross_refs(case_id)

        if not extractions:
            return self._empty_result(case_id, "No extractions found.")

        defendants_groups = self.defendant_extractor.extract_for_case(
            case_id, force=False
        )

        case_type = self._detect_case_type(case_id, extractions)
        logger.info(f"🎯 [SYNTHESIS] Case type detected: {case_type}")

        canonical = self._build_canonical_entities(extractions, defendants_groups)
        logger.info(f"🎯 [SYNTHESIS] Canonical entities: {canonical.stats()}")

        articles_by_law = self._extract_articles_by_law(case_id)
        total_articles = sum(len(v) for v in articles_by_law.values())

        # ═══ GUARDRAIL #2b: Regex ekstraktim para LLM ═══
        verified_citations = _extract_verified_citations_from_documents(self.db, case_id)
        logger.info(
            f"🔒 [GUARDRAIL #2b] Verified citations: "
            f"laws={verified_citations['total_laws']}, "
            f"articles={verified_citations['total_articles']}, "
            f"pairs={verified_citations['total_pairs']}"
        )

        doc_articles_available: Set[str] = {
            a["number"] for a in verified_citations.get("articles", [])
        }

        digest = self._build_digest(
            case, extractions, xrefs, defendants_groups,
            articles_by_law, case_type, verified_citations
        )
        logger.info(
            f"🔍 [SYNTHESIS] Digest built: {len(digest)} chars, "
            f"case_type={case_type or 'unknown'}, "
            f"docs={len(extractions)}, "
            f"verified_laws={verified_citations['total_laws']}, "
            f"verified_articles={verified_citations['total_articles']}, "
            f"verified_pairs={verified_citations['total_pairs']}, "
            f"case={case_id}"
        )

        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}
        guardrail_reports: Dict[str, Any] = {}
        total_hallucinations_fixed = 0
        total_institutions_fixed = 0
        total_prefix_fixes = 0
        total_citation_fixes = 0
        total_attribution_fixes = 0
        all_deadline_contradictions: List[Dict[str, Any]] = []

        for section_key, section_cfg in SECTION_PROMPTS.items():
            section_start = time.time()
            section_title = section_cfg["title"]

            if progress_callback:
                try:
                    progress_callback("section_started", {
                        "section_key": section_key,
                        "section_title": section_title,
                    })
                except Exception:
                    pass

            try:
                raw_content = self._synthesize_section_streaming(
                    section_key=section_key,
                    section_cfg=section_cfg,
                    digest=digest,
                    case=case,
                    stream_callback=section_stream_callback,
                )

                content, fix_stats = self._post_process_output(
                    raw_content, canonical
                )
                total_hallucinations_fixed += fix_stats.get("hallucinations_fixed", 0)
                total_institutions_fixed += fix_stats.get("institutions_fixed", 0)
                total_prefix_fixes += fix_stats.get("prefix_fixes", 0)

                # ═══ GUARDRAILS #3, #4, #5 për sections që citojnë nene ═══
                if section_key in ("legal_framework", "recommendations", "executive_summary", "key_findings_contradictions") and content:
                    logger.info(f"🔍 [GUARDRAILS] Checking {section_key}...")

                    # #4: Verifiko numrat e neneve
                    checker_report = self._verify_citations_word_by_word(
                        content, doc_articles_available
                    )

                    # #5: Verifiko atribuimin
                    attribution_report = self._verify_attribution_word_by_word(
                        content, verified_citations
                    )

                    # #5b: Kontradikta afatesh
                    deadline_report = self._detect_deadline_contradictions(content)

                    guardrail_reports[section_key] = {
                        "citations": checker_report,
                        "attributions": attribution_report,
                        "deadlines": deadline_report,
                    }

                    logger.info(
                        f"📊 [GUARDRAIL #4] {section_key}: "
                        f"citations_verified={len(checker_report['verified'])}, "
                        f"citations_unverified={len(checker_report['unverified'])}, "
                        f"attributions_unverified={len(attribution_report.get('unverified', []))}, "
                        f"deadlines_contradictions={len(deadline_report.get('contradictions', []))}"
                    )

                    # Track deadlines
                    if deadline_report.get("contradictions"):
                        all_deadline_contradictions.extend([
                            {**c, "section": section_key}
                            for c in deadline_report["contradictions"]
                        ])

                    # ═══ GUARDRAIL #3: Korrigjo me LLM ═══
                    has_citation_issues = bool(checker_report.get("unverified"))
                    has_attribution_issues = bool(attribution_report.get("unverified"))

                    if has_citation_issues or has_attribution_issues:
                        logger.info(
                            f"🔧 [GUARDRAIL #3] Correcting {section_key} — "
                            f"citations={len(checker_report.get('unverified', []))}, "
                            f"attributions={len(attribution_report.get('unverified', []))}"
                        )
                        corrected_content = self._correct_citations_with_llm(
                            content, checker_report, attribution_report, verified_citations
                        )

                        # Re-verify pas korrigjimit
                        report_after_cit = self._verify_citations_word_by_word(
                            corrected_content, doc_articles_available
                        )
                        report_after_attr = self._verify_attribution_word_by_word(
                            corrected_content, verified_citations
                        )
                        logger.info(
                            f"✅ [GUARDRAIL #3] {section_key} after correction: "
                            f"citations_hall_rate={report_after_cit['hallucination_rate']}%, "
                            f"attributions_hall_rate={report_after_attr.get('hallucination_rate', 0)}%"
                        )

                        total_citation_fixes += len(checker_report.get("unverified", []))
                        total_attribution_fixes += len(attribution_report.get("unverified", []))
                        content = corrected_content
                        guardrail_reports[section_key]["after_correction"] = {
                            "citations": report_after_cit,
                            "attributions": report_after_attr,
                        }

                sections[section_key] = {
                    "title": section_title,
                    "content": content,
                }
                section_stats[section_key] = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "content_length": len(content),
                    "hallucinations_fixed": fix_stats.get("hallucinations_fixed", 0),
                    "institutions_fixed": fix_stats.get("institutions_fixed", 0),
                    "prefix_fixes": fix_stats.get("prefix_fixes", 0),
                }

                if progress_callback:
                    try:
                        progress_callback("section_completed", {
                            "section_key": section_key,
                            "section_title": section_title,
                            "content_length": len(content),
                        })
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"❌ [SYNTHESIS] Section {section_key} failed: {e}")
                sections[section_key] = {
                    "title": section_title,
                    "content": "",
                    "error": str(e),
                }
                section_stats[section_key] = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "error": str(e),
                }

        duration = round(time.time() - start, 2)

        result = {
            "case_id": case_id,
            "scope": "case",
            "case_type": case_type,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "case_title": case.get("title") or case.get("case_name"),
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "scope": "case",
                "case_type": case_type,
                "documents_analyzed": len(extractions),
                "digest_chars": len(digest),
                "defendant_groups_count": len(defendants_groups),
                "defendants_total": sum(
                    len(g.get("defendants", [])) for g in defendants_groups
                ),
                "article_laws_count": len(articles_by_law),
                "article_descriptions_count": total_articles,
                "verified_laws_count": verified_citations["total_laws"],
                "verified_articles_count": verified_citations["total_articles"],
                "verified_pairs_count": verified_citations["total_pairs"],
                "canonical_persons": canonical.stats()["persons"],
                "canonical_organizations": canonical.stats()["organizations"],
                "hallucinations_fixed": total_hallucinations_fixed,
                "institutions_fixed": total_institutions_fixed,
                "prefix_fixes": total_prefix_fixes,
                "citation_hallucinations_fixed": total_citation_fixes,
                "attribution_hallucinations_fixed": total_attribution_fixes,
                "deadline_contradictions": len(all_deadline_contradictions),
                "sections_generated": len([s for s in sections.values() if s.get("content")]),
                "sections_total": len(SECTION_PROMPTS),
                "duration_sec": duration,
            },
            "guardrail_reports": guardrail_reports,
            "regex_verified_citations": verified_citations,
            "deadline_contradictions": all_deadline_contradictions,
            "section_stats": section_stats,
            "status": "completed",
        }

        self._persist(result)

        logger.info(
            f"✅ [SYNTHESIS] Complete: case={case_id}, "
            f"case_type={case_type}, "
            f"hallucinations_fixed={total_hallucinations_fixed}, "
            f"citation_hallucinations_fixed={total_citation_fixes}, "
            f"attribution_hallucinations_fixed={total_attribution_fixes}, "
            f"deadline_contradictions={len(all_deadline_contradictions)}, "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"duration={duration}s"
        )

        return result

    # ────────────────────────────────────────────────────────────────────
    # CASE TYPE DETECTION
    # ────────────────────────────────────────────────────────────────────

    def _detect_case_type(
        self,
        case_id: str,
        extractions: List[Dict[str, Any]],
    ) -> Optional[str]:
        civil_found = False
        penal_found = False
        civil_evidence = None
        penal_evidence = None

        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            query = {
                "$or": [
                    {"case_id": case_id},
                    {"case_id": case_oid},
                    {"case_id": str(case_oid)},
                ],
                "status": {"$ne": "DELETED"},
            }
            docs = list(self.db.documents.find(query, {"file_name": 1}))

            for doc in docs:
                filename_lower = (doc.get("file_name") or "").lower()

                if not civil_found:
                    for kw in CASE_TYPE_FAMILIES["civil_family"]["filename_keywords"]:
                        if kw in filename_lower:
                            civil_found = True
                            civil_evidence = doc.get("file_name")
                            break

                if not penal_found:
                    for kw in CASE_TYPE_FAMILIES["penal_family"]["filename_keywords"]:
                        if kw in filename_lower:
                            penal_found = True
                            penal_evidence = doc.get("file_name")
                            break

                if civil_found and penal_found:
                    break

            if civil_found and penal_found:
                dual_type = (
                    f"{CASE_TYPE_FAMILIES['civil_family']['label']} → "
                    f"{CASE_TYPE_FAMILIES['penal_family']['label']}"
                )
                return dual_type
            elif civil_found:
                return CASE_TYPE_FAMILIES["civil_family"]["label"]
            elif penal_found:
                return CASE_TYPE_FAMILIES["penal_family"]["label"]

        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] Override scan failed: {e}")

        scores = defaultdict(float)
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            query = {
                "$or": [
                    {"case_id": case_id},
                    {"case_id": case_oid},
                    {"case_id": str(case_oid)},
                ],
                "status": {"$ne": "DELETED"},
            }

            cursor = self.db.documents.find(
                query,
                {"_id": 1, "content": 1, "extracted_text": 1, "text": 1},
            ).limit(CASE_TYPE_MAX_DOCS)

            for doc in cursor:
                text = (
                    doc.get("content")
                    or doc.get("extracted_text")
                    or doc.get("text")
                    or ""
                )
                if not text:
                    continue

                text_lower = text.lower()
                text_scannable = text_lower[:CASE_TYPE_SCAN_CHARS_PER_DOC]

                for case_type, cfg in CASE_TYPE_PATTERNS.items():
                    weight = cfg["weight"]
                    for pattern in cfg["patterns"]:
                        matches = len(re.findall(pattern, text_scannable, re.IGNORECASE))
                        if matches > 0:
                            scores[case_type] += matches * weight

        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] _detect_case_type scan failed: {e}")

        if not scores:
            return None

        best = max(scores.items(), key=lambda x: x[1])
        return best[0]

    # ────────────────────────────────────────────────────────────────────
    # BUILD CANONICAL ENTITIES
    # ────────────────────────────────────────────────────────────────────

    def _build_canonical_entities(self, extractions, defendants_groups):
        canonical = CanonicalEntities()

        for ext in extractions:
            ebt = ext.get("entities_by_type", {})
            for label, role_name in [
                ("PARTY", "Palë"),
                ("JUDGE", "Gjyqtar"),
                ("PROSECUTOR", "Prokuror"),
                ("LAWYER", "Avokat"),
                ("WITNESS", "Dëshmitar"),
            ]:
                for item in ebt.get(label, []):
                    name = (item.get("text") or "").strip()
                    if name:
                        canonical.add_person(name, role=role_name)

            for item in ebt.get("ORGANIZATION", []):
                name = (item.get("text") or "").strip()
                if name:
                    canonical.add_organization(name)

            for item in ebt.get("CASE_NUMBER", []):
                cn = (item.get("text") or "").strip()
                if cn:
                    canonical.add_case_number(cn)

        for ext in extractions:
            meta = ext.get("metadata") or {}
            for p in meta.get("parties", []):
                if not isinstance(p, dict):
                    continue
                name = (p.get("name") or "").strip()
                role = (p.get("role") or "").strip()
                if name:
                    canonical.add_person(name, role=role)

            court = meta.get("court")
            if court:
                canonical.add_organization(str(court).strip())

            judge = meta.get("judge")
            if judge:
                canonical.add_person(str(judge).strip(), role="Gjyqtar")

        for group in defendants_groups:
            for d in group.get("defendants", []):
                name = (d.get("name") or "").strip()
                role = (d.get("role") or "").strip()
                if name:
                    canonical.add_person(name, role=role)

        return canonical

    # ────────────────────────────────────────────────────────────────────
    # POST-PROCESSING
    # ────────────────────────────────────────────────────────────────────

    def _fix_prefix_duplication(self, content, canonical):
        if not content:
            return content, 0

        fixes_count = [0]

        pattern = re.compile(
            r'\b([A-ZËÇa-zëç]+)\s+\1\b',
            re.UNICODE | re.IGNORECASE,
        )

        def replacer(match):
            word = match.group(1)
            fixes_count[0] += 1
            return word

        for _ in range(3):
            new_content = pattern.sub(replacer, content)
            if new_content == content:
                break
            content = new_content

        return content, fixes_count[0]

    def _detect_and_fix_hallucinations(self, content, canonical):
        if not content or not canonical.persons:
            return content, 0

        fixes_count = 0

        name_pattern = re.compile(
            r'(?<![\w])('
            r'(?:Dr\.|Prof\.|Mr\.|Znj\.|Z\.|M\.Sc\.|Gjyqtari|Gjyqtarja|'
            r'Prokurori|Prokurorja|Avokati|Avokatja)\s+'
            r')?'
            r'([A-ZËÇ][a-zëç]+(?:\s+[A-ZËÇ][a-zëç]+){1,3})'
            r'(?![\w])',
            re.UNICODE
        )

        for match in list(name_pattern.finditer(content)):
            title_prefix = match.group(1) or ""
            name_only = match.group(2).strip()

            name_deduped = _dedup_adjacent_words(name_only)
            if name_deduped != name_only:
                content = content[:match.start()] + \
                    f"{title_prefix}{name_deduped}" + \
                    content[match.end():]
                fixes_count += 1
                continue

            is_known, _, _ = _is_known_entity(name_only, canonical)
            if is_known:
                continue

            best_match_key = None
            best_score = 0.0
            second_best_score = 0.0

            normalized_input = _normalize_for_match(name_only)
            if not normalized_input:
                continue

            for candidate_key in canonical.get_all_person_keys():
                score = max(
                    _similarity_with_boost(normalized_input, candidate_key),
                    _similarity_with_boost(name_only, candidate_key),
                )

                if score > best_score:
                    second_best_score = best_score
                    best_score = score
                    best_match_key = candidate_key
                elif score > second_best_score:
                    second_best_score = score

            if best_score < SIMILARITY_THRESHOLD:
                continue

            if (best_score - second_best_score) < SIMILARITY_AMBIGUITY_GAP and second_best_score >= SIMILARITY_THRESHOLD:
                continue

            canonical_entry = canonical.get_person(best_match_key)
            if not canonical_entry:
                continue

            canonical_name = canonical_entry["canonical"]
            replacement = f"{title_prefix}{canonical_name}"

            content = content[:match.start()] + replacement + content[match.end():]
            fixes_count += 1

        return content, fixes_count

    def _verify_institutions(self, content, canonical):
        if not content or not canonical.persons:
            return content, 0

        fixes_count = 0

        for person_key, person_entry in canonical.persons.items():
            known_institutions = person_entry.get("institutions", set())
            if not known_institutions:
                continue

            canonical_name = person_entry["canonical"]
            correct_inst = next(iter(known_institutions))

            start = 0
            while True:
                idx = content.find(canonical_name, start)
                if idx == -1:
                    break

                window_start = idx + len(canonical_name)
                window_end = min(len(content), window_start + INSTITUTION_CONTEXT_WINDOW)
                window = content[window_start:window_end]

                wrong_inst_found = None
                for org_key, org_entry in canonical.organizations.items():
                    org_canonical = org_entry["canonical"]
                    if org_canonical in window:
                        is_correct = any(
                            org_canonical.lower() in inst.lower()
                            or inst.lower() in org_canonical.lower()
                            for inst in known_institutions
                        )
                        if not is_correct:
                            wrong_inst_found = org_canonical
                            break

                if wrong_inst_found:
                    wrong_pos_in_window = window.find(wrong_inst_found)
                    if wrong_pos_in_window != -1:
                        abs_pos = window_start + wrong_pos_in_window
                        content = (
                            content[:abs_pos]
                            + correct_inst
                            + content[abs_pos + len(wrong_inst_found):]
                        )
                        fixes_count += 1

                start = idx + len(canonical_name)

        return content, fixes_count

    def _cleanup_placeholder_text(self, content):
        content = re.sub(
            r'(Neni\s+\d+(?:[\.\/]\d+)*)\s*[—\-:]\s*'
            r'\[(?:[^\]]*(?:panjohur|numri|përshkrim|N\/A|i panjohur|e panjohur)[^\]]*)\]\s*',
            r'\1 ',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r'(Neni\s+\d+(?:[\.\/]\d+)*)\s*[—\-:]\s*'
            r'\((?:[^)]*(?:panjohur|nuk dihet|pa përshkrim)[^)]*)\)\s*',
            r'\1 ',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(r'\[numri\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[përshkrim\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[Ligji i panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[i panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[e panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[N\/A\]', '', content, flags=re.IGNORECASE)
        return content

    def _post_process_output(self, content, canonical):
        if not content:
            return content, {
                "hallucinations_fixed": 0,
                "institutions_fixed": 0,
                "prefix_fixes": 0,
            }

        content = self._cleanup_placeholder_text(content)
        content, prefix_fixes = self._fix_prefix_duplication(content, canonical)
        content, hall_fixes = self._detect_and_fix_hallucinations(content, canonical)
        content, inst_fixes = self._verify_institutions(content, canonical)

        return content, {
            "hallucinations_fixed": hall_fixes,
            "institutions_fixed": inst_fixes,
            "prefix_fixes": prefix_fixes,
        }

    # ────────────────────────────────────────────────────────────────────
    # ARTICLES BY LAW
    # ────────────────────────────────────────────────────────────────────

    def _extract_articles_by_law(self, case_id: str) -> Dict[str, Dict[str, str]]:
        articles_by_law = defaultdict(dict)
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            query = {
                "$or": [
                    {"case_id": case_id},
                    {"case_id": case_oid},
                    {"case_id": str(case_oid)},
                ],
                "status": {"$ne": "DELETED"},
            }

            cursor = self.db.documents.find(
                query,
                {"_id": 1, "content": 1, "extracted_text": 1, "text": 1},
            )

            for doc in cursor:
                text = (
                    doc.get("content")
                    or doc.get("extracted_text")
                    or doc.get("text")
                    or ""
                )
                if not text:
                    continue
                self._process_document_articles(text, articles_by_law)

            return dict(articles_by_law)
        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] Could not extract articles: {e}")
            return {}

    def _process_document_articles(self, text, articles_by_law):
        law_positions = []
        for match in LAW_WITH_NUMBER_PATTERN.finditer(text):
            law_name = self._normalize_law_name(match.group(1))
            law_positions.append((match.start(), law_name))

        all_articles = []

        for match in MULTI_ARTICLE_PATTERN.finditer(text):
            nums_group = (match.group(1) or "") + (match.group(2) or "") + (match.group(3) or "")
            numbers = re.findall(r'\d+(?:[\.\/]\d+)*', nums_group)

            description = match.group(4)
            if description:
                description = re.sub(r'\s+', ' ', description).strip(" .,;:")
                if len(description) > 200:
                    description = description[:200].rstrip() + "..."
            else:
                description = None

            for num in numbers:
                all_articles.append((match.start(), f"Neni {num}", description))

        for match in SINGLE_ARTICLE_PATTERN.finditer(text):
            article_num = match.group(1).strip()
            law_hint = (match.group(3) or "").strip()
            if law_hint:
                law_hint = re.sub(
                    r'^\s*(?:i|të|te|e|së)\s+',
                    '',
                    law_hint,
                    flags=re.IGNORECASE,
                ).strip()

            description = match.group(4)
            if description:
                description = re.sub(r'\s+', ' ', description).strip(" .,;:")
                if len(description) > 200:
                    description = description[:200].rstrip() + "..."
            else:
                description = None

            all_articles.append((match.start(), f"Neni {article_num}", description))

        for article_pos, article_key, description in all_articles:
            attributed_law = self._find_nearest_law(law_positions, article_pos)
            if not attributed_law:
                attributed_law = "Ligji i Paidentifikuar"

            if article_key not in articles_by_law[attributed_law]:
                articles_by_law[attributed_law][article_key] = description or ""

            if sum(len(v) for v in articles_by_law.values()) >= MAX_ARTICLE_DESCRIPTIONS:
                return

    def _find_nearest_law(self, law_positions, article_pos):
        if not law_positions:
            return None
        best_law = None
        best_distance = float("inf")
        for law_pos, law_name in law_positions:
            if law_pos < article_pos:
                distance = article_pos - law_pos
                if distance < best_distance and distance <= LAW_CONTEXT_WINDOW:
                    best_distance = distance
                    best_law = law_name
        return best_law

    def _normalize_law_name(self, raw):
        raw = raw.strip()
        raw = re.sub(r'\bKPPK\b', 'KPPRK', raw, flags=re.IGNORECASE)
        return raw

    # ────────────────────────────────────────────────────────────────────
    # STREAMING SECTION
    # ────────────────────────────────────────────────────────────────────

    def _synthesize_section_streaming(
        self, section_key, section_cfg, digest, case, stream_callback=None
    ):
        case_title = case.get("title") or case.get("case_name") or "Lënda"
        client_name = case.get("client_name") or "Klienti"

        system_prompt = f"""Ti je "Juristi AI - Asistenti Ligjor i Kosovës".

LËNDA: {case_title}
KLIENTI: {client_name}

{section_cfg['prompt']}

FORMATIMI:
- Përdor markdown me tituj (##, ###).
- Përfshi referenca specifike.
- Shkruaj në shqip standarde juridike.
- Mos shpik — bazohu VETËM në digest.
"""

        user_content = f"""DIGEST I LËNDËS:

{digest}

───────────────────────────────────────────────────────

DETYRA: Harto seksionin "{section_cfg['title']}"."""

        accumulated = ""
        buffer = ""
        last_emit = time.time()
        stream_succeeded = False

        try:
            for chunk in _stream_section_sync(system_prompt, user_content, temperature=0.1):
                stream_succeeded = True
                accumulated += chunk
                buffer += chunk
                now = time.time()
                if len(buffer) >= STREAM_BATCH_CHARS or (now - last_emit) >= STREAM_BATCH_INTERVAL_SEC:
                    if stream_callback and buffer:
                        try:
                            stream_callback(section_key, buffer)
                        except Exception:
                            pass
                    buffer = ""
                    last_emit = now
            if buffer and stream_callback:
                try:
                    stream_callback(section_key, buffer)
                except Exception:
                    pass
            return accumulated
        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] Streaming failed for {section_key}: {e}")
            if not stream_succeeded and not accumulated:
                try:
                    raw = _call_llm(
                        system_prompt=system_prompt,
                        user_content=user_content,
                        json_mode=False,
                        temperature=0.1,
                        model=FAST_SEARCH_MODEL,
                    )
                    accumulated = raw or ""
                    if stream_callback and accumulated:
                        try:
                            stream_callback(section_key, accumulated)
                        except Exception:
                            pass
                except Exception as e2:
                    logger.error(f"❌ [SYNTHESIS] Fallback also failed: {e2}")
                    raise
            return accumulated

    # ────────────────────────────────────────────────────────────────────
    # DIGEST
    # ────────────────────────────────────────────────────────────────────

    def _build_digest(
        self, case, extractions, xrefs, defendants_groups,
        articles_by_law, case_type=None, verified_citations=None,
    ):
        lines = []

        lines.append("=" * 70)
        lines.append("TË DHËNAT E LËNDËS")
        lines.append("=" * 70)
        lines.append(f"Titulli: {case.get('title') or case.get('case_name') or 'N/A'}")
        lines.append(f"Klienti: {case.get('client_name') or 'N/A'}")
        lines.append(f"Numri i dokumenteve: {len(extractions)}")
        lines.append("")

        # ═══ GUARDRAIL #2b: CITIMET E VËRTETUARA ═══
        if verified_citations:
            lines.append("=" * 70)
            lines.append("🔒 CITIMET E VËRTETUARA NGA DOKUMENTET (REGEX EXTRACTION)")
            lines.append("=" * 70)
            lines.append(
                "⚠️ KY ËSHTË BURIMI I VETËM I SË VËRTETËS. "
                "NUK LEJOHET TË SHPIKËSH LIGJE APO NENE QË NUK SHFAQEN KËTU."
            )
            lines.append("")

            lines.append(f"LIGJET E CITUARA ({verified_citations['total_laws']}):")
            if verified_citations["laws"]:
                for law in verified_citations["laws"]:
                    lines.append(f"  • {law}")
            else:
                lines.append("  (asnjë ligj i cituar në dokumente)")
            lines.append("")

            lines.append(f"NENET E CITUARA ({verified_citations['total_articles']}):")
            if verified_citations["articles"]:
                shown = set()
                for art in verified_citations["articles"][:60]:
                    par = f", par. {art['paragraph']}" if art.get("paragraph") else ""
                    doc_name = art.get("doc_name", "")
                    key = f"{art['number']}{par}"
                    if key in shown:
                        continue
                    shown.add(key)
                    lines.append(f"  • Neni {art['number']}{par}  [në: {doc_name}]")
            else:
                lines.append("  (asnjë nen i cituar në dokumente)")
            lines.append("")

            # V3.8: Çiftet e vërteta
            if verified_citations.get("article_law_pairs"):
                lines.append(f"ÇIFTET E VËRTETA (Neni X i Ligji) ({verified_citations['total_pairs']}):")
                for art, law in verified_citations["article_law_pairs"][:60]:
                    lines.append(f"  • Neni {art} i {law}")
                lines.append("")

            lines.append(
                "⚠️ RREGULL ABSOLUT: Përdor VETËM ligjet dhe nenet e mësipërme. "
                "ÇDO ligj/nen që nuk është në këtë listë KONSIDEROHET HALUDINACION."
            )
            lines.append("")

        if case_type:
            lines.append("=" * 70)
            lines.append("🎯 LLOJI I LËNDËS")
            lines.append("=" * 70)
            lines.append(f"**{case_type}**")
            if "→" in case_type:
                lines.append(
                    "Ky është një rast i DYFISHTË që ka evoluar nga "
                    "procedura civile (urdhër mbrojtjeje) në procedurë penale."
                )
            lines.append("")

        primary_doc = self._find_primary_document(extractions)
        if primary_doc:
            lines.append("=" * 70)
            lines.append(f"📄 DOKUMENTI KRYESOR: {primary_doc.get('file_name', 'N/A')}")
            lines.append("=" * 70)
            lines.append("")

        lines.append("=" * 70)
        lines.append("INDEKSI I DOKUMENTEVE")
        lines.append("=" * 70)
        for i, ext in enumerate(extractions, 1):
            marker = " ⭐ [KRYESOR]" if ext is primary_doc else ""
            lines.append(
                f"{i}. {ext.get('file_name', 'N/A')} "
                f"[{ext.get('document_type', 'N/A')}] "
                f"({ext.get('text_length', 0):,} chars){marker}"
            )
        lines.append("")

        if defendants_groups:
            self._append_defendants_groups(lines, defendants_groups)

        self._append_parties_excluding_defendants(lines, extractions, defendants_groups)

        if articles_by_law:
            self._append_articles_by_law(lines, articles_by_law)

        sc_decisions = self._extract_supreme_court_decisions(extractions)
        if sc_decisions:
            lines.append("=" * 70)
            lines.append("🏛️ AKTGJYKIMET E GJYKATËS SUPREME")
            lines.append("=" * 70)
            for d in sc_decisions:
                lines.append(f"  • {d}")
            lines.append("")

        if xrefs:
            self._append_cross_references(lines, xrefs)

        digest = "\n".join(lines)

        if len(digest) > MAX_DIGEST_CHARS:
            digest = digest[:MAX_DIGEST_CHARS] + "\n\n[...digest truncated...]"

        return digest

    def _append_articles_by_law(self, lines, articles_by_law):
        total = sum(len(v) for v in articles_by_law.values())

        lines.append("=" * 70)
        lines.append("📖 KONTEKSTI I NENEVE NË DOKUMENTE (JO PËRSHKRIME ZYRTARE)")
        lines.append("=" * 70)
        lines.append(
            f"Ky seksion përmban {total} nene me KONTEKST DOKUMENTI (jo përshkrime zyrtare)."
        )
        lines.append(
            "⚠️ KONTEKSTI ËSHTË JOZYRTAR. NËSE citon në raport → shkruaj "
            "VETËM 'Neni X i [Ligjit]' PA përshkrim."
        )
        lines.append("")

        for law_name in sorted(articles_by_law.keys()):
            articles = articles_by_law[law_name]
            if not articles:
                continue
            lines.append(f"**{law_name}:**")
            for article_key in sorted(articles.keys()):
                desc = articles[article_key]
                if desc:
                    lines.append(f"  • {article_key} — [KONTEKST DOKUMENTI: {desc}]")
                else:
                    lines.append(f"  • {article_key} (pa kontekst)")
            lines.append("")

    def _append_parties_excluding_defendants(self, lines, extractions, defendants_groups):
        defendant_names = set()
        for group in defendants_groups:
            for d in group.get("defendants", []):
                name = (d.get("name") or "").strip().lower()
                if name:
                    defendant_names.add(name)

        parties_raw = {}
        for ext in extractions:
            ebt = ext.get("entities_by_type", {})
            for item in ebt.get("PARTY", []):
                text = (item.get("text") or "").strip()
                if not text:
                    continue
                key = text.lower()
                if key not in parties_raw:
                    parties_raw[key] = text

        filtered = [v for k, v in parties_raw.items() if k not in defendant_names]

        if filtered:
            lines.append("=" * 70)
            lines.append("👥 PALËT NDËRGYQËSE")
            lines.append("=" * 70)
            for p in sorted(filtered):
                lines.append(f"  • {p}")
            lines.append("")

    def _append_defendants_groups(self, lines, defendants_groups):
        total = sum(len(g.get("defendants", [])) for g in defendants_groups)

        lines.append("=" * 70)
        lines.append("⚖️ GRUPET E TË PANDËHURVE")
        lines.append("=" * 70)
        lines.append(f"Total: {total} të pandehur në {len(defendants_groups)} grupe.")
        lines.append("")

        for group in defendants_groups:
            group_key = group.get("group", "?")
            title = group.get("title", "")
            lines.append(f"GRUPI {group_key}: {title}")
            for d in group.get("defendants", []):
                num = d.get("number", "")
                name = d.get("name", "")
                role = d.get("role", "")
                lines.append(f"  {num}. {name} — {role}")
            lines.append("")

    def _find_primary_document(self, extractions):
        priorities = [
            ("kallëzim", "kallzim"),
            ("aktakuzë", "aktakuze"),
            ("padi", "kërkesëpadi"),
            ("aktgjykim", "aktvendim"),
        ]
        for keywords in priorities:
            for ext in extractions:
                doc_type = (ext.get("document_type") or "").lower()
                if any(kw in doc_type for kw in keywords):
                    return ext
        if extractions:
            return max(extractions, key=lambda e: e.get("text_length", 0))
        return None

    def _extract_supreme_court_decisions(self, extractions):
        decisions = set()
        for ext in extractions:
            ebt = ext.get("entities_by_type", {})
            for item in ebt.get("CASE_NUMBER", []):
                text = (item.get("text") or "").strip()
                if not text:
                    continue
                if re.match(r'^(PML|Rev)\.?\s*[Nn]r', text, re.IGNORECASE):
                    decisions.add(text)
        return sorted(decisions)

    def _append_cross_references(self, lines, xrefs):
        lines.append("=" * 70)
        lines.append("LIDHJET MIDIS DOKUMENTEVE")
        lines.append("=" * 70)
        doc_refs = xrefs.get("document_references", [])
        if doc_refs:
            for ref in doc_refs[:20]:
                lines.append(
                    f"  • '{ref.get('source_file_name')}' → "
                    f"'{ref.get('target_file_name')}'"
                )
        lines.append("")

    # ────────────────────────────────────────────────────────────────────
    # LOADERS
    # ────────────────────────────────────────────────────────────────────

    def _load_case(self, case_id):
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            doc = self.db.cases.find_one({"_id": c_oid})
            return doc or {}
        except Exception:
            return {}

    def _load_extractions(self, case_id):
        try:
            query = {"case_id": str(case_id), "status": "completed"}
            cursor = self.db[EXTRACTION_COLLECTION].find(query).sort([("completed_at", 1)])
            return list(cursor)
        except Exception:
            return []

    def _load_cross_refs(self, case_id):
        try:
            doc = self.db[CROSS_REF_COLLECTION].find_one({"case_id": str(case_id)})
            return doc or {}
        except Exception:
            return {}

    # ────────────────────────────────────────────────────────────────────
    # PERSIST
    # ────────────────────────────────────────────────────────────────────

    def _persist(self, result):
        try:
            self.db[SYNTHESIS_COLLECTION].update_one(
                {"case_id": result["case_id"], "scope": "case"},
                {"$set": result},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"❌ [SYNTHESIS] Persist failed: {e}")
            raise

    def _empty_result(self, case_id, reason):
        return {
            "case_id": case_id,
            "scope": "case",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "sections": {},
            "stats": {
                "case_id": case_id,
                "scope": "case",
                "documents_analyzed": 0,
                "sections_generated": 0,
                "sections_total": len(SECTION_PROMPTS),
                "duration_sec": 0.0,
            },
            "status": "empty",
            "warning": reason,
        }

    def load(self, case_id):
        try:
            return self.db[SYNTHESIS_COLLECTION].find_one({
                "case_id": str(case_id),
                "scope": "case",
            })
        except Exception:
            return None


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_synthesis_service(db):
    return SynthesisService(db)