# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V4.2 (LEGAL AUDIT, ASCII-SAFE)
# V4.2: Shtuar _block_antihallucination() — liste e mbyllur e vlerave te lejuara
#       (data, ligje, nene, numra lende). Blloku shfaqet GJITHMONE pas meta.
#       Perditesuar _block_contradictions() per te shfaqur zonen (Fakte/Arsyetim/
#       Dispozitiv/Propozim) — ndihmon LLM te kuptoje pse kontradikta vlen.
# V4.1: FIX i vetem ndaj V4.0 — formatimi i paragrafit ne _block_articles:
#       ", par.2" -> " par. 2" (ne perputhje me konventen ligjore shqipe).
# V4.0: Fokus "auditim ligjor" (jo permbledhje) + 5 blloqe te reja konteksti:
#       dispositive, medical, tests, convictions, judge_court.
# V3.1: build_verified_context(section_key) + blloqe te vecanta.
# V3.0: Arkitekture e re: LLM NUK verifikon - vetem interpreton/shkruan.

from typing import Dict, Any, List, Optional, Set

DOCUMENT_REVIEW_PROMPTS = {
    # ===========================================================
    # 1. PERMBLEDHJE EKZEKUTIVE E AUDITIMIT
    # ===========================================================
    "document_summary": {
        "title": "PERMBLEDHJE EKZEKUTIVE E AUDITIMIT",
        "max_tokens": 1400,
        "prompt": """Ti je "Auditues Ligjor i Gjykates Supreme te Kosoves" ne zyre keshilluese.

DETYRA: Harto nje PERMBLEDHJE EKZEKUTIVE te dokumentit - jo nje rrefim, por nje
diagnoze profesionale per avokatin qe do te veproje me kete dokument.

STRUKTURA E DETYRUAR:

1. Klasifikimi i dokumentit
- Lloji: [Vendim / Aktvendim / Padi / Kontrate / Kallezim / ...]
- Leshuesi: [Gjykate / Prokurori / Pale / ...]
- Data dhe numri i lendes

2. Subjekti (palet + rolet)
- Palet kryesore
- Pozicioni i klientit (nese dihet)

3. Permbajtja operative (3-4 rreshta)
- Cka vendosi/pretendoi pala?
- Cilat ishin arsyet kryesore?

4. Ceshtje kritike qe avokati DUHET te dije
- Nese ka KONTRADIKTA te brendshme (kohezgjatje, distance) -> listoji
- Nese ka diagnoza mjekesore -> permendji me ICD
- Nese ka denime te meparshme -> permendji
- Nese ka teste mjekesore -> permend rezultatin

5. Niveli i auditimit
- Sa nene u verifikuan me sukses
- Sa nene mbeten te paverifikueshme

RREGULLA:
- Perdor VETEM faktet ne "FAKTET E VERIFIKUARA"
- Mos shpik asnje detaj
- Fokus ne ate qe Ndryshon vendimin, jo narrative
- Perfundim: 1-2 rreshta "Next step" i sugjeruar""",
    },

    # ===========================================================
    # 2. VERIFIKIMI I NENEVE - me zevendesime
    # ===========================================================
    "article_verification": {
        "title": "VERIFIKIMI DHE AUDITIMI I NENEVE LIGJORE",
        "max_tokens": 3500,
        "prompt": """Ti je "Verifikues i Neneve Ligjore" ne Gjykaten Supreme te Kosoves.

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
-> Sugjero zevendesimin konkret: "Ligji Nr. 03/L-182 eshte zevendesuar me 08/L-185"

STRUKTURA FUNDIT:
### Permbledhje e verifikimit
- Nene te verifikuara: X
- Nene me zevendesim te sugjeruar: Y
- Nene per verifikim manual: Z

MOS perfshi introduksione. Fillo direkt me nenet.""",
    },

    # ===========================================================
    # 3. PRECEDENTET E GJYKATES SUPREME
    # ===========================================================
    "supreme_court_precedents": {
        "title": "PRECEDENTET E GJYKATES SUPREME",
        "max_tokens": 2400,
        "prompt": """Ti je "Analist i Precedenteve" ne Gjykaten Supreme te Kosoves.

DETYRA: Analizo cdo numer lende te cituar dhe sugjero precedente relevante.

KLASIFIKIMI I SISTEMIT:
- OWN = numri i ketij dokumenti (NUK eshte precedent)
- PRECEDENT REAL = verifikuar ne bazen e Gjykates Supreme
- CITED_NOT_FOUND = cituar por qe nuk gjendet

STRUKTURA:

### A. Numrat e Cituar ne Dokument
Per cdo numer: statusi + pse ka rendesi.

### B. Vleresimi i Referencave
- A ka precedente te vertete?
- A eshte argumenti i mbeshtetur ligjerisht?

### C. Sugjerime per Precedente
NESE dokumenti nuk citon precedente, ose citon keq:
- Kerko ne faktet e verifikuara per kategori rasti (p.sh. "dhune ne familje")
- Sugjero kerkime konkrete qe avokati mund te beje:
  * "Gjykata Supreme - Aktgjykim per urdher mbrojtjeje me diagnoza psikiatrike"
  * "Gjykata Supreme - precedent per kontakt me femije te mitur"
- NUK LEJOHET te shpikesh numra precedentet
- NUK LEJOHET te pretendosh se ekzistojne pa verifikim

### D. Rendesia Praktike
Pse keta precedente jane te rendesishem per avokatin.""",
    },

    # ===========================================================
    # 4. ANALIZA E CILESISE SE HARTIMIT
    # ===========================================================
    "drafting_quality": {
        "title": "ANALIZA E CILESISE SE HARTIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Revizor i Cilesise se Akteve Gjyqesore" ne Gjykaten Supreme te Kosoves.

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
- A perputhet dispozitivi me arsyetimin?
- A perputhen kohezgjatjet/distanceat?
Nese ka kontradikta -> listoji te gjitha me referenca.

### E. Vleresimi perfundimtar
Note 1-5 me arsyetim 2-3 rreshta.

NUK LEJOHET te shpikesh mangesi qe nuk shfaqen ne fakte.""",
    },

    # ===========================================================
    # 5. GABIME DHE KORRIGJIME - me zevendesime konkrete
    # ===========================================================
    "errors_corrections": {
        "title": "GABIME, KONTRADIKTA DHE KORRIGJIME",
        "max_tokens": 3000,
        "prompt": """Ti je "Auditues i Akteve Gjyqesore" ne Gjykaten Supreme te Kosoves.

DETYRA: Raporto CDO gabim, kontradikte dhe propozo korrigjime konkrete.

FORMATI I DETYRUAR:

### A. Gabime ne nene
Per cdo nen qe NUK u verifikua:
    [X] Neni [X] ([Ligji i cituar])
        Problem: [pse nuk u gjet]
        Korrigjim i propozuar: [neni i sakte / ligji i ri]
        Impakti: [cka humbet pa kete]

### B. Kontradikta te brendshme
NESE KA KONTRADIKTA NE FAKTE -> listoji:
    [!] KONTRADIKTE ne [kohezgjatje/date/distance] (zona: [Fakte/Dispozitiv/...])
        Referenca 1: "[citat]" (pozicioni)
        Referenca 2: "[citat]" (pozicioni)
        Rekomandim: [cila vlen ligjerisht + si te verifikohet]

### C. Gabime procedurale
Vetem nese ka baze ne fakte. NESE NUK KA -> shkruaj "[OK] Nuk u identifikuan gabime procedurale."

### D. Korrigjime te rekomanduara
Per cdo gabim -> 1 rresht: Gabim -> Korrigjim (impakti)

RREGULLA ABSOLUTE:
- NUK LEJOHET te shpikesh gabime
- NUK LEJOHET te sugjerosh zevendesime pa baze ne fakte
- NESE NUK KA GABIME -> thuaj: "[OK] Dokumenti kaloi auditimin pa gabime kritike."
- KONTRADIKTAT jane gjithmone prioritet i larte - listoji te para""",
    },

    # ===========================================================
    # 6. HAPAT KONKRET TE VEPRIMIT
    # ===========================================================
    "action_steps": {
        "title": "PLANI I VEPRIMIT DHE REKOMANDIMET",
        "max_tokens": 2800,
        "prompt": """Ti je "Strateg i Larte Ligjor" ne Gjykaten Supreme te Kosoves.

DETYRA: Harto plan veprimi praktik per avokatin qe ka marre kete dokument.

STRUKTURA:

### A. Vleresimi i Situates
- Ku qendron klienti ne kete proces?
- Cilat jane mundesite reale (jo teoretike)?

### B. Hapat e Menjehershem (1-7 dite)
1. [Veprim konkret]
2. ...

RREGULLA PER AFATET:
- Nese dokumenti permend afat (p.sh. "8 dite per ankese") -> cituoje
- Nese nuk permendet -> shkruaj "Afati: kontrollo manualisht"
- NUK LEJOHET te shpikesh afate

### C. Hapat Afatgjate (1-3 muaj)
1. ...
2. ...

### D. Mundesite Procedurale
- Ankim / Kundershtim / Kerkese per rishqyrtim
- Kerkese per ndryshim / zgjatje
- Reference ne nene te sakta

### E. Rreziqet
Listo 3-5 rreziqe ME BAZE NE FAKTE:
- Cka mund te shkoje keq
- Si te mbrohet klienti

### F. Referencat Konkrete
- Ligjet perkatese (vetem ato qe jane ne fakte)
- Nenet specifike qe avokati duhet te konsultoje
- Precedente qe mund te perdore

RREGULLA:
- CDO veprim duhet te kete baze ne fakte
- CDO afat duhet te cituar ose te flagohet "kontrollo manualisht"
- CDO ligj duhet te jete ne fakte""",
    },
}


# ===========================================================
# V4.0: SECTION_CONTEXT_MAP - cka i duhet secilit seksion
# ===========================================================

SECTION_CONTEXT_MAP: Dict[str, List[str]] = {
    "document_summary": [
        "meta", "parties", "dispositive", "medical", "tests",
        "convictions", "judge_court", "contradictions", "articles", "laws",
    ],
    "article_verification": ["articles", "laws"],
    "supreme_court_precedents": ["case_numbers", "meta"],
    "drafting_quality": [
        "meta", "parties", "dispositive", "articles", "laws", "contradictions",
    ],
    "errors_corrections": [
        "articles", "laws", "contradictions", "dispositive", "medical",
    ],
    "action_steps": [
        "meta", "parties", "dates", "deadlines", "case_numbers",
        "dispositive", "judge_court",
    ],
}

ALL_CONTEXT_BLOCKS = [
    "meta", "articles", "laws", "case_numbers", "parties", "dates",
    "deadlines", "dispositive", "medical", "tests", "convictions",
    "judge_court", "contradictions",
]


# ===========================================================
# CONTEXT BLOCK BUILDERS
# ===========================================================

def _block_meta(
    document_type: str,
    file_name: str,
) -> List[str]:
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


# ═══════════════════════════════════════════════════════════════════════════
# V4.2: ANTI-HALLUCINATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════

def _collect_allowed_values(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
) -> Dict[str, Set[str]]:
    """
    V4.2: Mbledh te gjitha vlerat e lejuara nga profilet.
    Keto jane vlerat e vetme qe LLM mund t'i permende.
    """
    allowed: Dict[str, Set[str]] = {
        "dates": set(),
        "law_numbers": set(),
        "law_abbrevs": set(),
        "article_numbers": set(),
        "case_numbers": set(),
    }

    # Datat (display format)
    for d in fact_profile.get("dates", []) or []:
        if d.get("display"):
            allowed["dates"].add(d["display"])
        if d.get("iso"):
            allowed["dates"].add(d["iso"])

    # Ligjet sipas numrit
    for l in citation_profile.get("laws_by_number", []) or []:
        if l.get("number"):
            allowed["law_numbers"].add(l["number"])
    for l in verification_report.get("laws_by_number", []) or []:
        if l.get("number"):
            allowed["law_numbers"].add(l["number"])

    # Akronimet
    for a in citation_profile.get("abbreviations", []) or []:
        allowed["law_abbrevs"].add(a)

    # Nenet (numrat)
    for a in citation_profile.get("articles", []) or []:
        if a.get("number"):
            allowed["article_numbers"].add(a["number"])

    # Numrat e lendeve
    for c in citation_profile.get("case_numbers", []) or []:
        if c.get("case_number"):
            allowed["case_numbers"].add(c["case_number"])

    return allowed


def _block_antihallucination(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
) -> List[str]:
    """
    V4.2: Blloku ANTI-HALLUCINATION.

    Liston VETEM vlerat e lejuara (data, ligje, nene, numra lende).
    Cdo date/numer/ligj qe shfaqet ne output-in e LLM DUHET te ekzistoje ne kete liste.
    Cdo vlere jashte listes = hallucination.
    """
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

    # Datat
    if allowed["dates"]:
        lines.append(f"* DATAT E LEJUARA ({len(allowed['dates'])}):")
        for d in sorted(allowed["dates"]):
            lines.append(f"    - {d}")
        lines.append("")
    else:
        lines.append("* DATAT E LEJUARA: (asnje - mos permend asnje date)")
        lines.append("")

    # Ligjet
    if allowed["law_numbers"]:
        lines.append(f"* LIGJET E LEJUARA ({len(allowed['law_numbers'])}):")
        for l in sorted(allowed["law_numbers"]):
            lines.append(f"    - {l}")
        lines.append("")

    # Akronimet
    if allowed["law_abbrevs"]:
        lines.append(f"* AKRONIMET E LEJUARA ({len(allowed['law_abbrevs'])}):")
        for a in sorted(allowed["law_abbrevs"]):
            lines.append(f"    - {a}")
        lines.append("")

    # Nenet
    if allowed["article_numbers"]:
        lines.append(
            f"* NUMRAT E NENEVE TE LEJUARA ({len(allowed['article_numbers'])}):"
        )
        for a in sorted(allowed["article_numbers"], key=lambda x: (len(x), x)):
            lines.append(f"    - Neni {a}")
        lines.append("")

    # Numrat e lendeve
    if allowed["case_numbers"]:
        lines.append(
            f"* NUMRAT E LENDEVE TE LEJUARA ({len(allowed['case_numbers'])}):"
        )
        for c in sorted(allowed["case_numbers"]):
            lines.append(f"    - {c}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("KUJTESE: Nese dyshon per nje vlere, MOS E PERDOR.")
    lines.append("Me mire te thuash 'nuk eshte e dokumentuar' sesa te shpikesh.")
    lines.append("=" * 70)
    lines.append("")

    return lines


def _block_dispositive(fact_profile: Dict[str, Any]) -> List[str]:
    """V4.0: Pikat e dispozitivit (VENDIMTARE per vendime)."""
    lines = []
    points = fact_profile.get("dispositive_points", [])
    if not points:
        return lines

    lines.append("=" * 70)
    lines.append(f"[LIGJ] PIKAT E DISPOZITIVIT ({len(points)} pika) - PJESA OPERATIVE")
    lines.append("=" * 70)
    lines.append("[!] Kjo eshte pjesa OPERATIVE e dokumentit - me e rendesishmja ligjerisht.")
    lines.append("")
    for p in points:
        lines.append(f"**{p['roman']}.** {p['content']}")
        lines.append("")
    return lines


def _block_medical(fact_profile: Dict[str, Any]) -> List[str]:
    """V4.0: Gjetjet mjekesore (ICD + diagnoza)."""
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
    """V4.0: Testet mjekesore dhe rezultatet."""
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
    """V4.0: Denime te meparshme penale."""
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
    """V4.0: Gjyqtari, gjykata, afati i ankeses."""
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
    for a in verified_articles:
        status = "[OK] EKZISTON" if a["exists"] else "[X] NUK U GJET"
        law_hint = a.get("law_hint", "") or "-"
        # V4.1: formatim " par. N" (jo ", par.N")
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
    for dl in deadlines:
        lines.append(f"  * {dl['display']}")
        lines.append(f"    Konteksti: {dl.get('context', '')[:200]}")
    lines.append("")
    return lines


def _block_contradictions(fact_profile: Dict[str, Any]) -> List[str]:
    """
    V4.2: Kontradikta - tani me ZONE (Fakte/Arsyetim/Dispozitiv/Propozim).
    Zona tregon kontekstin ku ndodh kontradikta.
    """
    lines = []
    contradictions = fact_profile.get("contradictions", [])
    if not contradictions:
        return lines

    lines.append("=" * 70)
    lines.append(f"[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT ({len(contradictions)})")
    lines.append("=" * 70)
    lines.append("[!] KETO JANE FAKTE KRITIKE - DUHET LISTUAR NE RAPORT!")
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


# ===========================================================
# MAIN - build_verified_context (per-section) V4.2
# ===========================================================

def build_verified_context(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    document_type: str = "Dokument",
    file_name: str = "Dokument",
    section_key: Optional[str] = None,
) -> str:
    """
    V4.2: Nderton tekstin me faktet e verifikuara.
    Perfshin blloqet: meta, antihallucination (gjithmone), contradictions,
    dispositive, medical, tests, convictions, judge_court, articles, laws,
    case_numbers, parties, dates, deadlines.
    """
    if section_key:
        blocks_needed = SECTION_CONTEXT_MAP.get(section_key, ALL_CONTEXT_BLOCKS)
    else:
        blocks_needed = ALL_CONTEXT_BLOCKS

    lines: List[str] = []

    # Meta gjithmone se pari
    if "meta" in blocks_needed:
        lines.extend(_block_meta(document_type, file_name))
    else:
        lines.append("=" * 70)
        lines.append(f"DOKUMENTI: {file_name} - LLOJI: {document_type}")
        lines.append("=" * 70)
        lines.append("")

    # V4.2: ANTI-HALLUCINATION - GJITHMONE pas meta
    lines.extend(_block_antihallucination(
        citation_profile, fact_profile, verification_report
    ))

    # V4.0: Kontradikta te para (kritike)
    if "contradictions" in blocks_needed:
        lines.extend(_block_contradictions(fact_profile))

    # V4.0: Dispozitivi
    if "dispositive" in blocks_needed:
        lines.extend(_block_dispositive(fact_profile))

    # V4.0: Mjekesia
    if "medical" in blocks_needed:
        lines.extend(_block_medical(fact_profile))

    # V4.0: Testet
    if "tests" in blocks_needed:
        lines.extend(_block_tests(fact_profile))

    # V4.0: Denimet
    if "convictions" in blocks_needed:
        lines.extend(_block_convictions(fact_profile))

    # V4.0: Gjyqtari / gjykata
    if "judge_court" in blocks_needed:
        lines.extend(_block_judge_court(fact_profile))

    # Nenet
    if "articles" in blocks_needed:
        lines.extend(_block_articles(verification_report))

    # Ligjet
    if "laws" in blocks_needed:
        lines.extend(_block_laws(verification_report))

    # Numrat e lendeve
    if "case_numbers" in blocks_needed:
        lines.extend(_block_case_numbers(verification_report))

    # Palet
    if "parties" in blocks_needed:
        lines.extend(_block_parties(fact_profile))

    # Datat
    if "dates" in blocks_needed:
        lines.extend(_block_dates(fact_profile))

    # Afatet
    if "deadlines" in blocks_needed:
        lines.extend(_block_deadlines(fact_profile))

    result = "\n".join(lines).strip()
    return result