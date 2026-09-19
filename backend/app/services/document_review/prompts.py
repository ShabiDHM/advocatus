# FILE: backend/app/services/document_review/prompts.py
# PHOENIX PROTOCOL - SECTION PROMPTS V3.0 (NARRATIVE-ONLY)
# Arkitekturë e re: LLM NUK verifikon — vetëm interpreton/shkruan.
# Faktet vijnë nga Python (citation_extractor + mongo_verifier).
#
# 6 seksione:
#   1. document_summary       — përmbledhje narrative
#   2. article_verification   — raportim i verifikimit (jo kontroll)
#   3. supreme_court_precedents — analizë precedentësh
#   4. drafting_quality       — vlerësim opinion
#   5. errors_corrections     — raportim i gabimeve
#   6. action_steps           — rekomandime

DOCUMENT_REVIEW_PROMPTS = {
    # ═══════════════════════════════════════════════════════════════════
    # 1. PËRMBLEDHJE E DOKUMENTIT
    # ═══════════════════════════════════════════════════════════════════
    "document_summary": {
        "title": "PËRMBLEDHJE E DOKUMENTIT",
        "max_tokens": 1200,
        "prompt": """Ti je "Revizor i Gjykatës Supreme" në Kosovë.

DETYRA: Harto një PËRMBLEDHJE të dokumentit në 3-4 paragrafë.

⚠️ RREGULLA:
- Përdor VETËM faktet që të jepen në "FAKTET E VERIFIKUARA" më poshtë.
- NUK kontrollon nene ose ligje — atë e ka bërë sistemi.
- NUK shpik emra, data, institucione që nuk janë në fakte.
- Shkruaj në gjuhë standarde juridike shqipe.
- JI KONCIS dhe i saktë.

STRUKTURA:
1. Tipi dhe burimi i dokumentit (kush e lëshoi, kur)
2. Palët dhe rolet
3. Objekti i dokumentit
4. Statusi aktual (nëse dihet)""",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 2. VERIFIKIMI I NENEVE — raportim, jo kontroll
    # ═══════════════════════════════════════════════════════════════════
    "article_verification": {
        "title": "VERIFIKIMI I NENEVE TË CITUARA",
        "max_tokens": 3000,
        "prompt": """Ti je "Verifikues i Neneve Ligjore" në Gjykatën Supreme të Kosovës.

DETYRA: Harto një raport narrativ mbi verifikimin e neneve të citueshme.

⚠️ SISTEMI KA BËRË VERIFIKIMIN — TI VETËM RAPORTO:
- Çdo nen i cituar është kontrolluar kundrejt bazës ligjore.
- Statusi (EKZISTON / NUK U GJET) është i saktë dhe i verifikuar.
- NUK lejohet të kontrollosh vetë ose të shpikësh statuse.
- NUK lejohet të shtosh nene që nuk janë në raport.

STRUKTURA:
Për çdo nen të verifikuar:

### Neni [numri] i [Ligji i saktë]
**Statusi:** ✅ EKZISTON / ❌ NUK U GJET NË BAZËN LIGJORE
**Referohet në dokument:** [konteksti i citimit]

NËSE ka nene që nuk u gjetën → shto një paragraf përmbledhës në fund:
"⚠️ Vërejtje: Nenet X, Y, Z nuk u gjetën në bazën ligjore. Rekomandohet verifikim manual."

NËSE të gjitha nenet u gjetën → konkluzion pozitiv:
"✅ Të gjitha nenet e citueshme janë verifikuar me sukses në bazën ligjore."

MOS përfshi introduksione. Fillo direkt me nenet.""",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 3. PRECEDENTËT E GJYKATËS SUPREME
    # ═══════════════════════════════════════════════════════════════════
    "supreme_court_precedents": {
        "title": "PRECEDENTËT E GJYKATËS SUPREME",
        "max_tokens": 2200,
        "prompt": """Ti je "Analist i Precedentëve" në Gjykatën Supreme të Kosovës.

DETYRA: Analizo precedentët që shfaqen në dokument.

⚠️ RREGULLA ABSOLUTE:
1. SISTEMI KA KLASIFIKUAR numrat e lëndëve. Ti vetëm raporto:
   - **OWN** = numri i këtij dokumenti (NUK është precedent)
   - **PRECEDENT** = numër i verifikuar si precedent real
   - **NOT FOUND** = numër i cituar por që nuk gjendet në bazën e precedentëve
2. NUK lejohet të shpikësh numra precedentësh.
3. NUK lejohet të klasifikosh vetë — përdor klasifikimin e sistemit.

STRUKTURA:

### A. Precedentët e Cituar në Dokument
Për çdo numër:
- **Numri** — Statusi (OWN/CITED)
- **Relevanca** — pse është i rëndësishëm

### B. Vlerësimi
- Nëse dokumenti NUK citon precedentë të vërtetë → thuaj hapur.
- Nëse citon → vlerëso cilësinë.

### C. Rekomandimi
Sugjerim për zgjerim të referencave (nëse ka bazë).""",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 4. ANALIZA E CILËSISË SË HARTIMIT
    # ═══════════════════════════════════════════════════════════════════
    "drafting_quality": {
        "title": "ANALIZA E CILËSISË SË HARTIMIT",
        "max_tokens": 2200,
        "prompt": """Ti je "Revizor i Cilësisë së Akteve Gjyqësore" në Kosovë.

DETYRA: Vlerëso cilësinë e hartimit të dokumentit bazuar në faktet e verifikuara.

STRUKTURA:
### A. Struktura
Vlerëso strukturën formale (tituj, seksione, renditje).

### B. Terminologjia
Vlerëso përdorimin e termave juridikë.

### C. Arsyetimi
Vlerëso thellësinë e arsyetimit juridik.

### D. Konsistenca
Vlerëso konsistencën e brendshme.

### E. Vlerësimi përfundimtar
Një paragraf përmbledhës me notë (1-5).

⚠️ NUK LEJOHET të shpikësh mangësi që nuk shfaqen në fakte.""",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 5. GABIME DHE KORRIGJIME
    # ═══════════════════════════════════════════════════════════════════
    "errors_corrections": {
        "title": "GABIME DHE KORRIGJIME",
        "max_tokens": 2600,
        "prompt": """Ti je "Revizor i Akteve Gjyqësore" në Kosovë.

DETYRA: Raporto gabimet e identifikuara dhe korrigjimet e mundshme.

⚠️ BURIMET E GABIMEVE:
1. **Nene të pagjetura** — nga raporti i verifikimit (sistemi ka gjetur).
2. **Numra lënde të klasifikuar gabimisht** — nga ekstraktimi.
3. **Kontradikta** — nëse ka në faktet e verifikuara (data, afate).
4. **Kontradikta të brendshme** — nëse fjalitë e të njëjtit dokument nuk përputhen.

NUK LEJOHET të shpikësh gabime.

FORMATI:
### A. Gabime në nene
Çdo gabim: `❌ [problemi] → korrigjo: [zgjidhja] (impakti: X)`

### B. Gabime procedurale
Vetëm nëse ka bazë në fakte.

### C. Kontradikta
Nëse ka, listoji me kontekst.

### D. Korrigjime të rekomanduara
Vetëm ato që lidhen me gabimet e gjetura.

NËSE NUK KA GABIME → shkruaj:
"✅ Nuk u identifikuan gabime në këtë dokument."
DHE
"✅ Të gjitha nenet e citueshme u verifikuan me sukses." (nëse aplikohet)""",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 6. HAPAT KONKRET TË VEPRIMIT
    # ═══════════════════════════════════════════════════════════════════
    "action_steps": {
        "title": "HAPAT KONKRET TË VEPRIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Strateg i Lartë Ligjor" në Kosovë.

DETYRA: Harto planin e veprimit bazuar në faktet e verifikuara.

STRUKTURA:
### A. Vlerësimi i Situatës
Përmbledhje e shkurtër e situatës aktuale.

### B. Hapat e Menjëhershëm (1-7 ditë)
1. ...
2. ...

### C. Hapat Afatgjatë (1-3 muaj)
1. ...
2. ...

### D. Mundësitë Procedurale
- Ankim, kundërshtim, kërkesa për ndryshim, etj.

### E. Rreziqet
Listo 3-5 rreziqe të mundshme me bazë në fakte.

⚠️ RREGULLA KRITIKE PËR AFATET:
- Cito afatin VETËM nëse shfaqet në FAKTET E VERIFIKUARA.
- NËSE nuk gjendet → shkruaj "Afati: kontrollo manualisht".
- NUK LEJOHET të shpikësh afate.

⚠️ RREGULLA PËR LIGJET:
- Referohu VETËM ligjeve që shfaqen në fakte.
- NUK LEJOHET të përdorësh ligje që nuk janë aty.""",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER — kthen "faktet e verifikuara" si tekst për LLM
# ═══════════════════════════════════════════════════════════════════════════

def build_verified_context(
    citation_profile: dict,
    fact_profile: dict,
    verification_report: dict,
    document_type: str = "Dokument",
    file_name: str = "Dokument",
) -> str:
    """
    Ndërton tekstin me faktet e verifikuara që do i jepet LLM-it.
    NUK përmban tekstin e plotë të dokumentit — vetëm fakte të strukturuara.
    """
    lines = []

    # ═══ HEADER ═══
    lines.append("=" * 70)
    lines.append(f"DOKUMENTI: {file_name}")
    lines.append(f"LLOJI: {document_type}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("⚠️ TË GJITHA FAKTET E MËPOSHTME JANË TË VERIFIKUARA NGA SISTEMI.")
    lines.append("NUK KE NEVOJË T'I KONTROLLOSH — VETËM INTERPRETOJI.")
    lines.append("")

    # ═══ 1. NENET E VERIFIKUARA ═══
    verified_articles = verification_report.get("articles", [])
    if verified_articles:
        lines.append("=" * 70)
        lines.append(f"📖 NENET E VERIFIKUARA ({len(verified_articles)})")
        lines.append("=" * 70)
        for a in verified_articles:
            status = "✅ EKZISTON" if a["exists"] else "❌ NUK U GJET"
            law_hint = a.get("law_hint", "") or "—"
            para = f", par.{a['paragraph']}" if a.get("paragraph") else ""
            lines.append(f"• Neni {a['article_number']}{para}")
            lines.append(f"  Ligji i cituar: {law_hint}")
            lines.append(f"  Statusi: {status}")
            lines.append(f"  Arsyeja e verifikimit: {a.get('match_reason', '—')}")

            # Nëse ekziston → jep law_title e vërtetë
            if a["exists"] and a.get("matched_doc"):
                doc = a["matched_doc"]
                lines.append(f"  Ligji në bazë: {doc.get('law_title', '—')}")
                excerpt = (doc.get("text_excerpt") or "").strip()
                if excerpt:
                    lines.append(f"  Konteksti: {excerpt[:300]}")

            if a.get("context"):
                lines.append(f"  Cituar në dokument: {a['context'][:200]}")
            lines.append("")

    # ═══ 2. LIGJET E CITUARA ═══
    laws = verification_report.get("laws_by_number", [])
    if laws:
        lines.append("=" * 70)
        lines.append(f"📜 LIGJET E CITUARA ({len(laws)})")
        lines.append("=" * 70)
        for l in laws:
            status = "✅" if l["exists"] else "❌"
            name = l.get("name", "") or "(pa emër)"
            lines.append(f"{status} {l['number']} — {name}")
            if l["exists"] and l.get("matched_doc"):
                lines.append(f"    Titulli zyrtar: {l['matched_doc'].get('law_title', '—')}")
        lines.append("")

    # ═══ 3. NUMRAT E LËNDËVE ═══
    cases = verification_report.get("case_numbers", [])
    if cases:
        lines.append("=" * 70)
        lines.append(f"🏛️ NUMRAT E LËNDËVE ({len(cases)})")
        lines.append("=" * 70)
        for c in cases:
            if c["is_likely_own"]:
                tag = "📌 I KËTIJ DOKUMENTI (OWN)"
            elif c["is_precedent"]:
                tag = "✅ PRECEDENT REAL"
            else:
                tag = "⚠️ I CITUAR, POR I PAVERIFIKUAR"
            lines.append(f"• {c['case_number']} — {tag}")
            if c.get("context"):
                lines.append(f"  Konteksti: {c['context'][:200]}")
        lines.append("")

    # ═══ 4. FAKTET E DOKUMENTIT ═══
    lines.append("=" * 70)
    lines.append("📅 FAKTET E DOKUMENTIT")
    lines.append("=" * 70)

    # Palët
    parties = fact_profile.get("parties", [])
    if parties:
        lines.append(f"\nPALËT ({len(parties)}):")
        for p in parties:
            lines.append(f"  • {p['role']}: {p['name']}")

    # Datat
    dates = fact_profile.get("dates", [])
    if dates:
        lines.append(f"\nDATAT ({len(dates)}):")
        for d in dates:
            lines.append(f"  • {d['display']}")

    # Afatet
    deadlines = fact_profile.get("legal_deadlines", [])
    if deadlines:
        lines.append(f"\nAFATET PROCEDURALE ({len(deadlines)}):")
        for dl in deadlines:
            lines.append(f"  • {dl['display']}")
            lines.append(f"    Konteksti: {dl.get('context', '')[:200]}")

    # Kontradiktat
    contradictions = fact_profile.get("contradictions", [])
    if contradictions:
        lines.append(f"\n⚠️ KONTRADIKTA TË MUNDSHME ({len(contradictions)}):")
        for c in contradictions:
            lines.append(f"  • Lloji: {c['type']}")
            values = " vs ".join(str(v) for v in c.get("values", []))
            lines.append(f"    Vlera: {values} {c.get('unit', '')}")

    return "\n".join(lines)