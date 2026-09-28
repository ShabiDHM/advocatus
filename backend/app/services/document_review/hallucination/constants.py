# FILE: backend/app/services/document_review/hallucination/constants.py
# PHOENIX PROTOCOL - HALLUCINATION CONSTANTS V1.26
# V1.26: ROLE_AWARE FULL VERIFY — Shtuar TË GJITHA seksionet VERIFY në
#        ROLE_AWARE_SECTIONS. Arsyeja: çdo seksion VERIFY propozon nene
#        shtesë për draftin ("Nene që mund të mungojnë", "Rekomandime",
#        "Nëse mungon, shto..."). Këto janë SUGJERIME legjitime, jo
#        halucinacione. Pa këtë, raporti bllokohet kot.
#        Shtuar: formal_completeness, legal_quality, supporting_precedents,
#                weaknesses_risks, concrete_recommendations, readiness.
# V1.25: ROLE_AWARE (drafting_quality).
# V1.24: ROLE-AWARE EXTENSION (errors_corrections).
# V1.21: HEADING FILTER + ROLE-AWARE DOWNGRADE.

from typing import List, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# CASE NUMBER PREFIXES (që nuk janë akronime ligjesh)
# ═══════════════════════════════════════════════════════════════════════════

CASE_NUMBER_PREFIXES: Set[str] = {
    "PA1", "PKR", "PML", "REV", "KMLP", "ANR", "PZR",
    "CP", "AC", "PN", "KP", "ARJ", "A", "P",
    "KPK", "KPPRK", "KPRK",
}


# ═══════════════════════════════════════════════════════════════════════════
# FJALË TË ZAKONSHME SHQIPE ME KAPITALE (jo akronime)
# ═══════════════════════════════════════════════════════════════════════════

COMMON_ALBANIAN_UPPERCASE_WORDS: Set[str] = {
    "PENAL", "PENALE", "PENALI", "PENALIT",
    "KODI", "KODIT", "KODIN", "KODE",
    "LIGJI", "LIGJIT", "LIGJIN", "LIGJE", "LIGJET",
    "NENI", "NENIT", "NENIN", "NENE", "NENET",
    "GJYKATA", "GJYKATËS", "GJYKATES", "GJYKATEN",
    "FAMILJE", "FAMILJEN", "FAMILJES",
    "KUSHTETUTA", "KUSHTETUTËS", "KUSHTETUTES",
    "PROCEDURA", "PROCEDURËS", "PROCEDURES", "PROCEDUREN",
    "PROKURORIA", "PROKURORISË", "PROKURORISE", "PROKURORINË",
    "APELI", "APELIT", "SUPREME", "SUPREM", "SUPREMIT",
    "KOSOVËS", "KOSOVES", "KOSOVË", "REPUBLIKA", "REPUBLIKËS",
    "REPUBLIKES", "REPUBLIKEN",
    "PARAGRAFI", "PARAGRAFIT", "PIKA", "PIKËS", "PIKES", "KREU", "KREUT",
    "DISPOZITA", "DISPOZITËS", "DISPOZITAVE",
    "PERSON", "PERSONI", "PERSONA", "PERSONAT", "PERSONAVE",
    "DHUNA", "DHUNËS", "DHUNES", "DHUNËN",
    "FËMIJA", "FEMIJA", "FËMIJËS", "FEMIJES",
    "MITUR", "MITURI", "MITURIT",
    "KALLËZIM", "KALLZIM", "KALLËZIMI",
    "KËRKESA", "KERKESA", "KËRKESË", "KERKESE", "KËRKESËN",
    "HUDHJA", "HUDHJE", "HUDHJEN",
    "AKTAKUZA", "AKTAKUZËS", "AKTAKUZEN",
    "AKTGJYKIM", "AKTGJYKIMI", "AKTVENDIM", "AKTVENDIMI",
    "VENDIM", "VENDIMI", "VENDIME", "VENDIMEVE", "VENDIMIT",
    "FAKTI", "FAKTET", "FAKTEVE",
    "PROVA", "PROVAT", "PROVAVE",
    "DOKUMENT", "DOKUMENTI", "DOKUMENTE",
    "SHQIPËRI", "SHQIPERI", "SHQIP",
    "KONVENTA", "KONVENTËS", "TRAKTATI", "TRAKTATIT",
    "ANALIZA", "ANALIZË", "ANALIZEN",
    "RAPORTI", "RAPORT", "RAPORTIM", "RAPORTIMI",
    "SEKSIONI", "SEKSION", "SEKSIONET",
    "GATI", "READY", "PUNË", "PUNE", "PUNES",
    "STATUSI", "STATUS", "STATUSIN",
    "VLERËSIMI", "VLERESIMI",
    "KOMENT", "KOMENTI",
    "KRITIKE", "OPSIONALE", "REKOMANDIM", "REKOMANDIME",
    "PËRMBLEDHJE", "PERMBLEDHJE",
    "PËRFUNDIM", "PERFUNDIM",
    "FJALË", "FJALE",
    "LËNDA", "LENDA", "LËNDË", "LENDE",
    "NUMRI", "NUMRAT",
    "DATA", "DATAT", "DATAVE",
    "ORË", "ORE",
    "SIPAS", "KONFORM",
    "ANGAZHUAR", "ORGANI", "ORGANIT",
    "EKSPERTI", "EKSPERTIZA", "EKSPERTIZE",
    "DËSHMI", "DESHMI", "DËSHMITAR", "DESHMITAR",
    "MENDIM", "MENDIMI",
    "SHKRESA", "SHKRESE",
    "ZGJIDHJE", "ZGJIDHJEN",
    "ZGJIDHUR", "ZGJIDHURA",
    "MASA", "MASAT", "MASAVE",
    "ARRESTI", "ARRESTIM", "ARRESTIMI",
    "NDALIMI", "NDALIM", "NDALIMIT",
    "DENIMI", "DENIM", "DENIMIT", "DENIME",
    "TRAJTIM", "TRAJTIMI", "TRAJTIMIT",
    "HETIM", "HETIMI", "HETIMIT", "HETIME",
    "PADIA", "PADINË", "PADI",
    "PADITËSI", "PADITESI", "PADITUR",
    "PADITURI", "PADITURIT",
    "PËRGJIGJE", "PERGJIGJE", "PËRGJIGJA",
    "ANKESA", "ANKESË", "ANKESE", "ANKESEN",
    "KËRKESËPADI", "KERKESEPADI",
    "PARASHTRESA", "PARASHTRESE",
    "PALË", "PALE", "PALËT", "PALET",
    "SHOQËRIA", "SHOQERIA",
    # V1.26: Terma shtesë që ABBREV_PATTERN kap gabimisht
    "LARTË", "LARTE", "MESME", "MESME",
    "ULËT", "ULET", "MESËM", "MESEM",
    "SHKALLË", "SHKALLE",
    "IMPACT", "IMPACT",
    "SEVERITY",
}


# ═══════════════════════════════════════════════════════════════════════════
# HEADING WORDS (false-positive filter për akronime)
# ═══════════════════════════════════════════════════════════════════════════

COMMON_HEADING_WORDS: Set[str] = {
    "HAPAT", "HAPI", "HAP",
    "KRITIKË", "KRITIKE", "KRITIK",
    "MENJËHERSHËM", "MENJEHERSHEM", "MENJËHERSHME", "MENJEHERSHME",
    "AFATGJATË", "AFATGJATE", "AFATGJAT",
    "RREZIQET", "RREZIK", "RREZIQE",
    "MUNDËSITË", "MUNDESITE", "MUNDESI",
    "REFERENCAT", "REFERENCA", "REFERENCË", "REFERENCE",
    "SHËNIM", "SHENIM", "VËREJTJE", "VEREJTJE",
    "PËRMBLEDHJE", "PERMBLEDHJE",
    "STATISTIKA", "STATISTIKË",
    "VEPRIME", "VEPRIM", "VEPRIMET",
    "PLANI", "PLAN",
    "KONKLUZION", "KONKLUZIONE", "PËRFUNDIM", "PERFUNDIM",
    "SEKSIONI", "SEKSIONI", "SEKSION",
    "ANALIZA", "ANALIZA",
    "STRUKTURA", "STRUKTURE",
    "VLERËSIMI", "VLERESIMI", "VLERËSIM", "VLERESIM",
    "TERMINOLOGJIA", "TERMINOLOGJI",
    "ARSYETIMI", "ARSYETIM",
    "GABIME", "GABIM", "GABIMET",
    "KORRIGJIME", "KORRIGJIM",
    "DOKUMENTI", "DOKUMENT",
    "DUKJE", "DUKJA",
    "PROBLEMI", "PROBLEM",
    "SUGJERIMI", "SUGJERIM", "SUGJERIME",
    "REKOMANDIMI", "REKOMANDIM", "REKOMANDIME",
    "BAZA", "BAZAT",
    "DETAJE", "DETAJ",
    # V1.26: Terma shtesë që shfaqen në output-in e VERIFY
    "LARTË", "LARTE", "MESME",
    "ULËT", "ULET",
    "GATI", "PUNË", "PUNE",
    "KËRKON", "KERKON",
    "PËRPLOTË", "PERPLOTE",
}


# ═══════════════════════════════════════════════════════════════════════════
# V1.26: ROLE-AWARE SECTIONS — TË GJITHA seksionet e VERIFY
# ═══════════════════════════════════════════════════════════════════════════
# Arsyeja: çdo seksion i VERIFY-t propozon nene shtesë, sugjerime ligjore,
# ose referenca të reja për përmirësimin e draftit. Këto janë SUGJERIME
# legjitime — jo halucinacione. Vetëm HIGH severity bllokon (dmth vetëm
# kur LLM shpik fakte/numra që nuk ekzistojnë fare, jo sugjerime).

ROLE_AWARE_SECTIONS: Set[str] = {
    # ═══ ANALIZO sections (draft review) ═══
    "action_steps",
    "analiza_e_thelluar",
    "errors_corrections",
    "drafting_quality",
    # ═══ VERIFY sections (draft verification) ═══
    "formal_completeness",
    "legal_quality",
    "supporting_precedents",
    "weaknesses_risks",
    "concrete_recommendations",
    "readiness",
}


# ═══════════════════════════════════════════════════════════════════════════
# AMBIGUOUS LAW ABBREVIATIONS
# ═══════════════════════════════════════════════════════════════════════════

AMBIGUOUS_LAW_ABBREVS: Set[str] = {
    "KPK",
    "KPP",
    "KPPK",
}


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZIMET E RASËS GRAMATIKORE SHQIPE
# ═══════════════════════════════════════════════════════════════════════════

ALBANIAN_CASE_NORMALIZATIONS: List[Tuple[str, str]] = [
    (r'\bligjit\b', 'ligji'),
    (r'\bligjin\b', 'ligji'),
    (r'\bligje\b', 'ligji'),
    (r'\bligjet\b', 'ligji'),
    (r'\bligjeve\b', 'ligji'),
    (r'\bligji\b', 'ligji'),
    (r'\bligj\b', 'ligji'),
    (r'\bkodin\b', 'kodi'),
    (r'\bkodet\b', 'kodi'),
    (r'\bkodit\b', 'kodi'),
    (r'\bkod\b', 'kodi'),
    (r'\bproceduren\b', 'procedure'),
    (r'\bprocedures\b', 'procedure'),
    (r'\bprocedura\b', 'procedure'),
    (r'\bprocedurat\b', 'procedure'),
    (r'\bmarredheniet\b', 'marredhenie'),
    (r'\bmarredhenie\b', 'marredhenie'),
    (r'\bdetyrimet\b', 'detyrim'),
    (r'\bdetyrimeve\b', 'detyrim'),
    (r'\bfamiljen\b', 'familje'),
    (r'\bfamiljes\b', 'familje'),
    (r'\bmbrojtjen\b', 'mbrojtje'),
    (r'\bmbrojtjes\b', 'mbrojtje'),
    (r'\bdhunen\b', 'dhune'),
    (r'\bdhunes\b', 'dhune'),
    (r'\bfemijes\b', 'femije'),
    (r'\bfemijen\b', 'femije'),
    (r'\bpunen\b', 'pune'),
    (r'\bpunes\b', 'pune'),
    (r'\bshoqerite\b', 'shoqeri'),
    (r'\bshoqerive\b', 'shoqeri'),
    (r'\btregtare\b', 'tregtar'),
    (r'\btregtareve\b', 'tregtar'),
    (r'\bgjykaten\b', 'gjykate'),
    (r'\bgjykates\b', 'gjykate'),
    (r'\bkontestimore\b', 'kontestim'),
    (r'\bpenale\b', 'penal'),
    (r'\bpenal\b', 'penal'),
    (r'\bspeciale\b', 'speci'),
    (r'\bspecial\b', 'speci'),
    (r'\bkomerciale\b', 'komer'),
    (r'\bkomercial\b', 'komer'),
]


# ═══════════════════════════════════════════════════════════════════════════
# SUGGESTION CONTEXT (fjalë që tregojnë se citimi është sugjerim, jo fakt)
# ═══════════════════════════════════════════════════════════════════════════

SUGGESTION_CONTEXT_KEYWORDS: Tuple[str, ...] = (
    "mungon", "mungojnë", "mungesa",
    "sugjerim", "sugjerohet", "sugjeron",
    "duhet shtuar", "duhet të shtohet",
    "konsiderohet", "konsideruar",
    "rekomandohet", "rekomandim", "i rekomanduar",
    "verifikim manual", "verifikohet manualisht",
    "nuk u gjet", "nuk gjendet", "nuk ekziston",
    "mund të mungojë", "mund të mungojnë",
    "problem:",
    "është shkruar si",
    "është cituar si",
    "korrigjim", "korrigjohet", "korrigjimi",
    "në vend të", "ne vend te",
    "nuk duhet",
    "duhet të jetë", "duhet te jete",
    "rregullorja:", "rregullore:",
    "nene që mund", "nene qe mund",
    "sugjerime:", "sugjerim:",
    # V1.26: Fjalë të reja për raportet VERIFY
    "rekomandohet të shtohet",
    "kërkohet verifikim",
    "verifikim manual i nevojshëm",
    "nuk mund të konfirmohet",
    "supozohet se",
)