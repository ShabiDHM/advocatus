# FILE: backend/scripts/audit_mongo_verifier.py
"""
V282.34: Audit për mongo_verifier/ — grep termspecifik.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
DATA = BACKEND / "data"

TERMS = [
    # (emri, termi, root)
    ("HAGA_FEMIJET kudo",              "HAGA_FEMIJET",                          APP),
    ("HAGA_FEMIJET në JSON",           "HAGA_FEMIJET",                          DATA),
    ("Haga në JSON",                   "Haga",                                  DATA),
    ("Haga në JSON",                   "Hagë",                                  DATA),

    ("INTERNATIONAL_TREATIES",         "INTERNATIONAL_TREATIES",                APP),
    ("articles_via_international_treaty", "articles_via_international_treaty",  APP),
    ("articles_external",              "articles_external",                     APP),
    ("articles_external_kednj",        "articles_external_kednj",               APP),
    ("articles_external_okb",          "articles_external_okb",                 APP),
    ("articles_external_haga",         "articles_external_haga",                APP),

    ("ABBREV_SKIP_WORDS",              "ABBREV_SKIP_WORDS",                     APP),
    ("LAW_ABBREV_ALIASES",             "LAW_ABBREV_ALIASES",                    APP),
    ("KNOWN_ABBREV_KEYWORDS",          "KNOWN_ABBREV_KEYWORDS",                 APP),
    ("KNOWN_ABBREV_EXCLUDES",          "KNOWN_ABBREV_EXCLUDES",                 APP),
    ("KEYWORD_MATCH_STOPWORDS",        "KEYWORD_MATCH_STOPWORDS",               APP),
    ("LAW_SUCCESSOR_MAP",              "LAW_SUCCESSOR_MAP",                     APP),
    ("clear_registry_cache",           "clear_registry_cache",                  APP),

    ("get_all_external_sources",       "get_all_external_sources",              APP),
    ("find_external_source",           "find_external_source",                  APP),
]

# Edhe në scripts/ (teste)
TERMS += [
    ("ABBREV_SKIP_WORDS në teste",     "ABBREV_SKIP_WORDS",    BACKEND / "scripts"),
    ("LAW_ABBREV_ALIASES në teste",    "LAW_ABBREV_ALIASES",   BACKEND / "scripts"),
    ("clear_registry_cache në teste",  "clear_registry_cache", BACKEND / "scripts"),
    ("find_external_source në teste",  "find_external_source", BACKEND / "scripts"),
    ("get_all_external_sources në teste", "get_all_external_sources", BACKEND / "scripts"),
]

print(f"\n{'=' * 78}")
print("AUDIT — mongo_verifier/")
print(f"{'=' * 78}")

for desc, term, root in TERMS:
    if not root.exists():
        print(f"\n▶ '{term}'  ({desc}) — root nuk ekziston: {root}")
        continue

    hits = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if "__pycache__" in str(f):
            continue
        if f.suffix not in (".py", ".json", ".txt", ".md", ""):
            continue
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if term in txt:
            rel = str(f.relative_to(BACKEND)).replace("\\", "/")
            hits.append((rel, txt.count(term)))

    print(f"\n▶ '{term}'  ({desc})")
    if hits:
        for rel, cnt in sorted(hits)[:15]:
            print(f"    {rel}  ×{cnt}")
    else:
        print(f"    (asnjë hit)")

print(f"\n{'=' * 78}\n")