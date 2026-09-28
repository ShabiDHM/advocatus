# FILE: backend/app/services/document_review/verify/prompt_rules.py
# PHOENIX PROTOCOL - VERIFY PROMPT RULES V1.8
# V1.8: PROFESSIONAL LANGUAGE — Zëvendësuar "flamuj" → "konstatime",
#       "impashti" → "ndikimi", "sistemi" → "analiza". Shtuar
#       PROFESSIONAL_LANGUAGE_RULE që ndalon terminologjinë e sistemit
#       në output. Raporti lexohet si memorandum ligjor, jo si log teknik.
# V1.7: LAW_NUMBER_RULE.
# V1.6: FORENSIC_FINDINGS_RULE — labels SHQIP.

DEDUP_RULE = """

🛑 RREGULL ANTI-PËRSËRITJE:
- ÇDO gjetje, fakt, ose rekomandim shfaqet VETËM NJË HERË në të gjithë raportin.
- NUK përsërit pikat e seksioneve të tjera (1-8).
- Çdo seksion kontribuon KËNDVËSHTRIM TË RI, jo përmbledhje të mëparshme.
- Nëse diçka është trajtuar në një seksion tjetër, referoju shkurtimisht me "shih seksionin X" dhe mos e përsërit.
"""


PRECEDENT_SOURCE_RULE = """

🛑 RREGULL I DETYRUESHËM — BURIMI I PRECEDENTËVE (Rule 19):
- ÇDO precedent që përmendet në këtë seksion DUHET të ketë BURIMIN e deklaruar.
- NËSE precedenti vjen nga blloku [PRECEDENTE] (baza e Gjykatës Supreme):
  → shkruaj "Sipas bazës së Gjykatës Supreme".
- NËSE precedenti vjen nga vetë drafti (i cituar nga autori):
  → shkruaj "Sipas dokumentit".
- NUK LEJOHET citimi i një precedenti pa burim të deklaruar.
"""


CROSS_SECTION_CONSISTENCY_RULE = """

🛑 RREGULL KONSISTENCE NDËR-SEKSIONALE:
- QËNDRIMI NDËR-SEKSIONAL: Nuk kontradikton gjetjet e seksioneve 1-4.
- NËSE Seksioni 2 deklaroi "Nuk u identifikuan nene problematike":
  → NUK LEJOHET të pretendosh se një nen i cituar në draft është i GABUAR.
- NËSE do të kontradiktosh një seksion të mëparshëm — REFEROJU atij eksplicit:
  "shih Seksionin 2B" ose "shih Seksionin 4A".
"""


PRECEDENT_RECOMMENDATION_RULE = """

🛑 RREGULL PRECEDENTËSH NË REKOMANDIME:
- Shiko bllokun [PRECEDENTE] më lart.
- NËSE [PRECEDENTE] ka precedentë DHE drafti NUK i citon:
  → SHTO një rekomandim konkret: "Cito precedentin [numri] në [seksioni]".
- NËSE drafti NUK ka precedentë fare DHE [PRECEDENTE] ka të paktën një:
  → KY ËSHTË MUNGESË E RËNDËSISHME.
- NUK LEJOHET të shpikësh precedentë që nuk shfaqen në [PRECEDENTE].
"""


CASE_CONTEXT_RULE = """

🛑 RREGULL I DETYRUESHËM — KONTEKSTI I FASHIKULLIT (anti-hallucination):
- Blloku [FASHIKULLI] liston vlera që ekzistojnë në dokumentet e rastit.
- Përdor VETËM këto vlera kur i referohesh fashikullit.
- NËSE do të përmendësh një element që nuk është në [FASHIKULLI] as në draft:
  → SHKRUAJ: "Nuk u identifikua në fashikull." dhe VAZHDO.
- PËR KONTRADIKTA draft-vs-fashikull:
  * RAPORTOJE si mospërputhje me burimin "drafti kundër fashikullit".
- NËSE [FASHIKULLI] mungon → NUK përmend fashikullin.
"""


ABBREV_REPLACEMENT_RULE = """

🛑 RREGULL I DETYRUESHËM — ZËVENDËSIMI I AKRONIMEVE:

1. **VERIFIKO [NENE] PARA SË TË SUGJEROSH:** Nëse akronimi shfaqet në [NENE] → i vlefshëm. MOS e zëvendëso.

2. **AKRONIME STANDARDE (NUK zëvendësohen):**
   - KPPRK = Kodi i Procedurës Penale
   - KPRK = Kodi Penal
   - LPK, LMDHF — standard.

3. **KUR SUGJERON ZËVENDËSIM:** Cito të dyja akronimet + arsyen.

4. **VETËM KUR KA GABIM TË VËRTETË.**
"""


LAW_NUMBER_RULE = """

🛑 RREGULL ABSOLUT PËR NUMRIN E LIGJIT (anti-substitution):

Kur citon një nen, CITO SAKTËSISHT numrin e ligjit që shfaqet në 
bllokun [NENE] në rreshtin "Ligji i cituar: X".

RREGULLAT:

1. **NUMRI I LIGJIT ËSHTË I FIKSUAR:**
   - NUK LEJOHET të zëvendësosh numrin e ligjit me një kod TJETËR 
     (p.sh. 06/L-082, 06/L-084, 08/L-185) edhe nëse kodi tjetër është 
     ligj i vlefshëm në Kosovë.
   - NUK LEJOHET të caktosh numër ligji që NUK shfaqet në [NENE] 
     ose [LIGJE].

2. **NËSE NUMRI NUK SHFAQET:**
   - NËSE [NENE] thotë "Ligji i cituar: -" ose bosh → shkruaj VETËM emrin 
     e ligjit pa numër, ose "NUK U VERIFIKUA".

3. **NUK BASHKO LIGJE:**
   - Çdo nen i atribuohet VETËM një ligji (ai i [NENE]).

SHEMBUJ:
✅ "Neni 6 par. 2 i Ligjit për Mbrojtje nga Dhuna në Familje (03/L-182)"
❌ "Neni 6 par. 2 i Ligjit Nr. 06/L-082"
"""


# ═══════════════════════════════════════════════════════════════════════════
# V1.8: PROFESSIONAL_LANGUAGE_RULE — termini i sistemit nuk shfaqet në output
# ═══════════════════════════════════════════════════════════════════════════

PROFESSIONAL_LANGUAGE_RULE = """

🛑 RREGULL I DETYRUESHËM — GJUHA PROFESIONALE E RAPORTIT:

Ky raport është MEMORANDUM LIGJOR — lexohet nga avokatë, klientë, 
dhe palë të treta. Duhet të ruajë tonin e një dokumenti zyrtar 
këshillues. NUK është log i sistemit.

TERMA TË NDALUARA (mos i përdor kurrë në output):

| ❌ Joprofesionale | ✅ Profesionale |
|-------------------|----------------|
| "flamuj", "flamuj kritikë" | "konstatime", "konstatime kritike" |
| "flamuj forensikë" | "konstatimet e analizës" |
| "impashti i flamujve" | "ndikimi i konstatimeve" |
| "sistemi identifikoi" | "analiza nxorri në pah" |
| "sistemi zbuloi" | "u konstatua" / "rezulton" |
| "avokati duhet të" | "rekomandohet" / "këshillohet" |
| "duhet të konsiderohet" | "këshillohet shqyrtimi" |
| "bazë për kallëzim penal" | "bazë për procedim penal" |
| "bazë për apelim" | "bazë për rishqyrtim në apel" |
| "target", "flag", "scan", "trigger" | përkthe në shqip |

KONVENTA E GJUHËS:
- Fol me zë pasiv ose vetë të tretë: "u konstatua", "rezulton", 
  "konstatimet tregojnë".
- NUK përdor "unë" / "sistemi" / "ne" si subjekt.
- Fjalitë të plota, jo shkurtime teknike.
- Termat ligjorë në shqip: "marrëveshje", "konstatim", "shkelje", 
  "mosmarrëveshje", "rishqyrtim".

SHEMBUJ:

❌ JOPROFESIONALE:
   "Sistemi identifikoi 2 flamuj kritikë dhe 4 flamuj të rëndësishëm. 
    Avokati duhet të fokusohet në..."
   "Impashti i flamujve forensikë: flamuri CRITICAL për numra..."

✅ PROFESIONALE:
   "Analiza nxorri në pah 2 konstatime kritike dhe 4 konstatime të 
    rëndësishme. Rekomandohet fokusimi në..."
   "Ndikimi i konstatimeve: konstatimi kritik për numrat identikë..."

FJALORI I PËRKTHIMIT:
- flamuj → konstatime
- flamuj kritikë → konstatime kritike
- flamuj të rëndësishëm → konstatime të rëndësishme
- impashti → ndikimi
- forensik → i analizës (ose hiqe fare)
- sistemi → analiza / (ose hiqe)
- target → objektiv
- scan → skanim / analizë
"""


# ═══════════════════════════════════════════════════════════════════════════
# FORENSIC_FINDINGS_RULE (V1.8: terminologji profesionale)
# ═══════════════════════════════════════════════════════════════════════════

FORENSIC_FINDINGS_RULE = """

🛑 RREGULL I DETYRUESHËM — KONSTATIMET E ANALIZËS ([KONSTATIMET_E_ANALIZËS]):

Sistemi ka nxjerrë konstatime automatike nga analiza e fashikullit.
Këto janë gjetje DETERMINISTIKE — jo hamendje.

FILOZOFIA:
- Konstatimet janë FAKTE. Pranoji si të tillë.
- Jep KONTEKSTIN, ARSYETIMIN LIGJOR dhe VEPRIMIN.
- 🛑 NUK përdor termin "flamuj" — përdor "konstatime".

RREGULLA ABSOLUTE:

1. **CITOJE SAKTËSISHT KONSTATIMIN:**
   - Cito përmbajtjen e konstatimit (ose parafrazo besnikërisht).
   - NUK shto detaje që nuk shfaqen në të.

2. **KLASIFIKIMI SIPAS SHKALLËS (në SHQIP):**
   - **Kritike** → bazë për procedim penal ose rishqyrtim urgjent.
   - **E rëndësishme** → bazë për rishqyrtim ose kërkesë procedurale.
   - **Mesme** → dobësi procedurale.
   - **E ulët** → vërejtje kozmetike.

   ⚠️ NUK LEJOHET të shkruash "HIGH", "CRITICAL", "MEDIUM", "LOW".

3. **NUK SHPIK KONSTATIME TË REJA:**
   - NËSE [KONSTATIMET_E_ANALIZËS] nuk përmend një mospërputhje,
     NUK LEJOHET të pretendosh se ekziston.

4. **CILA SEKSIONE I TRAJTON:**
   - **drafting_quality** → përmend konstatimet si bazë për notën.
   - **action_steps** → për çdo konstatim kritik ose të rëndësishëm,
     propozo veprim konkret.
   - **analiza_e_thelluar** → përdor konstatimet si pika të reja.
   - **konstatimet_e_analizës** (seksion i veçantë) → përmbledhje e plotë.

5. **MOS PËRSËRIT KONSTATIMET NË ÇDO SEKSION:**
   - Referoju me "shih seksionin X".

SHEMBULL I SAKTË:
[KONSTATIMET_E_ANALIZËS] përmban:
  [E rëndësishme] Dënim i skaduar: Lënda 'P.nr.869/2018' është 6.3 vjet e vjetër.

Në analiza_e_thelluar:
  ✓ "Përdorimi i dënimit të skaduar tregon ose mosnjohje ligjore ose dashje
     për të ndikuar vendimin — të dyja baza për rishqyrtim në apel."

NË asnjë seksion KURRË:
  ✗ "flamuj HIGH" ← gjuhë e huaj
  ✗ "Sistemi identifikoi" ← subjekt teknik
"""


__all__ = [
    "DEDUP_RULE",
    "PRECEDENT_SOURCE_RULE",
    "CROSS_SECTION_CONSISTENCY_RULE",
    "PRECEDENT_RECOMMENDATION_RULE",
    "CASE_CONTEXT_RULE",
    "ABBREV_REPLACEMENT_RULE",
    "LAW_NUMBER_RULE",
    "PROFESSIONAL_LANGUAGE_RULE",
    "FORENSIC_FINDINGS_RULE",
]