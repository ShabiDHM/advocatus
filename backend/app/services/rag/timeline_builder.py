# FILE: backend/app/services/rag/timeline_builder.py
# PHOENIX PROTOCOL - TIMELINE BUILDER V1.1
# V1.1: FIX — Dedup key (fname, iso, context[:80]) në vend të (fname, iso).
#       Më parë ngjarje të shumta në të njëjtën datë brenda të njëjtit dokument
#       humbnin. Tani ruhen të gjitha nëse konteksti ndryshon.
# V1.0: Krijim fillestar.

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DATE PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

_NUMERIC_DATE_RE = re.compile(
    r'\b(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{4})\b',
)

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
    return any(t in query_lower for t in TIMELINE_TRIGGERS)


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


def _find_all_dates(text: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

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
    V1.1: Nxjerr ngjarjet (data + kontekst + burim).
    Dedup key përfshin kontekstin → ruhen ngjarje të ndryshme në të njëjtën ditë.
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

            pos = dm["position"]
            start = max(0, pos - 100)
            end = min(len(text), pos + 200)
            context = text[start:end].replace("\n", " ").strip()
            context = re.sub(r'\s+', ' ', context)

            # V1.1: Dedup key përfshin kontekstin (jo vetëm datën)
            dedup_key = (fname, dm["iso"], context[:80])
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

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

    logger.info(f"📅 [Timeline V1.1] {len(events)} ngjarje të ekstraktuara")

    return "\n".join(lines)