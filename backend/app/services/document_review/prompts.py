# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V4.27
# V4.27: MAX_TOKENS INCREASE — Rritur max_tokens për 6 seksione që u
#        cunguan në testimin e fundit (output më i gjatë se limit):
#        - document_summary: 1800 → 3000 (ishte copëtuar në Seksionin 5)
#        - drafting_quality: 2600 → 4000 (nota e fundit ishte prerë)
#        - errors_corrections: 3200 → 4000 (veprimet korrigjuese)
#        - action_steps: 3200 → 4000 (hapat 1-7 ditë + afatgjatë)
#        - analiza_e_thelluar: 3800 → 4500 (shenjat e reja)
#        - konstatimet_e_analizes: 2400 → 3200 (përmbledhje ekzekutive)
#        Zero impakt negativ: max_tokens është kufi maksimal, jo target.
# V4.26: PROFESSIONAL LANGUAGE (vazhdim).
# V4.25: "FLAMUJT_FORENSIK" → "KONSTATIMET_E_ANALIZËS".
# V4.24: LAW_NUMBER_RULE.

from typing import Dict, Any, List, Optional, Set

from .verify.prompt_rules import (
    DEDUP_RULE,
    PRECEDENT_SOURCE_RULE,
    CASE_CONTEXT_RULE,
    LAW_NUMBER_RULE,
    PROFESSIONAL_LANGUAGE_RULE,
    FORENSIC_FINDINGS_RULE,
)


DOCUMENT_REVIEW_PROMPTS = {

    # ═══════════════════════════════════════════════════════════════════
    # 1. DIAGNOZA E SITUATËS
    # ═══════════════════════════════════════════════════════════════════
    "document_summary": {
        "title": "DIAGNOZA E SITUATËS",
        "max_tokens": 3000,  # V4.27: 1800 → 3000
        "prompt": """Ti je "KËSHILLTAR I GJYKATËS SUPREME TË KOSOVËS" me 20+ vjet 
përvojë. Zyra jote është një ZYRË KËSHILLUESE — jo gjyqësore.

⚠️ MOS shkruaj titullin kryesor — shtohet automatikisht. Fillo DIREKT 
me seksionin 1.

MISIONI: Harto një DIAGNOZË të situatës — jo listë faktesh.

⚠️ RREGULL ABSOLUT PËR KLASIFIKIMIN:

0. **KLIENTI + ROLET:** Shih bllokun "[KLIENT]".
   - Në seksionin 2, raporto TË DYJA rolet:
     * Ndryshojnë → "Klienti (emri) është [roli_case] në rastin kryesor, 
       por në këtë dokument shfaqet si [roli_dokument]."
     * Përputhen → raporto vetëm një rol.
     * Nuk shfaqet → "NUK PËRCAKTOHET në dokument".

STRUKTURA E DETYRUAR (5 seksione):

### 1. Diagnoza e situatës (2-3 fjali)
### 2. Faktet themelore (3-4 fjali)
### 3. Çështje kritike me rëndësi për avokatin (3-5 pika)
### 4. Vlerësim fillestar — dyshimet kryesore
### 5. **Fokusi i rekomanduar** (1-2 fjali)
   - Formulo si rekomandim profesional:
     * ✅ "Rekomandohet fokusimi në..."
     * ✅ "Këshillohet të shqyrtohet..."
     * ❌ "Avokati duhet të fokusohet në..."

RREGULLA:
- Perdor VETEM faktet ne blloqet "[KLIENT]", "[DOK]", "[PALE]", "[PERSONA]"
- NUK shpik data, leshues, role
- 🛑 NUK CITE KODE LIGJORE që nuk shfaqen në bllokun [NENE] ose [LIGJE].
- Fjalitë të shkurtra. Çdo fjali me vlerë.
- NËSE blloku [FASHIKULLI] ekziston, referoju për konsistencë.

""" + PROFESSIONAL_LANGUAGE_RULE + CASE_CONTEXT_RULE + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 2. VERIFIKIMI I NENEVE
    # ═══════════════════════════════════════════════════════════════════
    "article_verification": {
        "title": "VERIFIKIMI DHE AUDITIMI I NENEVE LIGJORE",
        "max_tokens": 3500,  # V4.27: pa ndryshim (output ~4000 chars OK)
        "prompt": """Ti je "Verifikues i Cilësisë Ligjore" në zyrën këshilluese 
të Gjykatës Supreme. Ti nuk liston — DIAGNOSTIKON.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Raporto VETËM problemet me nenet e cituara.

STRUKTURA E DETYRUAR (3 seksione, jo më shumë):

### A. Nene problematike
Për ÇDO nen me problem, formato:

**[Neni X i Ligjit Y]**
- **Statusi:** NUK EKZISTON / KONTEKST I GABUAR / I PAPËRDORSHËM
- **Cituar në dokument:** "[citat i saktë]"
- **Problemi:** [shpjegim konkret]
- **Ndikimi:** [sa i rëndësishëm për rastin]

🛑 KATEGORITË E PROBLEMEVE:
1. **NUK EKZISTON** — neni nuk gjendet në ligjin e cituar
2. **KONTEKST I GABUAR** — neni ekziston, por në LIGJ TJETËR
3. **I PAPËRDORSHËM** — neni ekziston, por FUSHA NUK PËRPUTHET me dokumentin
4. **I ZËVENDËSUAR** — neni është zëvendësuar me version më të ri

🛑 RREGULL I PAPËRDORSHËM:
Nëse neni ekziston në ligj POR përmbajtja e tij është për fushë tjetër 
nga dokumenti → raporto si I PAPËRDORSHËM.

### B. Nene që mund të mungojnë
Vetëm sugjerime me bazë të fortë.

### C. Përmbledhje statistikore
1-2 fjali.

🛑 NUK LEJOHET:
- Të përsëritësh nenet e seksionit A (Python)
- Të shpikësh nene problematike që nuk gjenden në kontekst

""" + PROFESSIONAL_LANGUAGE_RULE + LAW_NUMBER_RULE + DEDUP_RULE + PRECEDENT_SOURCE_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 3. PRECEDENTËT
    # ═══════════════════════════════════════════════════════════════════
    "supreme_court_precedents": {
        "title": "PRECEDENTËT E GJYKATËS SUPREME",
        "max_tokens": 3500,  # V4.27: pa ndryshim
        "prompt": """Ti je "Analist i Precedentëve" në zyrën këshilluese të 
Gjykatës Supreme të Kosovës.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

🛑 RREGULLI #1 — MOS SHPIK PRECEDENTË:
- KUR NUK KA precedentë relevantë → shkruaj SAKTËSISHT: 
  "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme 
   për këtë çështje."

📌 KUPTIMI I TAG-ËVE NË BLLOKUN [LENDE]:
  * [OWN]   → numri i lëndës së VETË dokumentit. NUK është precedent.
  * [OK]    → precedent real, verifikuar në KB.
  * [CITIM] → precedent i CITUAR NË DOKUMENT.

STRUKTURA (3 seksione):

### A. Precedentë të Verifikuar nga Baza
Nëse s'ka → frazën standarde.

### B. Precedentë të Cituar në Dokument (jo të verifikuar)
FILLO me "Sipas dokumentit: ".

### C. Vlera Praktike për Këtë Rast
1-2 fjali.

""" + PROFESSIONAL_LANGUAGE_RULE + DEDUP_RULE + PRECEDENT_SOURCE_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 4. CILËSIA E HARTIMIT
    # ═══════════════════════════════════════════════════════════════════
    "drafting_quality": {
        "title": "ANALIZA E CILËSISË SË HARTIMIT",
        "max_tokens": 4000,  # V4.27: 2600 → 4000 (nota po pritej)
        "prompt": """Ti je "Revizor i Cilësisë së Akteve Gjyqësore".

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Vlerëso cilësinë e përgjithshme. Nota NUK është nominale.

🛑 RREGULL ABSOLUT PËR NOTËN:
- NUK MUND të jetë 5/5 nëse [KONSTATIMET_E_ANALIZËS] ka konstatime kritike ose 
  të rëndësishme.
- NUK MUND të jetë 5/5 nëse Section 5 ka shkelje.

KAP I NOTËS:
- **5/5 (Shkëlqyeshëm)** → vetëm nëse nuk u identifikuan gabime
- **4/5 (Shumë mirë)** → gabime të vogla procedurale pa ndikim
- **3/5 (I mirë)** → gabime thelbësore ose konstatime të rëndësishme
- **2/5 (I dobët)** → shkelje substanciale ose konstatime kritike
- **1/5 (Shumë i dobët)** → shkelje të rënda ligjore

STRUKTURA:

### A. Struktura formale
### B. Terminologjia juridike
### C. Arsyetimi juridik
### D. Konsistenca e brendshme
VETËM bllokun "[!] MOSPËRPUTHJE TË IDENTIFIKUARA AUTOMATIKISHT".

### E. Nota përfundimtare (1-5)
**Nota: X/5** — [arsyeja në 1 fjali]
- Nëse ka konstatime kritike ose të rëndësishme → referoju atyre
  me terma profesionale ("konstatime kritike" — JO "flamuj kritikë").

""" + PROFESSIONAL_LANGUAGE_RULE + FORENSIC_FINDINGS_RULE + CASE_CONTEXT_RULE + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 5. GABIME DHE KORRIGJIME
    # ═══════════════════════════════════════════════════════════════════
    "errors_corrections": {
        "title": "MOSPËRPUTHJE DHE VEPRIME KORRIGJUESE",
        "max_tokens": 4000,  # V4.27: 3200 → 4000
        "prompt": """Ti je "Zbulues i Shkeljeve Ligjore" në zyrën këshilluese 
të Gjykatës Supreme.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Identifiko shkeljet e VËRTETA me ndikim praktik që lidhen 
ME DRAFTIN DHE FASHIKULLIN.

📌 KONSTATIMET E ANALIZËS trajtohen ekskluzivisht në SEKSIONIN 8
   "KONSTATIMET E ANALIZËS" — NUK ripërsëriten këtu.

STRUKTURA (4 seksione):

### A. Gabime në nene
VETËM nëse ka gabime reale.

### B. Mospërputhje të brendshme
VETËM nga blloku "[!] MOSPËRPUTHJE TË IDENTIFIKUARA AUTOMATIKISHT".
Për çdo mospërputhje:
  - Cito TË DYJA vlerat me burimin specifik
  - Shpjego ndikimin praktik

### C. Gabime procedurale
Vetëm gabime reale nga vetë drafti ose fashikulli.

### D. Veprime korrigjuese të rekomanduara
3-5 veprime konkrete. Çdo veprim:
  - Përshkrim (5-10 fjalë)
  - Baza ligjore
  - Prioriteti

RREGULLA:
- NUK LEJOHET të shpikësh gabime
- NUK liston konstatime të analizës (ato janë në seksionin 8)
- Çdo gjetje ka ndikim praktik

""" + PROFESSIONAL_LANGUAGE_RULE + LAW_NUMBER_RULE + CASE_CONTEXT_RULE + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 6. PLANI I VEPRIMIT
    # ═══════════════════════════════════════════════════════════════════
    "action_steps": {
        "title": "PLANI I VEPRIMIT DHE REKOMANDIMET",
        "max_tokens": 4000,  # V4.27: 3200 → 4000
        "prompt": """Ti je "Strateg i Lartë Procedural" në zyrën këshilluese 
të Gjykatës Supreme.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Jep 3-5 veprime konkrete, të renditura me prioritet.

STRUKTURA (4 seksione):

### A. Vlerësimi i situatës (2-3 fjali)
### B. Hapat kritikë (24-48 orë)
### C. Hapat e rëndësishëm (1-7 ditë)
### D. Hapat afatgjatë (1-3 muaj)

🛑 PËR SECILIN VEPRIM:
- Emri i veprimit (5-10 fjalë)
- Baza ligjore
- Prioriteti

🛑 KONSTATIMET E ANALIZËS:
- Për ÇDO konstatim kritik ose të rëndësishëm:
  → SHTO një hap konkret në seksionin B ose C.
- Për konstatim kritik: prioritet i menjëhershëm (24-48h).
- Për konstatim të rëndësishëm: prioritet 1-7 ditë.

🛑 NUK LEJOHET:
- Veprime të përgjithshme si "Rishikoni dokumentet"
- Të listosh më shumë se 12 veprime
- Të përdorësh "HIGH"/"CRITICAL" në output

""" + PROFESSIONAL_LANGUAGE_RULE + FORENSIC_FINDINGS_RULE + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 7. ANALIZA E THELLUAR
    # ═══════════════════════════════════════════════════════════════════
    "analiza_e_thelluar": {
        "title": "ANALIZA E THELLUAR",
        "max_tokens": 4500,  # V4.27: 3800 → 4500
        "prompt": """Ti je "Analist i Thelluar i Akteve Gjyqësore".

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Identifiko ATE QË NJË AVOKAT I ZENE NUK E SHEH.

🛑 RREGULL ABSOLUT — PA PËRSËRITJE:
NËSE një gjetje është përmendur në:
  - Seksionin 1 → mos e përsërit
  - Seksionin 4 → mos e përsërit
  - Seksionin 5 → mos e përsërit

STRUKTURA (5 seksione):

### A. Modele dhe Shenja të Fshehta (2-3)
### B. Omissions dhe Boshllëqe Kritike (2-3)
### C. Standarde Provash (1-2)
### D. Arme të Mundshme të Kundërshtarit (1-2)
### E. **Ndikimi i Konstatimeve të Analizës**

PËR SEKSIONIN E:
- NUK ripërsërit konstatimet direkt.
- INTERPRETOJI: çfarë nënkuptojnë për strategjinë e rishqyrtimit në apel.
- Shembull:
  → "Konstatimi kritik për 5 dokumente me numër identik nuk është
     thjesht gabim administrativ — është model sistematik. Kjo tregon
     ose neglizhencë të vazhdueshme ose dashje për të maskuar veprime.
     Bazë për procedim penal ndaj personit përgjegjës për regjistrim."

🛑 RREGULLA FINALE:
- Vetëm shenja të reja — jo rifrazim i seksioneve 1-6
- 5-7 shenja TOTAL
- Çdo shenjë bazohet në FAKTE me referencë
- Nëse s'ka shenja të reja → shkruaj SAKTËSISHT:
  "Nuk u identifikuan shenja të reja përveç atyre të trajtuara në 
   seksionet 1-6. Dokumenti u analizua në thellësi."
- 🛑 NUK CITE KODE LIGJORE që nuk shfaqen në [NENE] / [LIGJE]
- 🛑 NUK përdor "flamuj" ose "HIGH"/"CRITICAL"

""" + PROFESSIONAL_LANGUAGE_RULE + FORENSIC_FINDINGS_RULE + CASE_CONTEXT_RULE + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 8. KONSTATIMET E ANALIZËS
    # ═══════════════════════════════════════════════════════════════════
    "konstatimet_e_analizes": {
        "title": "KONSTATIMET E ANALIZËS",
        "max_tokens": 3200,  # V4.27: 2400 → 3200
        "prompt": """Ti je "Analist i Lartë" që interpretons konstatimet e 
analizës së dokumentacionit.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Ky seksion është PËRMBLEDHJE E KONSTATIMEVE — jo analizë e re.
- Cito konstatimet.
- Shto ndikim praktik.
- NUK përsërit analizën e seksioneve 1-7.

STRUKTURA (3 seksione):

### A. Konstatime kritike
Për secilin konstatim me shkallë "Kritike" nga [KONSTATIMET_E_ANALIZËS]:

**[Kodi i konstatimit]**
- **Konstatimi:** [cito përmbajtjen e konstatimit]
- **Baza ligjore:** [cito]
- **Ndikimi praktik:** [pse ka rëndësi për klientin]
- **Veprimi i rekomanduar:** [cito ose përshtat]

Nëse nuk ka → "Nuk u identifikuan konstatime kritike."

### B. Konstatime të rëndësishme
Për secilin me shkallë "E rëndësishme": i njëjti format.

### C. Përmbledhje ekzekutive
1-3 fjali që përmbledhin konstatimet:
- Sa konstatime kritike ka
- Sa konstatime të rëndësishme ka
- Çfarë vlere ligjore kanë

SHEMBULL PËRMBLEDHJE:
"U identifikuan 2 konstatime kritike dhe 4 të rëndësishme që përbëjnë bazë të fortë për rishqyrtim në apel dhe procedim penal. Konstatimet kryesore: 5 dokumente me numër identik dhe mospërputhje midis dispozitivit dhe arsyetimit. Rekomandimi: apelim urgjent brenda afatit ligjor."

🛑 RREGULLA:
- Vetëm konstatimet e listuara në [KONSTATIMET_E_ANALIZËS] — nuk shpik.
- 🛑 NUK përdor "flamuj", "HIGH", "CRITICAL" — përdor "konstatime kritike" / "konstatime të rëndësishme".
- Cito kodin e konstatimit ashtu siç jepet.

""" + PROFESSIONAL_LANGUAGE_RULE + FORENSIC_FINDINGS_RULE + DEDUP_RULE,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION_CONTEXT_MAP
# ═══════════════════════════════════════════════════════════════════════════

SECTION_CONTEXT_MAP: Dict[str, List[str]] = {
    "document_summary": [
        "client", "meta", "parties", "dispositive", "medical", "tests",
        "convictions", "judge_court", "contradictions", "articles", "laws",
        "deadlines", "suspects",
        "case_context",
    ],
    "article_verification": ["articles", "laws"],
    "supreme_court_precedents": ["case_numbers", "meta", "precedents"],
    "drafting_quality": [
        "client", "meta", "parties", "dispositive", "articles", "laws",
        "contradictions", "reported_contradictions",
        "case_context",
        "forensic_findings",
    ],
    "errors_corrections": [
        "articles", "laws", "contradictions", "reported_contradictions",
        "dispositive", "medical",
        "case_context",
    ],
    "action_steps": [
        "client", "meta", "parties", "dates", "deadlines", "case_numbers",
        "dispositive", "judge_court",
        "forensic_findings",
    ],
    "analiza_e_thelluar": [
        "client", "meta", "parties", "dispositive", "articles", "laws",
        "case_numbers", "contradictions", "reported_contradictions",
        "medical", "tests", "convictions", "judge_court",
        "dates", "deadlines", "suspects",
        "case_context",
        "forensic_findings",
    ],
    "konstatimet_e_analizes": [
        "forensic_findings",
    ],
}

ALL_CONTEXT_BLOCKS = [
    "client", "meta", "articles", "laws", "case_numbers", "parties", "dates",
    "deadlines", "dispositive", "medical", "tests", "convictions",
    "judge_court", "contradictions", "reported_contradictions", "precedents",
    "suspects",
    "case_context",
    "forensic_findings",
]


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT BLOCK BUILDERS (të pandryshuara)
# ═══════════════════════════════════════════════════════════════════════════

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
        lines.append(f"🎯 Roli i deklaruar në rast: **{client_position.strip()}**")
        lines.append("")
        lines.append("⚠️ RREGULL I DETYRUAR PËR SEKSIONIN 2:")
        lines.append("")
        lines.append("  1. Roli i klientit në dokument — identifikoje nga teksti.")
        lines.append(f"  2. Roli i klientit në rast = '{client_position.strip()}'.")
        lines.append("  3. Nëse rolet ndryshojnë, shkruaj TË DYJA.")
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


def _block_case_context(case_profile: Optional[Dict[str, Any]]) -> List[str]:
    if not case_profile or not case_profile.get("has_context"):
        return []
    block = case_profile.get("block") or ""
    if not block.strip():
        return []
    return [block, ""]


def _block_forensic_findings(
    forensic_findings: Optional[Dict[str, Any]],
) -> List[str]:
    if not forensic_findings:
        return []
    block = forensic_findings.get("block") or ""
    if not block.strip():
        return []
    return [block, ""]


def _block_precedents(precedents: Optional[List[Dict[str, Any]]]) -> List[str]:
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("🏛️ PRECEDENTE RELEVANTE (nga baza e Gjykatës Supreme)")
    lines.append("=" * 70)
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
        lines.append("")

    lines.append("⚠️ RREGULL: Paraqit VETËM këta precedentë.")
    lines.append("")
    return lines


def _collect_allowed_values(citation_profile, fact_profile, verification_report):
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


def _block_antihallucination(citation_profile, fact_profile, verification_report) -> List[str]:
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


def _block_dispositive(fact_profile) -> List[str]:
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


def _block_medical(fact_profile) -> List[str]:
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


def _block_tests(fact_profile) -> List[str]:
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


def _block_convictions(fact_profile) -> List[str]:
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


def _block_judge_court(fact_profile) -> List[str]:
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


def _block_articles(verification_report) -> List[str]:
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


def _block_laws(verification_report) -> List[str]:
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


def _block_case_numbers(verification_report) -> List[str]:
    lines = []
    cases = verification_report.get("case_numbers", [])
    if not cases:
        return lines
    lines.append("=" * 70)
    lines.append(f"[LENDE] NUMRAT E LENDEVE ({len(cases)})")
    lines.append("=" * 70)
    lines.append("KUPTIMI I TAG-ËVE:")
    lines.append("  * [OWN]   — numri i lëndës së VETË dokumentit (NUK është precedent)")
    lines.append("  * [OK]    — precedent real, verifikuar në KB të Gjykatës Supreme")
    lines.append("  * [CITIM] — precedent i CITUAR NË DOKUMENT (referencë e vlefshme,")
    lines.append("              por JO verifikuar në bazë të pavarur)")
    lines.append("")
    for c in cases:
        if c["is_likely_own"]:
            tag = "[OWN]   I KETIJ DOKUMENTI"
        elif c["is_precedent"]:
            tag = "[OK]    PRECEDENT REAL (nga KB)"
        else:
            tag = "[CITIM] PRECEDENT I CITUAR NË DOKUMENT"
        lines.append(f"* {c['case_number']} — {tag}")
        if c.get("context"):
            lines.append(f"    Konteksti: {c['context'][:200]}")
    lines.append("")
    return lines


def _block_parties(fact_profile) -> List[str]:
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


def _block_suspects(fact_profile) -> List[str]:
    lines = []
    suspects = fact_profile.get("suspects", [])
    if not suspects:
        return lines
    lines.append("=" * 70)
    lines.append(f"[PERSONA] PERSONA TE DYSHUAR NE DOKUMENT ({len(suspects)})")
    lines.append("=" * 70)
    lines.append("⚠️ Lista e personave që dokumenti identifikon si të dyshuar.")
    lines.append("")
    current_group = ""
    for s in suspects:
        if s.get("group") and s["group"] != current_group:
            current_group = s["group"]
            lines.append(f"── {current_group} ──")
        lines.append(f"  {s['index']}. **{s['name']}** — {s['position_hint']}")
    lines.append("")
    return lines


def _block_dates(fact_profile) -> List[str]:
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


def _block_deadlines(fact_profile) -> List[str]:
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


def _block_contradictions(fact_profile) -> List[str]:
    lines = []
    contradictions = fact_profile.get("contradictions", [])
    if not contradictions:
        return lines
    lines.append("=" * 70)
    lines.append(f"[!] MOSPËRPUTHJE TË IDENTIFIKUARA AUTOMATIKISHT ({len(contradictions)})")
    lines.append("=" * 70)
    lines.append("[!] KETO JANE FAKTE KRITIKE - DUHET LISTUAR NE RAPORT!")
    lines.append("[!] KETO JANE MOSPËRPUTHJE TE DOKUMENTIT TONE (INTERNE).")
    lines.append("")
    for c in contradictions:
        values = " vs ".join(str(v) for v in c.get("values", []))
        zone_label = c.get("zone_label", "")
        zone_suffix = f" (zona: {zone_label})" if zone_label else ""
        lines.append(f"* Lloji: {c['type']}{zone_suffix}")
        lines.append(f"  Vlerat kontradiktore: **{values} {c.get('unit', '')}**")
        for ex in c.get("examples", [])[:4]:
            lines.append(f"  Shembull: {ex}")
        lines.append("")
    return lines


def _block_reported_contradictions(fact_profile) -> List[str]:
    lines = []
    reported = fact_profile.get("reported_contradictions", [])
    if not reported:
        return lines
    lines.append("=" * 70)
    lines.append(f"[i] MOSPËRPUTHJE TË RAPORTUARA NGA DOKUMENTI ({len(reported)})")
    lines.append("=" * 70)
    lines.append("ℹ️ KETO JANE MOSPËRPUTHJE QE DOKUMENTI RAPORTON PER DOKUMENTE TE TJERE.")
    lines.append("ℹ️ NUK JANE MOSPËRPUTHJE TE DOKUMENTIT TONE!")
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


# ═══════════════════════════════════════════════════════════════════════════
# MAIN API
# ═══════════════════════════════════════════════════════════════════════════

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
    case_profile: Optional[Dict[str, Any]] = None,
    forensic_findings: Optional[Dict[str, Any]] = None,
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

    if section_key in (
        "document_summary",
        "action_steps",
        "analiza_e_thelluar",
        "drafting_quality",
        "errors_corrections",
    ) and doc_text:
        lines.extend(_block_document_header(doc_text))

    lines.extend(_block_antihallucination(citation_profile, fact_profile, verification_report))

    if "forensic_findings" in blocks_needed:
        lines.extend(_block_forensic_findings(forensic_findings))

    if "case_context" in blocks_needed:
        lines.extend(_block_case_context(case_profile))

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

    if "suspects" in blocks_needed:
        lines.extend(_block_suspects(fact_profile))

    if "dates" in blocks_needed:
        lines.extend(_block_dates(fact_profile))

    if "deadlines" in blocks_needed:
        lines.extend(_block_deadlines(fact_profile))

    if "precedents" in blocks_needed:
        lines.extend(_block_precedents(precedents))

    return "\n".join(lines).strip()