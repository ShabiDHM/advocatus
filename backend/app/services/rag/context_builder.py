# FILE: backend/app/services/rag/context_builder.py
# PHOENIX PROTOCOL - CONTEXT BUILDER V6.4 (JUDICIAL-DOCS-ONLY WHITELIST)
# V6.4: Whitelist ekstraktohet VETËM nga dokumentet gjykatore (vendim/aktvendim/aktgjykim/urdhër).
#       Shtuar laws_by_file — tracking i cilit dokument citon cilin ligj.
#       Fallback: nëse nuk ka dokumente gjykatore → përdor të gjitha.
# V6.3: Whitelist vetëm nga db_documents.
# V6.2: Whitelist nga case_docs + global_docs.
# V6.1: Regex për ligjet me numër (03/L-182).

import re
import logging
from collections import Counter
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 450_000
RESERVED_FOR_WHITELIST = 25_000
MAX_DISPLAY_ARTICLES = 5

# V6.4: Fjalët kyçe për dokumentet gjykatore
JUDICIAL_DOC_KEYWORDS = ["vendim", "aktvendim", "aktgjykim", "urdhër", "urdher"]


# ═══════════════════════════════════════════════════════════════════════════
# REGEX PËR WHITELIST
# ═══════════════════════════════════════════════════════════════════════════

_ARTICLE_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)',
    re.IGNORECASE | re.UNICODE
)

_LAW_ABBREV_RE = re.compile(
    r'\b(KPPRK|KPRK|KPK|LPK|LMDHF|LMD|LFK|LSHT|LPP|KDPM|LPTS|PSRK|Kushtetuta)\b',
    re.IGNORECASE | re.UNICODE
)

_LAW_NUMBER_RE = re.compile(
    r'\bLigj(?:it|i|ji|in)?\s+(?:Nr\.?\s*)?(\d{2}\s*\/\s*[A-Za-z]\s*[-–]?\s*\d{2,4})\b',
    re.IGNORECASE | re.UNICODE
)

_ARTICLE_ABBREV_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)\s+(?:i|të|te|e|së)\s+'
    r'(KPPRK|KPRK|KPK|LPK|LMDHF|LMD|LFK|LSHT|LPP|KDPM|LPTS|PSRK|Kushtetuta)',
    re.IGNORECASE | re.UNICODE
)

_ARTICLE_LAWNUM_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)\s+(?:i|të|te|e|së)\s+'
    r'(?:i\s+)?Ligj(?:it|i|ji|in)?\s+(?:Nr\.?\s*)?(\d{2}\s*\/\s*[A-Za-z]\s*[-–]?\s*\d{2,4})',
    re.IGNORECASE | re.UNICODE
)


class ContextBuilder:
    """
    Ndërtuesi Qendror i Kontekstit Juridik (V6.4):
    - V6.4: Whitelist VETËM nga dokumentet gjykatore (jo nga 18 dokumentet e papërpunuara).
    - V6.3: Whitelist vetëm nga db_documents.
    - V6.0-6.2: Whitelist automatik + ligjet me numër.
    """

    @staticmethod
    def _get_best_document_text(doc: Dict[str, Any]) -> str:
        candidates = [
            doc.get("content") or "",
            doc.get("extracted_text") or "",
            doc.get("text_content") or "",
            doc.get("text") or "",
        ]
        valid_candidates = [c.strip() for c in candidates if isinstance(c, str) and len(c.strip()) > 0]
        if not valid_candidates:
            return ""
        return max(valid_candidates, key=len)

    @staticmethod
    def _get_expanded_text(d: Dict[str, Any]) -> str:
        metadata = d.get('metadata') or {}
        return (
            d.get('parent_text') or
            metadata.get('parent_text') or
            d.get('text') or
            metadata.get('text') or
            d.get('content') or
            metadata.get('content') or
            ""
        ).strip()

    @staticmethod
    def _prioritize_documents(documents: List[Dict]) -> List[Dict]:
        priority_keywords = {
            "aktvendim": 100, "aktgjykim": 100, "vendim": 95,
            "në emër të popullit": 95, "urdhër": 90, "urdher": 90,
            "ekspertiz": 85, "raport": 80, "procesverbal": 75,
            "padi": 70, "kundërpadi": 70, "kunderpadi": 70,
            "kallëzim": 70, "kallzim": 70, "ankes": 70,
            "kontratë": 65, "marrëvesh": 65,
            "korrespondenc": 40, "faturë": 40, "email": 30,
        }

        def get_priority(doc: Dict) -> int:
            file_name = (doc.get("file_name") or doc.get("title") or "").lower()
            max_priority = 0
            for keyword, priority in priority_keywords.items():
                if keyword in file_name:
                    max_priority = max(max_priority, priority)
            return max_priority

        return sorted(documents, key=get_priority, reverse=True)

    # ═══════════════════════════════════════════════════════════════════════
    # V6.4: JUDICIAL DOC FILTER
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _is_judicial_document(doc: Dict[str, Any]) -> bool:
        """Kthen True nëse dokumenti është gjykatore (vendim, aktvendim, aktgjykim, urdhër)."""
        name = (doc.get("file_name") or doc.get("title") or "").lower()
        return any(kw in name for kw in JUDICIAL_DOC_KEYWORDS)

    # ═══════════════════════════════════════════════════════════════════════
    # WHITELIST EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _normalize_law_number(raw: str) -> str:
        return re.sub(r'\s+', '', raw).upper().replace('–', '-')

    @staticmethod
    def _extract_citation_whitelist(all_text: str) -> Dict[str, Any]:
        articles_found = _ARTICLE_RE.findall(all_text)

        try:
            articles = sorted(set(articles_found), key=lambda x: (int(re.sub(r'\D', '', x) or 0), x))
        except Exception:
            articles = sorted(set(articles_found))

        law_abbrevs = sorted(set(m.upper() for m in _LAW_ABBREV_RE.findall(all_text)))

        law_numbers_raw = _LAW_NUMBER_RE.findall(all_text)
        law_numbers = sorted(set(ContextBuilder._normalize_law_number(n) for n in law_numbers_raw))

        pairs_set: Set[Tuple[str, str]] = set()
        for m in _ARTICLE_ABBREV_RE.finditer(all_text):
            pairs_set.add((m.group(1), m.group(2).upper()))
        for m in _ARTICLE_LAWNUM_RE.finditer(all_text):
            norm_num = ContextBuilder._normalize_law_number(m.group(2))
            pairs_set.add((m.group(1), f"Ligji Nr. {norm_num}"))
        pairs = sorted(pairs_set)

        counter = Counter(articles_found)
        articles_display = [a for a, _ in counter.most_common(MAX_DISPLAY_ARTICLES)]

        return {
            "articles": articles,
            "articles_display": articles_display,
            "laws_abbrev": law_abbrevs,
            "laws_number": law_numbers,
            "pairs": pairs,
        }

    @staticmethod
    def _extract_whitelist_from_case_files(db_documents: List[Dict]) -> Dict[str, Any]:
        """
        V6.4: Ekstrakton whitelist VETËM nga dokumentet gjykatore.
        Fallback: nëse nuk ka dokumente gjykatore → përdor të gjitha.
        Gjithashtu gjurmon cilat ligje citon secili dokument (laws_by_file).
        """
        # 1. Filtro vetëm dokumentet gjykatore
        judicial_docs = [d for d in (db_documents or []) if ContextBuilder._is_judicial_document(d)]

        used_filter = "judicial_only"
        if not judicial_docs:
            judicial_docs = db_documents or []
            used_filter = "all_docs_fallback"

        # 2. Ekstrakto tekst + gjurmo ligjet për secilin file
        parts: List[str] = []
        laws_by_file: Dict[str, List[str]] = {}

        for doc in judicial_docs:
            text = ContextBuilder._get_best_document_text(doc)
            if not text:
                continue

            parts.append(text)

            file_name = doc.get("file_name") or doc.get("title") or "N/A"
            doc_whitelist = ContextBuilder._extract_citation_whitelist(text)
            if doc_whitelist["laws_number"]:
                laws_by_file[file_name] = doc_whitelist["laws_number"]

        # 3. Ndërto whitelist-in e kombinuar
        combined = ContextBuilder._extract_citation_whitelist("\n".join(parts))

        # 4. Shto metadata
        combined["laws_by_file"] = laws_by_file
        combined["source_filter"] = used_filter
        combined["judicial_docs_count"] = len(judicial_docs)
        combined["total_docs_count"] = len(db_documents or [])

        return combined

    @staticmethod
    def _format_whitelist(whitelist: Dict[str, Any]) -> str:
        articles = whitelist.get("articles", [])
        laws_abbrev = whitelist.get("laws_abbrev", [])
        laws_number = whitelist.get("laws_number", [])
        pairs = whitelist.get("pairs", [])
        laws_by_file = whitelist.get("laws_by_file", {})
        source_filter = whitelist.get("source_filter", "unknown")

        lines: List[str] = []
        lines.append("\n" + "🔒" * 35)
        lines.append("🔒  CITIMET E LEJUARA — WHITELIST (VETËM KËTO MUND TË CITOSH)")
        lines.append("🔒" * 35)
        lines.append("")
        lines.append("⚠️ RREGULL ABSOLUT: Çdo nen, ligj ose afat që NUK është në këtë listë KONSIDEROHET HALUDINACION.")
        if source_filter == "judicial_only":
            lines.append("⚠️ Kjo listë përmban VETËM citime nga DOKUMENTET GJYKATORE (vendim, aktvendim, aktgjykim, urdhër).")
        else:
            lines.append("⚠️ Nuk u gjetën dokumente gjykatore — lista përfshin të gjitha dokumentet.")
        lines.append("")

        if laws_abbrev:
            lines.append(f"📜 LIGJET ME AKRONIM ({len(laws_abbrev)}):")
            for law in laws_abbrev:
                lines.append(f"   • {law}")
            lines.append("")

        if laws_number:
            lines.append(f"📜 LIGJET ME NUMËR ({len(laws_number)}):")
            lines.append("   ⚠️ Cito SAKTËSISHT numrin që shfaqet — MOS e zëvendëso me version tjetër!")
            for law in laws_number:
                lines.append(f"   • Ligji Nr. {law}")
            lines.append("")

        if not laws_abbrev and not laws_number:
            lines.append("📜 LIGJET: (asnjë ligj i identifikuar)")
            lines.append("   ⚠️ NËSE NUK KA LIGJE NË KËTË LISTË → NUK LEJOHET të citosh ASNJË nen.")
            lines.append("")

        if laws_by_file and len(laws_by_file) > 0:
            lines.append("📋 LIGJET SIPAS DOKUMENTIT:")
            for fname, laws in laws_by_file.items():
                laws_str = ", ".join(f"Ligji Nr. {l}" for l in laws)
                lines.append(f"   • {fname} → {laws_str}")
            lines.append("   ⚠️ NËSE pyetja i referohet një dokumenti specifik → cito ligjin e atij dokumenti.")
            lines.append("")

        if articles:
            shown = articles[:100]
            lines.append(f"📖 NENET E PRANISHME ({len(articles)} total):")
            for art in shown:
                lines.append(f"   • Neni {art}")
            if len(articles) > 100:
                lines.append(f"   ... dhe {len(articles) - 100} nene të tjera.")
            lines.append("")
        else:
            lines.append("📖 NENET: (asnjë nen i identifikuar)")
            lines.append("")
            
        if pairs:
            lines.append(f"✅ ÇIFTET E VËRTETA (Neni X i Ligjit) ({len(pairs)}):")
            for art, law in pairs[:80]:
                lines.append(f"   • Neni {art} i {law}")
            if len(pairs) > 80:
                lines.append(f"   ... dhe {len(pairs) - 80} çifte të tjera.")
            lines.append("")

        lines.append("❌ NUK LEJOHET:")
        lines.append("   • Të citosh LIGJE që nuk shfaqen në listën e mësipërme.")
        lines.append("   • Të zëvendësosh një ligj me numër (p.sh. 03/L-182) me një version tjetër (08/L-185) pa përmendur burimin.")
        lines.append("   • Të shpikësh numra neni që nuk janë më lart.")
        lines.append("   • Të përziesh KPK me KPRK, LPK me KPPRK, LMDHF me LFK, etj.")
        lines.append("")
        lines.append("🔒" * 35 + "\n")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════
    # BUILD
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def build(
        case_docs: List[Dict],
        global_docs: List[Dict],
        db_documents: List[Dict]
    ) -> Tuple[str, str]:
        manifest_lines = ["\n<<< REGJISTRI DOKTRINAR I SHKRESAVE TË FASHIKULLIT >>>\n"]
        context_blocks: List[str] = []
        seen_texts: Set[str] = set()

        prioritized_docs = ContextBuilder._prioritize_documents(db_documents)

        if prioritized_docs:
            for idx, doc in enumerate(prioritized_docs, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or f"Dokument_{idx}.pdf"
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"

                raw_t = ContextBuilder._get_best_document_text(doc)

                summ = (doc.get("summary") or "").strip()
                if "sinteza" in summ.lower() or len(summ) < 20:
                    summ = ""

                dense_passport = summ or raw_t[:500] or "Shkresë e administruar në fashikull."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:250]}...")

                if raw_t:
                    context_blocks.append(f"\n{'='*50}\n📄 SHKRESA ZYRTARE: {doc_clickable_link}\n{'='*50}\n{raw_t}\n")
                    seen_texts.add(raw_t[:150].lower())
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        semantic_blocks = []
        if case_docs:
            for d in case_docs:
                text = ContextBuilder._get_expanded_text(d)
                if text and len(text) > 40 and text[:150].lower() not in seen_texts:
                    src = d.get('source') or 'Dokument'
                    page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
                    semantic_blocks.append(f"📌 [{src}{page_info}]:\n{text}\n")
                    seen_texts.add(text[:150].lower())

        if semantic_blocks:
            context_blocks.append("\n<<< PROVAT KYÇE NGA KËRKIMI SEMANTIK >>>\n")
            context_blocks.extend(semantic_blocks)

        if global_docs:
            context_blocks.append("\n<<< JURISPRUDENCA DHE DITURIA GLOBALE E KOSOVËS >>>\n")
            for d in global_docs:
                source_tag = d.get('source') or 'Burim Juridik'
                text = ContextBuilder._get_expanded_text(d)
                if text and len(text) > 30:
                    context_blocks.append(f"🏛️ BURIMI: {source_tag}\n{text}\n")

        full_context = "".join(context_blocks)

        truncate_limit = MAX_CONTEXT_CHARS - RESERVED_FOR_WHITELIST
        if len(full_context) > truncate_limit:
            full_context = full_context[:truncate_limit] + "\n\n[...Konteksti u optimizua...]"

        whitelist = ContextBuilder._extract_whitelist_from_case_files(db_documents)
        whitelist_section = ContextBuilder._format_whitelist(whitelist)

        final_context = whitelist_section + full_context

        if len(final_context) > MAX_CONTEXT_CHARS:
            final_context = final_context[:MAX_CONTEXT_CHARS] + "\n\n[...u optimizua...]"

        logger.info(
            f"📊 [ContextBuilder V6.4] Kontekst: {len(final_context)} chars | "
            f"whitelist ({whitelist.get('source_filter')}): "
            f"{len(whitelist['articles'])} nene ({len(whitelist['articles_display'])} display), "
            f"{len(whitelist['laws_abbrev'])} akronime, "
            f"{len(whitelist['laws_number'])} ligje me numër, "
            f"{len(whitelist.get('laws_by_file', {}))} dokumente me ligje | "
            f"{whitelist.get('judicial_docs_count', 0)}/{whitelist.get('total_docs_count', 0)} docs gjykatore."
        )
        return "\n".join(manifest_lines), final_context

    @staticmethod
    def build_with_whitelist(
        case_docs: List[Dict],
        global_docs: List[Dict],
        db_documents: List[Dict]
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        V6.4: Kthen (manifest, context, whitelist).
        Whitelist VETËM nga dokumentet gjykatore.
        """
        manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)
        whitelist = ContextBuilder._extract_whitelist_from_case_files(db_documents)
        return manifest_str, context_str, whitelist