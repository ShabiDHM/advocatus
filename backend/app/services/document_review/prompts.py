# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V4.6 (LEGAL AUDIT, ASCII-SAFE)
# V4.6: BALANCIM I PRECEDENTEVE (fix overcorrection V4.5):
#       - Prompt "supreme_court_precedents" rishkruar me 3 NIVEL RELEVANCE:
#           (1) TEME IDENTIKE -> shpjego me 2-3 rreshta KONKRETE
#           (2) TEME E NGJASHME -> shpjego VETEM nese ka lidhje te qarte
#           (3) TEME E NDRYSHME -> "Nuk ka lidhje te drejtedrejte"
#         Kjo parandalon si spekullimin (V4.4) ashtu edhe overcorrection (V4.5)
#         ku LLM refuzonte edhe precedentët tematikë.
#       - Shtuar shembuj konkretë ne prompt (few-shot).
#       - max_tokens: 2400 -> 3500 (10 precedentë × shpjegim + Seksioni C
#         po pritej ne V4.5).
# V4.5: Rregull ndershmërie (overcorrected).
# V4.4: INTEGRIMI I PRECEDENTEVE TE VERTETA.
# V4.3: Fix-e pas raportit te Shtator 2026.
# V4.2: Shtuar _block_antihallucination().
# V4.1: FIX formatimi i paragrafit ne _block_articles.
# V4.0: Fokus "auditim ligjor" + 5 blloqe te reja konteksti.
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

⚠️ MOS shkruaj titullin kryesor ("PERMBLEDHJE EKZEKUTIVE E AUDITIMIT") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me seksionin 1.

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
- Perfundim: 1-2 rreshta "Hapi i ardhshëm" i sugjeruar""",
    },

    # ===========================================================
    # 2. VERIFIKIMI I NENEVE
    # ===========================================================
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
-> Sugjero zevendesimin konkret: "Ligji Nr. 03/L-182 eshte zevendesuar me 08/L-185"

STRUKTURA FUNDIT:
### Permbledhje e verifikimit
- Nene te verifikuara: X
- Nene me zevendesim te sugjeruar: Y
- Nene per verifikim manual: Z

MOS perfshi introduksione. Fillo direkt me nenet.""",
    },

    # ===========================================================
    # 3. PRECEDENTET E GJYKATES SUPREME (V4.6 - 3 nivele + shembuj)
    # ===========================================================
    "supreme_court_precedents": {
        "title": "PRECEDENTET E GJYKATES SUPREME",
        "max_tokens": 3500,
        "prompt": """Ti je "Analist i Precedenteve" ne Gjykaten Supreme te Kosoves.

⚠️ MOS shkruaj titullin kryesor ("PRECEDENTET E GJYKATES SUPREME") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me "### A. ...".

DETYRA: Analizo numrat e lendeve te cituar dhe paraqit precedentet relevante
qe SISTEMI ka gjetur ne bazen zyrtare te Gjykates Supreme.

═══════════════════════════════════════════════════════════════════════════
RREGULL ABSOLUT (KRITIKE)
═══════════════════════════════════════════════════════════════════════════
- Blloku "🏛️ PRECEDENTE RELEVANTE" permban precedentet e VERTETE te gjetur
  nga baza zyrtare. Keta jane BURIMI I VETEM I SE VERTETES.
- NUK LEJOHET te shpikesh numra precedentet, faqe, ose burime qe NUK
  shfaqen ne ate bllok.
- NUK LEJOHET te sugjerosh "kerkime konkrete" per avokatin.
- NESE blloku thote "Nuk u identifikuan precedentë relevante" -> shkruaj
  SAKTESISHT kete fraze, PA shtesa.

═══════════════════════════════════════════════════════════════════════════
RREGULL VLERESIMI I RELEVANCES (3 NIVELET)
═══════════════════════════════════════════════════════════════════════════

Per CDO precedent ne bllok, klasifikoji ne nje nga 3 nivelet:

▶ NIVELI 1 — TEME IDENTIKE:
  Precedenti trajton TE NJEJTEN teme si kjo lende (p.sh. te dyja per dhune
  familjare, urdher mbrojtjeje, kontakt me femije te mitur, kujdestari,
  ndryshim urdhri kufizues).
  → Shkruaj "Ka lidhje te drejtedrejte." + 2-3 rreshta KONKRETE si
    precedent mund te perdoret ne kete lende.

▶ NIVELI 2 — TEME E NGJASHME:
  Precedenti trajton teme te afert (p.sh. e drejta procedurale, gjykim
  i drejte, vleresim provash, parim i pergjithshem) POR jo te njejten
  çeshtje specifike.
  → Shkruaj "Ka lidhje indirekte permes [parimit X]." VETEM nese ka
    nje parim juridik te identifikueshem qe aplikohet direkt.

▶ NIVELI 3 — TEME E NDRYSHME:
  Precedenti trajton teme te tjera (p.sh. ndarje pasurie, kontrata civile,
  kompensim demi, kujdestari e fëmijëve ne kontekst tjeter, procedurë
  penale per krime te tjera).
  → Shkruaj SAKTESISHT: "Nuk ka lidhje te drejtedrejte me kete lende."
  PA fraza spekulative si:
    * "mund te jete i dobishem ne rastet kur..."
    * "mund te perdoret per..."
    * "thekson parimin e..." (kur parimi s'ka lidhje)

═══════════════════════════════════════════════════════════════════════════
SHEMBUJ KONKRETË (few-shot)
═══════════════════════════════════════════════════════════════════════════

Supozo se lendа eshte per DHUNE FAMILJARE + URDHER MBROJTJEJE + KONTAKT
ME FEMIJE TE MITUR.

✅ SAKTË (Niveli 1):
   1. Rev.Nr.240/2024
      Fragment: "...vendimi per besim te fëmijës nënës... kontaktit..."
      Rendesia praktike: Ka lidhje te drejtedrejte. Diskuton pikërisht
      besimin e fëmijës dhe kontaktin — tema identike me kete lende.
      Parimi i interesit superior te fëmijës aplikohet direkt.

✅ SAKTË (Niveli 2):
   2. Rev.Nr.171/24
      Fragment: "...qasja ne drejtesi...gjykim te drejte..."
      Rendesia praktike: Ka lidhje indirekte permes parimit te qasjes
      ne drejtesi. Perdoret nese pala ankohet per mohim te qasjes.

❌ SAKTË (Niveli 3 - REFUZO):
   3. Rev.Nr.64/2024
      Fragment: "...ndarje e pasurise familjare 1995...kontrata mbi
      mbajtjen e perjetshme..."
      Rendesia praktike: Nuk ka lidhje te drejtedrejte me kete lende.

❌ GABIM (spekullim - NUK LEJOHET):
   3. Rev.Nr.64/2024
      Rendesia praktike: "Ky precedent MUND TE JETE I DOBISHEM ne rastet
      ku bëhet fjalë për çështje të pasurisë familjare në kuadrin e
      urdhrave të mbrojtjes."  ← E NDALUAR. Krijon lidhje artificiale.

═══════════════════════════════════════════════════════════════════════════
STRUKTURA E OUTPUT-IT
═══════════════════════════════════════════════════════════════════════════

### A. Numrat e Cituar ne Dokument
Per cdo numer lende qe shfaqet ne dokument:
- Numri + statusi (OWN / PRECEDENT REAL / CITED_NOT_FOUND)
- Pse ka rendesi

### B. Precedentë Relevante (nga baza zyrtare)
Per cdo precedent ne bllok:
- Numri i lendes (saktesisht siç shfaqet)
- Fragmenti relevant (1-2 rreshta)
- Burimi + faqja
- Rendesia praktike (sipas 3 niveleve me lart)

### C. Rendesia Praktike (permbledhje)
Permbledhje e shkurter (3-5 rreshta) e precedentëve qe KANE lidhje
te drejtedrejte (Niveli 1 ose 2).

NESE asnje precedent nuk ka lidhje (te gjithe Niveli 3) -> shkruaj:
"Asnjë prej precedentëve të identifikuar nuk ka lidhje të drejtpërdrejtë
me temën e kësaj lënde. Rekomandohet kërkim shtesë manual."

NESE ka precedentë me lidhje -> permbledh per avokatin si mund t'i perdore.

RREGULLA FINALE:
- Perdor VETEM precedentet nga blloku "🏛️ PRECEDENTE RELEVANTE".
- NUK spekulon per lidhje qe nuk ekzistojne.
- NUK refuzon precedentët qe KANE lidhje.
- Balanco ndershmërine me vleren praktike per avokatin.""",
    },

    # ===========================================================
    # 4. ANALIZA E CILESISE SE HARTIMIT
    # ===========================================================
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
- A perputhet dispozitivi me arsyetimin?
- A perputhen kohezgjatjet/distanceat?
Nese ka kontradikta -> listoji te gjitha me referenca.

### E. Vleresimi perfundimtar
Note 1-5 me arsyetim 2-3 rreshta.

NUK LEJOHET te shpikesh mangesi qe nuk shfaqen ne fakte.""",
    },

    # ===========================================================
    # 5. GABIME DHE KORRIGJIME
    # ===========================================================
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

⚠️ MOS shkruaj titullin kryesor ("PLANI I VEPRIMIT DHE REKOMANDIMET") —
   shtohet automatikisht nga sistemi. Fillo DIREKT me "### A. ...".

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
  ME BURIMIN E SAKTE: "Sipas [emri i dokumentit], afati eshte N dite."
- NESE dokumenti NUK permend afat -> shkruaj SAKTESISHT:
    "Afati ligjor nuk u identifikua ne dokumentet e ngarkuara —
     kerkohet verifikim nga avokati."
- NUK LEJOHET te shkruash "Afati: kontrollo manualisht"
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
- CDO afat duhet te cituar me burim te sakte
- CDO ligj duhet te jete ne fakte""",
    },
}


# ===========================================================
# V4.0: SECTION_CONTEXT_MAP
# ===========================================================

SECTION_CONTEXT_MAP: Dict[str, List[str]] = {
    "document_summary": [
        "meta", "parties", "dispositive", "medical", "tests",
        "convictions", "judge_court", "contradictions", "articles", "laws",
    ],
    "article_verification": ["articles", "laws"],
    "supreme_court_precedents": ["case_numbers", "meta", "precedents"],
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
    "judge_court", "contradictions", "precedents",
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
# V4.4: PRECEDENTS BLOCK
# ═══════════════════════════════════════════════════════════════════════════

def _block_precedents(
    precedents: Optional[List[Dict[str, Any]]],
) -> List[str]:
    """
    V4.4: Blloku i precedenteve te vertete te gjetur nga legal_knowledge_base.
    """
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("🏛️ PRECEDENTE RELEVANTE (nga baza e Gjykatës Supreme)")
    lines.append("=" * 70)

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
    lines.append(
        "⚠️ ÇDO precedent i mëposhtëm është VERIFIKUAR në bazën zyrtare të "
        "Gjykatës Supreme."
    )
    lines.append(
        "⚠️ NUK LEJOHET të shpikësh numra të tjerë, faqe, ose burime."
    )
    lines.append(
        "⚠️ Klasifikoji sipas 3 niveleve të relevancës (shih prompt-in): "
        "TEME IDENTIKE -> shpjego; TEME E NGJASHME -> shpjego; "
        "TEME E NDRYSHME -> 'Nuk ka lidhje të drejtpërdrejtë'."
    )
    lines.append("")

    for i, p in enumerate(precedents, 1):
        case_number = str(p.get("case_number", "?")).strip()
        similarity = p.get("similarity", 0.0)
        excerpt = (p.get("text_excerpt") or "").strip()
        source = p.get("source", "?")
        page = p.get("page", "?")
        chunk_id = p.get("chunk_id", "?")

        lines.append(f"  {i}. [{case_number}] — similarity={similarity:.2f}")
        if excerpt:
            lines.append(f'     Fragment: "{excerpt[:400]}"')
        lines.append(f"     Burimi: {source}, faqe {page}")
        lines.append(f"     chunk_id: {chunk_id}")
        lines.append("")

    lines.append(
        "⚠️ RREGULL: Paraqit VETËM këta precedentë në raport. "
        "NUK LEJOHET të shpikësh asnjë tjetër."
    )
    lines.append("")
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# V4.2: ANTI-HALLUCINATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════

def _collect_allowed_values(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
) -> Dict[str, Set[str]]:
    allowed: Dict[str, Set[str]] = {
        "dates": set(),
        "law_numbers": set(),
        "law_abbrevs": set(),
        "article_numbers": set(),
        "case_numbers": set(),
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
    lines.append("Me mire te thuash 'nuk eshte e dokumentuar' sesa te shpikesh.")
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
    lines.append("[!] Kjo eshte pjesa OPERATIVE e dokumentit - me e rendesishmja ligjerisht.")
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
    for dl in deadlines:
        lines.append(f"  * {dl['display']}")
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
# MAIN - build_verified_context (per-section) V4.6
# ===========================================================

def build_verified_context(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    document_type: str = "Dokument",
    file_name: str = "Dokument",
    section_key: Optional[str] = None,
    precedents: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    V4.6: Nderton tekstin me faktet e verifikuara.

    Args:
        precedents: V4.4 - liste me precedentet e vertete (nga precedent_search).
                    Perdoret vetem per section_key="supreme_court_precedents".
    """
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

    lines.extend(_block_antihallucination(
        citation_profile, fact_profile, verification_report
    ))

    if "contradictions" in blocks_needed:
        lines.extend(_block_contradictions(fact_profile))

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

    result = "\n".join(lines).strip()
    return result