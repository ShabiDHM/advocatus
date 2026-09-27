# FILE: backend/app/services/rag/official_cleaner.py
# PHOENIX PROTOCOL - OFFICIAL TEXT CLEANER V1.0
# V1.0: EKSTRAKTUAR nga albanian_rag_service.py V282.25 (metodat self._*).
#       Konvertuar në funksione të pavarura (pa self).
#       - _unwrap_lines
#       - _extract_gazette_info
#       - _extract_law_number_from_source
#       - _is_document_header_line
#       - _is_law_header_candidate
#       - _is_header_continuation
#       - _remove_repeated_headers
#       - _clean_official_text
#       - _format_direct_answer
#       Zero varësi nga AlbanianRAGService.

import re
from collections import Counter
from typing import List, Optional, Dict, Any, Tuple


def _unwrap_lines(text: str) -> str:
    lines = text.splitlines()
    result: List[str] = []
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            result.append("")
            continue
        if result and result[-1]:
            prev = result[-1].rstrip()
            if prev.endswith((",", "-", "—", "–")) or (stripped and stripped[0].islower()):
                result[-1] = prev + " " + stripped.lstrip()
                continue
        result.append(stripped)
    return "\n".join(result)


def _extract_gazette_info(raw: str) -> Optional[str]:
    m = re.search(
        r'GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS\s*/\s*Nr\.?\s*(\d+)\s*/\s*([^,\n]+)',
        raw,
        re.IGNORECASE,
    )
    if m:
        return f"Gazeta Zyrtare Nr. **{m.group(1)}** / {m.group(2).strip()}"
    return None


def _extract_law_number_from_source(source: str) -> str:
    if not source:
        return ""
    m = re.search(r'(\d{2})\s*[_ ]?\s*L\s*[-_ ]?\s*(\d{2,4})', source, re.IGNORECASE)
    if m:
        return f"Ligji Nr. {m.group(1)}/L-{m.group(2)}"
    return ""


def _is_document_header_line(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 25:
        return False
    if stripped.endswith("."):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) < 15:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio < 0.7:
        return False
    words = stripped.split()
    if len(words) < 4:
        return False
    return True


def _is_law_header_candidate(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 25:
        return False
    if stripped.endswith("."):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) < 15:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio < 0.7:
        return False
    words = stripped.split()
    has_nr = bool(re.search(r'\bNR\.?\b', stripped, re.IGNORECASE))
    if has_nr or len(words) >= 4:
        return True
    return False


def _is_header_continuation(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 8:
        return False
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) < 5:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio >= 0.8


def _remove_repeated_headers(lines: List[str]) -> List[str]:
    candidates: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and _is_document_header_line(stripped):
            candidates.append(stripped)

    if not candidates:
        return lines

    counts = Counter(candidates)
    repeated = {l for l, c in counts.items() if c >= 2}
    if not repeated:
        return lines

    return [l for l in lines if l.strip() not in repeated]


def _clean_official_text(raw: str) -> str:
    if not raw:
        return ""
    text = raw

    text = re.sub(
        r'^.*GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*$',
        '',
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)

    lines = text.splitlines()
    lines = _remove_repeated_headers(lines)
    text = "\n".join(lines)

    lines = text.splitlines()
    filtered: List[str] = []
    skip_next_caps = False

    for line in lines:
        stripped = line.strip()

        if skip_next_caps:
            skip_next_caps = False
            if stripped and stripped.isupper() and 5 <= len(stripped) < 100 and stripped.split():
                continue

        if _is_law_header_candidate(stripped):
            skip_next_caps = True
            continue

        filtered.append(line)

    text = "\n".join(filtered)

    text = _unwrap_lines(text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)

    return text.strip()


def _format_direct_answer(
    verified_articles: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    pre_verify_disclaimer: str,
) -> str:
    parts: List[str] = []

    if pre_verify_disclaimer:
        parts.append(pre_verify_disclaimer.strip())

    for art, v in verified_articles:
        doc = v.get("matched_doc") or {}
        law_title_raw = doc.get("law_title") or art.get("law_hint", "Ligj i panjohur")
        source_file = doc.get("source", "") or ""
        page = doc.get("page")
        article_number = art.get("number", "")
        raw_body = doc.get("text_excerpt", "") or ""

        gazette_info = _extract_gazette_info(raw_body)
        law_number = _extract_law_number_from_source(source_file)
        clean_body = _clean_official_text(raw_body)

        parts.append(f"## ⚖️ Neni {article_number}")
        parts.append(f"#### 📘 {law_title_raw}")

        if clean_body:
            parts.append("---")
            parts.append(clean_body)

        source_meta: List[str] = []
        if law_number:
            source_meta.append(f"**{law_number}**")
        if gazette_info:
            source_meta.append(gazette_info)
        if page is not None:
            source_meta.append(f"Faqe **{page}**")
        if source_file:
            source_meta.append(f"`{source_file}`")

        if source_meta:
            parts.append("---")
            parts.append(f"📎 **Burimi zyrtar:** " + " · ".join(source_meta))

    parts.append("---")
    parts.append(
        "*ℹ️ Teksti i mësipërm është marrë drejtpërdrejt nga baza zyrtare ligjore "
        "e Republikës së Kosovës — pa përpunim nga AI.*\n\n"
        "*💬 Për interpretim, aplikim në fashikull, ose analizë të thelluar, "
        "vazhdoni me pyetjen tuaj.*"
    )

    return "\n\n".join(parts)