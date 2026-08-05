# FILE: backend/app/api/endpoints/laws_pkg/laws_dictionary.py
# PHOENIX PROTOCOL - LAWS DICTIONARY V4.0 (STRICT STATUTORY CODES & STRIP ALPHA HELPER)

import re
from typing import List, Any

def _strip_alpha(s: str) -> str:
    """Removes all spaces, hyphens, underscores, and .pdf extension for 100% exact matching."""
    clean = re.sub(r'\.pdf$', '', s.strip(), flags=re.IGNORECASE)
    return re.sub(r'[^a-zA-Z0-9]', '', clean).lower()

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = re.findall(r'\d+', article)
    return [int(p) for p in parts] if parts else [0]

def _is_academic_file(filename_or_title: str) -> bool:
    text = str(filename_or_title).upper()
    academic_keywords = [
        "AKADEMIA", "DORACAK", "UDHEZUES", "UDHËZUES", "COMMENTARY", 
        "CASE_LAW", "PRAKTIKË", "INSTITUTI", "LËNDËSH", "LENDESH",
        "AKTGJYKMET", "AKTGJYKMET_", "VENDIM", "VENDIMET"
    ]
    return any(k in text for k in academic_keywords)

OFFICIAL_KOSOVO_LAWS = {
    # Generic & Relative AI Phrases ("Ligji Përkatës")
    "ligji përkatës": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji perkates": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligjin përkatës": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligjin perkates": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji i përgjithshëm": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji i pergjithshem": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji i procedurës kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji per proceduren kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "procedurën kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "procedura kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",

    # Acronyms & Short Names
    "lsht": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "lpk": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "lmd": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "lpp": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "kpk": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "kppk": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "kpp": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "kushtetuta": "KUSHTETUTA E REPUBLIKËS SË KOSOVËS",
    
    # Official Full Statute Titles
    "kodi penal": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "procedurës penale": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "procedura penale": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "drejtësisë për të mitur": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "të mitur": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "shoqëritë tregtare": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "shoqerite tregtare": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "marrëdhëniet e detyrimeve": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "marredheniet e detyrimeve": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "procedurën përmbarimore": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "proceduren permbarimore": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "sigurinë dhe shëndetin në punë": "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
    "tatimin në të ardhurat e korporatave": "LIGJI NR. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
    "mbrojtjen e të dhënave personale": "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
    "mbrojtjen e fëmijës": "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
    "administrimin e procedurave tatimore": "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE",
    "familjen": "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
    "ligji i punës": "LIGJI NR. 03/L-212 I PUNËS",
    "ligji i punes": "LIGJI NR. 03/L-212 I PUNËS",

    # Number Codes
    "06/l-074": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "08/l-032": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "06/l-006": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "03/l-006": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "04/l-077": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "04/l-139": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "04/l-161": "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
    "05/l-029": "LIGJI NR. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
    "06/l-016": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "06/l-082": "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
    "06/l-084": "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
    "08/l-257": "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE",
    "2004/32": "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
    "03/l-212": "LIGJI NR. 03/L-212 I PUNËS"
}

def _normalize_hallucinated_title(raw_title: str, article: str) -> str:
    title_lower = raw_title.lower().strip()
    art_clean = re.sub(r'[^\d]', '', article.strip())
    art_num = int(art_clean) if art_clean.isdigit() else 0

    if "përkatës" in title_lower or "perkates" in title_lower or "përgjithshëm" in title_lower or "pergjithshem" in title_lower or not title_lower:
        if art_num in [297, 298, 299, 256, 258, 91, 92, 93, 110, 122]:
            return "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE"
        elif art_num in [136, 141, 330, 382, 376, 100, 150]:
            return "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE"
        elif art_num in [258, 259, 260, 250]:
            return "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE"
        elif art_num in [307, 308, 100, 200]:
            return "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS"

    if OFFICIAL_KOSOVO_LAWS.get(title_lower):
        return OFFICIAL_KOSOVO_LAWS[title_lower]

    for key, official_title in OFFICIAL_KOSOVO_LAWS.items():
        if key in title_lower or title_lower == key:
            return official_title

    law_code_match = re.search(r'\d{2,4}/l-\d{3}|\d{4}/\d{2}', title_lower)
    if law_code_match:
        code = law_code_match.group(0)
        if OFFICIAL_KOSOVO_LAWS.get(code):
            return OFFICIAL_KOSOVO_LAWS[code]

    if "penal" in title_lower and "procedur" in title_lower:
        return "KODI NR. 08/L-032 I PROCEDURËS PENALE"
    if "penal" in title_lower:
        return "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS"
    if "mitur" in title_lower:
        return "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR"
    if "familj" in title_lower:
        return "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS"
    if "shoqëri" in title_lower or "tregtar" in title_lower or "lsht" in title_lower:
        return "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE"
    if "detyrim" in title_lower or "lmd" in title_lower:
        return "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE"
    if "kontestim" in title_lower or "lpk" in title_lower:
        return "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE"
    if "punë" in title_lower or "puna" in title_lower:
        return "LIGJI NR. 03/L-212 I PUNËS"

    return raw_title