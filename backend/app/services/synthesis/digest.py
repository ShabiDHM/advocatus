# FILE: backend/app/services/synthesis/digest.py
# PHOENIX PROTOCOL - DIGEST BUILDER V1.4
# V1.4: PRECEDENTE TE VERTETA - shtuar precedents= param + _append_precedents_block().
#       Blloku "🏛️ PRECEDENTE RELEVANTE" shfaqet kur precedent_search kthen
#       rezultate. Blloku perfshin case_number, fragment, source, page,
#       topic_label, rerank_score. Ripërdorueshëm me document_review.
# V1.3: Shtuar bllok "📅 AFATET ME BURIME" — çdo afat me dokumentin burimor.
# V1.2: Hequr client_position nga KLIENTI block. Dedup i emrave me parenthetical.
#       Filtrim i noise: heq rolet e atribuuara gabimisht fëmijëve.
# V1.1: Shtuar bllok KLIENTI + PALËT ME ROLE nga metadata.parties.
# V1.0: Ekstraktuar nga synthesis_service.py V3.8.

import re
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from .constants import MAX_DIGEST_CHARS


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC — build digest
# ═══════════════════════════════════════════════════════════════════════════

def build_digest(
    case: Dict[str, Any],
    extractions: List[Dict[str, Any]],
    xrefs: Dict[str, Any],
    defendants_groups: List[Dict[str, Any]],
    articles_by_law: Dict[str, Dict[str, str]],
    case_type: Optional[str] = None,
    verified_citations: Optional[Dict[str, Any]] = None,
    precedents: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    V1.4: Nderton digest-in per Synthesis.
    Args:
        precedents: V1.4 - liste me precedente te vertete (nga precedent_search).
                    Perdoret per bllokun "🏛️ PRECEDENTE RELEVANTE".
    """
    lines: List[str] = []

    lines.append("=" * 70)
    lines.append("TË DHËNAT E LËNDËS")
    lines.append("=" * 70)
    lines.append(f"Titulli: {case.get('title') or case.get('case_name') or 'N/A'}")
    lines.append(f"Numri i dokumenteve: {len(extractions)}")
    lines.append("")

    # V1.2: KLIENTI pa client_position
    _append_client_block(lines, case)

    if verified_citations:
        _append_verified_citations(lines, verified_citations)

    if case_type:
        lines.append("=" * 70)
        lines.append("🎯 LLOJI I LËNDËS")
        lines.append("=" * 70)
        lines.append(f"**{case_type}**")
        if "→" in case_type:
            lines.append(
                "Ky është një rast i DYFISHTË që ka evoluar nga "
                "procedura civile (urdhër mbrojtjeje) në procedurë penale."
            )
        lines.append("")

    primary_doc = find_primary_document(extractions)
    if primary_doc:
        lines.append("=" * 70)
        lines.append(f"📄 DOKUMENTI KRYESOR: {primary_doc.get('file_name', 'N/A')}")
        lines.append("=" * 70)
        lines.append("")

    lines.append("=" * 70)
    lines.append("INDEKSI I DOKUMENTEVE")
    lines.append("=" * 70)
    for i, ext in enumerate(extractions, 1):
        marker = " ⭐ [KRYESOR]" if ext is primary_doc else ""
        lines.append(
            f"{i}. {ext.get('file_name', 'N/A')} "
            f"[{ext.get('document_type', 'N/A')}] "
            f"({ext.get('text_length', 0):,} chars){marker}"
        )
    lines.append("")

    # V1.2: PARTIES ME ROLE (dedup + filter children)
    _append_parties_with_roles(lines, extractions, defendants_groups)

    # V1.3: AFATET ME BURIME — parandalon atribuimin e gabuar
    _append_deadlines_with_sources(lines, extractions)

    if defendants_groups:
        _append_defendants_groups(lines, defendants_groups)

    if articles_by_law:
        _append_articles_by_law(lines, articles_by_law)

    sc_decisions = extract_supreme_court_decisions(extractions)
    if sc_decisions:
        lines.append("=" * 70)
        lines.append("🏛️ AKTGJYKIMET E GJYKATËS SUPREME")
        lines.append("=" * 70)
        for d in sc_decisions:
            lines.append(f"  • {d}")
        lines.append("")

    # ═══════════════════════════════════════════════════════════════════════
    # V1.4: PRECEDENTE TE VERTETA NGA BAZA E GJYKATES SUPREME
    # ═══════════════════════════════════════════════════════════════════════
    _append_precedents_block(lines, precedents)

    if xrefs:
        _append_cross_references(lines, xrefs)

    digest = "\n".join(lines)

    if len(digest) > MAX_DIGEST_CHARS:
        digest = digest[:MAX_DIGEST_CHARS] + "\n\n[...digest truncated...]"

    return digest


# ═══════════════════════════════════════════════════════════════════════════
# V1.4: PRECEDENTS BLOCK (i re)
# ═══════════════════════════════════════════════════════════════════════════

def _append_precedents_block(
    lines: List[str],
    precedents: Optional[List[Dict[str, Any]]],
) -> None:
    """
    V1.4: Blloku "🏛️ PRECEDENTE RELEVANTE" me precedentet e vertete.

    Nese lista eshte bosh ose None -> NUK shton asnje bllok.
    (LLM do te shkruaje fraze standarde ne legal_framework kur te mos kete
    precedentë — sipas prompt-it V1.5.)
    """
    if not precedents:
        return

    lines.append("=" * 70)
    lines.append("🏛️ PRECEDENTE RELEVANTE (nga baza e Gjykatës Supreme)")
    lines.append("=" * 70)
    lines.append(
        f"Total: {len(precedents)} precedentë të verifikuar në bazën zyrtare."
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
        "⚠️ Përdore këtë bllok në seksionin 'KUADRI LIGJOR DHE NENET' → "
        "nën-seksionin 'Jurisprudenca'."
    )
    lines.append(
        "⚠️ Para se të shkruash 'Rëndësia' për një precedent, kontrollo nëse "
        "ka lidhje TË DREJTPËRDREJTË me temën e lëndës. Nëse JO → shkruaj "
        "'Nuk ka lidhje të drejtpërdrejtë me këtë lëndë.' PA spekullim."
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
        "⚠️ RREGULL: Paraqit VETËM këta precedentë në raport. "
        "NUK LEJOHET të shpikësh asnjë tjetër."
    )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: HELPERS — name normalization + child detection
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_name_key(name: str) -> str:
    """
    V1.2: Normalizo emrin për dedupe.
    "Sanije (Azem) Bala" → "sanije bala"
    "Sanije Bala" → "sanije bala"
    """
    if not name:
        return ""
    n = re.sub(r'\([^)]*\)', '', name)          # Heq (Azem)
    n = re.sub(r'[.,;:"]', '', n)
    n = " ".join(n.split()).strip().lower()
    return n


def _extract_child_names(extractions: List[Dict[str, Any]]) -> Set[str]:
    """
    V1.2: Nxjerr emrat e fëmijëve nga rolet 'Fëmijët' / 'Fëmijë'.
    Kthen set me emra individualë (lowercase): {"andi", "elda", "elsa"}
    """
    child_tokens: Set[str] = set()
    for ext in extractions:
        meta = ext.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        for p in meta.get("parties", []) or []:
            if not isinstance(p, dict):
                continue
            role = (p.get("role") or "").lower()
            name = (p.get("name") or "").strip()
            if "fëmijë" in role or "femije" in role or "fëmij" in role:
                # Split "Elda dhe Andi" → ["elda", "andi"]
                parts = re.split(r'\s+(?:dhe|e|dhe\/ose|,)\s+', name, flags=re.IGNORECASE)
                for part in parts:
                    part = part.strip(" .,;:")
                    # Vetëm emri i parë (për të shmangur "dhe andi")
                    first_word = part.split()[0] if part.split() else ""
                    if len(first_word) >= 3:
                        child_tokens.add(first_word.lower())
    return child_tokens


def _is_child_name(display_name: str, child_names: Set[str]) -> bool:
    """Kontrollo nëse emri përputhet me fëmijë."""
    first_word = display_name.strip().split()[0].lower() if display_name.strip() else ""
    return first_word in child_names


# ═══════════════════════════════════════════════════════════════════════════
# V1.3: DEADLINES WITH SOURCES
# ═══════════════════════════════════════════════════════════════════════════

# Pattern: "X ditë" / "X muaj" / "X vjet" — për nxjerrjen e afateve
_DEADLINE_UNIT_PATTERN = re.compile(
    r'\b(\d{1,3})\s*(dit[ëe]|muaj|vjet|or[ëe]|jav[ëe])\b',
    re.IGNORECASE,
)

# Fjalë kyçe që tregojnë se është afat (jo kohëzgjatje e ngjarjes)
_DEADLINE_KEYWORDS = re.compile(
    r'\b(afat|afati|ankim|ankesa|kundërshtim|kundërshtimi|gjyq|'
    r'paraqitje|paraqitja|dorëzim|dorëzimi|apel|apeli|'
    r'afatligjor|brenda)\b',
    re.IGNORECASE,
)


def _extract_deadlines_from_extractions(
    extractions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V1.3: Nxjerr afatet nga metadata.deadlines ose legal_deadlines.
    Kthen listë me dict: {display, context, source_document}.
    Dedup sipas (value, source_document).
    """
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for ext in extractions:
        file_name = ext.get("file_name") or "?"
        meta = ext.get("metadata") or {}
        if not isinstance(meta, dict):
            continue

        # Burimet e mundshme të afateve
        deadline_lists = []
        for key in ("legal_deadlines", "deadlines", "afatet", "afate"):
            if isinstance(meta.get(key), list):
                deadline_lists.append(meta.get(key))

        for dlist in deadline_lists:
            for d in dlist:
                if not isinstance(d, dict):
                    continue
                display = (
                    d.get("display")
                    or d.get("value")
                    or d.get("text")
                    or ""
                ).strip()
                if not display:
                    continue

                context = (d.get("context") or "").strip()
                key = f"{display.lower()}|{file_name.lower()}"
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    "display": display,
                    "context": context,
                    "source_document": file_name,
                })

    # Fallback: nëse skema e metadave nuk ka deadlines,
    # skano tekstin e secilit dokument për "X ditë/muaj/vjet" + "afat/ankim"
    if not results:
        for ext in extractions:
            text = ext.get("text") or ext.get("raw_text") or ""
            if not text or len(text) < 20:
                continue
            file_name = ext.get("file_name") or "?"
            # Ndaj në fjali të thjeshta
            sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
            for sent in sentences:
                sent = sent.strip()
                if not sent or len(sent) > 500:
                    continue
                if not _DEADLINE_KEYWORDS.search(sent):
                    continue
                for m in _DEADLINE_UNIT_PATTERN.finditer(sent):
                    num, unit = m.group(1), m.group(2).lower()
                    display = f"{num} {unit}"
                    key = f"{display.lower()}|{file_name.lower()}"
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "display": display,
                        "context": sent[:250],
                        "source_document": file_name,
                    })

    return results


def _append_deadlines_with_sources(
    lines: List[str],
    extractions: List[Dict[str, Any]],
) -> None:
    """
    V1.3: Shton bllokun me afatet + dokumentin burimor.
    """
    deadlines = _extract_deadlines_from_extractions(extractions)

    if not deadlines:
        return

    lines.append("=" * 70)
    lines.append(f"📅 AFATET E IDENTIFIKUARA ME BURIME ({len(deadlines)})")
    lines.append("=" * 70)
    lines.append(
        "⚠️ ÇDO afat i cituar në raport DUHET të ketë BURIMIN e saktë "
        "(emri i dokumentit ku shfaqet)."
    )
    lines.append(
        "⚠️ NËSE ka dy afate kontradiktore për të njëjtën çështje → "
        "listoji TË GJITHA me burime, shto shënimin "
        "'[KONTRADIKTË — verifiko manualisht]'."
    )
    lines.append(
        "⚠️ MOS i atribuo afatin një dokumenti që NUK e përmend atë."
    )
    lines.append("")

    # Grupim sipas burimit — më i lexueshëm
    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in deadlines:
        by_source[d["source_document"]].append(d)

    for source in sorted(by_source.keys()):
        items = by_source[source]
        for d in items:
            lines.append(f"  • {d['display']} — [{source}]")
            if d.get("context"):
                lines.append(f"      Konteksti: \"{d['context'][:200]}\"")
        lines.append("")

    # Nëse ka afate të njëjtë numerikisht nga burime të ndryshme → flago
    display_to_sources: Dict[str, Set[str]] = defaultdict(set)
    for d in deadlines:
        display_to_sources[d["display"].lower()].add(d["source_document"])

    multi_source = {
        disp: srcs for disp, srcs in display_to_sources.items() if len(srcs) > 1
    }
    if multi_source:
        lines.append("⚠️ AFATE TË NJËJTA NË BURIME TË NDRYSHME (konfirmo saktësinë):")
        for disp, srcs in multi_source.items():
            lines.append(f"  • '{disp}' shfaqet në: {sorted(srcs)}")
        lines.append("")

    lines.append(
        "⚠️ RREGULL: Në raport shkruaj 'Sipas [dokumenti X], afati është N ditë.' "
        "KURRË mos atribuo afatin dokumentit të gabuar."
    )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: CLIENT BLOCK (pa client_position)
# ═══════════════════════════════════════════════════════════════════════════

def _append_client_block(lines: List[str], case: Dict[str, Any]) -> None:
    """
    V1.2: Blloku i klientit — VETËM emri. Roli real merret nga PALËT ME ROLE.
    NUK shfaqim client_position sepse shpesh është i pasaktë.
    """
    client_name = (case.get("client_name") or "").strip()
    client = case.get("client") or {}
    if not client_name and isinstance(client, dict):
        client_name = (client.get("name") or "").strip()

    if not client_name:
        return

    lines.append("=" * 70)
    lines.append("🎯 KLIENTI I AVOKATIT")
    lines.append("=" * 70)
    lines.append(f"Emri: {client_name}")
    lines.append(
        "⚠️ Roli i saktë i klientit MERRET nga blloku "
        "'👥 PALËT NDËRGYQËSE ME ROLE' poshtë."
    )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: PARTIES WITH ROLES (dedup + child filter)
# ═══════════════════════════════════════════════════════════════════════════

def _append_parties_with_roles(
    lines: List[str],
    extractions: List[Dict[str, Any]],
    defendants_groups: List[Dict[str, Any]],
) -> None:
    """
    V1.2: Nxjerr palët ME ROLE nga metadata.parties.
    - Dedup: "Sanije (Azem) Bala" == "Sanije Bala"
    - Filter: heq rolet e gabuara të fëmijëve (Andi, Elda, Elsa)
    """
    defendant_names: Set[str] = set()
    for group in defendants_groups:
        for d in group.get("defendants", []):
            n = (d.get("name") or "").strip().lower()
            if n:
                defendant_names.add(n)

    child_names = _extract_child_names(extractions)

    # Mblidh roles + display per canonical key (i normalizuar)
    # canonical_key -> {"display": str, "roles": Set[str], "variants": [str]}
    merged: Dict[str, Dict[str, Any]] = {}

    for ext in extractions:
        meta = ext.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        for p in meta.get("parties", []) or []:
            if not isinstance(p, dict):
                continue
            name = (p.get("name") or "").strip()
            role = (p.get("role") or "").strip()

            if not name or name.lower() in ("null", "none", "n/a"):
                continue
            if len(name) < 3:
                continue

            # V1.2: Skip fëmijët
            if _is_child_name(name, child_names):
                continue

            # V1.2: Skip fëmijët edhe kur roli është "Fëmijët" (mos mbaj si palë)
            role_lower = role.lower()
            if "fëmij" in role_lower or "femij" in role_lower:
                continue

            norm_key = _normalize_name_key(name)
            if not norm_key:
                continue

            if norm_key not in merged:
                merged[norm_key] = {
                    "display": name,
                    "roles": set(),
                    "variants": [name],
                }
            entry = merged[norm_key]
            entry["variants"].append(name)
            # Prefer longer display name (me parenthetical)
            if len(name) > len(entry["display"]):
                entry["display"] = name
            if role:
                entry["roles"].add(role)

    if not merged:
        return

    lines.append("=" * 70)
    lines.append("👥 PALËT NDËRGYQËSE ME ROLE (nga NER i dokumenteve)")
    lines.append("=" * 70)
    lines.append(
        "⚠️ KY ËSHTË BURIMI I VETËM I SË VËRTETËS për rolet e palëve. "
        "ÇDO rol që nuk shfaqet këtu KONSIDEROHET HALUDINACION."
    )
    lines.append(
        "⚠️ KURRË mos i ndrysho rolet. Nëse një person ka role të ndryshme "
        "në dokumente të ndryshme (faza civile vs penale), LISTOJI TË GJITHA."
    )
    lines.append("")

    for norm_key in sorted(merged.keys(), key=lambda k: merged[k]["display"]):
        entry = merged[norm_key]
        name = entry["display"]
        roles = entry["roles"]
        if roles:
            role_str = " / ".join(sorted(roles))
            lines.append(f"  • {name} — Roli: {role_str}")
        else:
            lines.append(f"  • {name} — (roli nuk u specifikua në NER)")
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# VERIFIED CITATIONS BLOCK
# ═══════════════════════════════════════════════════════════════════════════

def _append_verified_citations(
    lines: List[str],
    verified_citations: Dict[str, Any],
) -> None:
    lines.append("=" * 70)
    lines.append("🔒 CITIMET E VËRTETUARA NGA DOKUMENTET (REGEX EXTRACTION)")
    lines.append("=" * 70)
    lines.append(
        "⚠️ KY ËSHTË BURIMI I VETËM I SË VËRTETËS. "
        "NUK LEJOHET TË SHPIKËSH LIGJE APO NENE QË NUK SHFAQEN KËTU."
    )
    lines.append("")

    lines.append(f"LIGJET E CITUARA ({verified_citations['total_laws']}):")
    if verified_citations["laws"]:
        for law in verified_citations["laws"]:
            lines.append(f"  • {law}")
    else:
        lines.append("  (asnjë ligj i cituar në dokumente)")
    lines.append("")

    lines.append(f"NENET E CITUARA ({verified_citations['total_articles']}):")
    if verified_citations["articles"]:
        shown = set()
        for art in verified_citations["articles"][:60]:
            par = f", par. {art['paragraph']}" if art.get("paragraph") else ""
            doc_name = art.get("doc_name", "")
            key = f"{art['number']}{par}"
            if key in shown:
                continue
            shown.add(key)
            lines.append(f"  • Neni {art['number']}{par}  [në: {doc_name}]")
    else:
        lines.append("  (asnjë nen i cituar në dokumente)")
    lines.append("")

    if verified_citations.get("article_law_pairs"):
        lines.append(f"ÇIFTET E VËRTETA (Neni X i Ligji) ({verified_citations['total_pairs']}):")
        for art, law in verified_citations["article_law_pairs"][:60]:
            lines.append(f"  • Neni {art} i {law}")
        lines.append("")

    lines.append(
        "⚠️ RREGULL ABSOLUT: Përdor VETËM ligjet dhe nenet e mësipërme. "
        "ÇDO ligj/nen që nuk është në këtë listë KONSIDEROHET HALUDINACION."
    )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# APPENDERS
# ═══════════════════════════════════════════════════════════════════════════

def _append_articles_by_law(
    lines: List[str],
    articles_by_law: Dict[str, Dict[str, str]],
) -> None:
    total = sum(len(v) for v in articles_by_law.values())

    lines.append("=" * 70)
    lines.append("📖 KONTEKSTI I NENEVE NË DOKUMENTE (JO PËRSHKRIME ZYRTARE)")
    lines.append("=" * 70)
    lines.append(
        f"Ky seksion përmban {total} nene me KONTEKST DOKUMENTI (jo përshkrime zyrtare)."
    )
    lines.append(
        "⚠️ KONTEKSTI ËSHTË JOZYRTAR. NËSE citon në raport → shkruaj "
        "VETËM 'Neni X i [Ligjit]' PA përshkrim."
    )
    lines.append("")

    for law_name in sorted(articles_by_law.keys()):
        articles = articles_by_law[law_name]
        if not articles:
            continue
        lines.append(f"**{law_name}:**")
        for article_key in sorted(articles.keys()):
            desc = articles[article_key]
            if desc:
                lines.append(f"  • {article_key} — [KONTEKST DOKUMENTI: {desc}]")
            else:
                lines.append(f"  • {article_key} (pa kontekst)")
        lines.append("")


def _append_defendants_groups(
    lines: List[str],
    defendants_groups: List[Dict[str, Any]],
) -> None:
    total = sum(len(g.get("defendants", [])) for g in defendants_groups)

    lines.append("=" * 70)
    lines.append("⚖️ GRUPET E TË PANDËHURVE")
    lines.append("=" * 70)
    lines.append(f"Total: {total} të pandehur në {len(defendants_groups)} grupe.")
    lines.append("")

    for group in defendants_groups:
        group_key = group.get("group", "?")
        title = group.get("title", "")
        lines.append(f"GRUPI {group_key}: {title}")
        for d in group.get("defendants", []):
            num = d.get("number", "")
            name = d.get("name", "")
            role = d.get("role", "")
            lines.append(f"  {num}. {name} — {role}")
        lines.append("")


def _append_cross_references(lines: List[str], xrefs: Dict[str, Any]) -> None:
    lines.append("=" * 70)
    lines.append("LIDHJET MIDIS DOKUMENTEVE")
    lines.append("=" * 70)
    doc_refs = xrefs.get("document_references", [])
    if doc_refs:
        for ref in doc_refs[:20]:
            lines.append(
                f"  • '{ref.get('source_file_name')}' → "
                f"'{ref.get('target_file_name')}'"
            )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def find_primary_document(
    extractions: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    priorities = [
        ("kallëzim", "kallzim"),
        ("aktakuzë", "aktakuze"),
        ("padi", "kërkesëpadi"),
        ("aktgjykim", "aktvendim"),
    ]
    for keywords in priorities:
        for ext in extractions:
            doc_type = (ext.get("document_type") or "").lower()
            if any(kw in doc_type for kw in keywords):
                return ext
    if extractions:
        return max(extractions, key=lambda e: e.get("text_length", 0))
    return None


def extract_supreme_court_decisions(
    extractions: List[Dict[str, Any]],
) -> List[str]:
    decisions = set()
    for ext in extractions:
        ebt = ext.get("entities_by_type", {})
        for item in ebt.get("CASE_NUMBER", []):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            if re.match(r'^(PML|Rev)\.?\s*[Nn]r', text, re.IGNORECASE):
                decisions.add(text)
    return sorted(decisions)