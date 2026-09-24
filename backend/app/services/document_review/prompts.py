# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V4.12
# V4.12: CLIENT CONTEXT — kontekst i ri `[KLIENT]` me emrin e klientit dhe
#        rregull i ri për klasifikim të saktë të pozicionit (jo "pala e mbrojtur"
#        vetëm sepse dokumenti është në favor të saj).
# V4.11: DOCUMENT HEADER CONTEXT.

from typing import Dict, Any, List, Optional, Set

DOCUMENT_REVIEW_PROMPTS = {
    # 1. PERMBLEDHJE EKZEKUTIVE E AUDITIMIT
    "document_summary": {
        "title": "PERMBLEDHJE EKZEKUTIVE E AUDITIMIT",
        "max_tokens": 1400,
        "prompt": """Ti je "Auditues Ligjor i Gjykates Supreme te Kosoves" ne zyre keshilluese.

⚠️ MOS shkruaj titullin kryesor ("PERMBLEDHJE EKZEKUTIVE E AUDITIMIT") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me seksionin 1.

DETYRA: Harto nje PERMBLEDHJE EKZEKUTIVE te dokumentit - jo nje rrefim, por nje
diagnoze profesionale per avokatin qe do te veproje me kete dokument.

⚠️ RREGULL ABSOLUT PER KLASIFIKIMIN:

0. **KLIENTI (i rëndësishëm!):** Shih bllokun "[KLIENT]".
   - Nëse emri i klientit jepet → pozicioni i klientit DUHET të caktohet në
     raport me ATË emër, jo me palën "e mbrojtur" të dokumentit.
   - Shembull: në një Urdhër Mbrojtjeje ku klienti është "Pala Përgjegjëse",
     raporti DUHET të thotë "Klienti është Pala Përgjegjëse", JO
     "Pala e Mbrojtur".
   - Nëse klienti NUK jepet → shkruaj "NUK PËRCAKTOHET (klienti nuk është identifikuar)".

1. **Lëshuesi** = AI QE SHKRUAN dokumentin (parashtruesi), JO marrësi.
   Lexo bllokun "[DOK] FILLIMI I DOKUMENTIT" — shih kush nënshkruan, kujt i drejtohet.

2. **Data e dokumentit** = data qe shfaqet NE FILLIM ose NE FUND te dokumentit
   (shih bllokun "[DOK] FUNDI I DOKUMENTIT").
   ⚠️ NUK është data e nje ngjarjeje te permendur brenda dokumentit.
   Nese nuk e identifikon dot qarte → shkruaj "NUK PËRCAKTOHET".

3. **Roli i klientit** = roli i KLIENTIT TË IDENTIFIKUAR në këtë dokument.
   - Lexo "[KLIENT]" për emrin.
   - Lexo "[PALE]" për listën e palëve në dokument.
   - Cakto rolin e klientit (Paditës / I Paditur / Palë e Mbrojtur /
     Palë Përgjegjëse / Dëshmitar / I Pandehur / etj.)

STRUKTURA E DETYRUAR:

1. Klasifikimi i dokumentit
- Lloji: [Vendim / Aktvendim / Padi / Kontrate / Kallëzim / Raport / ...]
- Lëshuesi: [shih rregullin 1]
- Data dhe numri i lendes [shih rregullin 2]

2. Subjekti (palet + rolet)
- Palet kryesore
- Pozicioni i klientit [shih rregullin 3, me emrin konkret]

3. Permbajtja operative (3-4 rreshta)
- Cka pretendoi/kerkoi parashtruesi?
- Cilat ishin arsyet kryesore?

4. Ceshtje kritike qe avokati DUHET te dije
- Nese ka KONTRADIKTA te brendshme → listoji
- Nese ka diagnoza mjekesore → permendji me ICD
- Nese ka denime te meparshme → permendji
- Nese ka teste mjekesore → permend rezultatin

5. Niveli i auditimit
- Sa nene u verifikuan me sukses
- Sa nene mbeten te paverifikueshme

RREGULLA FINALE:
- Perdor VETEM faktet ne blloqet "[KLIENT]", "[DOK]", "[PALE]", "[NENE]", "[AFAT]"
- Nese nje fakt NUK shfaqet → shkruaj "NUK PËRCAKTOHET ne dokument"
- NUK shpik data, leshues, role
- Perfundim: 1-2 rreshta "Hapi i ardhshëm" i sugjeruar""",
    },

    # 2. VERIFIKIMI I NENEVE — i paprekur
    "article_verification": {
        "title": "VERIFIKIMI DHE AUDITIMI I NENEVE LIGJORE",
        "max_tokens": 3500,
        "prompt": """Ti je "Verifikues i Neneve Ligjore" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor ("VERIFIKIMI DHE AUDITIMI I NENEVE LIGJORE")
   — shtohet automatikisht nga sistemi. Fillo DIREKT me nenet.

DETYRA: Harto nje raport te plote verifikimi per CDO nen te cituar.

SISTEMI KA BERE VERIFIKIMIN - TI VETEM RAPORTO DHE SUGJERO.

Per CDO nen te cituar ne dokument:

### Neni [numri] i [Ligji i cituar]
Statusi: EKZISTON / NUK U GJET / U GJET NE LIGJ TE RI
Vendndodhja: [Ligji + neni i sakte]
Cituar ne dokument: "[konteksti i citimit]"

Nese EKZISTON:
-> Konfirmo saktesine e citimit.

Nese NUK U GJET:
-> Propozo nese:
   (a) Ka zevendesim ne ligjin e ri (shih "SUGJERIM ZEVENDESIMI" ne fakte)
   (b) Referenca mund te jete gabim shkrimi
   (c) Neni ka nevoje per verifikim manual

Nese u gjet ne LIGJ TE RI (successor):
-> Sugjero zevendesimin konkret.

═══════════════════════════════════════════════════════════════════════════
🛑 RREGULL ABSOLUT — NUK LEJOHET PROPOZIM LIGJI SPECIFIK PA KONFIRMIM
═══════════════════════════════════════════════════════════════════════════

NESE ne bllokun "[NENE] NENET E VERIFIKUARA" neni ka:
   - "Ligji i cituar: -"  (vizë) / bosh
   - "Statusi: [X] NUK U GJET"
   - NUK ka fushe "Ligji ne baze: ..."

ATEHERE:

❌ NUK LEJOHET:
   - "Korrigjim i propozuar: Neni X i KPPRK-së"
   - "Korrigjim i propozuar: Neni X i KPRK-së"
   - Çdo propozim që emërton nje ligj specifik

✅ SHKRUAJ SAKTËSISHT:
   - "Statusi: NUK U VERIFIKUA"
   - "Vendndodhja: -"
   - "Vërejtje: Ligji burim nuk është i identifikuar në dokumentin
      e ngarkuar. Kërkohet verifikim manual nga avokati."

═══════════════════════════════════════════════════════════════════════════
NENE QE SHFAQEN DY HERE
═══════════════════════════════════════════════════════════════════════════

Sistemi i deduplifikon nenet para se t'i dergoje. NESE prap shfaqet
i njejti numer dy here, trajtoji si NJE nen te vetem.

STRUKTURA FUNDIT:
### Permbledhje e verifikimit
- Nene te verifikuara: X
- Nene me zevendesim te sugjeruar: Y
- Nene per verifikim manual: Z

MOS perfshi introduksione. Fillo direkt me nenet.""",
    },

    # 3. PRECEDENTET (i paprekur)
    "supreme_court_precedents": {
        "title": "PRECEDENTET E GJYKATES SUPREME",
        "max_tokens": 3500,
        "prompt": """Ti je "Analist i Precedenteve" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor ("PRECEDENTET E GJYKATES SUPREME") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me "### A. ...".

DETYRA: Analizo numrat e lendeve te cituar dhe paraqit precedentet relevante
qe SISTEMI ka gjetur ne bazen zyrtare te Gjykates Supreme.

RREGULL ABSOLUT:
- Blloku "🏛️ PRECEDENTE RELEVANTE" permban precedentet e VERTETE.
- NUK LEJOHET te shpikesh numra precedentet, faqe, ose burime.
- NESE blloku thote "Nuk u identifikuan" -> shkruaj SAKTESISHT ate fraze.

SHENIM — NGA VJNE PRECEDENTET:
Keta precedente NUK vijne nga fashikulli i kesaj lende. Ata jane gjetur nga
BAZA GLOBALE E GJYKATES SUPREME (legal_knowledge_base). NUK thuaj "sipas
dokumentit te fashikullit" — THUAJ "nga baza zyrtare e Gjykates Supreme".

RREGULL VLERESIMI I RELEVANCES (3 NIVELET — KONSISTENCE E STRIKTE):

▶ NIVELI 1 — TEME IDENTIKE:
  → Shkruaj: "NIVELI 1 — Ka lidhje të drejtpërdrejtë."

▶ NIVELI 2 — TEME E NGJASHME:
  → Shkruaj: "NIVELI 2 — Ka lidhje indirekte përmes [parimit X]."

▶ NIVELI 3 — TEME E NDRYSHME:
  → Shkruaj SAKTËSISHT: "NIVELI 3 — Nuk ka lidhje të drejtpërdrejtë."

🛑 KONSISTENCE:
   NIVELI 1 ⟺ "Ka lidhje të drejtpërdrejtë."
   NIVELI 2 ⟺ "Ka lidhje indirekte."
   NIVELI 3 ⟺ "Nuk ka lidhje."

STRUKTURA E OUTPUT-IT:

### A. Numrat e Cituar ne Dokument
- Numri + statusi (OWN / PRECEDENT REAL / CITED_NOT_FOUND)

### B. Precedentë Relevante
- Numri + Tema + Fragment + Burimi + Rendesia (NIVELI 1/2/3)

### C. Rendesia Praktike (permbledhje)""",
    },

    # 4. ANALIZA E CILESISE SE HARTIMIT (i paprekur)
    "drafting_quality": {
        "title": "ANALIZA E CILESISE SE HARTIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Revizor i Cilesise se Akteve Gjyqesore" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor ("ANALIZA E CILESISE SE HARTIMIT") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me "### A. ...".

DETYRA: Vlereso cilesine formale dhe permbajtesore te dokumentit.

STRUKTURA:

### A. Struktura formale
- A ka strukture te qarte (tituj, pika, seksione)?
- A ka dispozitiv te vecante (per vendime)?
- A jane pikat e dispozitivit te numertuara sakte?

### B. Terminologjia juridike
- A eshte perdorur terminologji standarde?
- A ka gabime shkrimi ne terma juridike?
- A jane citimet ligjore te formesuara sakte?

### C. Arsyetimi juridik
- A eshte arsyetimi i bazuar ne nene?
- A jane perdorur nenet e sakta?
- A ka analize te thelle ose vetem konstatim?

### D. Konsistenca e brendshme
KONTROLLO PER KONTRADIKTA:
⚠️ Perdor VETEM bllokun "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".
   - NESE ka → listoji
   - NESE nuk ka → shkruaj "[OK] Nuk u identifikuan kontradikta të brendshme."

⚠️ KONTRADIKTAT E RAPORTUARA (blloku "[i]") NUK numërohen si kontradikta
   të dokumentit. Mos i listo në këtë seksion.

### E. Vleresimi perfundimtar
Note 1-5 me arsyetim 2-3 rreshta.

NUK LEJOHET te shpikesh mangesi qe nuk shfaqen ne fakte.""",
    },

    # 5. GABIME DHE KORRIGJIME (i paprekur)
    "errors_corrections": {
        "title": "GABIME, KONTRADIKTA DHE KORRIGJIME",
        "max_tokens": 3000,
        "prompt": """Ti je "Auditues i Akteve Gjyqesore" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor ("GABIME, KONTRADIKTA DHE KORRIGJIME") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me "### A. ...".

DETYRA: Raporto CDO gabim, kontradikte dhe propozo korrigjime konkrete.

FORMATI I DETYRUAR:

### A. Gabime ne nene
Per cdo nen qe NUK u verifikua:
    [X] Neni [X] ([Ligji i cituar])
        Problem: [pse nuk u gjet]
        Korrigjim i propozuar: [neni i sakte / ligji i ri]
        Impakti: [cka humbet pa kete]

🛑 RREGULL ABSOLUT — KURRË MOS PROPOZO LIGJ SPECIFIK PA KONFIRMIM

NESE "Ligji i cituar" eshte: "-" / bosh / "(pa ligj)" / "NUK U GJET":

ATEHERE:
❌ NUK LEJOHET:
   - "Korrigjim i propozuar: Neni X i KPPRK-së"
   - Çdo propozim me emer ligji

✅ SHKRUAJ SAKTËSISHT:
    [X] Neni X (pa ligj)
        Problem: Ligji burim nuk është i identifikuar në dokument.
        Korrigjim i propozuar: Kërkohet verifikim manual.
        Impakti: Nuk mund të konfirmohet saktesia e referencës.

### B. Kontradikta te brendshme
⚠️ RREGULL ABSOLUT:
  - KONTROLLO VETEM bllokun "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".
  - NESE ka → listoji.
  - NESE nuk ka → shkruaj: "[OK] Nuk u identifikuan kontradikta të brendshme."

  ⚠️ Blloku "[i] KONTRADIKTA TE RAPORTUARA" → shfaqi në nënseksion
     "### B.1 Kontradikta të raportuara (jashtë dokumentit)".

### C. Gabime procedurale
Vetem nese ka baze ne fakte. NESE NUK KA -> "[OK] Nuk u identifikuan gabime procedurale."

### D. Korrigjime te rekomanduara
Per cdo gabim -> 1 rresht: Gabim -> Korrigjim (impakti)

RREGULLA ABSOLUTE:
- NUK LEJOHET te shpikesh gabime
- NUK LEJOHET ligj specifik pa konfirmim
- KONTRADIKTAT merren VETEM nga blloku automatik""",
    },

    # 6. HAPAT KONKRET TE VEPRIMIT (i paprekur)
    "action_steps": {
        "title": "PLANI I VEPRIMIT DHE REKOMANDIMET",
        "max_tokens": 2800,
        "prompt": """Ti je "Strateg i Larte Ligjor" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor ("PLANI I VEPRIMIT DHE REKOMANDIMET") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me "### A. ...".

DETYRA: Harto plan veprimi praktik per avokatin.

STRUKTURA:

### A. Vleresimi i Situates
- Ku qendron klienti ne kete proces?
- Cilat jane mundesite reale?

### B. Hapat e Menjehershem (1-7 dite)
1. [Veprim konkret]
2. ...

RREGULLA PER AFATET (STRIKTE):
- Nese dokumenti permend afat -> cituoje ME BURIMIN E SAKTE.
- NESE dokumenti NUK permend afat -> "Afati ligjor nuk u identifikua
  ne dokumentet e ngarkuara — kerkohet verifikim nga avokati."
- NUK LEJOHET "Afati: kontrollo manualisht"

🛑 NDALIM ABSOLUT I AFATEVE TE SHPIKURA:
- NUK LEJOHET te shkruash afate specifike ("24 ore", "48 ore", "8 dite",
  "15 dite", "3 dite", "1 jave") QE NUK SHFAQEN NE BLLOKUN [AFAT].
- Nese rekomandon urgjence → "Menjëherë" ose "Sa më parë".

### C. Hapat Afatgjate (1-3 muaj)

### D. Mundesite Procedurale
- Ankim / Kundershtim / Kerkese per rishqyrtim
- Reference ne nene te sakta (vetem ato qe jane ne fakte)

### E. Rreziqet
Listo 3-5 rreziqe ME BAZE NE FAKTE.

### F. Referencat Konkrete
- Ligjet perkatese (vetem ato qe jane ne fakte)
- Nenet specifike qe avokati duhet te konsultoje
- Precedente qe mund te perdore

RREGULLA:
- CDO veprim duhet te kete baze ne fakte
- CDO afat duhet te cituar me burim te sakte
- CDO ligj duhet te jete ne fakte""",
    },
}


SECTION_CONTEXT_MAP: Dict[str, List[str]] = {
    "document_summary": [
        "client", "meta", "parties", "dispositive", "medical", "tests",
        "convictions", "judge_court", "contradictions", "articles", "laws",
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
}

ALL_CONTEXT_BLOCKS = [
    "client", "meta", "articles", "laws", "case_numbers", "parties", "dates",
    "deadlines", "dispositive", "medical", "tests", "convictions",
    "judge_court", "contradictions", "reported_contradictions", "precedents",
]


# ===========================================================
# CONTEXT BLOCK BUILDERS
# ===========================================================

def _block_client_context(client_name: Optional[str]) -> List[str]:
    """V4.12: Kontekst i klientit per klasifikim te saktë te pozicionit."""
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

    return [
        "=" * 70,
        "[KLIENT] KONTEKST I KLIENTIT",
        "=" * 70,
        "",
        f"👤 KLIENTI (personi që përfaqësohet): **{client_name.strip()}**",
        "",
        "⚠️ RREGULL ABSOLUT:",
        f"  - Pozicioni i klientit në dokument DUHET të caktohet bazuar në emrin",
        f"    '{client_name.strip()}' — JO bazuar në atë se kujt i shërben dokumenti.",
        f"  - Nëse '{client_name.strip()}' është 'Pala Përgjegjëse' → ky është pozicioni.",
        f"  - Nëse '{client_name.strip()}' është 'Pala e Mbrojtur' → ky është pozicioni.",
        f"  - Nëse emri nuk shfaqet në dokument → 'NUK PËRCAKTOHET ne dokument'.",
        "",
    ]


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
    lines.append("[DOK] FILLIMI I DOKUMENTIT (per klasifikim + meta)")
    lines.append("=" * 70)
    lines.append("")

    header = doc_text[:1500].strip()
    if header:
        lines.append(header)
        lines.append("")

    lines.append("=" * 70)
    lines.append("[DOK] FUNDI I DOKUMENTIT (per date + nenshkrim)")
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
    lines.append(
        "ℹ️ KETA PRECEDENTE VIJNE NGA BAZA GLOBALE E GJYKATES SUPREME — "
        "jo nga fashikulli i kesaj lende."
    )
    lines.append("")

    if not precedents:
        lines.append(
            "Nuk u identifikuan precedentë relevante në bazën e Gjykatës "
            "Supreme për këtë lëndë."
        )
        lines.append("")
        lines.append(
            "⚠️ NUK LEJOHET të shpikësh numra precedentësh, faqe, ose burime. "
            "Shkruaj SAKTËSISHT fjalinë e mësipërme në raport."
        )
        lines.append("")
        return lines

    lines.append(
        f"Total: {len(precedents)} precedentë relevantë të verifikuar në bazën zyrtare."
    )
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

    lines.append(
        "⚠️ RREGULL: Paraqit VETËM këta precedentë. NUK LEJOHET të shpikësh asnjë."
    )
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
    allowed = _collect_allowed_values(
        citation_profile, fact_profile, verification_report
    )

    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("[!] ANTI-HALLUCINATION - LISTA E VLERAVE TE LEJUARA")
    lines.append("=" * 70)
    lines.append("")
    lines.append("RREGULL ABSOLUT: Ne output-in tend mund te permendesh VETEM")
    lines.append("vlera qe shfaqen ne listat me poshte. CDO vlere tjeter eshte")
    lines.append("HALLUCINATION dhe do te refuzohet automatikisht nga sistemi.")
    lines.append("")

    if allowed["dates"]:
        lines.append(f"* DATAT E LEJUARA ({len(allowed['dates'])}):")
        for d in sorted(allowed["dates"]):
            lines.append(f"    - {d}")
        lines.append("")
    else:
        lines.append("* DATAT E LEJUARA: (asnje - mos permend asnje date)")
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
        lines.append(
            f"* NUMRAT E NENEVE TE LEJUARA ({len(allowed['article_numbers'])}):"
        )
        for a in sorted(allowed["article_numbers"], key=lambda x: (len(x), x)):
            lines.append(f"    - Neni {a}")
        lines.append("")

    if allowed["case_numbers"]:
        lines.append(
            f"* NUMRAT E LENDEVE TE LEJUARA ({len(allowed['case_numbers'])}):"
        )
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
    lines.append(f"[LIGJ] PIKAT E DISPOZITIVIT ({len(points)} pika) - PJESA OPERATIVE")
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
    lines.append(
        "⚠️ NESE i njejti numer neni shfaqet DY HERE (me ligj + pa ligj), "
        "TRAJTOJI SI NJE NEN NE RAPORT."
    )
    lines.append(
        "⚠️ NESE 'Ligji i cituar: -' ose bosh → KURRË mos propozo ligj specifik."
    )
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
            lines.append(f"  [SUGJERIM] ZEVENDESIM I SUGJERUAR:")
            lines.append(f"     {sr.get('old_law', '')} -> {sr.get('new_law', '')}")
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
    lines.append(
        "⚠️ Per cdo afat, BURIMI (source_document) eshte treguar. "
        "Cito ate emer ne raport."
    )
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
    client_name: Optional[str] = None,   # V4.12
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

    # V4.12: Client context (gjithmonë kur jepet)
    if "client" in blocks_needed or client_name:
        lines.extend(_block_client_context(client_name))

    if section_key in ("document_summary", "action_steps") and doc_text:
        lines.extend(_block_document_header(doc_text))

    lines.extend(_block_antihallucination(
        citation_profile, fact_profile, verification_report
    ))

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