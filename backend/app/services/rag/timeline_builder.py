# FILE: backend/app/services/rag/timeline_builder.py
# PHOENIX PROTOCOL - TIMELINE BUILDER V1.3
# V1.3: FULL DATE VALIDATION —
#       - Të dyja rrugët (numeric + written) tani validon me `datetime.date(y, m, d)`.
#         Përpara: "31 Shkurt 2024" dhe "31.02.2024" prodhonin "2024-02-31"
#         (ISO invalid) dhe hynin në kronologji. Tani refuzohen.
# V1.2: DATE VALIDATION CONSISTENCY (ditë + vit).
# V1.1: Dedup key (fname, iso, context[:80]).
# V1.0: Krijim fillestar.

import re
import logging
from datetime import date as _date
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


def _safe_iso(d: int, mo: int, y: int) -> str:
    """
    V1.3: Kthen ISO string nëse data është kalendarikisht e vlefshme, përndryshe
    string bosh. Përdor datetime.date — kap automatikisht 31 Shkurt, 31 Prill,
    vitet e brishtë, etj.
    """
    if not (1990 <= y <= 2050):
        return ""
    try:
        dt = _date(y, mo, d)
        return dt.isoformat()
    except (ValueError, TypeError):
        return ""


def _find_all_dates(text: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for m in _NUMERIC_DATE_RE.finditer(text):
        d, mo, y = m.group(1), m.group(2), m.group(3)
        iso = _safe_iso(int(d), int(mo), int(y))
        if iso:
            results.append({
                "iso": iso,
                "position": m.start(),
                "raw": m.group(0),
            })

    for m in _WRITTEN_DATE_RE.finditer(text):
        d, month_name, y = m.group(1), m.group(2).lower(), m.group(3)
        mo = _MONTH_NAMES.get(month_name)
        if not mo:
            continue
        iso = _safe_iso(int(d), int(mo), int(y))
        if iso:
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

    logger.info(f"📅 [Timeline V1.3] {len(events)} ngjarje të ekstraktuara")

    return "\n".join(lines)