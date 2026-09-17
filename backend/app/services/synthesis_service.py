# FILE: backend/app/services/synthesis_service.py
# PHOENIX PROTOCOL - SYNTHESIS SERVICE V3.6
# V3.6: Dual case type detection — "Kërkesë për Urdhër Mbrojtjeje → Procedurë Penale"
#       when both civil (mbrojtje) and penal (aktakuzë) keywords exist.

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
    DEEP_ANALYSIS_MODEL,
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
    r'(?:KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT)\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r')',
    re.IGNORECASE
)

LAW_ABBREVIATION_PATTERN = re.compile(
    r'\b(KPPRK|KPRK|LPK|LMD|LFK|LSHT|Kushtetuta)\b',
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
            r"parandalimi\s+dhe\s+mbrojtja\s+nga\s+dhuna",
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
            r"kontakt(?:i)?\s+me\s+f[eë]mij[eë]n",
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


# ────────────────────────────────────────────────────────────────────────────
# V3.6 — DUAL CASE TYPE FAMILIES
# ────────────────────────────────────────────────────────────────────────────

# Keywords që tregojnë praninë e një familje ligjore në fashikull.
# Nëse ka BOTH families → case type i dyfishtë me shigjetë.

CASE_TYPE_FAMILIES = {
    "civil_family": {
        "label": "Kërkesë për Urdhër Mbrojtjeje",
        "filename_keywords": [
            "mbrojtje", "mbrojtjes", "mbrojtës", "mbrojtes",
            "vendim_per_urdher", "urdher_mbrojtje", "urdhermbrojtje",
            "dhune", "dhunë", "dhuna",
            "familje", "familjar", "familjare",
            "shkurorëzim", "shkurorezim", "divorc",
            "kujdestari",
        ],
    },
    "penal_family": {
        "label": "Procedurë Penale",
        "filename_keywords": [
            "aktakuz", "aktakuze",
            "kallzim", "kallëzim", "kallzim_penal",
            "kerkese_per_hudhje", "kërkesë_për_hedhje",
            "hedhje_akuz", "hedhjes_se_akuz",
            "refuzimi_e_hedhjes",
            "penale", "penal",
            "prokuror",
            "pandehur", "padisur",
        ],
    },
}


# ────────────────────────────────────────────────────────────────────────────
# STRICT RULES
# ────────────────────────────────────────────────────────────────────────────

STRICT_RULES = """
⚠️  RREGULLA TË PAFEKSIONUESHME:

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

5. ⚠️  RREGULL ABSOLUT PËR NENET E LIGJEVE:
   - NËSE DIGEST-i përmban seksionin "📖 PËRSHKRIMET E NENEVE", 
     përdor VETËM përshkrimet që janë aty.
   - NËSE një nen shfaqet VETËM si numër (pa përshkrim), shkruaj VETËM 
     "Neni X i [Ligjit]" — PA shpikje përshkrimi.
   - NUK LEJOHET të shpikësh, interpretosh ose riformulosh përshkrime 
     neni që nuk janë në digest.
   - SHEMBULL I GABIMIT:
        ❌ "Neni 3 par.4: Definimi i palës së mbrojtur." (i shpikur)
        ❌ "Neni 1.2 i LMDHF" (format i gabuar — neni nuk është 1.2)
        ✅ "Neni 3 i LMDHF" (vetëm numri, pa përshkrim)
        ✅ "Neni 6 i LMDHF"
   - NUK LEJOHET: "[numri]", "[Ligji i panjohur]", "[i panjohur]", 
     "(i panjohur)", "[N/A]".

6. PËR AKTGJYKIMET E GJYKATËS SUPREME: cito TË GJITHA nga seksioni 
   "AKTGJYKIMET E GJYKATËS SUPREME".

7. PËR TË PANDËHURIT: NËSE digest-i përmban "GRUPET E TË PANDËHURVE", 
   raportoji të gjithë sipas grupeve — ME NUMRIN, EMRI DHE ROLI.
   NËSE NUK përmban grupet, shkruaj "Nuk ka të pandehur të identifikuar" 
   — MOS shpik.

8. ⚠️  LLOJI I LËNDËS (KRITIK):
   - NËSE digest-i përmban seksionin "🎯 LLOJI I LËNDËS", ky është 
     lloji i saktë i lëndës.
   - PËRDOR atë lloj në të gjithë raportin — MOS e ndrysho.
   - NËSE lloji është i dyfishtë (p.sh. "Kërkesë për Urdhër Mbrojtjeje → 
     Procedurë Penale"), pasqyro të DYJA fazat në analizë:
        * Faza 1: Procedura civile (urdhër mbrojtjeje)
        * Faza 2: Procedura penale (aktakuza, hedhja e saj)
   - Lloji i lëndës përcakton TERMINOLOGJINË:
        * Kallëzim Penal → "i pandehur", "prokuror", "vepër penale"
        * Padi Civile → "paditës", "i paditur", "kërkesëpadi"
        * Kërkesë për Urdhër Mbrojtjeje → "palë e mbrojtur", 
          "palë përgjegjëse", "masa mbrojtëse"
        * Procedurë Penale → "i pandehur", "prokuror", "aktakuzë"
        * I dyfishtë → përdor terminologjinë e duhur për secilën fazë
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
- Shëno afatet procedurale
- Refero dokumentin specifik
- NËSE lënda ka fazë civile + penale, dalloji fazat në kronologji

FORMATI:
[Data] — [Ngjarja] — [Rëndësia] — [Referenca dokumenti]

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
  NËSE NUK përmban grupet, shkruaj "Nuk ka të pandehur të identifikuar"
  — MOS shpik.
- Përfaqësuesit ligjorë (avokatët) — ME KUIDES:
    * VETËM personat me titull "avokat/avokate" ose "përfaqësues ligjor"
    * NUK lejohet klasifikimi i punonjësve socialë, zyrtarëve ZMV, 
      ose ekspertëve si avokatë.
- Zyrtarët gjyqësorë — ME INSTITUCIONIN E SAKTË
- Ekspertët (mjekësorë, psikiatër, psikologë)
- Dëshmitarët e mundshëm
- Organizatat/institucionet

⚠️  TERMINOLOGJIA varet nga LLOJI I LËNDËS (shih seksionin 🎯).

⚠️  DEDUP: NËSE një emër shfaqet si "Elda" dhe "Elda Bala", 
bashkoji në formën e plotë.

""" + STRICT_RULES,
    },

    "legal_framework": {
        "title": "KUADRI LIGJOR DHE NENET",
        "max_tokens": 2600,
        "prompt": """Ti je jurist ekspert në legjislacionin e Kosovës. Bazuar në 
digest-in, harto KUADRIN LIGJOR.

⚠️  RREGULL ABSOLUT PËR NENET:
- Seksioni "📖 PËRSHKRIMET E NENEVE" i digest-it i ka nenet 
  TË GRUPUARA SIPAS LIGJIT.
- Për ÇDO nen, ATRIBUOJE VETËM në ligjin që shfaqet në atë seksion.
- NËSE një nen shfaqet VETËM si "Neni X" (pa përshkrim), shkruaj VETËM:
    "Neni X i [Ligjit]"
  PA shpikje përshkrimi.
- NUK LEJOHET: "[numri]", "[Ligji i panjohur]", "[i panjohur]", 
  "(i panjohur)", "[N/A]".
- SHEMBUJ TË GABIMEVE QË DUHEN SHMANGUR:
    ❌ "Neni 1.2: Përcaktimi i qëllimit të ligjit." (përshkrim + format i gabuar)
    ❌ "Neni 6.par.1: Procedurat për lëshimin..." (përshkrim + format i gabuar)
  SAKTË:
    ✅ "Neni 1 i LMDHF"
    ✅ "Neni 6 i LMDHF"

DETYRA:
- Ligjet kryesore me numra
- Nenet sipas ligjit të saktë
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
   Për ÇDO opsion të aplikueshëm, jep:
   
   1. **Ankesë** (nëse ka vendim të formës së prerë në fashikull)
      - Kundër cilit vendim?
      - Në cilin organ (Gjykata e Apelit / Gjykata Supreme)?
      - Cilat arsye ligjore (cito nenet)?
      - Afati ligjor?
      - Mundësia e suksesit: E LARTË / E MESME / E ULËT
   
   2. **Kundërpadi** (nëse pala kundërshtare ka paraqitur padi)
      - Kundër kujt?
      - Cilat kërkesa konkrete?
      - Baza ligjore?
      - Afati?
      - Mundësia e suksesit: E LARTË / E MESME / E ULËT
   
   3. **Kallëzim Penal** (nëse fashikulli tregon vepra penale nga zyrtarë)
      - Kundër cilëve persona konkret?
      - Cilat vepra penale (cito nenet e KPRK-së)?
      - Cilat prova e mbështesin?
      - Në cilin organ (Prokuroria Themelore / Speciale)?
      - Afati?
      - Mundësia e suksesit: E LARTË / E MESME / E ULËT
   
   4. **Kthim në Afat** (nëse ka skaduar afat për shkak pengesash)
      - Për cilat veprime?
      - Bazat ligjore?
      - Mundësia e suksesit: E LARTË / E MESME / E ULËT
   
   5. **Mjet Tjetër Juridik** (revizion, kërkesë kushtetuese, etj.)
      - Nëse aplikueshme
      - Arsyeja + afati + mundësia

C. REKOMANDIMI PËRFUNDIMTAR
   Bazuar në analizën e mësipërme, jep VEPRIMIN KRYESOR të rekomanduar:
   
   ▶ VEPRIMI KRYESOR: [Ankesë / Kundërpadi / Kallëzim Penal / Mjet tjetër]
   ▶ ARSYEJA: [2-3 fjali që justifikojnë zgjedhjen]
   ▶ HAPAT KONKRET (1, 2, 3, ...):
      1. [Hapi 1] — afati: [data] — përgjegjësi: [kush]
      2. [Hapi 2] — afati: [data]
      3. ...
   ▶ AFATET KRITIKE: listo të gjitha afatet ligjore që skadojnë
   ▶ RREZIQET: [çfarë mund të shkojë keq nëse nuk veprohet]

⚠️  RREGULLA:
- NUK shpik nene, afate ose procedura që nuk gjenden në ligjin pozitiv 
  të Kosovës.
- NUK rekomandon kallëzim penal nëse fashikulli nuk tregon vepra penale.
- NUK rekomandon kundërpadi nëse nuk ka bazë procedurale.
- Cito SAKTËSISHT nenet dhe afatet.

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
# DEDUP ADJACENT WORDS
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


# ────────────────────────────────────────────────────────────────────────────
# SIMILARITY HELPERS
# ────────────────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────────────────
# SYNC STREAMING
# ────────────────────────────────────────────────────────────────────────────

def _stream_section_sync(system_prompt, user_content, temperature=0.1):
    if not _get_api_key():
        return
    full_sys = _prepare_system_prompt(system_prompt)
    sanitized = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()
    try:
        stream = client.chat.completions.create(
            model=DEEP_ANALYSIS_MODEL,
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
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class SynthesisService:
    """
    V3.6 — Dual case type detection.
    """

    def __init__(self, db):
        self.db = db
        self.defendant_extractor = get_defendant_group_extractor(db)

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

        digest = self._build_digest(
            case, extractions, xrefs, defendants_groups,
            articles_by_law, case_type
        )
        logger.info(
            f"🔍 [SYNTHESIS] Digest built: {len(digest)} chars, "
            f"case_type={case_type or 'unknown'}, "
            f"docs={len(extractions)}, "
            f"defendant_groups={len(defendants_groups)}, "
            f"defendants={sum(len(g.get('defendants', [])) for g in defendants_groups)}, "
            f"articles_by_law={len(articles_by_law)} laws, "
            f"total_articles={total_articles}, "
            f"case={case_id}"
        )

        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}
        total_hallucinations_fixed = 0
        total_institutions_fixed = 0
        total_prefix_fixes = 0

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
                "canonical_persons": canonical.stats()["persons"],
                "canonical_organizations": canonical.stats()["organizations"],
                "hallucinations_fixed": total_hallucinations_fixed,
                "institutions_fixed": total_institutions_fixed,
                "prefix_fixes": total_prefix_fixes,
                "sections_generated": len([s for s in sections.values() if s.get("content")]),
                "sections_total": len(SECTION_PROMPTS),
                "duration_sec": duration,
            },
            "section_stats": section_stats,
            "status": "completed",
        }

        self._persist(result)

        logger.info(
            f"✅ [SYNTHESIS] Complete: case={case_id}, "
            f"case_type={case_type}, "
            f"hallucinations_fixed={total_hallucinations_fixed}, "
            f"institutions_fixed={total_institutions_fixed}, "
            f"prefix_fixes={total_prefix_fixes}, "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"duration={duration}s"
        )

        return result

    # ────────────────────────────────────────────────────────────────────
    # V3.6 — DUAL CASE TYPE DETECTION
    # ────────────────────────────────────────────────────────────────────

    def _detect_case_type(
        self,
        case_id: str,
        extractions: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        V3.6: Detekton llojin e lëndës:
          1. Scan TË GJITHA dokumentet për keywords të familjeve ligjore
          2. Nëse ka BOTH civil + penal → dual case type me shigjetë
          3. Nëse ka vetëm një → case type i vetëm
          4. Fallback: score-based detection
        """
        # ═══ HAPI 1: Scan TË GJITHA dokumentet për families ═══
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

                # Kontrollo civil family
                if not civil_found:
                    for kw in CASE_TYPE_FAMILIES["civil_family"]["filename_keywords"]:
                        if kw in filename_lower:
                            civil_found = True
                            civil_evidence = doc.get("file_name")
                            break

                # Kontrollo penal family
                if not penal_found:
                    for kw in CASE_TYPE_FAMILIES["penal_family"]["filename_keywords"]:
                        if kw in filename_lower:
                            penal_found = True
                            penal_evidence = doc.get("file_name")
                            break

                if civil_found and penal_found:
                    break

            # Log findings
            if civil_found:
                logger.info(
                    f"🎯 [SYNTHESIS] Civil family found: "
                    f"'{civil_evidence}'"
                )
            if penal_found:
                logger.info(
                    f"🎯 [SYNTHESIS] Penal family found: "
                    f"'{penal_evidence}'"
                )

            # Decision: dual or single
            if civil_found and penal_found:
                dual_type = (
                    f"{CASE_TYPE_FAMILIES['civil_family']['label']} → "
                    f"{CASE_TYPE_FAMILIES['penal_family']['label']}"
                )
                logger.info(
                    f"🎯 [SYNTHESIS] DUAL case type detected: '{dual_type}'"
                )
                return dual_type
            elif civil_found:
                logger.info(
                    f"🎯 [SYNTHESIS] Case type: "
                    f"'{CASE_TYPE_FAMILIES['civil_family']['label']}'"
                )
                return CASE_TYPE_FAMILIES["civil_family"]["label"]
            elif penal_found:
                logger.info(
                    f"🎯 [SYNTHESIS] Case type: "
                    f"'{CASE_TYPE_FAMILIES['penal_family']['label']}'"
                )
                return CASE_TYPE_FAMILIES["penal_family"]["label"]

        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] Override scan failed: {e}")

        # ═══ HAPI 2: Score-based fallback ═══
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

            total_chars = 0
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
                total_chars += len(text_lower)
                text_scannable = text_lower[:CASE_TYPE_SCAN_CHARS_PER_DOC]

                for case_type, cfg in CASE_TYPE_PATTERNS.items():
                    weight = cfg["weight"]
                    for pattern in cfg["patterns"]:
                        matches = len(re.findall(pattern, text_scannable, re.IGNORECASE))
                        if matches > 0:
                            scores[case_type] += matches * weight

            logger.info(
                f"🎯 [SYNTHESIS] Case type scan: "
                f"{total_chars} chars from documents"
            )
        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] _detect_case_type scan failed: {e}")

        if not scores:
            return None

        top_3 = sorted(scores.items(), key=lambda x: -x[1])[:3]
        logger.info(
            f"🎯 [SYNTHESIS] Case type scores (no override): {dict(top_3)}"
        )

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
                    institution = None
                    if "—" in role:
                        parts = role.split("—", 1)
                        if len(parts) == 2:
                            institution = parts[1].strip()
                    elif "," in role:
                        institution = role
                    canonical.add_person(name, role=role, institution=institution)

        return canonical

    # ────────────────────────────────────────────────────────────────────
    # ADJACENT WORD DEDUP
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
            logger.info(
                f"🔧 [SYNTHESIS] Adjacent word deduped: "
                f"'{word} {word}' → '{word}'"
            )
            return word

        for _ in range(3):
            new_content = pattern.sub(replacer, content)
            if new_content == content:
                break
            content = new_content

        return content, fixes_count[0]

    # ────────────────────────────────────────────────────────────────────
    # HALLUCINATION DETECTION
    # ────────────────────────────────────────────────────────────────────

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
            full_match = match.group(0)
            title_prefix = match.group(1) or ""
            name_only = match.group(2).strip()

            name_deduped = _dedup_adjacent_words(name_only)
            if name_deduped != name_only:
                content = content[:match.start()] + \
                    f"{title_prefix}{name_deduped}" + \
                    content[match.end():]
                fixes_count += 1
                logger.info(
                    f"🔧 [SYNTHESIS] Adjacent dedup: "
                    f"'{name_only}' → '{name_deduped}'"
                )
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
                logger.warning(
                    f"⚠️ [SYNTHESIS] Ambiguous match for '{name_only}': "
                    f"best='{best_match_key}' ({best_score:.2f}), "
                    f"second={second_best_score:.2f}. Skipping."
                )
                continue

            canonical_entry = canonical.get_person(best_match_key)
            if not canonical_entry:
                continue

            canonical_name = canonical_entry["canonical"]
            replacement = f"{title_prefix}{canonical_name}"

            content = content[:match.start()] + replacement + content[match.end():]
            fixes_count += 1

            logger.info(
                f"🔧 [SYNTHESIS] Hallucination fixed: "
                f"'{name_only}' → '{canonical_name}' (similarity: {best_score:.2f})"
            )

        return content, fixes_count

    # ────────────────────────────────────────────────────────────────────
    # INSTITUTION VERIFICATION
    # ────────────────────────────────────────────────────────────────────

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
                        logger.info(
                            f"🔧 [SYNTHESIS] Institution fixed for '{canonical_name}': "
                            f"'{wrong_inst_found}' → '{correct_inst}'"
                        )

                start = idx + len(canonical_name)

        return content, fixes_count

    # ────────────────────────────────────────────────────────────────────
    # PLACEHOLDER CLEANUP
    # ────────────────────────────────────────────────────────────────────

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
        content = re.sub(
            r'(Neni\s+\d+(?:[\.\/]\d+)*)\s+i\s+'
            r'\[(?:[^\]]*(?:panjohur|i panjohur|e panjohur)[^\]]*)\]\s*',
            r'\1 ',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(r'\[numri\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[përshkrim\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[përshkrimi\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[Ligji i panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[Ligj i panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[i panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[e panjohur\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[N\/A\]', '', content, flags=re.IGNORECASE)
        content = re.sub(
            r'\s*[—\-:]\s*\[(?:[^\]]*?(?:panjohur|numri|përshkrim|N\/A)[^\]]*?)\]\s*',
            ' ',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r'(\*\*\[Ligji\s+Nr\.?\s+[^\]]+\]\*\*)\s*[—\-:]\s*'
            r'\[(?:[^\]]*(?:panjohur|i panjohur|N\/A)[^\]]*)\]\s*',
            r'\1',
            content,
            flags=re.IGNORECASE,
        )
        return content

    # ────────────────────────────────────────────────────────────────────
    # POST-PROCESSING
    # ────────────────────────────────────────────────────────────────────

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

            total = sum(len(v) for v in articles_by_law.values())
            logger.info(
                f"📖 [SYNTHESIS] Extracted {total} article descriptions "
                f"across {len(articles_by_law)} laws"
            )
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
            full_match = match.group(0)
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
                        except Exception as e:
                            logger.warning(f"⚠️ stream_callback failed: {e}")
                    buffer = ""
                    last_emit = now
            if buffer and stream_callback:
                try:
                    stream_callback(section_key, buffer)
                except Exception as e:
                    logger.warning(f"⚠️ stream_callback (flush) failed: {e}")
            return accumulated
        except Exception as e:
            logger.warning(
                f"⚠️ [SYNTHESIS] Streaming failed for {section_key}, "
                f"falling back to non-streaming: {e}"
            )
            if not stream_succeeded and not accumulated:
                try:
                    raw = _call_llm(
                        system_prompt=system_prompt,
                        user_content=user_content,
                        json_mode=False,
                        temperature=0.1,
                        model=DEEP_ANALYSIS_MODEL,
                    )
                    accumulated = raw or ""
                    if stream_callback and accumulated:
                        try:
                            stream_callback(section_key, accumulated)
                        except Exception as e2:
                            logger.warning(f"⚠️ stream_callback (fallback) failed: {e2}")
                except Exception as e2:
                    logger.error(f"❌ [SYNTHESIS] Fallback also failed: {e2}")
                    raise
            return accumulated

    # ────────────────────────────────────────────────────────────────────
    # DIGEST
    # ────────────────────────────────────────────────────────────────────

    def _build_digest(
        self, case, extractions, xrefs, defendants_groups,
        articles_by_law, case_type=None,
    ):
        lines = []

        lines.append("=" * 70)
        lines.append("TË DHËNAT E LËNDËS")
        lines.append("=" * 70)
        lines.append(f"Titulli: {case.get('title') or case.get('case_name') or 'N/A'}")
        lines.append(f"Klienti: {case.get('client_name') or 'N/A'}")
        lines.append(f"Pozicioni: {case.get('client_position') or case.get('client_role') or 'N/A'}")
        lines.append(f"Numri i dokumenteve: {len(extractions)}")
        lines.append("")

        if case_type:
            lines.append("=" * 70)
            lines.append("🎯 LLOJI I LËNDËS")
            lines.append("=" * 70)
            if "→" in case_type:
                lines.append(
                    f"**{case_type}**\n"
                    f"Ky është një rast i DYFISHTË që ka evoluar nga "
                    f"procedura civile (urdhër mbrojtjeje) në procedurë penale "
                    f"(aktakuzë). Në raport, pasqyro të DYJA fazat:\n"
                    f"  • Faza 1 (Civile): Kërkesë për Urdhër Mbrojtjeje\n"
                    f"  • Faza 2 (Penale): Procedurë me Aktakuzë\n"
                    f"Përdor terminologjinë e saktë për secilën fazë."
                )
            else:
                lines.append(
                    f"**{case_type}**\n"
                    f"Ky është lloji i saktë i lëndës, i përcaktuar nga analiza "
                    f"e dokumenteve dhe dokumenti kryesor. Përdor terminologjinë "
                    f"e saktë për këtë lloj lënde."
                )
            lines.append("")

        primary_doc = self._find_primary_document(extractions)
        if primary_doc:
            lines.append("=" * 70)
            lines.append(f"📄 DOKUMENTI KRYESOR: {primary_doc.get('file_name', 'N/A')}")
            lines.append("=" * 70)
            lines.append(
                f"Lloji: {primary_doc.get('document_type', 'N/A')}\n"
                f"Ky është dokumenti më i rëndësishëm i lëndës."
            )
            lines.append("")

        lines.append("=" * 70)
        lines.append("INDEKSI I DOKUMENTEVE")
        lines.append("=" * 70)
        for i, ext in enumerate(extractions, 1):
            marker = " ⭐ [KRYESOR]" if ext is primary_doc else ""
            lines.append(
                f"{i}. {ext.get('file_name', 'N/A')} "
                f"[{ext.get('document_type', 'N/A')}] "
                f"({ext.get('text_length', 0):,} chars, "
                f"{ext.get('stats', {}).get('total_entities', 0)} entitete){marker}"
            )
        lines.append("")

        for i, ext in enumerate(extractions, 1):
            self._append_document_section(lines, i, ext)

        if defendants_groups:
            self._append_defendants_groups(lines, defendants_groups)
        else:
            lines.append("=" * 70)
            lines.append("⚖️  GRUPET E TË PANDËHURVE")
            lines.append("=" * 70)
            lines.append(
                "NUK U IDENTIFIKUAN grupe të pandehurish në dokumentet e "
                "analizuara."
            )
            lines.append("")

        self._append_parties_excluding_defendants(lines, extractions, defendants_groups)

        if articles_by_law:
            self._append_articles_by_law(lines, articles_by_law)

        sc_decisions = self._extract_supreme_court_decisions(extractions)
        if sc_decisions:
            lines.append("=" * 70)
            lines.append("🏛️  AKTGJYKIMET E GJYKATËS SUPREME TË PËRMENDURA")
            lines.append("=" * 70)
            lines.append("Citoji TË GJITHA në seksionin 'KUADRI LIGJOR'.")
            lines.append("")
            for d in sc_decisions:
                lines.append(f"  • {d}")
            lines.append("")

        if xrefs:
            self._append_cross_references(lines, xrefs)

        digest = "\n".join(lines)

        if len(digest) > MAX_DIGEST_CHARS:
            logger.warning(
                f"⚠️ [SYNTHESIS] Digest too large ({len(digest)} chars), "
                f"truncating to {MAX_DIGEST_CHARS}"
            )
            digest = digest[:MAX_DIGEST_CHARS] + "\n\n[...digest truncated...]"

        return digest

    def _append_articles_by_law(self, lines, articles_by_law):
        total = sum(len(v) for v in articles_by_law.values())

        lines.append("=" * 70)
        lines.append("📖 PËRSHKRIMET E NENEVE (TË GRUPUARA SIPAS LIGJIT)")
        lines.append("=" * 70)
        lines.append(
            f"Ky seksion përmban {total} nene të nxjerrura nga teksti burimor, "
            f"TË GRUPUARA SIPAS LIGJIT PËRKATËS."
        )
        lines.append(
            "KUR citon një nen në raport:"
        )
        lines.append(
            "  • NËSE neni ka përshkrim (pas em-dash), përdore FJALË PËR FJALË."
        )
        lines.append(
            "  • NËSE neni shfaqet VETËM si numër (pa përshkrim), shkruaj "
            "VETËM 'Neni X i [Ligjit]' — PA shpikje përshkrimi."
        )
        lines.append(
            "NUK LEJOHET: '[numri]', '[Ligji i panjohur]', '(i panjohur)', "
            "'Neni X.Y' në vend të 'Neni X'."
        )
        lines.append("")

        def law_sort_key(law_name):
            has_number = bool(re.search(r'Nr\.?\s+\d+', law_name, re.IGNORECASE))
            return (0 if has_number else 1, law_name.lower())

        for law_name in sorted(articles_by_law.keys(), key=law_sort_key):
            articles = articles_by_law[law_name]
            if not articles:
                continue
            lines.append(f"**{law_name}:**")

            def article_sort_key(article_key):
                m = re.search(r'Neni\s+(\d+)(?:[\.\/](\d+))?', article_key)
                if m:
                    major = int(m.group(1))
                    minor = int(m.group(2)) if m.group(2) else 0
                    return (major, minor, article_key)
                return (9999, 9999, article_key)

            for article_key in sorted(articles.keys(), key=article_sort_key):
                desc = articles[article_key]
                if desc:
                    lines.append(f"  • {article_key} — {desc}")
                else:
                    lines.append(f"  • {article_key} (pa përshkrim në bazë)")
            lines.append("")

    def _append_parties_excluding_defendants(self, lines, extractions, defendants_groups):
        defendant_names = set()
        for group in defendants_groups:
            for d in group.get("defendants", []):
                name = (d.get("name") or "").strip().lower()
                if name:
                    defendant_names.add(name)
                    parts = name.split()
                    if parts:
                        defendant_names.add(parts[0])
                        if len(parts) > 1:
                            defendant_names.add(parts[-1])

        parties_raw = {}
        for ext in extractions:
            ebt = ext.get("entities_by_type", {})
            for item in ebt.get("PARTY", []):
                text = (item.get("text") or "").strip()
                if not text:
                    continue
                key = text.lower()
                if key not in parties_raw:
                    parties_raw[key] = {
                        "text": text,
                        "documents": [],
                        "confidence": item.get("confidence", 0.0),
                    }
                parties_raw[key]["documents"].append(ext.get("file_name", ""))

        filtered_parties = []
        for key, p in parties_raw.items():
            parts = key.split()
            is_defendant = False
            if key in defendant_names:
                is_defendant = True
            else:
                for part in parts:
                    if len(part) > 3 and part in defendant_names:
                        is_defendant = True
                        break
            if not is_defendant:
                filtered_parties.append(p)

        if filtered_parties:
            lines.append("=" * 70)
            lines.append("👥 PALËT NDËRGYQËSE (pa të pandehurit)")
            lines.append("=" * 70)
            lines.append("Personat që NUK janë në grupet e të pandehurve.")
            lines.append("")
            for p in sorted(filtered_parties, key=lambda x: x["text"]):
                lines.append(f"  • {p['text']}")
            lines.append("")
        else:
            lines.append("=" * 70)
            lines.append("👥 PALËT NDËRGYQËSE")
            lines.append("=" * 70)
            lines.append(
                "Të gjitha palët e identifikuara janë në grupet e "
                "të pandehurve."
            )
            lines.append("")

    def _append_defendants_groups(self, lines, defendants_groups):
        total = sum(len(g.get("defendants", [])) for g in defendants_groups)

        lines.append("=" * 70)
        lines.append("⚖️  GRUPET E TË PANDËHURVE (nga kallëzimi penal)")
        lines.append("=" * 70)
        lines.append(
            f"Kallëzimi penal identifikon {total} të pandehur, "
            f"të organizuar në {len(defendants_groups)} grupe."
        )
        lines.append("")

        for group in defendants_groups:
            group_key = group.get("group", "?")
            title = group.get("title", "")
            subtitle = group.get("subtitle", "")

            lines.append(f"GRUPI {group_key}: {title}")
            if subtitle:
                lines.append(f"  ({subtitle[:120]})")
            for d in group.get("defendants", []):
                num = d.get("number", "")
                name = d.get("name", "")
                role = d.get("role", "")
                lines.append(f"  {num}. {name} — {role}")
            lines.append("")

    def _append_document_section(self, lines, idx, ext):
        lines.append("=" * 70)
        lines.append(f"DOKUMENTI #{idx}: {ext.get('file_name', 'N/A')}")
        lines.append("=" * 70)
        lines.append(f"Lloji: {ext.get('document_type', 'N/A')}")
        lines.append(f"Madhësia: {ext.get('text_length', 0):,} chars")
        lines.append("")

        meta = ext.get("metadata") or {}
        meta_lines = []
        for k, v in meta.items():
            if v in (None, "", [], {}):
                continue
            v_str = str(v)
            if len(v_str) > 150:
                v_str = v_str[:150] + "..."
            meta_lines.append(f"  {k}: {v_str}")
        if meta_lines:
            lines.append("METADATA:")
            lines.extend(meta_lines)
            lines.append("")

        ebt = ext.get("entities_by_type", {})
        entity_order = [
            ("PARTY", 30), ("JUDGE", 20), ("PROSECUTOR", 20),
            ("LAWYER", 20), ("WITNESS", 30), ("COURT", 20), ("ORGANIZATION", 30),
        ]
        for label, limit in entity_order:
            items = ebt.get(label, [])
            if not items:
                continue
            lines.append(f"[{label}] — {len(items)}:")
            for item in items[:limit]:
                lines.append(f"  • {item.get('text', '')}")
            if len(items) > limit:
                lines.append(f"  ... dhe {len(items) - limit} të tjera")
            lines.append("")

        statutes = ebt.get("STATUTE", [])
        if statutes:
            lines.append(f"[STATUTE] — {len(statutes)}:")
            for item in statutes[:40]:
                lines.append(f"  • {item.get('text', '')}")
            if len(statutes) > 40:
                lines.append(f"  ... dhe {len(statutes) - 40} të tjera")
            lines.append("")

        articles = ebt.get("ARTICLE", [])
        if articles:
            lines.append(f"[ARTICLE] — {len(articles)}:")
            for item in articles[:60]:
                lines.append(f"  • {item.get('text', '')}")
            if len(articles) > 60:
                lines.append(f"  ... dhe {len(articles) - 60} të tjera")
            lines.append("")

        case_nums = ebt.get("CASE_NUMBER", [])
        if case_nums:
            lines.append(f"[CASE_NUMBER] — {len(case_nums)}:")
            for item in case_nums[:40]:
                lines.append(f"  • {item.get('text', '')}")
            if len(case_nums) > 40:
                lines.append(f"  ... dhe {len(case_nums) - 40} të tjera")
            lines.append("")

        lines.append("")

    def _find_primary_document(self, extractions):
        priorities = [
            ("kallëzim", "kallzim"),
            ("aktakuzë", "aktakuze"),
            ("padi", "kërkesëpadi", "kerkesepadi"),
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
        lines.append("LIDHJET MIDIS DOKUMENTEVE (CROSS-REFERENCES)")
        lines.append("=" * 70)

        doc_refs = xrefs.get("document_references", [])
        if doc_refs:
            lines.append(f"\nReferencat dokument-dokument ({len(doc_refs)}):")
            for ref in doc_refs[:20]:
                lines.append(
                    f"  • '{ref.get('source_file_name')}' → "
                    f"'{ref.get('target_file_name')}' "
                    f"(përmes {ref.get('via_case_number')})"
                )

        cn_chain = xrefs.get("case_number_chain", {})
        if cn_chain:
            shared = {k: v for k, v in cn_chain.items() if len(v) > 1}
            if shared:
                lines.append(f"\nNumrat e lëndës në shumë dokumente:")
                for cn, docs in sorted(shared.items(), key=lambda x: -len(x[1]))[:15]:
                    lines.append(f"  • '{cn}' — në {len(docs)} dokumente")

        party_app = xrefs.get("party_appearances", {})
        if party_app:
            multi = {k: v for k, v in party_app.items() if len(v) > 1}
            if multi:
                lines.append(f"\nPersonat në shumë dokumente:")
                for name, docs in sorted(multi.items(), key=lambda x: -len(x[1]))[:20]:
                    lines.append(f"  • '{name}' — në {len(docs)} dokumente")

        lines.append("")

    # ────────────────────────────────────────────────────────────────────
    # LOADERS
    # ────────────────────────────────────────────────────────────────────

    def _load_case(self, case_id):
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            doc = self.db.cases.find_one({"_id": c_oid})
            return doc or {}
        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] Could not load case: {e}")
            return {}

    def _load_extractions(self, case_id):
        try:
            query = {"case_id": str(case_id), "status": "completed"}
            cursor = self.db[EXTRACTION_COLLECTION].find(query).sort(
                [("completed_at", 1)]
            )
            return list(cursor)
        except Exception as e:
            logger.error(f"❌ [SYNTHESIS] load_extractions failed: {e}")
            return []

    def _load_cross_refs(self, case_id):
        try:
            doc = self.db[CROSS_REF_COLLECTION].find_one({"case_id": str(case_id)})
            return doc or {}
        except Exception as e:
            logger.warning(f"⚠️ [SYNTHESIS] load_cross_refs failed: {e}")
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
        except Exception as e:
            logger.error(f"❌ [SYNTHESIS] load failed: {e}")
            return None


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_synthesis_service(db):
    return SynthesisService(db)