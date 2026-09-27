# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V4.18
# V4.18: 3 FIX-E KONKRETE —
#        (A) document_summary.title "PERMBLEDHJE EKZEKUTIVE E AUDITIMIT" →
#            "DIAGNOZA E SITUATËS". Arsye: raporti është memorandum 
#            këshillues, jo audit teknik.
#        (B) drafting_quality: shtuar RREGULL I RE — kontradiktat mund të 
#            përmenden VETËM nga blloku [!]. Nëse blloku është bosh → nuk 
#            lejohet të referohen kontradikta. Fix për kontradiktën midis 
#            seksionit 4 (3/5 me kontradikta) dhe seksionit 5 
#            ("nuk u identifikuan kontradikta").
#        (C) action_steps: shtuar RREGULL FINAL — pa boilerplate 
#            "⛔ KUJDES"/"SHËNIM"/"VËREJTJE" në fund. LLM shpikte shënime 
#            që nuk ishin në prompt.
# V4.17: COUNSELOR ROLE REFRAME + DEDUP HARDENED + PRECEDENT SOURCE RULE.
# V4.16: FIX-E B.4, B.5, B.6, B.7.
# V4.15: DOCUMENT HEADER + CONTEXT MAP FIX.

from typing import Dict, Any, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════
# DEDUP_RULE
# ═══════════════════════════════════════════════════════════════════════════

DEDUP_RULE = """

🛑 RREGULL ANTI-PËRSËRITJE (DEDUP):

FILOZOFIA: Ky raport është një MEMORANDUM i vetëm — jo 7 dokumente të pavarur.
Kontradikta dhe përsëritje brenda raportit dëmtojnë besueshmërinë.

RREGULLA:
1. Çdo fakt, gjetje, ose rekomandim shfaqet VETËM NJË HERË — në seksionin 
   që i përket.
2. Referime: nëse duhet të përmendësh diçka që u trajtua në seksion tjetër, 
   shkruaj vetëm "shih seksionin X — [temë]" dhe vazhdo.
3. Kontradikta e brendshme e raportit = e papranueshme:
   ❌ SHEMBULL I GABUAR:
      - Seksioni 4 (Cilësia): "Nota 5/5 — Shkëlqyeshëm, nuk ka mangësi"
      - Seksioni 5 (Gabime): "U identifikuan 3 shkelje thelbësore procedurale"
      → KONTRA DIKTOR. Klienti nuk di çka të besojë.
   ✅ SHEMBULL I MIRË:
      - Seksioni 4: "Nota 3/5 — Dokumenti ka shkelje procedurale të 
         identifikuara në seksionin 5."
      - Seksioni 5: "[lista e shkeljeve]"
      → KONSISTENT. Nota reflekton gjetjet.

4. Fusha specifike që NUK duhen përsëritur:
   - Diagnoza mjekësore: përmendet në dokument_summary. Referoju në tjera 
     seksione vetëm me "shih diagnozën në seksionin 1".
   - Nenet e cituara: shfaqen në article_verification. Nuk relistohen 
     në drafting_quality ose errors_corrections.
   - Kontradikta e fakteve: shfaqet në errors_corrections me burimin e 
     saktë. Nuk përsëritet në analiza_e_thelluar.

5. Para se të nisësh një seksion, pyet veten:
   - "A kam shkruar ndonjë gjë që tashmë është mbuluar në seksione të 
     tjera?" Nëse PO → heq atë pjesë, referoju shkurtimisht.

6. Shenjat e reja (analiza_e_thelluar) duhet të jenë TË VËRTETA TË REJA — 
   jo rifrazim i gjetjeve të mëparshme.
"""


# ═══════════════════════════════════════════════════════════════════════════
# PRECEDENT_SOURCE_RULE
# ═══════════════════════════════════════════════════════════════════════════

PRECEDENT_SOURCE_RULE = """

🛑 RREGULL PRECEDENTËSH — BURIMI I DETYRUESHËM:

Kur citon një precedent (PML.Nr.X, Rev.Nr.X, P.nr.X, C.nr.X, CA.nr.X, 
PP.II.nr.X, KMLP.Nr.X), DEKLARO BURIMIN:

✅ FORMA E SAKTË:
   - "Sipas bazës së Gjykatës Supreme të Kosovës: Në vendimin PML.Nr.185/2025, 
     datë 16.04.2025, Gjykata Supreme konstaton se ..."
   - "Sipas vendimit PML.Nr.185/2025 (burimi: VENDIME TË PËRZGJEDHURA.pdf, 
     faqe 134): ..."

❌ FORMA E GABUAR (MOS e bëj):
   - "Gjykata Supreme thotë se ..." (pa specifikuar burimin — E GABUAR)
   - "Në vendimin PML.Nr.X, Gjykata Supreme sanksionon ..." (pretendon 
     verifikim zyrtar pa deklaruar se është citim)

🛑 KUFIZIME ABSOLUTE:
   1. NUK LEJOHET të shpikësh numra lëndësh që nuk shfaqen në kontekst.
   2. NUK LEJOHET të citosh precedent pa numër lënde (p.sh. "një vendim 
      i Gjykatës Supreme" pa numër — E GABUAR).
   3. NËSE nuk ka precedentë në kontekst → shkruaj SAKTËSISHT:
      "Nuk u identifikuan precedentë relevantë për këtë rast."
   4. NËSE dokumenti citon një precedent por ai NUK gjendet në bazën e 
      verifikuar → deklaro: "Sipas dokumentit [emri]: [citim]" — jo 
      "Sipas bazës së Gjykatës Supreme".
"""


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT_REVIEW_PROMPTS — V4.18
# ═══════════════════════════════════════════════════════════════════════════

DOCUMENT_REVIEW_PROMPTS = {

    # ═══════════════════════════════════════════════════════════════════
    # 1. DIAGNOZA E SITUATËS (V4.18: title ndryshuar)
    # ═══════════════════════════════════════════════════════════════════
    "document_summary": {
        "title": "DIAGNOZA E SITUATËS",
        "max_tokens": 1800,
        "prompt": """Ti je "KËSHILLTAR I GJYKATËS SUPREME TË KOSOVËS" me 20+ vjet 
përvojë në çështje civile, penale dhe familjare. Zyra jote është një 
ZYRË KËSHILLUESE — jo gjyqësore. Nuk vendos, por i shpjegon kolegëve 
avokatë se çka kanë përpara.

⚠️ MOS shkruaj titullin kryesor — shtohet automatikisht. Fillo DIREKT 
me seksionin 1.

MISIONI: Harto një DIAGNOZË të situatës — jo listë faktesh, jo raport 
teknik. Klienti (avokati) e lexon këtë të parin dhe duhet të dijë BRENDA 
60 SEKONDAVE: çka është dokumenti, kush kundër kujt, çka pretendohet, 
dhe ku mendohet se ka problem.

⚠️ RREGULL ABSOLUT PËR KLASIFIKIMIN:

0. **KLIENTI + ROLET:** Shih bllokun "[KLIENT]".
   - Blloku ka: emrin e klientit + rolin e deklaruar në rast + rolin në 
     këtë dokument.
   - Në seksionin 2, raporto TË DYJA rolet:
     * Ndryshojnë → "Klienti (emri) është [roli_case] në rastin kryesor, 
       por në këtë dokument shfaqet si [roli_dokument]."
     * Përputhen → raporto vetëm një rol.
     * Nuk shfaqet → "NUK PËRCAKTOHET në dokument".

1. **Lëshuesi** = AI QE SHKRUAN dokumentin. Lexo "[DOK] FILLIMI".

2. **Data** = data NE FILLIM ose NE FUND. Jo data e ngjarjeve.

3. **Roli i klientit** — si rregulli 0.

STRUKTURA E DETYRUAR (5 seksione, jo më shumë):

### 1. Diagnoza e situatës (2-3 fjali)
- Çka është dokumenti (lloji, lëshuesi, data, numri)
- Kush është në qendër — klienti dhe roli i tij
- Çka është në diskutim (objekti i çështjes)

### 2. Faktet themelore (3-4 fjali, vetëm ato kritike)
- Çka ka ndodhur (me datë)
- Kush është kundërshtari
- Çka pretendohet / çka u vendos

### 3. Çështje kritike që avokati DUHET të dijë (3-5 pika)
- Kontradikta të brendshme të dokumentit (nëse ka)
- Diagnoza mjekësore (me ICD)
- Dënime të mëparshme
- Teste mjekësore
- **Persona të dyshuar** — NËSE blloku [PERSONA] ekziston, listo numrin 
  total dhe grupet kryesore
- ÇDO pika duhet të ketë numër referimi (neni, data, faqja)

### 4. Diagnoza e shpejtë — ku është dyshimi
- Ku mendon se ka shkelje (pa detaje — ato shkojnë në seksionin 5)
- 1-2 fjali: "Dokumenti paraqet [X], por dyshimet kryesore lidhen me [Y]"

### 5. Fokus i rekomanduar (1-2 fjali)
- Ku duhet avokati të fokusojë vëmendjen para se të vazhdojë

RREGULLA:
- Perdor VETEM faktet ne blloqet "[KLIENT]", "[DOK]", "[PALE]", "[PERSONA]", 
  "[NENE]", "[AFAT]"
- NUK shpik data, leshues, role
- Fjalitë të shkurtra. Çdo fjali me vlerë.
- NUK përsërit atë që shfaqet në seksione të tjera

""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 2. VERIFIKIMI I NENEVE
    # ═══════════════════════════════════════════════════════════════════
    "article_verification": {
        "title": "VERIFIKIMI DHE AUDITIMI I NENEVE LIGJORE",
        "max_tokens": 3500,
        "prompt": """Ti je "Verifikues i Cilësisë Ligjore" në zyrën këshilluese 
të Gjykatës Supreme. Ti nuk liston — DIAGNOSTIKON.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Raporto VETËM problemet me nenet e cituara. Nenet që janë OK nuk 
kanë nevojë të listohen — ato janë vetëkuptohet të sakta.

SISTEMI KA BËRË VERIFIKIMIN — TI VETËM RAPORTO PROBLEMET.

STRUKTURA E DETYRUAR (3 seksione, jo më shumë):

### A. Nene problematike
Për ÇDO nen me problem, formato:

**[Neni X i Ligjit Y]**
- **Statusi:** NUK EKZISTON / KONTEKST I GABUAR / I PAPËRDORSHËM
- **Cituar në dokument:** "[citat i saktë]"
- **Problemi:** [shpjegim konkret]
- **Impakti:** [sa i rëndësishëm për rastin]

🛑 KATEGORITË E PROBLEMEVE:
1. **NUK EKZISTON** — neni nuk gjendet në ligjin e cituar
2. **KONTEKST I GABUAR** — neni ekziston, por në LIGJ TJETËR 
   (p.sh. dokumenti thotë "Neni 182 LPK", por gjendet vetëm në LFK)
3. **I PAPËRDORSHËM** — neni ekziston në ligjin e cituar, por FUSHA 
   NUK PËRPUTHET me dokumentin 
   (p.sh. "Neni 50 LPK" flet për kambial/çek, dokumenti flet për 
   urdhër mbrojtjeje → I PAPËRDORSHËM)
4. **I ZËVENDËSUAR** — neni është zëvendësuar me version më të ri

🛑 RREGULL I PAPËRDORSHËM (KRITIK):
Nëse neni ekziston në ligj POR përmbajtja e tij është për fushë tjetër 
nga dokumenti → raporto si I PAPËRDORSHËM. MOS thuaj "i saktë dhe i 
zbatueshëm" pa kontrolluar fushën.

SHEMBULL:
❌ E GABUAR: "Neni 50 i LPK-së — i saktë dhe i zbatueshëm në kontekstin 
   e dokumentit" (POR neni flet për kambial)
✅ E SAKTË: "Neni 50 i LPK-së — I PAPËRDORSHËM. Neni ekziston, por 
   rregullon kompetencën për kambial/çek, jo procedurat e urdhrit 
   mbrojtës. Referenca ka gjasa të jetë gabim."

### B. Nene që mund të mungojnë
Vetëm sugjerime me bazë të fortë. Format:
  [?] Neni X i Ligjit Y — [arsyeja pse duhet konsideruar]
      ⚠️ Verifikim manual i nevojshëm para shtimit.

### C. Përmbledhje statistikore
1-2 fjali: 
- Sa nene ishin problematike
- Sa u sugjeruan si të mundshëm që mungojnë
- Nëse të gjitha ishin OK → "Nuk u identifikuan probleme me nenet."

🛑 NUK LEJOHET:
- Të përsëritësh nenet që tashmë shfaqen në seksionin A (Python)
- Të shpikësh nene problematike që nuk gjenden në kontekst
- Të thuash "i saktë dhe i zbatueshëm" pa kontrolluar fushën

""" + DEDUP_RULE + PRECEDENT_SOURCE_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 3. PRECEDENTËT
    # ═══════════════════════════════════════════════════════════════════
    "supreme_court_precedents": {
        "title": "PRECEDENTET E GJYKATES SUPREME",
        "max_tokens": 3500,
        "prompt": """Ti je "Analist i Precedentëve" në zyrën këshilluese të 
Gjykatës Supreme të Kosovës.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

🛑 RREGULL ABSOLUT — BURIMI I PRECEDENTËVE:
- Blloku "🏛️ PRECEDENTE RELEVANTE" përmban precedentët e VËRTETË nga KB.
- Blloku "[LENDE]" përmban numrat e cituar NË DOKUMENTIN ORIGJINAL.
- Blloku "📚 PRECEDENTË TË CITUAR NË DOKUMENTET E FASHIKULLIT" (nëse 
  ekziston) tregon se dokumenti citon precedentë që NUK janë në bazë.

🛑 RREGULLI #1 — MOS SHPIK PRECEDENTË:
- KUR NUK KA precedentë relevantë → shkruaj SAKTËSISHT: 
  "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme 
   për këtë çështje."
- NUK LEJOHET të shpikësh numra lëndësh që nuk shfaqen në kontekst.
- NUK LEJOHET të përmendësh "[Rev.nr.X/YYYY]" pa i gjetur në kontekst.

SHEMBULL I GABUAR (nga prod):
❌ Raporti shkruan: "[Rev.nr. 43/2022] — Ka lidhje të drejtpërdrejtë..."
   POR Rev.nr.43/2022 nuk shfaqet askund në kontekstin e dhënë.
   → HALLEZINIM. NUK LEJOHET.

📌 KUPTIMI I TAG-ËVE NË BLLOKUN [LENDE]:
  * [OWN]   → numri i lëndës së VETË dokumentit. NUK është precedent.
  * [OK]    → precedent real, verifikuar në KB.
  * [CITIM] → precedent i CITUAR NË DOKUMENT (referencë e vlefshme, 
              por JO verifikuar në bazë të pavarur).

STRUKTURA (3 seksione):

### A. Precedentë të Verifikuar nga Baza
Vetëm ata që shfaqen në bllokun "🏛️ PRECEDENTE RELEVANTE". 
Nëse s'ka → shkruaj frazën standarde.

### B. Precedentë të Cituar në Dokument (jo të verifikuar)
Ata që shfaqen në [LENDE] me tag [CITIM], ose në bllokun "PRECEDENTË 
TË CITUAR". Për ta, FILLO me "Sipas dokumentit: ".

### C. Vlera Praktike për Këtë Rast
1-2 fjali: pse precedentët e listuar (ose mungesa e tyre) kanë rëndësi.

RREGULLA:
- SHKRUAJ VETËM NË SHQIP
- Çdo citim me numër të plotë lënde
- Pa deklarim burimi → NUK LEJOHET

""" + DEDUP_RULE + PRECEDENT_SOURCE_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 4. CILËSIA E HARTIMIT (V4.18: + RREGULL I RE për kontradiktat)
    # ═══════════════════════════════════════════════════════════════════
    "drafting_quality": {
        "title": "ANALIZA E CILESISE SE HARTIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Revizor i Cilësisë së Akteve Gjyqësore" në zyrën 
këshilluese të Gjykatës Supreme.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Vlerëso cilësinë e përgjithshme të dokumentit. Nota NUK është 
nominale — reflekton gjetjet.

🛑 RREGULL ABSOLUT PËR NOTËN (KRITIKE):

Nota përfundimtare NUK MUND të jetë 5/5 nëse:
- Seksioni 5 (Gabime) ka identifikuar shkelje thelbësore procedurale
- Seksioni 5 ka listuar kontradikta të brendshme
- Seksioni 5 ka listuar vulnerabilitete strategjike

KAP I NOTËS sipas gjetjeve:
- **5/5 (Shkëlqyeshëm)** → vetëm nëse nuk u identifikuan gabime
- **4/5 (Shumë mirë)** → gabime të vogla procedurale pa impakt
- **3/5 (I mirë)** → gabime thelbësore procedurale ose kontradikta 
  të brendshme
- **2/5 (I dobët)** → shkelje substanciale + procedurale
- **1/5 (Shumë i dobët)** → shkelje të rënda ligjore

🛑 KONTRADIKTA E BRENDSHME (KRITIKE):
Nëse në këtë seksion vlerëson 5/5 dhe në seksionin 5 (Gabime) ka shkelje 
të identifikuara → KONTRA DIKTOR.
Prandaj:
- PARA se të shkruash notën, kontrollo bllokun "[!] KONTRADIKTA TE 
  IDENTIFIKUARA AUTOMATIKISHT" dhe "[GABIME]".
- Nëse ka gabime → nota maksimumi 3/5.
- Shpjego: "Nota [X]/5 reflekton [N] gabime të identifikuara në 
  seksionin 5."

🛑 RREGULL I RE (V4.18) — KONTRADIKTA NUK MUND TË SHPIKET:
- Kontradiktat mund të përmenden VETËM nga blloku 
  "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".
- NËSE ky bllok është BOSH ose NUK EKZISTON në kontekst → 
  NUK LEJOHET të përmendësh kontradikta në seksionin D.
- NËSE vendos notë < 5/5 pa kontradikta → referoju VETËM arsyeve të 
  tjera (strukturë, terminologji, arsyetim, procedurë).
- KONTRADIKTA midis këtij seksioni dhe seksionit 5 (errors_corrections) 
  është E PAPRANUESHME. Nëse seksioni 5 thotë "nuk u identifikuan 
  kontradikta", atëherë edhe ky seksion NUK LEJOHET të përmendë 
  kontradikta.

STRUKTURA:

### A. Struktura formale
Kujdes: Nëse lloji është KALLËZIM PENAL, PADI, ANKESË, KËRKESËPADI, 
APEL ose AKT PROCEDURAL — NUK kërkohet "Përmbledhje Ekzekutive" ose 
"Konkluzione". Struktura me seksione I-VIII konsiderohet E PLOTË. 
NUK penalizo.

### B. Terminologjia juridike
Përdorim i saktë i termave.

### C. Arsyetimi juridik
A është arsyetimi koherent? A mbështetet në fakte?

### D. Konsistenca e brendshme
VETËM bllokun "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".
Për çdo kontradiktë, cito BURIMIN specifik:
  - "X në [dispozitiv / arsyetim / propozim] kundrejt Y në [zonë tjetër]"
  - VENDNDODHJA (dispozitiv / arsyetim) është thelbësore.
NËSE blloku është bosh → shkruaj "Nuk u identifikuan kontradikta të 
brendshme nga sistemi." NUK shpik kontradikta.

### E. Nota përfundimtare (1-5)
**Nota: X/5** — [arsyeja në 1 fjali]
- Nëse ka gabime në seksionin 5 → referoju atyre.
- Nuk lejohet 5/5 nëse ka shkelje.

RREGULLA:
- NUK LEJOHET të shpikësh mangësi që nuk shfaqen në kontekst.
- Nota duhet të REFLEKTOJË gjetjet, jo të jetë nominale.
- NUK LEJOHET të përmendësh kontradikta nëse blloku [!] është bosh.

""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 5. GABIME DHE KORRIGJIME
    # ═══════════════════════════════════════════════════════════════════
    "errors_corrections": {
        "title": "GABIME, KONTRADIKTA DHE KORRIGJIME",
        "max_tokens": 3200,
        "prompt": """Ti je "Zbulues i Shkeljeve Ligjore" në zyrën këshilluese 
të Gjykatës Supreme.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Identifiko shkeljet e VËRTETA me impakt praktik. NUK liston 
gjithçka — fokus në atë që ka rëndësi për klientin.

STRUKTURA (5 seksione):

### A. Gabime në nene
VETËM nëse ka gabime reale. Format:
  [X] Neni X i [Ligjit] — **Statusi:** NUK EKZISTON / I PAPËRDORSHËM 
       / KONTEKST I GABUAR
      - Problem: [shpjegim]
      - Impakti: [sa i rëndësishëm]
      - Korrigjim: [veprim konkret]

Nëse nuk ka → "Nuk u identifikuan gabime në nene."

### B. Kontradikta të brendshme
VETËM nga blloku "[!] KONTRADIKTA TE IDENTIFIKUARA AUTOMATIKISHT".
Për çdo kontradiktë:
  - Cito TË DYJA vlerat me burimin specifik:
    "X (dispozitiv, faqe Y) vs. Z (arsyetim, faqe W)"
  - Shpjego impaktin praktik

Nëse nuk ka → "Nuk u identifikuan kontradikta të brendshme."

### C. Gabime procedurale
Vetëm gabime reale procedurale (jo vëzhgime të përgjithshme).
Format: [shkelja] — [baza ligjore] — [impakti praktik]

### D. Korrigjime të rekomanduara
3-5 veprime konkrete. Çdo veprim:
  - Përshkrim (5-10 fjalë)
  - Baza ligjore
  - Prioriteti (i menjëhershëm / afatgjatë)

### E. **Vulnerabilitete Strategjike**
Ku mund ta godasë pala kundërshtare?
- Cilat pika të arsyetimit janë të dobëta?
- Çfarë do të bënte një avokat i kundërshtarit?
- Cilat fakte mund të sfidohen?

Listo 2-3 vulnerabilitete ME BAZË NË FAKTE (jo hamendje).

RREGULLA:
- NUK LEJOHET të shpikësh gabime
- NUK LEJOHET të përsëritësh nga seksione të tjera
- Çdo gjetje duhet të ketë impakt praktik
- Nëse nuk ka gabime reale → thuaj atë qartë

""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 6. PLANI I VEPRIMIT (V4.18: + RREGULL FINAL pa boilerplate)
    # ═══════════════════════════════════════════════════════════════════
    "action_steps": {
        "title": "PLANI I VEPRIMIT DHE REKOMANDIMET",
        "max_tokens": 3000,
        "prompt": """Ti je "Strateg i Lartë Procedural" në zyrën këshilluese 
të Gjykatës Supreme. Ti nuk bën listë detyrash — jep PLAN me prioritet.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Jep 3-5 veprime konkrete, të renditura me prioritet, që klienti 
duhet të ndërmarrë. Fokus në ATË QË KA RËNDËSI, jo gjithçka.

STRUKTURA (4 seksione — jo më shumë):

### A. Vlerësimi i Situatës (2-3 fjali)
- Ku jemi në procedurë
- Sa urgjente është situata
- Kufizimet kryesore (afate, prova)

### B. HAPAT KRITIKË (para çdo gjëje tjetër)
Vetëm veprimet që DUHET të ndodhin brenda 24-48 orësh:
- Bullet-point me përshkrim (5-8 fjalë)
- Me baza ligjore
- Me afat konkret

### C. HAPAT E RËNDËSISHËM (1-7 ditë)
3-4 veprime të planifikuara për javën e parë.

### D. HAPAT AFATGJATË (1-3 muaj)
3-4 veprime për strategjinë afatgjatë.

🛑 RREGULLI PËR SECILIN VEPRIM:
- Emri i veprimit (5-10 fjalë)
- Baza ligjore (1 fjali, me referencë)
- Prioriteti (i menjëhershëm / 1-7 ditë / afatgjatë)

🛑 NUK LEJOHET:
- Veprime të përgjithshme si "Rishikoni dokumentet" — TË GJITHA veprimet 
  duhet të jenë KONKRETE
- Të listosh më shumë se 12 veprime totalisht — cilësia > sasia
- Rekomandime pa bazë ligjore

RREGULLA PËR AFATET:
- Nëse dokumenti përmend afat → cituoje ME BURIMIN.
- Nëse NUK përmend → "Afati ligjor: kontrollo manualisht."

🛑 RREGULL FINAL (V4.18) — PA BOILERPLATE:
- NUK LEJOHET të shtosh seksione "⛔ KUJDES", "SHËNIM", "VËREJTJE", 
  "MENDIM", "REKOMANDIM SHTESË" në fund të këtij seksioni.
- Përfundo NATYRSHËM me seksionin D.
- Çdo shënim i tillë është boilerplate dhe minon tonin këshillues.

""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════
    # 7. ANALIZA E THELLUAR
    # ═══════════════════════════════════════════════════════════════════
    "analiza_e_thelluar": {
        "title": "ANALIZA E THELLUAR",
        "max_tokens": 3500,
        "prompt": """Ti je "Analist i Thelluar i Akteve Gjyqësore" në zyrën 
këshilluese të Gjykatës Supreme.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Identifiko ATE QË NJË AVOKAT I ZENE NUK E SHEH — shenja, 
modele, boshllëqe që NUK SHFAQEN në seksionet 1-6.

🛑 RREGULL ABSOLUT — PA PËRSËRITJE:
Ky seksion është DALLIMI midis një asistenti dhe një kolegu me përvojë.
NËSE një gjetje është përmendur në:
  - Seksionin 1 (document_summary) → mos e përsërit
  - Seksionin 4 (drafting_quality) → mos e përsërit
  - Seksionin 5 (errors_corrections) → mos e përsërit

SHEMBUJ KONKRETË TË PËRSËRITJES (NUK LEJOHET):
❌ "Perseritje e diagnozës psikiatrike" — kjo u tha në dokument_summary
❌ "Mungesa e konsentimit" — kjo u tha në errors_corrections (nëse është 
   gabim procedural)
❌ "Kontradikta në diagnozën psikiatrike" — kjo u tha në errors_corrections
❌ "Nenet 194, 208, 209 LPK u përdorën për të justifikuar vendimin" — 
   kjo u tha në article_verification

SHEMBUJ TË MIRË (gjëra të reja):
✅ "Gjykata e Apelit citon nenin 182 LPK për shkelje thelbësore, por 
   dokumenti nuk e specifikon SE CILA nga shkeljet (b, g, j, k, m) 
   u konstatua — duke e lënë të paqartë bazën për apelim."
✅ "Përdorimi i shprehjes 'kjo nuk do të jetë pengesë që me rastin e 
   vendosjes në procedura tjera të rregullta' — fragment 2-fjalësh që 
   hap rrugën për padi të re, pa qartësi procedurale."
✅ "Kalimi nga 'caktim i përkohshëm' (neni 34.3) në 'urdhër mbrojtje' 
   (neni 29-31) — dy institute të ndryshme me kohëzgjatje të ndryshme."

STRUKTURA (4 seksione):

### A. Modele dhe Shenja të Fshehta (2-3)
Shenja që nuk u trajtuan në seksione të tjera.

### B. Omissions dhe Boshllëqe Kritike (2-3)
- Nene që DUHET të ishin cituar por mungon
- Procedura që nuk përmenden (konsentim, njoftim, prani)
- Afate që nuk specifikohen

### C. Standarde Provash (1-2)
A është zbatuar standardi i duhur i provës?

### D. Arme të Mundshme të Kundërshtarit (1-2)
Shenja specifike që mund të përdoren në apelim.

🛑 RREGULLA FINALE:
- Vetëm shenja të reja — jo rifrazim i seksioneve 1-6
- 5-7 shenja TOTAL (jo më shumë)
- Çdo shenjë bazohet në FAKTE me referencë
- Nëse s'ka shenja të reja → shkruaj SAKTËSISHT:
  "Nuk u identifikuan shenja të reja përveç atyre të trajtuara në 
   seksionet 1-6. Dokumenti u analizua në thellësi."

RREGULLA:
- Fokus ne shenja qe NUK shfaqen ne seksionet e tjera
- Cilësia > Sasia
- Shmang hamendjen — bazo çdo shenje ne FAKTE

""" + DEDUP_RULE,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION_CONTEXT_MAP
# ═══════════════════════════════════════════════════════════════════════════

SECTION_CONTEXT_MAP: Dict[str, List[str]] = {
    "document_summary": [
        "client", "meta", "parties", "dispositive", "medical", "tests",
        "convictions", "judge_court", "contradictions", "articles", "laws",
        "deadlines",
        "suspects",
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
    "analiza_e_thelluar": [
        "client", "meta", "parties", "dispositive", "articles", "laws",
        "case_numbers", "contradictions", "reported_contradictions",
        "medical", "tests", "convictions", "judge_court",
        "dates", "deadlines",
        "suspects",
    ],
}

ALL_CONTEXT_BLOCKS = [
    "client", "meta", "articles", "laws", "case_numbers", "parties", "dates",
    "deadlines", "dispositive", "medical", "tests", "convictions",
    "judge_court", "contradictions", "reported_contradictions", "precedents",
    "suspects",
]


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT BLOCK BUILDERS — të pandryshuara nga V4.17
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


def _block_suspects(fact_profile: Dict[str, Any]) -> List[str]:
    lines = []
    suspects = fact_profile.get("suspects", [])
    if not suspects:
        return lines
    lines.append("=" * 70)
    lines.append(f"[PERSONA] PERSONA TE DYSHUAR NE DOKUMENT ({len(suspects)})")
    lines.append("=" * 70)
    lines.append("⚠️ Lista e personave që dokumenti identifikon si të dyshuar.")
    lines.append("⚠️ Përfshin emrin + pozicionin/rolin e tyre në dokument.")
    lines.append("")
    current_group = ""
    for s in suspects:
        if s.get("group") and s["group"] != current_group:
            current_group = s["group"]
            lines.append(f"── {current_group} ──")
        lines.append(f"  {s['index']}. **{s['name']}** — {s['position_hint']}")
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
    lines.append("[!] Per secilen kontradikte, cito BURIMIN specifik:")
    lines.append("    - Kush është në DISPOZITIV? Kush është në ARSYETIM?")
    lines.append("    - Kush është në PROPOZIM/KËRKESË? Kush është në Fakte?")
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

    if section_key in (
        "document_summary",
        "action_steps",
        "analiza_e_thelluar",
        "drafting_quality",
        "errors_corrections",
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

    if "suspects" in blocks_needed:
        lines.extend(_block_suspects(fact_profile))

    if "dates" in blocks_needed:
        lines.extend(_block_dates(fact_profile))

    if "deadlines" in blocks_needed:
        lines.extend(_block_deadlines(fact_profile))

    if "precedents" in blocks_needed:
        lines.extend(_block_precedents(precedents))

    return "\n".join(lines).strip()