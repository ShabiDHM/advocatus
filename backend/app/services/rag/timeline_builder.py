# FILE: backend/app/services/rag/timeline_builder.py
# PHOENIX PROTOCOL - TIMELINE BUILDER V1.0
# Qëllimi: kur user kërkon kronologji, ekstrakto datat + kontekstin nga
# dokumentet dhe ndërto timeline të renditur.
#
# Triggers: "kronologji", "timeline", "kur ka ndodhur", "data".

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DATE PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

# Numeric: 16.02.2024, 16/02/2024
_NUMERIC_DATE_RE = re.compile(
    r'\b(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{4})\b',
)

# Written month: 16 shkurt 2024
_MONTH_NAMES = {
    "janar": "01", "janarit": "01",
    "shkurt": "02", "shkurtit": "02",
    "mars": "03", "marsit": "03",
    "prill": "04", "prillit": "04",
    "maj": "05", "majit": "05",
    "qershor": "06", "qershorit": "06",
    "korrik": "07", "korrikut": "07",
    "gusht": "08", "gushtit": "08",
    "shtator": "09", "shtatorit": "09",
    "tetor": "10", "tetorit": "10",
    "nëntor": "11", "nëntorit": "11", "nentor": "11",
    "dhjetor": "12", "dhjetorit": "12",
}
_WRITTEN_DATE_RE = re.compile(
    r'\b(\d{1,2})\s+(' + "|".join(_MONTH_NAMES.keys()) + r')\s+(\d{4})\b',
    re.IGNORECASE,
)

TIMELINE_TRIGGERS = [
    "kronologji", "kronologjia", "kronologjik",
    "timeline", "radhitje", "radhitja",
    "renditja kohore", "renditje kronologjike",
    "kur ka ndodhur", "kur kanë ndodhur", "kur u ngrit",
    "data e", "datat e", "ngjarjet kryesore",
]


def user_wants_timeline(query_lower: str) -> bool:
    """V1.0: Kontrollo nëse përdoruesi kërkon kronologji."""
    return any(t in query_lower for t in TIMELINE_TRIGGERS)


def _get_doc_text(doc: Dict[str, Any]) -> str:
    """Nxjerr tekstin më të plotë nga dokumenti."""
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


def _find_all_dates(text: str) -> List[Dict[str, Any]]:
    """Kthen listë me datat e gjetura: {iso, position, raw}."""
    results: List[Dict[str, Any]] = []

    # Numeric dates
    for m in _NUMERIC_DATE_RE.finditer(text):
        d, mo, y = m.group(1), m.group(2), m.group(3)
        d_int = int(d)
        mo_int = int(mo)
        y_int = int(y)
        if 1 <= d_int <= 31 and 1 <= mo_int <= 12 and 1990 <= y_int <= 2050:
            iso = f"{y_int:04d}-{mo_int:02d}-{d_int:02d}"
            results.append({
                "iso": iso,
                "position": m.start(),
                "raw": m.group(0),
            })

    # Written month dates
    for m in _WRITTEN_DATE_RE.finditer(text):
        d, month_name, y = m.group(1), m.group(2).lower(), m.group(3)
        mo = _MONTH_NAMES.get(month_name, "01")
        iso = f"{y}-{mo}-{int(d):02d}"
        results.append({
            "iso": iso,
            "position": m.start(),
            "raw": m.group(0),
        })

    return results


def extract_events(
    documents: List[Dict[str, Any]],
    max_per_doc: int = 15,
) -> List[Dict[str, Any]]:
    """
    V1.0: Nxjerr ngjarjet (data + kontekst + burim).
    Kthen listë të renditur kronologjikisht.
    """
    events: List[Dict[str, Any]] = []
    seen: set = set()

    for doc in documents:
        fname = doc.get("file_name") or doc.get("title") or "?"
        text = _get_doc_text(doc)
        if not text:
            continue

        date_matches = _find_all_dates(text)
        per_doc_count = 0

        for dm in date_matches:
            if per_doc_count >= max_per_doc:
                break

            # Dedupe: një datë unike per dokument
            key = (fname, dm["iso"])
            if key in seen:
                continue
            seen.add(key)

            # Konteksti rreth datës
            pos = dm["position"]
            start = max(0, pos - 100)
            end = min(len(text), pos + 200)
            context = text[start:end].replace("\n", " ").strip()
            # Heq hapësirat e tepërta
            context = re.sub(r'\s+', ' ', context)

            events.append({
                "iso": dm["iso"],
                "raw": dm["raw"],
                "context": context[:300],
                "source": fname,
            })
            per_doc_count += 1

    events.sort(key=lambda e: e["iso"])
    return events


def build_timeline(events: List[Dict[str, Any]], max_events: int = 25) -> str:
    """
    V1.0: Ndërton timeline markdown për LLM.
    """
    if not events:
        return ""

    lines: List[str] = []
    lines.append("\n<<< KRONOLOGJIA E NGJARJEVE (e ekstraktuar automatikisht) >>>\n")
    lines.append(
        "⚠️ Datat u ekstraktuan me regex nga tekstet e dokumenteve. "
        "Konteksti është i prerë — verifiko në dokumentin origjinal.\n"
    )
    lines.append("")

    for e in events[:max_events]:
        lines.append(f"**{e['raw']}** — {e['context']}")
        lines.append(f"  _(burimi: {e['source']})_")
        lines.append("")

    lines.append(
        "📋 DETYRË: Ndërto kronologjinë e plotë të ngjarjeve duke u bazuar "
        "në këto data. Rendit ngjarjet sipas datës, thekso momentet kritike "
        "dhe afatet procedurale."
    )
    lines.append("")

    logger.info(f"📅 [Timeline V1.0] {len(events)} ngjarje të ekstraktuara")

    return "\n".join(lines)