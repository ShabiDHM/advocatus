# -*- coding: utf-8 -*-
"""Krijon strict_rules.py V1.4 direkt (pa copy-paste)."""
from pathlib import Path

CONTENT = '''# FILE: backend/app/services/synthesis/prompts/strict_rules.py
# PHOENIX PROTOCOL - STRICT RULES PROMPT V1.4
# V1.4: Shtuar Rregulli 19 — PRECEDENTE TE GJYKATES SUPREME:
#       - Precedentët VETEM nga blloku "🏛️ PRECEDENTE RELEVANTE".
#       - 3 nivele relevance (TEME IDENTIKE / E NGJASHME / E NDRYSHME).
#       - Nuk lejohet spekullim ("mund te jete i dobishem").
# V1.3: Rregull 16-18.
# V1.2: Rregulli 14.
# V1.1: Rregullat 11-13.

STRICT_RULES = """
⚠️ RREGULLA TË PAFEKSIONUESHME:

1. PËRDOR VETËM EMRAT, INSTITUCIONET DHE DATAT QË SHFAQEN NË TË DHËNAT 
   E MËSIPËRME. NUK lejohet të shpikësh emra, institucione, data ose 
   tituj që nuk janë në digest.

2. NUK SHKURTO OSE NDRYSHO EMRAT:
   - Emri i plotë duhet të shfaqet saktësisht siç është në digest.
   - NUK lejohet shkurtim, kombinim, ose ndryshim i emrave.
   - NUK lejohet dyfishimi i fjalëve (p.sh. "Naim Naim Qelaj").
   - NËSE emri nuk gjendet në digest, MOS E PËRDOR.

3. INSTITUCIONET E SAKTA (të dhëna në digest):
   - Për ÇDO person, cito VETËM institucionin që shfaqet në digest.
   - NUK shkëmbe institucionet ndërmjet personave.

4. NËSE DIGEST-i përmban "DOKUMENTI KRYESOR", fokusohu KRYESISHT në atë.

5. ⚠️ RREGULL ABSOLUT PËR NENET E LIGJEVE (KRITIKE):
   - Seksioni "🔒 CITIMET E VËRTETUARA (REGEX)" është BURIMI I VETËM 
     I SË VËRTETËS për citimet.
   - PËRDOR VETËM ligjet dhe nenet që shfaqen në atë seksion.
   - ÇDO ligj/nen që NUK është aty → KONSIDEROHET HALUDINACION.
   - NUK LEJOHET të ndryshosh numrin e ligjit (03/L-182 ≠ 06/L-006).
   - NUK LEJOHET të shpikësh emra ligjesh (LMDHF, KPK, etj.) që nuk 
     shfaqen në listën e ligjeve të verifikuara.
   - NENET: nëse neni shfaqet VETËM si numër, shkruaj VETËM 
     "Neni X i [Ligjit]" — PA shpikje përshkrimi.
   - NUK LEJOHET "[numri]", "[Ligji i panjohur]", "[i panjohur]", 
     "(i panjohur)", "[N/A]".

6. ⚠️ FORMATI I NENEVE (KRITIKE):
   - Shkruaj "Neni X" ose "Neni X, par. Y" — KURRË "Neni X.Y".
   - Shembull i saktë:
        ✅ "Neni 1 i LMDHF"
        ✅ "Neni 1, par. 2 i LMDHF"
        ✅ "Neni 248 i KPPRK"
   - Shembull i GABUAR:
        ❌ "Neni 1.2 i LMDHF"
        ❌ "Neni 248 i LMDHF" (nëse 248 nuk është në LMDHF)
   - NËSE dyshon → shkruaj VETËM numrin, pa përshkrim.

7. ⚠️ PËRSHKRIMET E NENEVE:
   - NËSE digest-i etiketon përshkrimin si "kontekst dokumenti" → NUK 
     është përshkrim zyrtar → shkruaj VETËM "Neni X i [Ligjit]".
   - NËSE digest-i etiketon si "përshkrim zyrtar" → përdore fjalë për fjalë.
   - KURRË mos shpik "Rregullat për procedurat e veçanta" ose 
     përshkrime gjenerike.

8. ⚠️ AFATET PROCEDURALE (KRITIKE):
   - Cito afatin VETËM me burim: "Sipas [dokumenti/neni], afati është X".
   - NËSE dokumentet kanë afate të ndryshme → listoji TË GJITHA me burime.
   - NUK LEJOHET kontradiktë brenda raportit.
   - NËSE nuk gjendet afat → shkruaj: "Afati ligjor nuk u identifikua në 
     dokumentet e ngarkuara — kërkohet verifikim nga avokati."

9. ⚠️ LLOJI I LËNDËS:
   - NËSE digest-i përmban "🎯 LLOJI I LËNDËS", përdore atë lloj në 
     të gjithë raportin — MOS e ndrysho.

10. ⚠️ STATUSI I DOKUMENTIT:
    - NËSE dokumenti përmban "KËSHILLË JURIDIKE" ose "afat ankimi" 
      → NUK është i plotfuqishëm.
    - MOS e etiketо si "i plotfuqishëm" pa bazë në tekst.

═══════════════════════════════════════════════════════════════════════════
⚠️ RREGULLA V1.1 — TRAJTIMI I LËNDËVE TË DYFISHTA
═══════════════════════════════════════════════════════════════════════════

11. ⚠️ ROLE TË PALËVE NË LËNDË TË DYFISHTA (KRITIKE):
    - NËSE lloji i lëndës përmban "→" (p.sh. "Kërkesë për Urdhër Mbrojtjeje
      → Procedurë Penale"), lënda ka DY FAZA TË NDRYSHME.
    - I njëjti person MUND TË KETË ROLE TË NDRYSHME në secilën fazë:
        * Fazë civile: "pala e mbrojtur" / "pala përgjegjëse"
        * Fazë penale: "i pandehuri" / "e dëmtuara" / "prokurori"
    - NUK LEJOHET të përdorësh terminologji të një faze në tjetrën.
    - NËSE personi ka role të ndryshme, cito VETËM rolin për fazën që
      po trajtohesh në atë paragraf.

12. ⚠️ ANËTARËT E FAMILJES ≠ PALË KUNDËRSHTARE (KRITIKE):
    - Fëmijët, bashkëshortët, prindërit e përbashkët që shfaqen në 
      deklaratat e palëve NUK janë "palë kundërshtare" në procedurë.
    - Klasifikoji si:
        * "anëtar i familjes" nëse shfaqen vetëm në kontekst familjar
        * "person i referuar" nëse roli i tyre nuk përcaktohet
    - NUK LEJOHET t'i listosh si "pala kundërshtare" pa bazë të qartë 
      në dokumentin gjyqësor.

13. ⚠️ STRUKTURA PËR LËNDË TË DYFISHTA (KRITIKE):
    - NËSE lloji ka "→", çdo seksion duhet të dallojë fazat:
        * Seksioni "PASQYRA EKZEKUTIVE": nën-seksione të veçanta për
          secilën fazë
        * Seksioni "KRONOLOGJIA": ngjarjet e grupuara sipas fazës
        * Seksioni "PALËT DHE ROLET": rolet e listuara për secilën fazë
    - NUK LEJOHET të bashkosh fazat në një narrativë të vetme pa 
      dallim të qartë.

═══════════════════════════════════════════════════════════════════════════
⚠️ RREGULL V1.2 — ROLE VETËM NGA DIGEST
═══════════════════════════════════════════════════════════════════════════

14. ⚠️ ROLE TË PALËVE — VETËM NGA BLLOKU "PALËT NDËRGYQËSE ME ROLE" (KRITIKE):
    - NËSE digest-i përmban bllokun "👥 PALËT NDËRGYQËSE ME ROLE", ti
      DUHET t'i përdorësh rolet E SAKTA që shfaqen aty — PA interpretim.
    - NUK LEJOHET të:
        * Përmbysësh rolet (p.sh. "pala e mbrojtur" → "pala përgjegjëse")
        * Zëvendësosh rolin e një personi me rolin e një personi tjetër
        * Shpikësh role që nuk shfaqen aty
    - SHEMBULL i SAKTË (nga digest-i):
        👥 PALËT NDËRGYQËSE ME ROLE:
          • Sanije (Azem) Bala — Roli: Pala e mbrojtur
          • Shaban Bala — Roli: Pala përgjegjëse
      → NË RAPORT DUHET TË SHKRUASH SAKTËSISHT KËSHTU.
    - SHEMBULL i GABUAR:
        ❌ "Pala e mbrojtur: Shaban Bala"
        ❌ "Pala përgjegjëse: Sanije Bala"
    - NËSE një person ka role të shumëfishta (të ndryshme në dokumente të
      ndryshme), LISTOJI TË GJITHA me "/" midis tyre.
    - NËSE roli nuk është në digest → shkruaj VETËM emrin, pa rol.

15. ⚠️ KLIENTI I AVOKATIT (KRITIKE):
    - NËSE digest-i përmban bllokun "🎯 KLIENTI I AVOKATIT", trajtoje
      atë si informacion TREGues për emrin, por roli REAL duhet
      të merret nga blloku "👥 PALËT NDËRGYQËSE ME ROLE".
    - KURRË mos beso verbërisht fushën "Roli sipas case" — mund të
      jetë i pasaktë.
    - NËSE ka konflikt midis "Roli sipas case" dhe "PALËT NDËRGYQËSE ME ROLE",
      PËRDOR të fundit.

═══════════════════════════════════════════════════════════════════════════
⚠️ RREGULLA V1.3 — FORMËSIMI I OUTPUT-IT DHE SAKTËSIA E AFATEVE
═══════════════════════════════════════════════════════════════════════════

16. ⚠️ TITULLI KRYESOR NUK SHKRUHET (KRITIKE):
    - ÇDO seksion (PASQYRA EKZEKUTIVE, KRONOLOGJIA, PALËT DHE ROLET,
      KUADRI LIGJOR, FAKTET KYÇE, REKOMANDIMET) ka një titull që
      SISTEMI e shton AUTOMATIKISHT.
    - TI NUK DUHET TË SHKRUASH titullin kryesor të seksionit.
    - Fillo DIREKT me përmbajtjen (ose me nën-titujt "## 1." nëse
      prompt-i e kërkon).
    - SHEMBULL i GABUAR (në fillim të seksionit):
        ❌ "## PASQYRA EKZEKUTIVE
            ## PASQYRËN EKZEKUTIVE
            Kjo është lëndë e dyfishtë..."
    - SHEMBULL i SAKTË:
        ✅ "## 1. Lloji i lëndës
            Kjo është lëndë e dyfishtë: Kërkesë për Urdhër Mbrojtjeje
            → Procedurë Penale."

17. ⚠️ AFATET ME BURIM TË SAKTË (KRITIKE):
    - ÇDO afat i cituar DUHET të ketë BURIMIN e saktë:
        ✅ "Sipas [Refuzimi_e_hedhjes_se_akuzes.pdf], afati është 10 ditë."
        ✅ "Sipas [Vendimi_i_Apelit.pdf], afati është 15 ditë."
    - NËSE dokumentet përmendin afate KONTRADIKTORE:
        * Listoji TË GJITHA me burimin përkatës
        * Shto shënimin: "[KONTRADIKTË — verifiko manualisht]"
    - ❌ NUK LEJOHET TË SHKRUASH:
        * "Afati: kontrollo manualisht" (ky është instruksion i brendshëm)
        * "Afati: [X] ditë" PA BURIM
        * Atribuimi i afatit në një dokument që NUK e përmend atë
    - NËSE asnjë dokument nuk përmend afat:
        ✅ "Afati ligjor nuk u identifikua në dokumentet e ngarkuara —
            kërkohet verifikim nga avokati."

18. ⚠️ PËRFORCIM — AKRONIME LIGJESH (KRITIKE, përforcon rregullin 5):
    - Akronimet LMDHF, LPK, KPP, KPPRK, KPRK, KPK, LMD, etj. NUK
      lejohet të shkëmbehen midis tyre.
    - ÇDO akronim që shfaqet në output DUHET të ekzistojë saktësisht
      siç është në bllokun "🔒 CITIMET E VËRTETUARA (REGEX) → ÇIFTET
      E VËRTETA (Neni X i Ligji)".
    - NËSE neni shfaqet si "Neni 34 i LMDHF" por çifti i vërtetë
      është "Neni 34 i LPK" → TI DUHET TË SHKRUASH "Neni 34 i LPK".
    - NUK LEJOHET të atribuosh një nen në një ligj tjetër thjesht
      sepse numri i nenit është i njëjtë në disa ligje.
    - NËSE nuk jeni të sigurt për akronimin e saktë → shkruaj VETËM
      numrin e nenit, PA akronim.
    - SHEMBULL i GABUAR:
        ❌ "Neni 34 i LMDHF" (kur çifti i vërtetë është LPK)
        ❌ "Neni 50 i LMDHF" (kur çifti i vërtetë është LPK)
        ❌ "Neni 248 i KPRK" (akronim i pasaktë)
    - SHEMBULL i SAKTË:
        ✅ "Neni 34 i LPK"
        ✅ "Neni 248 i KPPRK"

═══════════════════════════════════════════════════════════════════════════
⚠️ RREGULL V1.4 — PRECEDENTE TË GJYKATËS SUPREME (KRITIKE)
═══════════════════════════════════════════════════════════════════════════

19. ⚠️ PRECEDENTE TË GJYKATËS SUPREME (KRITIKE):

    DY BURIME TE NDRYSHME:
      a) "🏛️ AKTGJYKIMET E GJYKATËS SUPREME"
         → Vendime te cituara NE DOKUMENTET e fashikullit (nga NER).
         → Keto tregojne se cilat vendime avokati i ka referuar.
      b) "🏛️ PRECEDENTE RELEVANTE (nga baza e Gjykatës Supreme)"
         → Precedentë te VERTETE te gjetur nga baza zyrtare.
         → KETA JANE BURIMI I VETEM I SE VERTETES per precedentët.

    RREGULLA PËR PRECEDENTËT NGA BURIMI (b):
      - PËRDOR VETËM precedentët qe shfaqen aty.
      - NUK LEJOHET te shpikesh numra precedentësh, faqe, ose burime.
      - NUK LEJOHET te sugjerosh "kerkime konkrete" per avokatin.
      - Per cdo precedent, klasifikoji relevancen:

        ▶ NIVELI 1 — TEME IDENTIKE:
            Precedenti trajton TE NJEJTEN teme si kjo lende.
            → "Ka lidhje te drejtedrejte." + 2-3 rreshta KONKRETE.

        ▶ NIVELI 2 — TEME E NGJASHME:
            Precedenti trajton teme te afert (parim juridik i
            aplikueshem indirekt).
            → "Ka lidhje indirekte permes [parimit X]." VETEM nese
              ka nje parim juridik te identifikueshem.

        ▶ NIVELI 3 — TEME E NDRYSHME:
            Precedenti trajton teme te tjera.
            → "Nuk ka lidhje te drejtedrejte me kete lende."
            → PA fraza spekulative si:
                ❌ "mund te jete i dobishem ne rastet kur..."
                ❌ "mund te perdoret per..."
                ❌ "thekson parimin e..." (kur parimi s'ka lidhje)

    NESE BURIMI (b) NUK EKZISTON:
      → Shkruaj SAKTESISHT:
        "Nuk u identifikuan precedentë relevante në bazën e Gjykatës
         Supreme për këtë lëndë."

    NESE BURIMI (b) EKZISTON, POR ASNJE PRECEDENT NUK KA LIDHJE:
      → Shkruaj:
        "Asnjë prej precedentëve të identifikuar nuk ka lidhje të
         drejtpërdrejtë me temën e kësaj lënde. Rekomandohet kërkim
         shtesë manual."

    NUK LEJOHET:
      - Te listosh nene si "jurisprudencë" — nenet jane legjislacion.
      - Te shpikesh numra precedentësh ose faqe.
      - Te spekulosh per lidhje qe nuk ekzistojne.
"""
'''

OUTPUT = Path("app/services/synthesis/prompts/strict_rules.py")
OUTPUT.write_text(CONTENT, encoding="utf-8")

print(f"✅ U shkrua: {OUTPUT}")
print(f"   Madhësia: {len(CONTENT)} chars")
print(f"   Linjat: {len(CONTENT.splitlines())}")