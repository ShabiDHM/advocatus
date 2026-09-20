# FILE: backend/app/services/synthesis/prompts/section_prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V1.4
# V1.4: Fix typo — "RREZIQET" → "RREZIQET" (LLM e kopjon verbatim).
# V1.3: Fix-e pas raportit të Shtator 2026:
#       - "Next Step" → "Hapi i Ardhshëm" (shqip)
#       - "Afati: kontrollo manualisht" → formulim profesional
#       - legal_framework: Jurisprudenca kushtëzohet nga ekzistenca në digest
#       - Të gjitha: udhëzim për të mos shkruar titullin kryesor të seksionit
# V1.2: Shtuar FEW-SHOT EXAMPLES në executive_summary + parties_and_roles.
# V1.1: Struktura dual-matter.

from .strict_rules import STRICT_RULES


SECTION_PROMPTS = {
    "executive_summary": {
        "title": "PASQYRA EKZEKUTIVE",
        "max_tokens": 1500,
        "prompt": """Ti je jurist i lartë në Kosovë. Bazuar në digest-in,
harto përmbajtjen e PASQYRËS EKZEKUTIVE.

⚠️ MOS shkruaj titullin kryesor ("PASQYRA EKZEKUTIVE") — shtohet
   automatikisht nga sistemi. Fillo DIREKT me "## 1. Lloji i lëndës"
   ose me përmbajtjen.

═══════════════════════════════════════════════════════════════════════════
🛑 RREGULL ABSOLUT (KRITIKE — LEXO PARA ÇDO GJËJE TJETËR)
═══════════════════════════════════════════════════════════════════════════

Për rolet e palëve, PËRDOR VETËM bllokun "👥 PALËT NDËRGYQËSE ME ROLE".
NUK LEJOHET TË:
  ❌ Përmbysësh rolet midis personave
  ❌ Shpikësh role që nuk shfaqen në atë bllok
  ❌ Zëvendësosh rolin e një personi me rolin e një personi tjetër

NËSE blloku thotë:
  👥 PALËT NDËRGYQËSE ME ROLE:
    • Sanije (Azem) Bala — Roli: Pala e mbrojtur
    • Shaban Bala — Roli: Pala përgjegjëse / I pandehuri

ATËHERË output-i DUHET të thotë:
  ✅ Pala e mbrojtur: Sanije (Azem) Bala
  ✅ Pala përgjegjëse: Shaban Bala
  ✅ I pandehuri: Shaban Bala

❌ KURRË MOS SHKRUAJ:
  ❌ "Pala e mbrojtur: Shaban Bala" (SHABAN ËSHTË PALA PËRGJEGJËSE)
  ❌ "Pala përgjegjëse: Sanije Bala" (SANIJE ËSHTË PALA E MBROJTUR)
  ❌ "E dëmtuara: Shaban Bala" (SHABAN ËSHTË I PANDEHURI, JO I DËMTUARI)

NUK LEJOHET të konsultosh fusha të tjera për role. VETËM blloku i palëve.

═══════════════════════════════════════════════════════════════════════════

⚠️ KONTROLLO SEKSIONIN "🎯 LLOJI I LËNDËS":

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RASTI A: Lloji përmban "→" (LËNDË E DYFISHTA)

Struktura e detyruar:

## 1. Lloji i lëndës
Deklaro: "Kjo është lëndë e dyfishtë: [faza 1] → [faza 2]".

## 2. FAZA E PARË — [emri i fazës]
- Palët me rolet e SAKTA për këtë fazë (p.sh. "pala e mbrojtur",
  "pala përgjegjëse")
- Objekti i kontestit
- Akti/Vendimi kryesor
- Burimi: emri i dokumentit

## 3. FAZA E DYTË — [emri i fazës]
- Palët me rolet e SAKTA (MUND TË JENË TË NDRYSHME)
- Objekti
- Statusi aktual
- Burimi: emri i dokumentit

## 4. Çështje kritike për avokatin
- Lista me pika

## 5. Hapi i Ardhshëm
- 1-2 rreshta

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RASTI B: Lloji pa "→" (LËNDË E VETME)

Struktura standarde (5-7 paragrafë):
- Lloji i lëndës
- Palët kryesore me rolet e sakta
- Objekti i kontestit
- Pretendimet kryesore
- Gjendja aktuale
- Jurisprudenca relevante
- Rezultati i mundshëm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ RREGULLA:
- MOS bashko fazat në një narrative të vetme.
- Anëtarët e familjes (fëmijë, bashkëshortë) NUK janë "palë kundërshtare".
- Cito afatin VETËM me burim.

""" + STRICT_RULES,
    },

    "chronology": {
        "title": "KRONOLOGJIA E NGJARJEVE",
        "max_tokens": 2200,
        "prompt": """Ti je jurist kronolog. Bazuar në DATAT dhe dokumentet,
harto KRONOLOGJINË E DETAJUAR.

⚠️ MOS shkruaj titullin kryesor ("KRONOLOGJIA E NGJARJEVE") — shtohet
   automatikisht nga sistemi.

⚠️ NËSE LLOJI KA "→" (lëndë e dyfishtë):

Struktura:
### FAZA E PARË — [emri i fazës]
[Data] — [Ngjarja] — [Rëndësia] — [Referenca dokumenti]

### FAZA E DYTË — [emri i fazës]
[Data] — [Ngjarja] — [Rëndësia] — [Referenca dokumenti]

⚠️ NËSE LLOJI ËSHTË I VETËM:
Një listë unike e renditur sipas datës.

DETYRA:
- Rendit ngjarjet sipas datës
- Për çdo ngjarje: data, akti, palët, rëndësia
- Shëno afatet procedurale VETËM nëse shfaqen në dokument
- Refero dokumentin specifik

⚠️ KURRË mos shpik datë që nuk shfaqet në dokumentet.
⚠️ NËSE data e një ngjarjeje nuk gjendet në dokument → OSE shkruaj
   "Data: e pandarë në dokument" (pa kllapa false), OSE hiqe rreshtin.

""" + STRICT_RULES,
    },

    "parties_and_roles": {
        "title": "PALËT DHE ROLET",
        "max_tokens": 3000,
        "prompt": """Ti je jurist proceduralist. Bazuar në ekstraktimet,
harto listën e plotë të PALËVE DHE PERSONAVE KYÇ.

⚠️ MOS shkruaj titullin kryesor ("PALËT DHE ROLET") — shtohet
   automatikisht nga sistemi.

═══════════════════════════════════════════════════════════════════════════
🛑 RREGULL ABSOLUT PËR ROLET
═══════════════════════════════════════════════════════════════════════════

Burimi i vetëm për rolet është "👥 PALËT NDËRGYQËSE ME ROLE" nga digest-i.
TI VETËM RIKOPJO ATË BLLOK ME FORMATIM — PA INTERPRETIM.

FEW-SHOT SHEMBULL:

Digest-i:
  👥 PALËT NDËRGYQËSE ME ROLE:
    • Sanije (Azem) Bala — Roli: Pala e mbrojtur
    • Shaban Bala — Roli: I pandehuri / Pala përgjegjëse

Output i SAKTË:

## FAZA E PARË — Kërkesë për Urdhër Mbrojtjeje
### Palët Ndërgjyqëse
- Pala e mbrojtur: Sanije (Azem) Bala
- Pala përgjegjëse: Shaban Bala

## FAZA E DYTË — Procedurë Penale
### Palët Ndërgjyqëse
- I pandehuri: Shaban Bala
- E dëmtuara: Sanije (Azem) Bala

❌ KURRË MOS SHKRUAJ KËSHTU:
  ❌ "Pala e mbrojtur: Shaban Bala" (i përmbysur)
  ❌ "Pala përgjegjëse: Sanije Bala" (i përmbysur)
  ❌ "Pala kundërshtare: Andi Bala" (Andi është fëmijë, jo palë)

═══════════════════════════════════════════════════════════════════════════

⚠️ NËSE LLOJI KA "→" (lëndë e dyfishtë):

## FAZA E PARË — [civile]
### Palët Ndërgjyqëse
- [Roli]: [Emri i plotë]
- [Roli]: [Emri i plotë]

### Gjyqtarë / Zyrtarë
- ...

## FAZA E DYTË — [penale]
### Palët Ndërgjyqëse
- [Roli]: [Emri i plotë]

### Prokurori / Mbrojtësi
- ...

## Persona të tjerë të referuar
- Anëtarë familjarë: [lista]
- Dëshmitarë të mundshëm: [lista]

⚠️ NËSE LLOJI ËSHTË I VETËM — strukturë standarde.

⚠️ RREGULLA TË PAFEKSIONUESHME:
1. Anëtarët e familjes NUK JANË "palë kundërshtare".
2. NUK shkëmbe rolet ndërmjet fazave.
3. Cito rolin VETËM nëse shfaqet literal në digest.

""" + STRICT_RULES,
    },

    "legal_framework": {
        "title": "KUADRI LIGJOR DHE NENET",
        "max_tokens": 2600,
        "prompt": """Ti je jurist ekspert në legjislacionin e Kosovës. Bazuar në 
digest-in, harto KUADRIN LIGJOR.

⚠️ MOS shkruaj titullin kryesor ("KUADRI LIGJOR DHE NENET") — shtohet
   automatikisht nga sistemi.

⚠️ RREGULL ABSOLUT (GUARDRAIL #1):
- Seksioni "🔒 CITIMET E VËRTETUARA (REGEX)" është BURIMI I VETËM 
  I SË VËRTETËS.
- PËRDOR VETËM ligjet dhe nenet që shfaqen në atë seksion.
- ÇDO ligj/nen që nuk është aty do të fshihet nga Guardrail #4.
- NUK LEJOHET të ndryshosh numrin e ligjit (03/L-182 ≠ 06/L-006).
- NUK LEJOHET të shpikësh akronime ligjesh (LMDHF, KPK) që nuk janë 
  në listën e ligjeve të verifikuara.
- FORMATI: "Neni X" ose "Neni X, par. Y" — KURRË "Neni X.Y".
- NËSE neni shfaqet VETËM si numër, shkruaj VETËM:
    "Neni X i [Ligjit]"
  PA shpikje përshkrimi.

DETYRA:
- Ligjet kryesore me numra (VETËM ato në digest)
- Nenet sipas ligjit të saktë (VETËM ato në digest)
- Jurisprudenca e Gjykatës Supreme — VETËM nëse ekziston në digest
  (seksioni "🏛️ AKTGJYKIMET E GJYKATËS SUPREME")
  ⚠️ NËSE NUK KA → shkruaj SAKTËSISHT:
     "Nuk u identifikuan vendime të Gjykatës Supreme në fashikull.
      Jurisprudenca relevante duhet të kërkohet veçmas."
  ❌ NUK LEJOHET të listosh nene si "jurisprudencë" — nenet janë
     legjislacion, jo vendime gjyqësore.
- Hierarkia e burimeve

""" + STRICT_RULES,
    },

    "key_findings_contradictions": {
        "title": "FAKTET KYÇE DHE KUNDËRSHTITË",
        "max_tokens": 2400,
        "prompt": """Ti je jurist analitik. Identifiko FAKTET KYÇE dhe KUNDËRSHTITË.

⚠️ MOS shkruaj titullin kryesor ("FAKTET KYÇE DHE KUNDËRSHTITË") —
   shtohet automatikisht nga sistemi.

DETYRA:
A. FAKTET KYÇE (8-12)
B. KUNDËRSHTITË
C. PROVAT

⚠️ NËSE lloji i lëndës ka "→", dalloji faktet sipas fazave:
- Fakte civile
- Fakte penale

⚠️ KUPTIMI I "KUNDËRSHTIVE":
- KUNDËRSHTIA = kontradiktë faktike midis dy burimeve (jo strategji).
- PËRDOR kohën e TASHME ("pala pretendon", "dokumenti thotë").
- ❌ NUK LEJOHET koha e ardhme ("do të argumentojë", "do të kontestohet")
  — këto janë strategji, NUK janë kontradikta. Vendi i tyre është
  te seksioni "REKOMANDIMET".

⚠️ SEKSIONI C — PROVAT:
- Listo VETËM provat që EKZISTOJNË realisht në fashikull.
- ❌ NUK LEJOHET "çdo provë tjetër që do të paraqitet" — kjo është spekulim.
- Për çdo provë: emri i dokumentit/tipit + roli në çështje.

⚠️ NUK LEJOHET të krijosh fakte ose kontradikta që nuk gjenden në digest.

""" + STRICT_RULES,
    },

    "recommendations": {
        "title": "REKOMANDIMET DHE HAPAT KONKRET TË VEPRIMIT",
        "max_tokens": 3000,
        "prompt": """Ti je jurist strategjik me përvojë dekadash në Gjykatën Supreme 
të Kosovës. Bazuar në digest-in, harto ANALIZËN E DEFEKTEVE PROCEDURALE 
dhe REKOMANDIMIN STRATEGJIK për klientin.

⚠️ MOS shkruaj titullin kryesor ("REKOMANDIMET DHE HAPAT KONKRET TË VEPRIMIT")
   — shtohet automatikisht nga sistemi.

DETYRA:

A. DEFEKTET PROCEDURALE DHE MATERIALE
   - Listo ÇDO defekt të identifikuar në fashikull
   - Për secilin: cito nenet e shkelura + dokumentin ku gjendet
   - Klasifiko: defekt procedural / shkelje e ligjit material / konflikt interesi

B. VLERËSIMI I OPSIONEVE LIGJORE
   Analizo VETËM opsionet që kanë bazë në fashikullin e dhënë.
   ⚠️ NËSE lënda ka "→" (dy faza), listoji opsionet VECMAS për çdo fazë.

C. REKOMANDIMI PËRFUNDIMTAR
   ▶ VEPRIMI KRYESOR
   ▶ ARSYEJA
   ▶ HAPAT KONKRET (1, 2, 3, ...)
   ▶ AFATET KRITIKE: listo VETËM ato që shfaqen në dokumentet
   ▶ RREZIQET

⚠️ RREGULLA KRITIKE PËR AFATET:
- Cito VETËM afate që shfaqen në digest (dokumentet e fashikullit),
  ME BURIMIN E SAKTË: "Sipas [dokumenti X], afati është N ditë."
- NËSE dokumentet përmendin afate KONTRADIKTORE → listoji TË GJITHA
  me burimin përkatës dhe shëno: "[KONTRADIKTË — verifiko manualisht]".
- NËSE asnjë dokument nuk përmend afat → shkruaj SAKTËSISHT:
    "Afati ligjor nuk u identifikua në dokumentet e ngarkuara —
     kërkohet verifikim nga avokati."
  ❌ NUK LEJOHET "Afati: kontrollo manualisht" (instruksion i brendshëm).
- NUK LEJOHET të shpikësh afate nga ligji i përgjithshëm.

""" + STRICT_RULES,
    },
}