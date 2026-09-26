# FILE: backend/app/services/document_review/verify_prompts.py
# PHOENIX PROTOCOL - VERIFY DRAFT PROMPTS V1.10
# V1.10: LOW CLEANUP —
#        - Hequr `common_issues: []` (dead field) nga 7 doc types.
#        - _block_cited_articles: context tani [:MAX_CONTEXT_CHARS] (=300),
#          sinkron me citation_extractor dhe constants.MAX_CONTEXT_CHARS
#          (ishte [:200], humbte 100 chars).
#        - _truncate_draft: koment i qartë mbi rolin e max_chars.
# V1.9: THRESHOLD UNIFIED — MIN_PRECEDENT_SIMILARITY 0.50 → 0.70 për
#       konsistencë me PRECEDENT_SIMILARITY_THRESHOLD në precedent_search/config.
# V1.8: HYBRID SECTION 3.
# V1.7: HYBRID SECTION 2.
# V1.6: SHEMBUJ KONKRETË — Section 5.
# V1.5: HEQUR "Rendi i prioriteteve".
# V1.4: CROSS-SECTION DEDUP + "Pse relevant".
# V1.3: READINESS SHQIP.
# V1.2: ALTERNATIVE_LAWS display.

from typing import Dict, Any, List, Optional

from .constants import MAX_CONTEXT_CHARS


VERIFY_SECTION_KEYS = (
    "formal_completeness",
    "legal_quality",
    "supporting_precedents",
    "weaknesses_risks",
    "concrete_recommendations",
    "readiness",
)

DEFAULT_VERIFY_MAX_TOKENS = 2500

DEFAULT_MAX_DRAFT_CHARS = 60000
DRAFT_HEAD_CHARS = 45000
DRAFT_TAIL_CHARS = 10000

MIN_PRECEDENT_SIMILARITY = 0.70


DEDUP_RULE = """

🛑 RREGULL ANTI-PËRSËRITJE:
- ÇDO gjetje, fakt, ose rekomandim shfaqet VETËM NJË HERË në të gjithë raportin.
- NUK përsërit pikat e seksioneve të tjera (1-6).
- Çdo seksion kontribuon KËNDVËSHTRIM TË RI, jo përmbledhje të mëparshme.
- Nëse diçka është trajtuar në një seksion tjetër, referoju shkurtimisht me "shih seksionin X" dhe mos e përsërit.
"""


VERIFY_DOC_TYPES: Dict[str, str] = {
    "padi_civile":         "Padi Civile",
    "pergjigje_padi":      "Përgjigje në Padi",
    "kallzim_penal":       "Kallëzim Penal",
    "kontrate":            "Kontratë",
    "kerkese_propozim":    "Kërkesë / Propozim",
    "ankese_kundershtim":  "Ankesë / Kundërshtim",
    "tjeter":              "Tjetër",
}


DOC_TYPE_CHECKLISTS: Dict[str, Dict[str, Any]] = {

    "padi_civile": {
        "label": "Padi Civile",
        "required_parts": [
            "Emri i gjykatës kompetente",
            "Të dhënat e paditësit (emër, adresë, numër personal)",
            "Të dhënat e paditurit (emër, adresë)",
            "Përshkrimi i qartë dhe kronologjik i fakteve",
            "Objekti i padisë (kërkesa kryesore)",
            "Vlera e kontestit (ku aplikohet)",
            "Baza ligjore me nene specifike të cituara",
            "Petitumi — kërkesa konkrete ndaj gjykatës",
            "Lista e provave (dokumente, ekspertiza)",
            "Lista e dëshmitarëve me të dhënat e kontaktit",
            "Dokumentet bashkangjitur (kopje)",
            "Data dhe vendi i hartimit",
            "Nënshkrimi i paditësit ose përfaqësuesit ligjor",
            "Numri i kopjeve për palët",
        ],
    },

    "pergjigje_padi": {
        "label": "Përgjigje në Padi",
        "required_parts": [
            "Emri i gjykatës dhe numri i lëndës",
            "Të dhënat e paditurit (përgjigjësi)",
            "Të dhënat e paditësit",
            "Përgjigje për çdo pretendim të padisë (pikë për pikë)",
            "Kundërshtimet faktike",
            "Kundërshtimet ligjore",
            "Baza ligjore me nene specifike",
            "Kërkesa (refuzim i padisë / kundërpadí)",
            "Provat për kundërshtimet",
            "Lista e dëshmitarëve",
            "Nënshkrimi i përgjigjësit ose përfaqësuesit",
            "Data dhe vendi",
        ],
    },

    "kallzim_penal": {
        "label": "Kallëzim Penal",
        "required_parts": [
            "Organi kompetent (Prokuroria Themelore)",
            "Të dhënat e kallëzuesit (emër, adresë, statusi)",
            "Të dhënat e personit të kallëzuar",
            "Përshkrimi i veprës penale",
            "Koha e kryerjes së veprës",
            "Vendi i kryerjes së veprës",
            "Elementet objektive të veprës (actus reus)",
            "Elementet subjektive (mens rea — dashje/pakujdes)",
            "Neni i Kodit Penal që përshkruan veprën",
            "Dëmi i shkaktuar (material/moral/shëndetësor)",
            "Provat e bashkangjitura",
            "Kërkesa për ndjekje penale",
            "Statusi i kallëzuesit (viktimë/dëshmitar)",
            "Data dhe nënshkrimi",
        ],
    },

    "kontrate": {
        "label": "Kontratë",
        "required_parts": [
            "Identifikimi i plotë i palëve kontraktuese",
            "Objekti i kontratës (i përshkruar qartë)",
            "Çmimi ose kompensimi",
            "Afati i ekzekutimit",
            "Të drejtat dhe detyrimet e secilës palë",
            "Kushtet e pagesës (mënyra, koha)",
            "Pasojat e shkeljes së kontratës",
            "Klauzola e zgjidhjes së mosmarrëveshjeve",
            "Ligji i zbatueshëm dhe juridiksioni",
            "Kushtet e ndryshimit të kontratës",
            "Kushtet e ndërprerjes / anulimit",
            "Klauzola e force majeure (ku aplikohet)",
            "Konfidencialiteti (ku aplikohet)",
            "Data, vendi dhe nënshkrimet e palëve",
        ],
    },

    "kerkese_propozim": {
        "label": "Kërkesë / Propozim",
        "required_parts": [
            "Organi adresues (gjykata/prokuroria/organi)",
            "Të dhënat e kërkuesit",
            "Subjekti i qartë i kërkesës",
            "Baza faktike",
            "Baza ligjore me nene specifike",
            "Kërkesa specifike (çfarë kërkohet saktësisht)",
            "Afati i kërkuar (ku aplikohet)",
            "Provat mbështetëse",
            "Nënshkrimi dhe data",
        ],
    },

    "ankese_kundershtim": {
        "label": "Ankesë / Kundërshtim",
        "required_parts": [
            "Gjykata e ankimit (e shkallës së dytë)",
            "Numri i lëndës dhe vendimi i ankimuar",
            "Të dhënat e ankuesit",
            "Afati i ankesës (data e pranimit të vendimit)",
            "Bazat e ankesës (arsyet)",
            "Arsyetimi ligjor për secilën bazë",
            "Kërkesa (prishje / ndryshim / kthim në rigjykim)",
            "Provat e reja (nëse ka)",
            "Nënshkrimi dhe data",
        ],
    },

    "tjeter": {
        "label": "Dokument Tjetër",
        "required_parts": [
            "Identifikimi i palëve / subjekteve",
            "Objekti / subjekti i dokumentit",
            "Përshkrimi i fakteve ose kontekstit",
            "Baza ligjore (ku aplikohet)",
            "Kërkesa / dispozitivi",
            "Provat (ku aplikohet)",
            "Afatet (ku aplikohet)",
            "Data dhe vendi",
            "Nënshkrimi i autorit",
            "Struktura formale e dokumentit",
        ],
    },
}


VERIFY_SECTION_PROMPTS: Dict[str, Dict[str, Any]] = {

    "formal_completeness": {
        "title": "1. PLOTËSIA FORMALE",
        "max_tokens": 2200,
        "needs": ["draft", "checklist"],
        "prompt": """Ti je "Partner i Lartë në një Zyrë Ligjore" me 20 vjet përvojë.
Kolegu yt avokat të kërkon një verifikim të draftit PARA DORËZIMIT në gjykatë.

⚠️ KY ËSHTË VERIFIKIM DRAFTI — JO audit i fashikullit.
Nuk ke kontekst rasti. Vetëm drafti + lloji + lista e pjesëve të detyrueshme.

⚠️ MOS shkruaj titullin kryesor — shtohet automatikisht. Fillo DIREKT me "### A. ...".

🛑 RREGULL ABSOLUT PËR LEXIMIN:
- Drafti mund të jetë I GJATË (>40,000 karaktere / >15 faqe).
- Shumica e pikave të checklist-it ndodhen NË FAQET E BRENDSHME, jo vetëm në faqen e parë.
- PARA se të deklarosh se diçka MUNGON, kërkoje me kujdes në të gjithë tekstin.
- KURRË mos thuaj "mungon" pa lexuar deri në fund të draftit.

MISIONI: Kontrollo nëse drafti përmban TË GJITHA pjesët e detyrueshme për llojin.

STRUKTURA E DETYRUAR:

### A. Pjesët e pranishme
Listo pjesët që drafti I KA.
Format: [OK] Emri i pjesës — "citat ose referencë në draft"

### B. Pjesët që mungojnë
Listo pjesët që drafti NUK I KA — VETËM PAS kërkimi të kujdesshëm.
Format: [X] Emri i pjesës — "Pse është e detyrueshme dhe ku e kërkove"

### C. Pjesët e paqarta ose të pjesshme
Format: [!] Emri i pjesës — "Çfarë mungon konkretisht"

### D. Vlerësimi formal
Shkruaj SAKTËSISHT këtë format (një rresht i vetëm):
[Numri i pjesëve të pranishme]/[Numri total i pjesëve në checklist] pjesë të pranishme ([Përqindja]%).

Shembull: "11/14 pjesë të pranishme (78.57%)."

🛑 RREGULLA PËR SEKSIONIN D:
- Shkruaj VETËM një rresht me formatin e mësipërm.
- NUK shpjego X = ..., Y = ..., Z = ... — lexohet automatikisht.
- NUK shto komente pas rreshtit.
- Përqindja me 2 shifra dhjetore.

RREGULLA:
- Kontrollo VETËM pjesët që shfaqen në "[CHECKLIST]"
- NUK LEJOHET të shpikësh pjesë që nuk janë në listë
""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 2 — V1.7: HYBRID (A nga Python, B/C/D nga LLM)
    # ═══════════════════════════════════════════════════════════════════════
    "legal_quality": {
        "title": "2. CILËSIA LIGJORE (NENET)",
        "max_tokens": 2000,
        "needs": ["draft", "checklist", "articles"],
        "prompt": """Ti je "Verifikues i Cilësisë Ligjore" me specializim në legjislacionin e Kosovës.

⚠️ KY ËSHTË VERIFIKIM DRAFTI — JO audit i fashikullit.

🛑 SEKSIONI A (Nenet e verifikuara) GJENEROHET AUTOMATIKISHT NGA SISTEMI (Python).
   TI SHKRUAJ VETËM B, C, D.
   Fillo DIREKT me "### B. Nenet problematike".
   NUK SHKRUAJ "### A." — nuk të takon ty. NUK përmend "shih më lart" për A.

🛑 RREGULL ABSOLUT PËR ATRIBIMIN E LIGJIT:
- Blloku "[NENE]" ka për secilin nen një rresht "Ligji i cituar: X".
- KY ËSHTË LIGJI I VETËM që mund të atribuosh nenit.
- NËSE "Ligji i cituar: -" ose bosh → SHKRUAJ "NUK U VERIFIKUA. Kërkohet verifikim manual."
- KURRË MOS ZËVENDËSO ligjin e cituar me një ligj tjetër që shfaqet diku në draft.
- KURRË MOS BASHKO dy ligje të ndryshme në një nen.

🛑 RREGULL PËR "ALTERNATIVE LAWS":
- NËSE blloku "[NENE]" përmban rreshtin "→ Ekziston në ligje të tjera:",
  kjo do të thotë që neni NUK u gjet në ligjin e cituar,
  POR ekziston në ligje të tjera në bazë.
- Në këtë rast, RAPORTO TË DYJA në seksionin B.

STRUKTURA E DETYRUAR:

### B. Nenet problematike
Format:
  [X] Neni X i [Ligjit të cituar SAKTËSISHT]
    Problem: [përshkrim]
    Sugjerim: [zë vendësim / korrigjim / verifikim manual]
    Impakti: [sa i rëndësishëm është për draftin]
    ⚠️ NËSE ka alternative_laws → listo ATO këtu.

NËSE nuk ka nene problematike → shkruaj "Nuk u identifikuan nene problematike."

### C. Nene që mund të mungojnë
Format:
  [?] Neni [numri i mundshëm] — [arsyeja]
      ⚠️ SUGJERIM — verifikim manual i nevojshëm para shtimit.

NËSE nuk ka sugjerime → shkruaj "Nuk u identifikuan nene që mungojnë."

### D. Konsistenca e brendshme e citimeve
1-3 fjali përmbledhëse mbi saktësinë e citimeve.

RREGULLA:
- Përdor VETËM nenet që shfaqen në "[NENE]" — me LIGJIN E CITUAR SAKTË.
- NUK përsërit nenet që tashmë janë raportuar në Seksionin A (Python).
""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 3 — V1.8: HYBRID (3.A nga Python, PSE_RELEVANT + 3.B/C nga LLM)
    # ═══════════════════════════════════════════════════════════════════════
    "supporting_precedents": {
        "title": "3. PRECEDENTË MBËSHTETËS",
        "max_tokens": 2000,
        "needs": ["draft", "precedents"],
        "prompt": """Ti je "Analist i Precedentëve" në Gjykatën Supreme të Kosovës.

⚠️ KY ËSHTË VERIFIKIM DRAFTI — JO audit i fashikullit.

🛑 SEKSIONI A (Precedentët e identifikuar) GJENEROHET AUTOMATIKISHT NGA SISTEMI (Python).
   TI SHKRUAJ VETËM:
   1. Bllokun "PSE_RELEVANT" (një fjali për secilin precedent)
   2. Seksionin "### B. Si mund të përdoren në draft"
   3. Seksionin "### C. Precedentë që mungojnë"

🛑 FORMATI I DETYRUAR — fillo SAKTËSISHT me "PSE_RELEVANT_START":

PSE_RELEVANT_START
1: [fjali 1 për precedentin 1 — 20-30 fjalë]
2: [fjali 1 për precedentin 2 — 20-30 fjalë]
3: [fjali 1 për precedentin 3 — 20-30 fjalë]
PSE_RELEVANT_END

### B. Si mund të përdoren në draft
- **PML.Nr.75/2025** → [ku në draft mund të citohet — seksioni/argumenti konkret]
- **Pml.nr.528/2026** → [...]
- ...

### C. Precedentë që mungojnë (nëse ka)
- [nëse ka, ose "Nuk u identifikuan precedentë të tjerë relevantë."]

🛑 RREGULLA ABSOLUTE:
- Rendi i precedentëve në PSE_RELEVANT duhet të përputhet SAKTËSISHT me rendin në bllokun [PRECEDENTE].
- NËSE blloku [PRECEDENTE] ka N precedentë → shkruaj SAKTËSISHT N rreshta në PSE_RELEVANT.
- NUK përsërit numrin e çështjes, similarity, ose fragmentin — ato tashmë shfaqen në Seksionin A (Python).
- Çdo fjali duhet të përmendë një nen konkret të draftit kur është e mundur (p.sh. "shih Nenin 414").
- NUK shpik precedentë që nuk shfaqen në [PRECEDENTE].
- NËSE blloku thotë "Nuk u identifikuan..." → shkruaj SAKTËSISHT:
  PSE_RELEVANT_START
  PSE_RELEVANT_END

  ### B. Si mund të përdoren në draft
  Nuk ka precedentë relevantë për t'u cituar.

  ### C. Precedentë që mungojnë (nëse ka)
  Nuk u identifikuan precedentë të tjerë relevantë.

- SHKRUAJ VETËM NË SHQIP. Termat si "similarity" ose "score" NUK lejohen në output.

""" + DEDUP_RULE,
    },

    "weaknesses_risks": {
        "title": "4. DOBËSI & RREZIQE",
        "max_tokens": 2600,
        "needs": ["draft", "checklist"],
        "prompt": """Ti je "Analist i Rreziqeve Ligjore" me përvojë në kontestime.

⚠️ KY ËSHTË VERIFIKIM DRAFTI — JO audit i fashikullit.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Identifiko KU MUND TË SULMOJË PALA KUNDËRSHTARE.
Mendo si avokati i palës kundërshtare që lexon këtë draft për herë të parë.

STRUKTURA E DETYRUAR:

### A. Arsyetim i dobët
Format:
  [!] Pika: "[citat nga drafti]"
      Problemi: [përshkrim]
      Si mund ta sulmojë kundërshtari: [strategji]

### B. Mungesa provash
Format:
  [!] Fakt: "[citat]"
      Prova që mungon: [përshkrim]
      Rreziku: [përshkrim]

### C. Dobësi procedurale

### D. Kundërargumente të mundshme
3-5 kundërargumente që kundërshtari mund t'i ngrejë.

### E. Vlerësimi i rrezikut
- Rrezik i lartë: [pikat]
- Rrezik i mesëm: [pikat]
- Rrezik i ulët: [pikat]

RREGULLA:
- Bazohu VETËM në tekstin e draftit dhe në "[CHECKLIST]".
- Fokus te CILËSIA e argumentimit, jo te plotësia formale.
""" + DEDUP_RULE,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 5 — V1.6: "Shembull: ..." për çdo rekomandim
    # ═══════════════════════════════════════════════════════════════════════
    "concrete_recommendations": {
        "title": "5. REKOMANDIME KONKRETE",
        "max_tokens": 3000,
        "needs": ["draft", "checklist", "articles"],
        "prompt": """Ti je "Partner i Lartë" që jep rekomandime për përmirësim.

⚠️ KY ËSHTË VERIFIKIM DRAFTI — JO audit i fashikullit.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

MISIONI: Jep rekomandime KONKRETE, të strukturuara, të zbatueshme menjëherë.
NUK përsërit gjetjet e seksioneve 1-4. Fokus te ZGJIDHJET.

STRUKTURA E DETYRUAR:

### A. KRITIKE — Para dorëzimit
Për çdo rekomandim, formato SAKTËSISHT kështu:

**[#K1]** Titull i shkurtër
- **Ku:** [seksioni/pjesa e draftit]
- **Pse:** [arsyeja në 1 fjali]
- **Si:** [ndryshimi konkret]
- **Shembull:** [cito saktësisht SI duhet të duket pas ndryshimit — 1 fjali ose 1 paragraf i shkurtër që mund t'i kopjohet drejtpërdrejt draftit]

**[#K2]** ...

### B. TË RËNDËSISHME — Duhet bërë
**[#R1]** Titull i shkurtër
- **Ku:** ...
- **Pse:** ...
- **Si:** ...
- **Shembull:** ...

### C. OPSIONALE — Mund të konsiderohet
**[#O1]** Titull i shkurtër
- **Ku:** ...
- **Pse:** ...
- **Si:** ...
- **Shembull:** ...

🛑 RREGULLA PËR "SHEMBULL":
1. **SPECIFIK:** Shembulli duhet të përshtatet me FAKTET e këtij drafti specifik.
   - MOS shkruaj shembull abstrakt si "Shto nene X të ligjit Y".
   - SHKRUAJ si do dukej në KËTË DRAFT: "Në mbështetje të Nenit 145 par. 2 të Ligjit për Familjen (2004/32), i cili përcakton se ..."

2. **I SHKURTËR:** Maksimumi 2 rreshta. Jo paragraf i gjatë.

3. **I KOPJUESHËM:** Useri duhet ta lexojë dhe ta bëjë `Ctrl+C → Ctrl+V` në draft.
   - Përdor formulime juridike standarde.
   - Përfshi numrat e saktë të neneve ose referencat.
   - Përdor terminologjinë e draftit.

4. **PËRSHTATUR, JO KOPJUAR:**
   - Shembulli është MODEL — jo tekst i gatshëm nga ndonjë burim tjetër.
   - MOS kopjo tekst verbatim nga [NENE] ose [CHECKLIST].
   - NËSE nuk mund të krijosh shembull specifik → shkruaj "Shembull: [Nuk aplikueshëm për këtë draft]" dhe vazhdo.

5. **ASNJË SHPIKJE:** Nuk shpik fakte, nene, ose referenca që nuk shfaqen në draft ose [NENE].

6. **NË SHQIP:** Edhe kur citon ligj, përdor emërtimin shqip.

SHEMBUJ TË SAKTË (i mirë vs i dobët):

✅ SHEMBULL I MIRË:
**[#K1]** Shto referencën e nenit për alimentacionin
- **Ku:** Seksioni II.B, paragrafi 3
- **Pse:** Kërkesa për rritje të alimentacionit mbetet pa bazë ligjore.
- **Si:** Cito nenin që përcakton proporcionalitetin e alimentacionit.
- **Shembull:** "Në mbështetje të Nenit 330 të Ligjit për Familjen (2004/32), detyrimi për alimentacion përcaktohet në proporcion me mjetet e paditurit dhe nevojat e fëmijës."

❌ SHEMBULL I DOBËT (MOS e bëj):
**[#K1]** Shto nene
- **Ku:** Diku
- **Pse:** Nuk ka baza ligjore
- **Si:** Shto ligjin
- **Shembull:** "Duhet të shtosh nenet përkatëse të ligjit." ← SHUMË ABSTRAKT

🛑 RREGULLA PËR SEKSIONIN 5:
- NUK shto seksion "Rendi i prioriteteve" ose listë të ngjashme.
- Prioriteti tregohet VETËM nga emri i seksionit (KRITIKE / TË RËNDËSISHME / OPSIONALE).
- Çdo rekomandim me referencë konkrete në draft.
- NUK LEJOHET rekomandim i përgjithshëm pa bazë.
- Prioriteti KRITIKE rezervohet vetëm për probleme që pengojnë dorëzimin.
""" + DEDUP_RULE,
    },

    "readiness": {
        "title": "6. GATISHMËRIA",
        "max_tokens": 1600,
        "needs": ["draft", "checklist"],
        "prompt": """Ti je "Partner i Lartë" që jep verdiktin final.

⚠️ KY ËSHTË VERIFIKIM DRAFTI — JO audit i fashikullit.
Konteksti: drafti + lloji + checklist.

⚠️ MOS shkruaj titullin kryesor. Fillo DIREKT me "### A. ...".

🛑 RREGULL ABSOLUT PËR GJUHËN:
- Përdor EKSKLUZIVISHT termat SHQIP.
- NUK LEJOHET të shkruash "READY", "NEEDS WORK", "INCOMPLETE", "UNKNOWN" në asnjë pjesë të tekstit.

MISIONI: Jep një vlerësim të qartë të gatishmërisë së draftit.

STRUKTURA E DETYRUAR:

### A. Vlerësimi
Zgjidh SAKTËSISHT NJË nga tri nivelet (shkronja kapitale):

**GATI** — Gati për dorëzim, pa ndryshime kritike
**KËRKON PUNË** — Ka nevojë për përmirësime, por baza është e shëndoshë
**I PËRPLOTË** — Mungon baza formale ose ligjore; nuk mund të dorëzohet

### B. Arsyetimi
3-5 pika që justifikojnë vlerësimin.
Format: "* [pika] — [shpjegim]"

### C. Kushtet për ngritjen e nivelit
Nëse vlerësimi NUK është **GATI**:
- Çfarë duhet bërë për të arritur **GATI**
- Sa kohë merr (vlerësim realist)

### D. Statusi i përgjithshëm
Përmbledhje 2-3 rreshta.

RREGULLA:
- **GATI** rezervohet vetëm nëse:
  * Plotësia formale >= 90%
  * Nuk ka nene problematike
  * Nuk ka dobësi kritike
- **KËRKON PUNË** nëse: 60-89% plotësi ose dobësi të përmirësueshme
- **I PËRPLOTË** nëse: < 60% plotësi ose mungesë e bazës ligjore
""" + DEDUP_RULE,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _truncate_draft(doc_text: str, max_chars: int = DEFAULT_MAX_DRAFT_CHARS) -> str:
    """
    V1.10: Truncon draftin nëse kalon max_chars.

    Komportament:
      - Nëse len(doc_text) <= max_chars → kthen tekstin e plotë.
      - Nëse kalon → kthen HEAD (45000) + marker + TAIL (10000) = ~55000 chars.

    Parametri `max_chars` shërben VETËM si prag (threshold) për të vendosur
    nëse truncohet. Madhësia e output-it nuk varet nga `max_chars`, por nga
    konstantet DRAFT_HEAD_CHARS dhe DRAFT_TAIL_CHARS.
    """
    if not doc_text:
        return ""
    if len(doc_text) <= max_chars:
        return doc_text

    head = doc_text[:DRAFT_HEAD_CHARS]
    tail = doc_text[-DRAFT_TAIL_CHARS:]
    omitted = len(doc_text) - DRAFT_HEAD_CHARS - DRAFT_TAIL_CHARS
    return (
        head
        + f"\n\n[...{omitted} karaktere të hequra për gjatësi — kontrollo fundin e draftit...]\n\n"
        + tail
    )


def _block_draft_header(doc_type: str, file_name: str) -> List[str]:
    label = VERIFY_DOC_TYPES.get(doc_type, "Dokument")
    return [
        "=" * 70,
        f"VERIFIKIM DRAFTI — LLOJI: {label}",
        f"FILE: {file_name}",
        "=" * 70,
        "",
        "ℹ️ KY ËSHTË VERIFIKIM I DRAFTIT — JO audit i fashikullit.",
        "Nuk ka kontekst rasti. Vetëm drafti + lloji + precedentët realë.",
        "",
    ]


def _block_draft_text(doc_text: str) -> List[str]:
    if not doc_text or not doc_text.strip():
        return [
            "=" * 70,
            "[DRAFT] TEKSTI I DRAFTIT",
            "=" * 70,
            "",
            "⚠️ Drafti është bosh ose i palexueshëm.",
            "",
        ]

    truncated = _truncate_draft(doc_text)
    was_truncated = len(doc_text) > DEFAULT_MAX_DRAFT_CHARS

    header_lines = [
        "=" * 70,
        f"[DRAFT] TEKSTI I PLOTË I DRAFTIT ({len(truncated)} chars"
        + (f", i truncuar nga {len(doc_text)})" if was_truncated else ")"),
        "=" * 70,
        "",
    ]

    if was_truncated:
        header_lines.extend([
            "⚠️ DRAFT I GJATË — u ruajt koka (45K chars) + fundi (10K chars).",
            "   Kontrollo ME KUJDES të dyja pjesët para se të deklarosh mungesa.",
            "",
        ])

    return header_lines + [truncated, ""]


def _block_checklist(doc_type: str) -> List[str]:
    checklist = DOC_TYPE_CHECKLISTS.get(doc_type)
    if not checklist:
        return [
            "=" * 70,
            "[CHECKLIST] PJESËT E DETYRUESHME",
            "=" * 70,
            "",
            "⚠️ Nuk ka checklist specifik për këtë lloj dokumenti.",
            "",
        ]

    lines: List[str] = [
        "=" * 70,
        f"[CHECKLIST] PJESËT E DETYRUESHME PËR: {checklist['label']}",
        "=" * 70,
        "",
    ]

    for i, part in enumerate(checklist["required_parts"], 1):
        lines.append(f"  {i}. {part}")

    lines.append("")
    return lines


def _block_cited_articles(
    verification_report: Optional[Dict[str, Any]],
) -> List[str]:
    if not verification_report:
        return [
            "=" * 70,
            "[NENE] NENET E CITUARA NË DRAFT",
            "=" * 70,
            "",
            "⚠️ Nuk ka verifikim të neneve (baza ligjore e paaksesueshme).",
            "",
        ]

    articles = verification_report.get("articles", [])
    if not articles:
        return [
            "=" * 70,
            "[NENE] NENET E CITUARA NË DRAFT",
            "=" * 70,
            "",
            "Nuk u identifikuan nene të cituara në draft.",
            "",
        ]

    lines: List[str] = [
        "=" * 70,
        f"[NENE] NENET E CITUARA ({len(articles)})",
        "=" * 70,
        "",
        "🛑 RREGULL ABSOLUT PËR ATRIBIMIN E LIGJIT:",
        "   * 'Ligji i cituar' POSHTË është i vetmi që mund të atribuohet nenit.",
        "   * NËSE 'Ligji i cituar: -' / bosh → SHKRUAJ 'NUK U VERIFIKUA'.",
        "   * KURRË mos zëvendëso ligjin e cituar me një ligj tjetër në draft.",
        "",
    ]

    for a in articles:
        status = "[OK] EKZISTON" if a.get("exists") else "[X] NUK U GJET"
        law_hint = a.get("law_hint", "") or "-"
        para = f" par. {a['paragraph']}" if a.get("paragraph") else ""
        lines.append(f"* Neni {a.get('article_number', '?')}{para}")
        lines.append(f"  Ligji i cituar: {law_hint}")
        lines.append(f"  Statusi: {status}")
        if a.get("match_reason"):
            lines.append(f"  Arsyeja: {a['match_reason']}")
        if a.get("exists") and a.get("matched_doc"):
            doc = a["matched_doc"]
            lines.append(f"  Ligji në bazë: {doc.get('law_title', '-')}")

        if a.get("alternative_laws"):
            alts = a["alternative_laws"]
            if alts and isinstance(alts[0], dict):
                lines.append(f"  → Ekziston në ligje të tjera:")
                for alt in alts[:5]:
                    lines.append(f"     - {alt.get('law_title', '')[:100]}")
            elif alts and isinstance(alts[0], str):
                lines.append(f"  → Ekziston në ligje të tjera:")
                for alt in alts[:5]:
                    lines.append(f"     - {alt[:100]}")

        # V1.10: [:MAX_CONTEXT_CHARS] = 300 (sinkron me extractor)
        if a.get("context"):
            lines.append(f"  Cituar në draft: {a['context'][:MAX_CONTEXT_CHARS]}")
        lines.append("")

    return lines


def _block_precedents(
    precedents: Optional[List[Dict[str, Any]]],
) -> List[str]:
    lines: List[str] = [
        "=" * 70,
        "[PRECEDENTE] REZULTATET NGA BAZA E GJYKATËS SUPREME",
        "=" * 70,
        "",
    ]

    if not precedents:
        lines.extend([
            "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme për këtë çështje.",
            "",
            "⚠️ SHKRUAJ SAKTËSISHT KËTË FRAZË në raport. MOS shpik precedentë.",
            "",
        ])
        return lines

    filtered = []
    excluded = []
    for p in precedents:
        sim = p.get("similarity")
        try:
            sim_f = float(sim) if sim is not None else 0.0
        except (TypeError, ValueError):
            sim_f = 0.0
        if sim_f >= MIN_PRECEDENT_SIMILARITY:
            filtered.append(p)
        else:
            excluded.append((p.get("case_number", "?"), sim_f))

    if excluded:
        lines.append(
            f"⚠️ U FILTRUAN {len(excluded)} precedentë me similarity < "
            f"{MIN_PRECEDENT_SIMILARITY:.2f}:"
        )
        for cn, sim in excluded[:5]:
            lines.append(f"     - [{cn}] similarity={sim:.2f} (i përjashtuar)")
        lines.append("")

    if not filtered:
        lines.extend([
            "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme për këtë çështje.",
            "",
            "⚠️ SHKRUAJ SAKTËSISHT KËTË FRAZË në raport. MOS shpik precedentë.",
            "",
        ])
        return lines

    lines.append(f"Total: {len(filtered)} precedentë relevantë të verifikuar.")
    lines.append("")

    for i, p in enumerate(filtered, 1):
        cn = str(p.get("case_number", "?")).strip()
        sim = p.get("similarity", 0.0) or 0.0
        excerpt = (p.get("text_excerpt") or "").strip()
        source = p.get("source", "?")
        page = p.get("page", "?")
        topic = p.get("topic_label")
        rerank = p.get("rerank_score")

        lines.append(f"  {i}. [{cn}] — similarity={sim:.2f}")
        if rerank is not None:
            lines.append(f"     Rerank score: {rerank:.2f}")
        if topic:
            lines.append(f"     Tema: {topic}")
        if excerpt:
            lines.append(f'     Fragment: "{excerpt[:400]}"')
        lines.append(f"     Burimi: {source}, faqe {page}")
        lines.append("")

    lines.append("⚠️ RREGULL: Paraqit VETËM këta precedentë. NUK LEJOHET të shpikësh asnjë.")
    lines.append("")
    return lines


def build_verify_context(
    doc_type: str,
    doc_text: str,
    file_name: str,
    section_key: str,
    precedents: Optional[List[Dict[str, Any]]] = None,
    verification_report: Optional[Dict[str, Any]] = None,
) -> str:
    section_cfg = VERIFY_SECTION_PROMPTS.get(section_key)
    needs: List[str] = cfg.get("needs", []) if (cfg := section_cfg) else []

    lines: List[str] = []

    lines.extend(_block_draft_header(doc_type, file_name))

    if "draft" in needs:
        lines.extend(_block_draft_text(doc_text))

    if "checklist" in needs:
        lines.extend(_block_checklist(doc_type))

    if "articles" in needs:
        lines.extend(_block_cited_articles(verification_report))

    if "precedents" in needs:
        lines.extend(_block_precedents(precedents))

    return "\n".join(lines).strip()


def get_verify_section_keys() -> List[str]:
    return list(VERIFY_SECTION_KEYS)


def get_verify_doc_types() -> Dict[str, str]:
    return dict(VERIFY_DOC_TYPES)


def get_checklist(doc_type: str) -> Optional[Dict[str, Any]]:
    return DOC_TYPE_CHECKLISTS.get(doc_type)


def _cli_test():
    print("=" * 70)
    print("VERIFY PROMPTS V1.10 — DIAGNOSTIKË")
    print("=" * 70)

    print(f"\nLlojet e dokumenteve ({len(VERIFY_DOC_TYPES)}):")
    for k, v in VERIFY_DOC_TYPES.items():
        n = len(DOC_TYPE_CHECKLISTS.get(k, {}).get("required_parts", []))
        print(f"  - {k:22s} → {v} ({n} pika)")

    print(f"\nSeksionet ({len(VERIFY_SECTION_KEYS)}):")
    for k in VERIFY_SECTION_KEYS:
        cfg = VERIFY_SECTION_PROMPTS[k]
        needs = cfg.get("needs", [])
        print(f"  - {k:25s} max_tokens={cfg.get('max_tokens')} needs={needs}")

    print(f"\nV1.10 Konstante:")
    print(f"  - DEFAULT_MAX_DRAFT_CHARS: {DEFAULT_MAX_DRAFT_CHARS}")
    print(f"  - MIN_PRECEDENT_SIMILARITY: {MIN_PRECEDENT_SIMILARITY}")
    print(f"  - MAX_CONTEXT_CHARS (nga constants): {MAX_CONTEXT_CHARS}")


if __name__ == "__main__":
    _cli_test()