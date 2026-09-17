# FILE: backend/app/services/albanian_metadata_extractor.py
# PHOENIX PROTOCOL - METADATA EXTRACTOR V8.1
# FIX: FAST_MODEL → FAST_SEARCH_MODEL (emri i saktë nga llm_client.py)
# ZERO SILENT TRUNCATION • CHUNK-AWARE • EXPANDED FIELDS • BATCH READY

import re
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timezone

from app.services.llm.llm_client import (
    _call_llm,
    clean_and_parse_json,
    FAST_SEARCH_MODEL,   # ✅ FIX: emri i saktë
)

logger = logging.getLogger(__name__)


DEFAULT_CHUNK_SIZE = 8000
DEFAULT_CHUNK_OVERLAP = 500
MAX_SCAN_CHUNK = 100_000
MIN_TEXT_LENGTH = 20


METADATA_PROMPT = """
Ti je "Specialist i Arkivës dhe Regjistrit Ligjor" për Republikën e Kosovës.

DETYRA JOTE:
Identifiko dhe nxirr të dhënat strukturore (Metadata) nga teksti i dhënë.
Mos anashkalo asnjë fushë që mund të identifikohet. Nëse një fushë mungon, vendos null.

FUSHAT E DETYRUESHME (FORMATI JSON):
- court: Emri i Gjykatës apo Institucionit (psh. "Gjykata Komerciale e Kosovës", "Gjykata Themelore në Prishtinë", "QPS").
- judge: Emri i Gjyqtarit / Kryetarit të trupit gjykues.
- case_number: Numri i Lëndës (psh. "KE.nr.662/2022", "C.nr.120/21", "P.nr.45/20").
- parties: Lista e palëve me rolet e tyre ekzakte. Formati: [{"role": "Paditësi", "name": "Emri"}, ...]
- document_type: Lloji (Aktvendim, Aktgjykim, Padi, Kundërpadi, Prapësim, Ekspertizë, Kontratë, Kërkesë, Ankesë, Revizion, Njoftim, Urdhër, Memo, Vërtetim).
- date: Data e saktë e shkresës (formati DD.MM.YYYY ose "15 mars 2026").
- amount: Vlera monetare në EUR (nëse përmendet). Numër i pastër pa simbol.
- jurisdiction_check: "KOSOVË" ose "E HUAJ".
- statute: Lista e ligjeve të referuara (psh. ["LPK", "LMD", "KPRK"]).
- articles: Lista e neneve të referuara (psh. ["neni 45", "neni 177"]).
- subject: Objekti i lëndës / kërkesës në një fjali të shkurtër.
- deadline_mentioned: Afat procedural i përmendur në tekst (psh. "15 ditë", "30 ditë"), ose null.

RREGULLA:
1. Nxirr vetëm atë që gjendet në tekst — mos sajo.
2. Për parties, ruaj rolin ekzakt siç shfaqet në dokument.
3. Kthe VETËM objektin JSON të vlefshëm. Asnjë tekst shtesë.

SHEMBULL I DALJES:
{
  "court": "Gjykata Komerciale e Kosovës",
  "judge": "Arben Krasniqi",
  "case_number": "KE.nr.662/2022",
  "parties": [{"role": "Paditësi", "name": "Besa Sh.P.K."}, {"role": "E paditura", "name": "Albi Sh.P.K."}],
  "document_type": "Padi",
  "date": "15.03.2022",
  "amount": 50000.00,
  "jurisdiction_check": "KOSOVË",
  "statute": ["LPK", "LMD"],
  "articles": ["neni 45", "neni 177"],
  "subject": "Kërkesë për pagesën e borxhit kontraktual",
  "deadline_mentioned": null
}
"""


class AlbanianMetadataExtractor:
    """
    Ekstraktuesi Qendror i Metatëdhënave Ligjore për Kosovë (V8.1):
    - Zero silent truncation (chunk-aware).
    - Merge inteligjent i rezultateve nga chunks të shumtë.
    - Fusha të reja: statute, articles, subject, deadline_mentioned.
    - Batch API për shumë dokumente.
    - Stats + warnings për diagnostikim.
    - Backward compatible: extract() mbetet i njëjti API.
    """

    def __init__(self):
        self.chunk_size = DEFAULT_CHUNK_SIZE
        self.chunk_overlap = DEFAULT_CHUNK_OVERLAP

        self.patterns = {
            'contract_section': re.compile(
                r'Neni\s+(\d+\.?\d*)[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE
            ),
            'date': re.compile(
                r'(\d{1,2}\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s+\d{4})',
                re.IGNORECASE
            ),
            'case_reference': re.compile(
                r'(?:Çështja|Lënda|Numri|Nr\.?)\s*(?:Nr\.?)?\s*([A-Z]{1,3}\.?\s*nr\.?\s*[\w\-\/]+)',
                re.IGNORECASE
            ),
            'party': re.compile(
                r'(Paditësi|Padituesi|Pale|E Paditura|I Pandehuri|Parashtruesi)\s*[:\-]\s*(.+?)(?=\n|$)',
                re.IGNORECASE
            ),
            'amount': re.compile(
                r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(€|EUR|euro)',
                re.IGNORECASE
            ),
            'court': re.compile(
                r'(Gjykat[aë]s?\s+(e|ë)\s+[\w\s]+)', re.IGNORECASE
            ),
            'judge': re.compile(
                r'(Gjyqtar[i|e]\s+[\w\s]+)', re.IGNORECASE
            ),
        }

        self._extended_patterns = {
            'statute': re.compile(
                r'\b(LMD|LPK|KPRK|KPPRK|LSHT|LFK|Kushtetuta|Ligji\s+për\s+[\w\s]+)\b',
                re.IGNORECASE
            ),
            'articles': re.compile(
                r'\bneni\s+\d+(?:[\.\/]\d+)*', re.IGNORECASE
            ),
            'deadline_mentioned': re.compile(
                r'\b(\d{1,3}\s*(?:ditë|dite|muaj|vjet))\b', re.IGNORECASE
            ),
        }

        logger.info(
            f"✅ [METADATA] Kosovo Metadata Extractor V8.1 Initialized "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

    def _chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[Tuple[str, int, int]]:
        if not text:
            return []

        cs = chunk_size if chunk_size is not None else self.chunk_size
        ov = overlap if overlap is not None else self.chunk_overlap

        if len(text) <= cs:
            return [(text, 0, 0)]

        chunks: List[Tuple[str, int, int]] = []
        start = 0
        idx = 0
        step = max(1, cs - ov)

        while start < len(text):
            end = min(start + cs, len(text))
            chunks.append((text[start:end], start, idx))
            if end >= len(text):
                break
            start += step
            idx += 1

        return chunks

    def _extract_chunk_with_llm(self, chunk_text: str) -> Optional[Dict[str, Any]]:
        if not chunk_text or len(chunk_text.strip()) < MIN_TEXT_LENGTH:
            return None

        try:
            raw_content = _call_llm(
                system_prompt=METADATA_PROMPT,
                user_content=f"TEKSTI I DOKUMENTIT PËR METADATA:\n{chunk_text}",
                json_mode=True,
                temperature=0.0,
                model=FAST_SEARCH_MODEL,   # ✅ FIX
            )

            if not raw_content:
                return None

            parsed = clean_and_parse_json(raw_content)
            if parsed and isinstance(parsed, dict):
                return parsed

        except Exception as e:
            logger.warning(f"⚠️ [METADATA] LLM chunk extraction failed: {e}")

        return None

    def _merge_chunk_results(
        self,
        chunk_results: List[Optional[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        valid = [r for r in chunk_results if isinstance(r, dict) and r]
        if not valid:
            return {}

        def _vote(field: str) -> Optional[str]:
            counts: Dict[str, int] = {}
            for r in valid:
                v = r.get(field)
                if v and str(v).strip():
                    key = str(v).strip()
                    counts[key] = counts.get(key, 0) + 1
            if not counts:
                return None
            return max(counts.items(), key=lambda x: x[1])[0]

        def _union_parties() -> List[Dict[str, str]]:
            seen = set()
            result = []
            for r in valid:
                parties = r.get("parties") or []
                if not isinstance(parties, list):
                    continue
                for p in parties:
                    if not isinstance(p, dict):
                        continue
                    role = str(p.get("role", "")).strip()
                    name = str(p.get("name", "")).strip()
                    if not name:
                        continue
                    key = (role.lower(), name.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    result.append({"role": role, "name": name})
            return result

        def _union_list(field: str) -> List[str]:
            seen = set()
            result = []
            for r in valid:
                items = r.get(field) or []
                if not isinstance(items, list):
                    continue
                for item in items:
                    s = str(item).strip()
                    if not s:
                        continue
                    low = s.lower()
                    if low in seen:
                        continue
                    seen.add(low)
                    result.append(s)
            return result

        def _max_amount() -> Optional[float]:
            amounts = []
            for r in valid:
                a = r.get("amount")
                if a is None:
                    continue
                try:
                    amounts.append(float(a))
                except (ValueError, TypeError):
                    continue
            return max(amounts) if amounts else None

        return {
            "court": _vote("court"),
            "judge": _vote("judge"),
            "case_number": _vote("case_number"),
            "document_type": _vote("document_type"),
            "date": _vote("date"),
            "subject": _vote("subject"),
            "deadline_mentioned": _vote("deadline_mentioned"),
            "amount": _max_amount(),
            "jurisdiction_check": _vote("jurisdiction_check") or "KOSOVË",
            "parties": _union_parties(),
            "statute": _union_list("statute"),
            "articles": _union_list("articles"),
        }

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}

        if not text:
            return metadata

        def _search_full(pattern: re.Pattern, source: str):
            if len(source) <= MAX_SCAN_CHUNK:
                return pattern.search(source)
            for i in range(0, len(source), MAX_SCAN_CHUNK):
                m = pattern.search(source[i:i + MAX_SCAN_CHUNK])
                if m:
                    return m
            return None

        def _findall_full(pattern: re.Pattern, source: str) -> List[str]:
            if len(source) <= MAX_SCAN_CHUNK:
                return pattern.findall(source)
            results: List[str] = []
            for i in range(0, len(source), MAX_SCAN_CHUNK):
                results.extend(pattern.findall(source[i:i + MAX_SCAN_CHUNK]))
            return results

        m = _search_full(self.patterns['case_reference'], text)
        if m:
            metadata['case_number'] = m.group(1)

        m = _search_full(self.patterns['court'], text)
        if m:
            metadata['court'] = m.group(0).strip()

        m = _search_full(self.patterns['judge'], text)
        if m:
            metadata['judge'] = m.group(0).strip()

        m = _search_full(self.patterns['amount'], text)
        if m:
            metadata['amount'] = f"{m.group(1)} {m.group(2)}"

        parties: List[Dict[str, str]] = []
        if len(text) <= MAX_SCAN_CHUNK:
            matches = self.patterns['party'].findall(text)
        else:
            matches = []
            for i in range(0, len(text), MAX_SCAN_CHUNK):
                matches.extend(self.patterns['party'].findall(text[i:i + MAX_SCAN_CHUNK]))
        seen_parties = set()
        for role, name in matches:
            key = (role.lower().strip(), name.lower().strip())
            if key in seen_parties:
                continue
            seen_parties.add(key)
            parties.append({"role": role.strip(), "name": name.strip()})
        if parties:
            metadata['parties'] = parties

        statutes = _findall_full(self._extended_patterns['statute'], text)
        if statutes:
            seen = set()
            unique = []
            for s in statutes:
                low = s.lower().strip()
                if low in seen:
                    continue
                seen.add(low)
                unique.append(s.strip())
            metadata['statute'] = unique

        articles = _findall_full(self._extended_patterns['articles'], text)
        if articles:
            seen = set()
            unique = []
            for a in articles:
                low = a.lower().strip()
                if low in seen:
                    continue
                seen.add(low)
                unique.append(a.strip())
            metadata['articles'] = unique

        m = _search_full(self._extended_patterns['deadline_mentioned'], text)
        if m:
            metadata['deadline_mentioned'] = m.group(1).strip()

        return metadata

    def extract(
        self,
        text: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not text:
            return {
                "document_id": document_id,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "court": None,
                "judge": None,
                "case_number": None,
                "parties": [],
                "document_type": None,
                "amount": None,
                "date": None,
                "jurisdiction": "KOSOVË",
                "statute": [],
                "articles": [],
                "subject": None,
                "deadline_mentioned": None,
                "confidence": 0.0,
                "stats": {
                    "text_length": 0,
                    "total_chunks": 0,
                    "chunks_with_llm_success": 0,
                    "duration_sec": 0.0,
                },
                "warnings": ["Empty text provided"],
            }

        start_time = time.time()
        warnings: List[str] = []

        chunks = self._chunk_text(text)
        total_chunks = len(chunks)

        logger.info(
            f"🔍 [METADATA] Extraction start: doc={document_id}, "
            f"len={len(text)}, chunks={total_chunks}"
        )

        chunk_results: List[Optional[Dict[str, Any]]] = []
        llm_success = 0
        for chunk_text, _offset, chunk_idx in chunks:
            result = self._extract_chunk_with_llm(chunk_text)
            if result:
                llm_success += 1
            chunk_results.append(result)

        merged = self._merge_chunk_results(chunk_results)

        if not merged:
            warnings.append("LLM extraction produced no results — using regex fallback.")
            merged = self._extract_with_regex(text)

        confidence = round(llm_success / total_chunks, 2) if total_chunks else 0.0
        duration = round(time.time() - start_time, 2)

        result = {
            "document_id": document_id,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "court": merged.get("court"),
            "judge": merged.get("judge"),
            "case_number": merged.get("case_number"),
            "parties": merged.get("parties", []),
            "document_type": merged.get("document_type"),
            "amount": merged.get("amount"),
            "date": merged.get("date"),
            "jurisdiction": merged.get("jurisdiction_check", "KOSOVË"),
            "statute": merged.get("statute", []),
            "articles": merged.get("articles", []),
            "subject": merged.get("subject"),
            "deadline_mentioned": merged.get("deadline_mentioned"),
            "confidence": confidence,
            "stats": {
                "text_length": len(text),
                "total_chunks": total_chunks,
                "chunks_with_llm_success": llm_success,
                "duration_sec": duration,
            },
            "warnings": warnings,
        }

        logger.info(
            f"✅ [METADATA] Extraction complete: doc={document_id}, "
            f"chunks={total_chunks}, llm_ok={llm_success}, "
            f"duration={duration}s"
        )

        return result

    def extract_batch(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        results: Dict[str, Any] = {}
        total = len(documents)

        logger.info(f"🔍 [METADATA] Batch extraction: {total} documents")

        for idx, doc in enumerate(documents):
            doc_id = str(doc.get("id") or doc.get("_id") or f"doc_{idx}")
            doc_text = doc.get("text") or ""

            if progress_callback:
                try:
                    progress_callback("document_started", {
                        "document_index": idx,
                        "total_documents": total,
                        "document_id": doc_id,
                    })
                except Exception as e:
                    logger.warning(f"progress_callback (started) failed: {e}")

            results[doc_id] = self.extract(doc_text, document_id=doc_id)

            if progress_callback:
                try:
                    progress_callback("document_completed", {
                        "document_index": idx,
                        "total_documents": total,
                        "document_id": doc_id,
                    })
                except Exception as e:
                    logger.warning(f"progress_callback (completed) failed: {e}")

        duration = round(time.time() - start_time, 2)

        return {
            "documents": results,
            "stats": {
                "total_documents": total,
                "duration_sec": duration,
            },
        }


albanian_metadata_extractor = AlbanianMetadataExtractor()