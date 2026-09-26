# FILE: backend/app/services/rag/cross_doc_comparator.py
# PHOENIX PROTOCOL - CROSS-DOCUMENT COMPARATOR V1.2
# V1.2: FIX — sort_key kthen gjithmonë tuple me 3 elemente (0/1, int, str).
#       Më parë tuple me 2 elemente vs 3 → TypeError në përzierje.
# V1.1: (1) Normalizim "Neni 1.2" → "1" (bazë), për të shmangur duplikim.
#       (2) Dedup i neneve pas normalizimit.
# V1.0: Krijim fillestar.

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

_ARTICLE_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)',
    re.IGNORECASE | re.UNICODE,
)

_LAW_NUMBER_RE = re.compile(
    r'\bLigj(?:it|i|ji|in)?\s+(?:Nr\.?\s*)?(\d{2}\s*\/\s*[A-Za-z]\s*[-–]?\s*\d{2,4})\b',
    re.IGNORECASE | re.UNICODE,
)

COMPARISON_TRIGGERS = [
    "krahaso", "krahasim", "krahasuar", "krahasimi", "krahasoj",
    "dallim", "dallime", "dallimi", "dallimet",
    "ndryshim", "ndryshime", "ndryshimi",
    "cilat nene", "cilat ligje", "të përbashkëta", "te perbashketa",
    "se paku", "vs", "versus",
]


def user_wants_comparison(query_lower: str) -> bool:
    return any(t in query_lower for t in COMPARISON_TRIGGERS)


def _normalize_article(num: str) -> str:
    if not num:
        return num
    base = num.split(".")[0].split("/")[0].strip()
    return base if base.isdigit() else num


def _get_doc_text(doc: Dict[str, Any]) -> str:
    candidates = [
        doc.get("content") or "",
        doc.get("extracted_text") or "",
        doc.get("text_content") or "",
        doc.get("text") or "",
    ]
    valid = [c.strip() for c in candidates if isinstance(c, str) and len(c.strip()) > 0]
    if not valid:
        return ""
    return max(valid, key=len)


def extract_articles_per_document(documents: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}

    for doc in documents:
        fname = doc.get("file_name") or doc.get("title") or "?"
        text = _get_doc_text(doc)
        if not text:
            continue

        raw_articles = _ARTICLE_RE.findall(text)
        normalized = sorted(set(_normalize_article(a) for a in raw_articles))

        laws = sorted(set(
            re.sub(r'\s+', '', m).upper().replace('–', '-')
            for m in _LAW_NUMBER_RE.findall(text)
        ))

        result[fname] = {
            "articles": normalized,
            "laws": laws,
        }

    return result


def build_comparison_table(documents: List[Dict[str, Any]]) -> str:
    per_doc = extract_articles_per_document(documents)
    if not per_doc:
        return ""

    all_articles = set()
    for data in per_doc.values():
        all_articles.update(data["articles"])

    if not all_articles:
        return ""

    def sort_key(x: str):
        # V1.2: Tuple uniforme me 3 elemente gjithmonë
        try:
            return (0, int(x), "")
        except (ValueError, TypeError):
            return (1, 0, str(x))

    sorted_articles = sorted(all_articles, key=sort_key)
    doc_names = list(per_doc.keys())

    lines: List[str] = []
    lines.append("\n<<< KRAHASIM MIDIS DOKUMENTEVE (i ekstraktuar automatikisht) >>>\n")
    lines.append("⚠️ Tabela tregon VETËM nenet që shfaqen në tekstet e dokumenteve.\n")
    lines.append(f"📊 Krahasim midis: {', '.join(doc_names)}\n")
    lines.append("")

    header = "| Neni | " + " | ".join(doc_names) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(doc_names) + 1))

    for art in sorted_articles:
        cells = [f"Neni {art}"]
        for doc_name in doc_names:
            if art in per_doc[doc_name]["articles"]:
                cells.append("✅")
            else:
                cells.append("—")
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")

    all_laws = set()
    for data in per_doc.values():
        all_laws.update(data["laws"])

    if all_laws:
        lines.append("### Ligjet e citara sipas dokumentit\n")
        for doc_name, data in per_doc.items():
            laws_str = ", ".join(f"Ligji Nr. {l}" for l in data["laws"]) or "(asnjë)"
            lines.append(f"- **{doc_name}**: {laws_str}")
        lines.append("")

    lines.append(
        "📋 DETYRË: Krahaso dokumentet duke u bazuar në këtë tabelë. "
        "Thekso nenet e përbashkëta, dallimet dhe implikimet ligjore."
    )
    lines.append("")

    logger.info(
        f"📊 [Comparator V1.2] Tabelë e krijuar: "
        f"{len(sorted_articles)} nene × {len(doc_names)} dokumente"
    )

    return "\n".join(lines)