# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V4.15
# V4.15: DOCUMENT HEADER + CONTEXT MAP FIX —
#        - _block_document_header() tani aplikohet edhe për
#          "drafting_quality" dhe "errors_corrections" (vlerësojnë formën
#          dhe gabimet procedurale → duan fillim/fund të dokumentit).
#        - Shtuar "deadlines" në SECTION_CONTEXT_MAP["document_summary"]
#          (prompt-i e referonte "[AFAT]" por blloku nuk ofrohej).
# V4.14: RIGOROUS ANALYSIS — shtuar seksione per analize te thelle:
#        - document_summary: "Shenja te fshehta" + "Modele"
#        - errors_corrections: "Vulnerabilitete strategjike"
#        - action_steps: "Veprime kritike qe mund te mungojne"
#        - NEW section "analiza_e_thelluar" (7-seksione)
# V4.13: CLIENT POSITION.
# V4.12: CLIENT CONTEXT.

from typing import Dict, Any, List, Optional, Set

DOCUMENT_REVIEW_PROMPTS = {
    # 1. PERMBLEDHJE EKZEKUTIVE
    "document_summary": {
        "title": "PERMBLEDHJE EKZEKUTIVE E AUDITIMIT",
        "max_tokens": 1800,
        "prompt": """Ti je "Auditues Ligjor i Gjykates Supreme te Kosoves" ne zyre keshilluese.

⚠️ MOS shkruaj titullin kryesor — shtohet automatikisht. Fillo DIREKT me seksionin 1.

DETYRA: Harto nje PERMBLEDHJE EKZEKUTIVE - jo rrefim, por DIAGNOZE PROFESIONALE.

⚠️ RREGULL ABSOLUT PER KLASIFIKIMIN:

0. **KLIENTI + ROLET:** Shih bllokun "[KLIENT]".
   - Blloku ka: emrin e klientit + rolin e deklaruar në rast + rolin në këtë dokument.
   - Në seksionin 2, raporto TË DYJA rolet:
     * Ndryshojnë → "Klienti (emri) është [roli_case] në rastin kryesor, por
       në këtë dokument shfaqet si [roli_dokument]."
     * Përputhen → raporto vetëm një rol.
     * Nuk shfaqet → "NUK PËRCAKTOHET në dokument".

1. **Lëshuesi** = AI QE SHKRUAN dokumentin. Lexo "[DOK] FILLIMI".

2. **Data** = data NE FILLIM ose NE FUND. Jo data e ngjarjeve.

3. **Roli i klientit** — si rregulli 0.

STRUKTURA E DETYRUAR:

1. Klasifikimi i dokumentit
- Lloji / Lëshuesi / Data + numri

2. Subjekti (palet + rolet)
- Palet kryesore
- Pozicioni i klientit

3. Permbajtja operative (3-4 rreshta)

4. Ceshtje kritike qe avokati DUHET te dije
- Kontradikta te brendshme (nese ka)
- Diagnoza mjekesore (me ICD)
- Denime te meparshme
- Teste mjekesore

5. Niveli i auditimit
- Sa nene u verifikuan
- Sa mbeten te paverifikueshme

6. **Shenja te Fshehta** (1-2 shenja qe nje avokat i zene mund t'i kete humbur)
- Nje detaj i vogel por i rendesishem
- Nje rrethanë e pazakonshme
- Nje veprim qe nuk pershtatet me rrjedhën normale

7. **Modele te Identifikuara** (1-2 modele)
- Perseritje datash, emrash, termash
- Veprime te njejta ne momente te ndryshme
- Zgjedhje gjyqesore qe tregojne paragjykim

RREGULLA:
- Perdor VETEM faktet ne blloqet "[KLIENT]", "[DOK]", "[PALE]", "[NENE]", "[AFAT]"
- Nese s'ka shenja → "Nuk u identifikuan"
- NUK shpik data, leshues, role""",
    },

    # 2. VERIFIKIMI I NENEVE
    "article_verification": {
        "title": "VERIFIKIMI DHE AUDITIMI I NENEVE LIGJORE",
        "max_tokens": 3500,
        "prompt": """Ti je "Verifikues i Neneve Ligjore" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me nenet.

DETYRA: Harto raport te plote verifikimi per CDO nen te cituar.

SISTEMI KA BERE VERIFIKIMIN - TI VETEM RAPORTO DHE SUGJERO.

Per CDO nen:

### Neni [numri] i [Ligji i cituar]
Statusi: EKZISTON / NUK U GJET / U GJET NE LIGJ TE RI
Vendndodhja: [Ligji + neni i sakte]
Cituar ne dokument: "[konteksti]"

Nese EKZISTON → Konfirmo saktesine.
Nese NUK U GJET → Propozo (zevendësim / gabim shkrimi / verifikim manual).
Nese successor → Sugjero zevendesimin.

🛑 NUK LEJOHET PROPOZIM LIGJI SPECIFIK PA KONFIRMIM.
NESE "Ligji i cituar: -" / bosh / "NUK U GJET":
✅ SHKRUAJ: "Statusi: NUK U VERIFIKUA" + "Kërkohet verifikim manual."

STRUKTURA FUNDIT:
### Permbledhje e verifikimit
- Nene te verifikuara: X
- Nene me zevendesim: Y
- Nene per verifikim manual: Z""",
    },

    # 3. PRECEDENTET
    "supreme_court_precedents": {
        "title": "PRECEDENTET E GJYKATES SUPREME",
        "max_tokens": 3500,
        "prompt": """Ti je "Analist i Precedenteve" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

RREGULL ABSOLUT:
- Blloku "🏛️ PRECEDENTE RELEVANTE" permban precedentet e VERTETE.
- NUK LEJOHET te shpikesh numra precedentet, faqe, ose burime.
- NESE blloku thote "Nuk u identifikuan" → shkruaj SAKTESISHT ate fraze.

SHENIM: Precedentet jane nga BAZA GLOBALE E GJYKATES SUPREME. NUK thuaj "sipas dokumentit".

RREGULL RELEVANCE (3 NIVELET):
▶ NIVELI 1 — TEME IDENTIKE → "Ka lidhje të drejtpërdrejtë."
▶ NIVELI 2 — TEME E NGJASHME → "Ka lidhje indirekte përmes [parimit X]."
▶ NIVELI 3 — TEME E NDRYSHME → "Nuk ka lidhje të drejtpërdrejtë."

STRUKTURA:
### A. Numrat e Cituar ne Dokument
### B. Precedentë Relevante
### C. Rendesia Praktike""",
    },

    # 4. ANALIZA E CILESISE
    "drafting_quality": {
        "title": "ANALIZA E CILESISE SE HARTIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Revizor i Cilesise se Akteve Gjyqesore".

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

STRUKTURA:
### A. Struktura formale
### B. Terminologjia juridike
### C. Arsyetimi juridik
### D. Konsistenca e brendshme
Perdor VETEM bllokun "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".
### E. Vleresimi perfundimtar
Note 1-5 me arsyetim.

NUK LEJOHET te shpikesh mangesi qe nuk shfaqen ne fakte.""",
    },

    # 5. GABIME DHE KORRIGJIME
    "errors_corrections": {
        "title": "GABIME, KONTRADIKTA DHE KORRIGJIME",
        "max_tokens": 3200,
        "prompt": """Ti je "Auditues i Akteve Gjyqesore".

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

FORMATI:

### A. Gabime ne nene
Per cdo nen qe NUK u verifikua:
    [X] Neni X ([Ligji])
        Problem:
        Korrigjim:
        Impakti:

🛑 NESE "Ligji: -" / bosh → SHKRUAJ "Kërkohet verifikim manual."
   NUK LEJOHET te propozosh ligj specifik pa konfirmim.

### B. Kontradikta te brendshme
VETEM bllokun "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".

### C. Gabime procedurale
### D. Korrigjime te rekomanduara

### E. **Vulnerabilitete Strategjike** (E RE)
Ku mund te godase pala kundërshtare?
- Cilat pika te arsyetimit jane te dobëta?
- Çfarë do të bënte nje avokat i kundërshtarit me këtë dokument?
- Cilat fakte mund të sfidohen?

Listo 2-3 vulnerabilitete ME BAZE NE FAKTE.

RREGULLA:
- NUK LEJOHET te shpikesh gabime
- NUK LEJOHET ligj specifik pa konfirmim""",
    },

    # 6. PLANI I VEPRIMIT
    "action_steps": {
        "title": "PLANI I VEPRIMIT DHE REKOMANDIMET",
        "max_tokens": 3000,
        "prompt": """Ti je "Strateg i Larte Ligjor".

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

STRUKTURA:

### A. Vleresimi i Situates
### B. Hapat e Menjehershem (1-7 dite)
### C. Hapat Afatgjate (1-3 muaj)
### D. Mundesite Procedurale
### E. Rreziqet
### F. Referencat Konkrete

RREGULLA PER AFATET:
- Nese dokumenti permend afat → cituoje ME BURIMIN.
- NESE NUK permend → "Afati ligjor nuk u identifikua — kerkohet verifikim."
- NUK LEJOHET te shkruash afate qe nuk shfaqen ne bllokun [AFAT].

### G. **Veprime Kritike qe Mund te Mungojne** (E RE)
Veprime qe avokati DUHET te ndermarre, por qe mund t'i harroje:
- Kerkesa procedurale te zakonshme per kete lloj ceshtjeje
- Mbrojtje ligjore qe nuk eshte ngritur
- Te drejta te pashfrytezuara
- Afate kritike qe mund te kene kaluar pa verejtje
- Kerkesa per ekspertize, deshmitare, prova shtese

Listo 2-3 veprime ME BAZE NE FAKTE.

RREGULLA: CDO veprim me baze ne fakte, CDO ligj ne fakte.""",
    },

    # 7. ANALIZA E THELLUAR (I RI)
    "analiza_e_thelluar": {
        "title": "ANALIZA E THELLUAR",
        "max_tokens": 3500,
        "prompt": """Ti je "Analist i Thelluar i Akteve Gjyqesore" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Identifiko ATE QE NJE AVOKAT I ZENE NUK E SHEH.
Ky seksion eshte DALLIMI midis nje assitenti dhe nje kolegu me eksperience.

⚠️ Fokus ne SHENJA qe NUK shfaqen ne seksionet e tjera. Mos perserit.

STRUKTURA:

### A. Modele dhe Shenja te Fshehta (2-3)
- Perseritje datash, emrash, termash ne momente te ndryshme (a ka pattern?)
- Veprime te njejta nga i njejti aktor (a eshte sistematike?)
- Zgjedhje gjyqesore qe tregojne paragjykim ose prirje
- Perdorim te njejte i termave/subjekteve si teknike retorike
- KOHË: a perseriten afate, pushime, shtyrje?

### B. Omissions dhe Boshllëqe Kritike (2-3)
- Nene qe DUHET te ishin cituar por MUNGON
- Procedura qe nuk permenden (konsentim, njoftim, prani, transparencë)
- Pala qe duhej te ishin te pranishme por mungojne (fëmija, avokati, eksperti)
- Afate qe nuk percaktohen (a ka boshllëqe kohore?)
- Mekanizma zbatimi qe nuk specifikohen
- Raporte/ekspertiza te permendura por te pabashkangjitura

### C. Standarde Provash (1-2)
- Cili eshte standardi i kerkuar? (paraprakisht, mbi dyshim te arsyeshem, provë e plote?)
- A eshte zbatuar saktë?
- A ka prova te konsiderueshme por te shpërfillura?
- Diagnozat/ekspertizat — a mbeshteten ne fakte te verifikueshme?

### D. Arme te Mundshme te Kundërshtarit (1-2)
Nese avokati e ankimon, ku do te godasë kundërshtari?
- Pikat e dobeta te arsyetimit
- Kontradiktat qe mund te perdoren
- Procedura qe mund te sfidohen

### E. Veprime Kritike qe Mund te Mungojne (1-2)
- Kerkesa procedurale te harruara
- Mbrojtje qe nuk eshte ngritur
- Te drejta te pashfrytezuara
- Afate qe mund te kene kaluar

RREGULLA:
- Fokus ne shenja qe NUK shfaqen ne seksionet e tjera
- Perdor VETEM faktet ne blloqet "[!]"
- Nese s'ka shenja per nje nen-seksion → "Nuk u identifikuan"
- **5-7 shenja TOTAL** (jo te gjitha te detyrueshme)
- Cilësia > Sasia
- Shmang hamendjen — bazo çdo shenje ne FAKTE""",
    },
}


# V4.15: "deadlines" shtuar në document_summary (përputhet me prompt-in [AFAT])
SECTION_CONTEXT_MAP: Dict[str, List[str]] = {
    "document_summary": [
        "client", "meta", "parties", "dispositive", "medical", "tests",
        "convictions", "judge_court", "contradictions", "articles", "laws",
        "deadlines",   # V4.15: prompt-i referon "[AFAT]"
    ],
    "article_verification": ["articles", "laws"],
    "supreme_court_precedents": ["case_numbers", "meta", "precedents"],
    "drafting_quality": [
        "client", "meta", "parties", "dispositive", "articles", "laws",
        "contradictions", "reported_contradictions",
    ],
    "errors_corrections": [
        "articles", "laws", "contradictions", "reported_contradictions",
        "dispositive", "medical",
    ],
    "action_steps": [
        "client", "meta", "parties", "dates", "deadlines", "case_numbers",
        "dispositive", "judge_court",
    ],
    # V4.14: Analiza e thelluar — kontekst i plotë
    "analiza_e_thelluar": [
        "client", "meta", "parties", "dispositive", "articles", "laws",
        "case_numbers", "contradictions", "reported_contradictions",
        "medical", "tests", "convictions", "judge_court",
        "dates", "deadlines",
    ],
}

ALL_CONTEXT_BLOCKS = [
    "client", "meta", "articles", "laws", "case_numbers", "parties", "dates",
    "deadlines", "dispositive", "medical", "tests", "convictions",
    "judge_court", "contradictions", "reported_contradictions", "precedents",
]


# ===========================================================
# CONTEXT BLOCK BUILDERS
# ===========================================================

def _block_client_context(
    client_name: Optional[str],
    client_position: Optional[str] = None,
) -> List[str]:
    if not client_name or not client_name.strip():
        return [
            "=" * 70,
            "[KLIENT] KONTEKST I KLIENTIT",
            "=" * 70,
            "",
            "⚠️ Emri i klientit nuk është i disponueshëm.",
            "Në seksionin 2, shkruaj 'NUK PËRCAKTOHET (klienti nuk është identifikuar)'.",
            "",
        ]

    clean_name = client_name.strip()

    lines: List[str] = [
        "=" * 70,
        "[KLIENT] KONTEKST I KLIENTIT",
        "=" * 70,
        "",
        f"👤 KLIENTI (personi që përfaqësohet): **{clean_name}**",
        "",
    ]

    if client_position and str(client_position).strip():
        lines.append(f"🎯 Roli i deklaruar në rast (case-level): **{client_position.strip()}**")
        lines.append("")
        lines.append("⚠️ RREGULL I DETYRUAR PËR SEKSIONIN 2:")
        lines.append("")
        lines.append(f"  1. **Roli i klientit në dokument** — identifikoje nga teksti.")
        lines.append(f"  2. **Roli i klientit në rast** = '{client_position.strip()}'.")
        lines.append(f"  3. **Nëse rolet ndryshojnë**, shkruaj TË DYJA:")
        lines.append(f"     \"Klienti ({clean_name}) është {client_position.strip()} në")
        lines.append(f"      rastin kryesor, por në këtë dokument shfaqet si [roli_dokument].\"")
        lines.append(f"  4. **Nëse përputhen**, raporto vetëm një rol.")
        lines.append(f"  5. **Nëse emri '{clean_name}' nuk shfaqet** → 'NUK PËRCAKTOHET'.")
        lines.append("")
    else:
        lines.append("⚠️ Roli i deklaruar në case nuk është i disponueshëm.")
        lines.append("")
        lines.append(f"  - Cakto rolin e '{clean_name}' bazuar VETËM në tekst.")
        lines.append(f"  - Nëse emri nuk shfaqet → 'NUK PËRCAKTOHET në dokument'.")
        lines.append("")

    return lines


def _block_meta(document_type: str, file_name: str) -> List[str]:
    return [
        "=" * 70,
        f"DOKUMENTI: {file_name}",
        f"LLOJI: {document_type}",
        "=" * 70,
        "",
        "[!] TE GJITHA FAKTET E ME POSHTME JANE TE VERIFIKUARA NGA SISTEMI.",
        "NUK KE NEVOJE T'I KONTROLLOSH - VETEM INTERPRETOJI.",
        "",
    ]


def _block_document_header(doc_text: Optional[str]) -> List[str]:
    if not doc_text or not doc_text.strip():
        return []

    lines: List[str] = []

    lines.append("=" * 70)
    lines.append("[DOK] FILLIMI I DOKUMENTIT")
    lines.append("=" * 70)
    lines.append("")

    header = doc_text[:1500].strip()
    if header:
        lines.append(header)
        lines.append("")

    lines.append("=" * 70)
    lines.append("[DOK] FUNDI I DOKUMENTIT")
    lines.append("=" * 70)
    lines.append("")

    footer = doc_text[-500:].strip()
    if footer:
        lines.append(footer)
        lines.append("")

    return lines


def _block_precedents(precedents: Optional[List[Dict[str, Any]]]) -> List[str]:
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("🏛️ PRECEDENTE RELEVANTE (nga baza e Gjykatës Supreme)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("ℹ️ KETA PRECEDENTE VIJNE NGA BAZA GLOBALE E GJYKATES SUPREME — jo nga fashikulli.")
    lines.append("")

    if not precedents:
        lines.append("Nuk u identifikuan precedentë relevante në bazën e Gjykatës Supreme për këtë lëndë.")
        lines.append("")
        lines.append("⚠️ NUK LEJOHET të shpikësh numra precedentësh, faqe, ose burime.")
        lines.append("")
        return lines

    lines.append(f"Total: {len(precedents)} precedentë relevantë të verifikuar.")
    lines.append("")

    for i, p in enumerate(precedents, 1):
        case_number = str(p.get("case_number", "?")).strip()
        similarity = p.get("similarity", 0.0)
        excerpt = (p.get("text_excerpt") or "").strip()
        source = p.get("source", "?")
        page = p.get("page", "?")
        chunk_id = p.get("chunk_id", "?")
        topic_label = p.get("topic_label")
        rerank_score = p.get("rerank_score")

        lines.append(f"  {i}. [{case_number}] — similarity={similarity:.2f}")
        if rerank_score is not None:
            lines.append(f"     Rerank score: {rerank_score:.2f}")
        if topic_label:
            lines.append(f"     Tema: {topic_label}")
        if excerpt:
            lines.append(f'     Fragment: "{excerpt[:400]}"')
        lines.append(f"     Burimi: {source}, faqe {page}")
        lines.append(f"     chunk_id: {chunk_id}")
        lines.append("")

    lines.append("⚠️ RREGULL: Paraqit VETËM këta precedentë. NUK LEJOHET të shpikësh asnjë.")
    lines.append("")
    return lines


def _collect_allowed_values(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
) -> Dict[str, Set[str]]:
    allowed: Dict[str, Set[str]] = {
        "dates": set(), "law_numbers": set(), "law_abbrevs": set(),
        "article_numbers": set(), "case_numbers": set(),
    }

    for d in fact_profile.get("dates", []) or []:
        if d.get("display"):
            allowed["dates"].add(d["display"])
        if d.get("iso"):
            allowed["dates"].add(d["iso"])

    for l in citation_profile.get("laws_by_number", []) or []:
        if l.get("number"):
            allowed["law_numbers"].add(l["number"])
    for l in verification_report.get("laws_by_number", []) or []:
        if l.get("number"):
            allowed["law_numbers"].add(l["number"])

    for a in citation_profile.get("abbreviations", []) or []:
        allowed["law_abbrevs"].add(a)

    for a in citation_profile.get("articles", []) or []:
        if a.get("number"):
            allowed["article_numbers"].add(a["number"])

    for c in citation_profile.get("case_numbers", []) or []:
        if c.get("case_number"):
            allowed["case_numbers"].add(c["case_number"])

    return allowed


def _block_antihallucination(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
) -> List[str]:
    allowed = _collect_allowed_values(citation_profile, fact_profile, verification_report)

    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("[!] ANTI-HALLUCINATION - LISTA E VLERAVE TE LEJUARA")
    lines.append("=" * 70)
    lines.append("")
    lines.append("RREGULL ABSOLUT: Ne output-in tend mund te permendesh VETEM")
    lines.append("vlera qe shfaqen ne listat me poshte.")
    lines.append("")

    if allowed["dates"]:
        lines.append(f"* DATAT E LEJUARA ({len(allowed['dates'])}):")
        for d in sorted(allowed["dates"]):
            lines.append(f"    - {d}")
        lines.append("")
    else:
        lines.append("* DATAT E LEJUARA: (asnje)")
        lines.append("")

    if allowed["law_numbers"]:
        lines.append(f"* LIGJET E LEJUARA ({len(allowed['law_numbers'])}):")
        for l in sorted(allowed["law_numbers"]):
            lines.append(f"    - {l}")
        lines.append("")

    if allowed["law_abbrevs"]:
        lines.append(f"* AKRONIMET E LEJUARA ({len(allowed['law_abbrevs'])}):")
        for a in sorted(allowed["law_abbrevs"]):
            lines.append(f"    - {a}")
        lines.append("")

    if allowed["article_numbers"]:
        lines.append(f"* NUMRAT E NENEVE TE LEJUARA ({len(allowed['article_numbers'])}):")
        for a in sorted(allowed["article_numbers"], key=lambda x: (len(x), x)):
            lines.append(f"    - Neni {a}")
        lines.append("")

    if allowed["case_numbers"]:
        lines.append(f"* NUMRAT E LENDEVE TE LEJUARA ({len(allowed['case_numbers'])}):")
        for c in sorted(allowed["case_numbers"]):
            lines.append(f"    - {c}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("KUJTESE: Nese dyshon per nje vlere, MOS E PERDOR.")
    lines.append("=" * 70)
    lines.append("")
    return lines


def _block_dispositive(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    points = fact_profile.get("dispositive_points", [])
    if not points:
        return lines
    lines.append("=" * 70)
    lines.append(f"[LIGJ] PIKAT E DISPOZITIVIT ({len(points)} pika)")
    lines.append("=" * 70)
    lines.append("")
    for p in points:
        lines.append(f"**{p['roman']}.** {p['content']}")
        lines.append("")
    return lines


def _block_medical(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    findings = fact_profile.get("medical_findings", [])
    if not findings:
        return lines
    lines.append("=" * 70)
    lines.append(f"[MJESI] GJETJET MJEKESORE ({len(findings)})")
    lines.append("=" * 70)
    for f in findings:
        if f["type"] == "icd_code":
            lines.append(f"* Kodi ICD-10: **{f['code']}**")
            lines.append(f"  Konteksti: {f.get('context', '')[:300]}")
        elif f["type"] == "diagnosis_context":
            lines.append(f"* Diagnoza: {f.get('keyword', '')}")
            lines.append(f"  Konteksti: {f.get('context', '')[:300]}")
        lines.append("")
    return lines


def _block_tests(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    tests = fact_profile.get("medical_tests", [])
    if not tests:
        return lines
    lines.append("=" * 70)
    lines.append(f"[TEST] TESTET MJEKESORE / TOKSIKOLOGJIKE ({len(tests)})")
    lines.append("=" * 70)
    for t in tests:
        result_icon = {
            "negative": "[OK] NEGATIV",
            "positive": "[!] POZITIV",
            "unknown": "[?] Rezultat i papercaktuar",
        }.get(t.get("result", "unknown"), "[?]")
        lines.append(f"* {t['test_type']} -> {result_icon}")
        lines.append(f"  Konteksti: {t.get('context', '')[:300]}")
        lines.append("")
    return lines


def _block_convictions(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    convictions = fact_profile.get("prior_convictions", [])
    if not convictions:
        return lines
    lines.append("=" * 70)
    lines.append(f"[!] DENIME TE MEPARSHME PENALE ({len(convictions)})")
    lines.append("=" * 70)
    for c in convictions:
        is_penal = "PENAL" if c.get("is_penal") else "CIVIL/ADMINISTRATIV"
        lines.append(f"* {c['case_number']} ({is_penal})")
        lines.append(f"  Konteksti: {c.get('context', '')[:300]}")
        lines.append("")
    return lines


def _block_judge_court(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    info = fact_profile.get("judge_and_court", {})
    if not info or not any(info.values()):
        return lines
    lines.append("=" * 70)
    lines.append("[PROCEDURE] INFORMACION PROCEDURAL")
    lines.append("=" * 70)
    if info.get("judge_name"):
        lines.append(f"* Gjyqtari: **{info['judge_name']}**")
    if info.get("court_name"):
        lines.append(f"* Gjykata: **{info['court_name']}**")
    if info.get("appeal_deadline"):
        lines.append(f"* Afati i ankeses: **{info['appeal_deadline']}**")
    lines.append("")
    return lines


def _block_articles(verification_report: Dict[str, Any]) -> List[str]:
    lines = []
    verified_articles = verification_report.get("articles", [])
    if not verified_articles:
        return lines

    lines.append("=" * 70)
    lines.append(f"[NENE] NENET E VERIFIKUARA ({len(verified_articles)})")
    lines.append("=" * 70)
    lines.append("⚠️ NESE i njejti numer neni shfaqet DY HERE, TRAJTOJI SI NJE NEN.")
    lines.append("⚠️ NESE 'Ligji i cituar: -' ose bosh → KURRË mos propozo ligj specifik.")
    lines.append("")
    for a in verified_articles:
        status = "[OK] EKZISTON" if a["exists"] else "[X] NUK U GJET"
        law_hint = a.get("law_hint", "") or "-"
        para = f" par. {a['paragraph']}" if a.get("paragraph") else ""
        lines.append(f"* Neni {a['article_number']}{para}")
        lines.append(f"  Ligji i cituar: {law_hint}")
        lines.append(f"  Statusi: {status}")
        lines.append(f"  Arsyeja e verifikimit: {a.get('match_reason', '-')}")

        if a["exists"] and a.get("matched_doc"):
            doc = a["matched_doc"]
            lines.append(f"  Ligji ne baze: {doc.get('law_title', '-')}")
            excerpt = (doc.get("text_excerpt") or "").strip()
            if excerpt:
                lines.append(f"  Konteksti: {excerpt[:300]}")

        if a.get("suggested_replacement"):
            sr = a["suggested_replacement"]
            lines.append(f"  [SUGJERIM] ZEVENDESIM: {sr.get('old_law', '')} -> {sr.get('new_law', '')}")
            lines.append(f"     {sr.get('note', '')}")

        if a.get("alternative_laws"):
            alts = a["alternative_laws"]
            if alts and isinstance(alts[0], dict):
                lines.append(f"  -> Ekziston ne ligje te tjera:")
                for alt in alts[:3]:
                    lines.append(f"     - {alt.get('law_title', '')[:80]}")

        if a.get("context"):
            lines.append(f"  Cituar ne dokument: {a['context'][:200]}")
        lines.append("")
    return lines


def _block_laws(verification_report: Dict[str, Any]) -> List[str]:
    lines = []
    laws = verification_report.get("laws_by_number", [])
    if not laws:
        return lines
    lines.append("=" * 70)
    lines.append(f"[LIGJE] LIGJET E CITUARA ({len(laws)})")
    lines.append("=" * 70)
    for l in laws:
        status = "[OK]" if l["exists"] else "[X]"
        name = l.get("name", "") or "(pa emer)"
        lines.append(f"{status} {l['number']} - {name}")
        if l["exists"] and l.get("matched_doc"):
            lines.append(f"    Titulli zyrtar: {l['matched_doc'].get('law_title', '-')}")
        if l.get("suggested_replacement"):
            sr = l["suggested_replacement"]
            lines.append(f"    [SUGJERIM] ZEVENDESIM: {sr.get('old_law', '')} -> {sr.get('new_law', '')}")
        lines.append("")
    return lines


def _block_case_numbers(verification_report: Dict[str, Any]) -> List[str]:
    lines = []
    cases = verification_report.get("case_numbers", [])
    if not cases:
        return lines
    lines.append("=" * 70)
    lines.append(f"[LENDE] NUMRAT E LENDEVE ({len(cases)})")
    lines.append("=" * 70)
    for c in cases:
        if c["is_likely_own"]:
            tag = "[OWN] I KETIJ DOKUMENTI"
        elif c["is_precedent"]:
            tag = "[OK] PRECEDENT REAL"
        else:
            tag = "[!] I CITUAR, POR I PAVERIFIKUAR"
        lines.append(f"* {c['case_number']} - {tag}")
        if c.get("context"):
            lines.append(f"  Konteksti: {c['context'][:200]}")
    lines.append("")
    return lines


def _block_parties(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    parties = fact_profile.get("parties", [])
    if not parties:
        return lines
    lines.append("=" * 70)
    lines.append(f"[PALE] PALET ({len(parties)})")
    lines.append("=" * 70)
    for p in parties:
        lines.append(f"  * {p['role']}: {p['name']}")
    lines.append("")
    return lines


def _block_dates(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    dates = fact_profile.get("dates", [])
    if not dates:
        return lines
    lines.append("=" * 70)
    lines.append(f"[DATA] DATAT ({len(dates)})")
    lines.append("=" * 70)
    for d in dates:
        lines.append(f"  * {d['display']}")
    lines.append("")
    return lines


def _block_deadlines(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    deadlines = fact_profile.get("legal_deadlines", [])
    if not deadlines:
        return lines
    lines.append("=" * 70)
    lines.append(f"[AFAT] AFATET PROCEDURALE ({len(deadlines)})")
    lines.append("=" * 70)
    lines.append("⚠️ Per cdo afat, BURIMI eshte treguar. Cito ate emer.")
    lines.append("")
    for dl in deadlines:
        source = dl.get("source_document") or "(e panjohur)"
        lines.append(f"  * {dl['display']} (burimi: {source})")
        lines.append(f"    Konteksti: {dl.get('context', '')[:200]}")
    lines.append("")
    return lines


def _block_contradictions(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    contradictions = fact_profile.get("contradictions", [])
    if not contradictions:
        return lines
    lines.append("=" * 70)
    lines.append(f"[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT ({len(contradictions)})")
    lines.append("=" * 70)
    lines.append("[!] KETO JANE FAKTE KRITIKE - DUHET LISTUAR NE RAPORT!")
    lines.append("[!] KETO JANE KONTRADIKTA TE DOKUMENTIT TONE (INTERNE).")
    lines.append("")
    for c in contradictions:
        values = " vs ".join(str(v) for v in c.get("values", []))
        zone_label = c.get("zone_label", "")
        zone_suffix = f" (zona: {zone_label})" if zone_label else ""
        lines.append(f"* Lloji: {c['type']}{zone_suffix}")
        lines.append(f"  Vlerat kontradiktore: **{values} {c.get('unit', '')}**")
        for ex in c.get("examples", [])[:2]:
            lines.append(f"  Shembull: {ex}")
        lines.append("")
    return lines


def _block_reported_contradictions(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    reported = fact_profile.get("reported_contradictions", [])
    if not reported:
        return lines
    lines.append("=" * 70)
    lines.append(f"[i] KONTRADIKTA TE RAPORTUARA NGA DOKUMENTI ({len(reported)})")
    lines.append("=" * 70)
    lines.append("ℹ️ KETO JANE KONTRADIKTA QE DOKUMENTI RAPORTON PER DOKUMENTE TE TJERE.")
    lines.append("ℹ️ NUK JANE KONTRADIKTA TE DOKUMENTIT TONE!")
    lines.append("")
    for c in reported:
        values = " vs ".join(str(v) for v in c.get("values", []))
        zone_label = c.get("zone_label", "")
        zone_suffix = f" (zona: {zone_label})" if zone_label else ""
        lines.append(f"* Lloji: {c['type']}{zone_suffix}")
        lines.append(f"  Vlerat: **{values} {c.get('unit', '')}**")
        for ex in c.get("examples", [])[:2]:
            lines.append(f"  Shembull: {ex}")
        lines.append("")
    return lines


def build_verified_context(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    document_type: str = "Dokument",
    file_name: str = "Dokument",
    section_key: Optional[str] = None,
    precedents: Optional[List[Dict[str, Any]]] = None,
    doc_text: Optional[str] = None,
    client_name: Optional[str] = None,
    client_position: Optional[str] = None,
) -> str:
    if section_key:
        blocks_needed = SECTION_CONTEXT_MAP.get(section_key, ALL_CONTEXT_BLOCKS)
    else:
        blocks_needed = ALL_CONTEXT_BLOCKS

    lines: List[str] = []

    if "meta" in blocks_needed:
        lines.extend(_block_meta(document_type, file_name))
    else:
        lines.append("=" * 70)
        lines.append(f"DOKUMENTI: {file_name} - LLOJI: {document_type}")
        lines.append("=" * 70)
        lines.append("")

    if "client" in blocks_needed or client_name:
        lines.extend(_block_client_context(client_name, client_position))

    # V4.15: _block_document_header aplikohet edhe për drafting_quality
    # dhe errors_corrections (vlerësojnë formën dhe gabimet procedurale)
    if section_key in (
        "document_summary",
        "action_steps",
        "analiza_e_thelluar",
        "drafting_quality",       # V4.15
        "errors_corrections",     # V4.15
    ) and doc_text:
        lines.extend(_block_document_header(doc_text))

    lines.extend(_block_antihallucination(citation_profile, fact_profile, verification_report))

    if "contradictions" in blocks_needed:
        lines.extend(_block_contradictions(fact_profile))

    if "reported_contradictions" in blocks_needed:
        lines.extend(_block_reported_contradictions(fact_profile))

    if "dispositive" in blocks_needed:
        lines.extend(_block_dispositive(fact_profile))

    if "medical" in blocks_needed:
        lines.extend(_block_medical(fact_profile))

    if "tests" in blocks_needed:
        lines.extend(_block_tests(fact_profile))

    if "convictions" in blocks_needed:
        lines.extend(_block_convictions(fact_profile))

    if "judge_court" in blocks_needed:
        lines.extend(_block_judge_court(fact_profile))

    if "articles" in blocks_needed:
        lines.extend(_block_articles(verification_report))

    if "laws" in blocks_needed:
        lines.extend(_block_laws(verification_report))

    if "case_numbers" in blocks_needed:
        lines.extend(_block_case_numbers(verification_report))

    if "parties" in blocks_needed:
        lines.extend(_block_parties(fact_profile))

    if "dates" in blocks_needed:
        lines.extend(_block_dates(fact_profile))

    if "deadlines" in blocks_needed:
        lines.extend(_block_deadlines(fact_profile))

    if "precedents" in blocks_needed:
        lines.extend(_block_precedents(precedents))

    return "\n".join(lines).strip()