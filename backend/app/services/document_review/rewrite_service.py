# FILE: backend/app/services/document_review/rewrite_service.py
# PHOENIX PROTOCOL - DOCUMENT REWRITE SERVICE V2.4
# V2.4: MULTI-DEVICE — shtuar get_saved_rewrite() për të lexuar
#       rishkrimin e ruajtur nga cases.document_rewrites.{doc_id}.
#       - I njëjti rishkrim i aksesueshëm nga çdo pajisje.
#       - Filtro sipas doc_type (për të shmangur mospërputhje).
# V2.3: POST-PROCESSING — _normalize_rewrite_structure().
# V2.2: VALIDATION.
# V2.1: NO CONTEXT.

import os
import re
import time
import logging
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple

from bson import ObjectId
from bson.errors import InvalidId

from .persistence import load_document, load_extraction
from .rewrite_prompts import (
    build_chunk_rewrite_prompt,
    get_rewrite_doc_types,
    REWRITE_SYSTEM_PROMPT,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_DRAFT_CHARS,
)
from .rewrite_validator import validate_rewrite
from app.services.llm.llm_client import (
    _get_sync_client,
    DEEP_ANALYSIS_MODEL,
)

logger = logging.getLogger(__name__)

MAX_CONCURRENT_CHUNKS = int(os.getenv("REWRITE_MAX_WORKERS", "5"))
CHUNK_MAX_TOKENS = int(os.getenv("REWRITE_CHUNK_MAX_TOKENS", "3000"))
REWRITE_TEMPERATURE = float(os.getenv("REWRITE_TEMPERATURE", "0.3"))
REWRITE_MODEL = os.getenv("REWRITE_MODEL", DEEP_ANALYSIS_MODEL)


# ═══════════════════════════════════════════════════════════════════════════
# V2.3: STRUCTURE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

_DOC_TITLES = {
    "KALLËZIM PENAL",
    "PADI CIVILE",
    "PËRGJIGJE NË PADI",
    "KONTRATË",
    "KËRKESË / PROPOZIM",
    "ANKESË / KUNDËRSHTIM",
    "DOKUMENT TJETËR",
}

_SUB_SUB_KEYWORDS = (
    "Kualifikimi Ligjor Penal",
    "Elementi Objektiv",
    "Elementi Subjektiv",
    "Elementi Subjektiv (Dashja",
    "Kualifikimi Ligjor",
    "Veprimi ",
)


def _classify_heading(text: str) -> int:
    t = text.strip()
    if not t:
        return 4

    t_upper = t.upper()

    if t_upper in _DOC_TITLES:
        return 1

    for kw in _SUB_SUB_KEYWORDS:
        if t.startswith(kw):
            return 5

    if re.match(r'^GRUPI\s+[IVX]+', t_upper):
        return 3

    if re.match(r'^[IVX]+\.\s+[A-ZËÇÄÖÜ]', t):
        return 2

    if re.match(r'^[A-Z]\.\s+[A-ZËÇÄÖÜ]', t):
        return 3

    if re.match(r'^[IVX]+\.\d+', t):
        return 3

    stripped = re.sub(r'[—\-–:].*$', '', t).strip()
    words = stripped.split()
    if (
        2 <= len(words) <= 6
        and all(re.match(r'^[A-ZËÇÄÖÜ][A-ZËÇÄÖÜ\.\-]*$', w) for w in words)
        and not any(w.endswith('.') for w in words)
        and len(stripped) <= 60
    ):
        return 3

    if re.match(r'^(DR|PROF|M\.SC|MR|ZNJ|Z)\.?\s', t_upper):
        return 3

    if re.match(r'^Veprimi\s+\d+\.\d+', t):
        return 4

    if re.match(r'^(Kërkesa|Kërkesë|Sigurimin|Sigurimi|Marrjen|Marrja|Thirrjen|Thirrja|Verifikimin|Verifikimi|Administrimin|Administrimi|Sekuestrimin|Sekuestrimi|Garantimin|Garantimi|Ngritjen|Ngritja|Parashtruesi|Rekomandime|Rendi)', t):
        return 4

    if re.match(r'^(Cilësia|Cilesia|Baza|Aktvendimi|Aktakuza|Prova\s+\d+|Dëshmitar|Vendimi|Fillimi)', t):
        return 4

    if len(t) <= 60 and t.isupper() and len(t.split()) >= 2:
        return 3

    return 4


def _heading_dedup_key(text: str) -> str:
    key = text.upper()
    key = re.sub(r'^[IVX0-9]+\.\s*', '', key)
    key = re.sub(r'[^A-Z0-9ËÇÄÖÜ ]', '', key)
    key = re.sub(r'\s+', ' ', key).strip()
    return key


def _normalize_rewrite_structure(content: str) -> Tuple[str, Dict[str, int]]:
    if not content:
        return content, {"deduped": 0, "releveled": 0, "empty_removed": 0}

    lines = content.split('\n')
    result: List[str] = []

    seen_top_headings: Dict[str, int] = {}
    stats = {"deduped": 0, "releveled": 0, "empty_removed": 0}

    heading_pattern = re.compile(r'^(#{1,6})\s+(.+?)\s*$')

    for line in lines:
        m = heading_pattern.match(line)
        if not m:
            result.append(line)
            continue

        old_level = len(m.group(1))
        text = m.group(2).strip()

        new_level = _classify_heading(text)
        if new_level != old_level:
            stats["releveled"] += 1

        is_top = new_level <= 2
        is_grupi = bool(re.match(r'^GRUPI\s+[IVX]+', text.upper()))

        if is_top or is_grupi:
            key = _heading_dedup_key(text)
            if key in seen_top_headings:
                stats["deduped"] += 1
                logger.debug(f"🧹 [NORMALIZE] Skipped duplicate: '{text}'")
                continue
            seen_top_headings[key] = new_level

        result.append('#' * new_level + ' ' + text)

    cleaned: List[str] = []
    blank_count = 0
    for line in result:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                cleaned.append(line)
        else:
            blank_count = 0
            cleaned.append(line)

    final = '\n'.join(cleaned).strip()

    logger.info(
        f"🧹 [NORMALIZE V2.4] Structure: "
        f"deduped={stats['deduped']}, "
        f"releveled={stats['releveled']}"
    )

    return final, stats


# ═══════════════════════════════════════════════════════════════════════════
# SPLIT
# ═══════════════════════════════════════════════════════════════════════════

def _split_into_chunks(text: str, max_chars: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    if not text or not text.strip():
        return []

    if len(text) <= max_chars:
        return [text.strip()]

    parts = re.split(r'(\n#{2,3} )', text)

    combined: List[str] = []
    i = 0
    while i < len(parts):
        if i == 0:
            combined.append(parts[0])
            i += 1
        elif i + 1 < len(parts):
            combined.append(parts[i] + parts[i + 1])
            i += 2
        else:
            combined.append(parts[i])
            i += 1

    chunks: List[str] = []
    current = ""
    for part in combined:
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current += part
        else:
            if current:
                chunks.append(current)
            if len(part) > max_chars:
                sub_parts = part.split('\n\n')
                sub_current = ""
                for sp in sub_parts:
                    sep = "\n\n" if sub_current else ""
                    if len(sub_current) + len(sep) + len(sp) <= max_chars:
                        sub_current += sep + sp
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = sp
                if sub_current:
                    chunks.append(sub_current)
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)

    return [c.strip() for c in chunks if c.strip()]


# ═══════════════════════════════════════════════════════════════════════════
# LLM CALL
# ═══════════════════════════════════════════════════════════════════════════

def _call_llm_for_chunk(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = CHUNK_MAX_TOKENS,
    temperature: float = REWRITE_TEMPERATURE,
    model: str = REWRITE_MODEL,
) -> Dict[str, Any]:
    client = _get_sync_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    if not response or not response.choices:
        return {"content": "", "finish_reason": "empty", "input_tokens": 0, "output_tokens": 0}

    choice = response.choices[0]
    content = choice.message.content or ""
    finish_reason = getattr(choice, "finish_reason", "unknown")

    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

    return {
        "content": content,
        "finish_reason": finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _clean_llm_content(content: str) -> str:
    if not content:
        return ""
    content = content.strip()
    for prefix in (
        "Këtu është dokumenti i rishkruar:",
        "Ky është versioni i përditësuar:",
        "Dokumenti i rishkruar:",
        "Rishkrimi i pjesës:",
        "```markdown",
        "```",
    ):
        if content.startswith(prefix):
            content = content[len(prefix):].strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    return content


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_verification_findings(verification: Dict[str, Any]) -> str:
    lines = []

    readiness = verification.get("readiness", "I PANJOHUR")
    readiness_sq = {
        "READY": "GATI",
        "NEEDS WORK": "KËRKON PUNË",
        "INCOMPLETE": "I PËRPLOTË",
        "UNKNOWN": "I PANJOHUR",
    }.get(readiness, readiness)
    lines.append(f"Statusi i verifikimit: {readiness_sq}")
    lines.append("")

    sections = verification.get("sections", {}) or {}

    recommendations = sections.get("concrete_recommendations", {})
    if recommendations.get("content"):
        lines.append("### REKOMANDIMET KONKRETE")
        lines.append(recommendations["content"][:3500])
        lines.append("")

    legal = sections.get("legal_quality", {})
    if legal.get("content"):
        lines.append("### CILËSIA LIGJORE (nene)")
        lines.append(legal["content"][:1500])
        lines.append("")

    return "\n".join(lines).strip()


def _persist_rewrite(
    db,
    case_id: str,
    document_id: str,
    rewrite_entry: Dict[str, Any],
) -> bool:
    try:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        except InvalidId:
            c_oid = case_id

        minimal = {
            "doc_type": rewrite_entry.get("doc_type"),
            "doc_type_label": rewrite_entry.get("doc_type_label"),
            "file_name": rewrite_entry.get("file_name"),
            "built_at": rewrite_entry.get("built_at"),
            "content": rewrite_entry.get("content"),
            "content_chars": rewrite_entry.get("content_chars"),
            "original_chars": rewrite_entry.get("original_chars"),
            "duration_sec": rewrite_entry.get("duration_sec"),
            "score_before": rewrite_entry.get("score_before"),
            "chunks_total": rewrite_entry.get("chunks_total"),
            "chunks_failed": rewrite_entry.get("chunks_failed"),
            "input_tokens": rewrite_entry.get("input_tokens"),
            "output_tokens": rewrite_entry.get("output_tokens"),
            "validation": rewrite_entry.get("validation"),
            "structure_stats": rewrite_entry.get("structure_stats"),
        }

        result = db.cases.update_one(
            {"_id": c_oid},
            {"$set": {f"document_rewrites.{document_id}": minimal}},
            upsert=False,
        )

        if result.matched_count == 0:
            logger.warning(
                f"⚠️ [REWRITE PERSIST] Case nuk u gjet: case={case_id}, doc={document_id}"
            )
            return False

        logger.info(
            f"💾 [REWRITE PERSIST] Ruajtur: case={case_id}, doc={document_id}, "
            f"chars={minimal['content_chars']}, chunks={minimal['chunks_total']}, "
            f"validation={(minimal['validation'] or {}).get('severity', '?')}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ [REWRITE PERSIST] Dështoi: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════════════════

class DocumentRewriter:
    def __init__(self, db):
        self.db = db

    # ─────────────────────────────────────────────────────────────────────
    # V2.4: GET SAVED REWRITE (multi-device)
    # ─────────────────────────────────────────────────────────────────────
    def get_saved_rewrite(
        self,
        case_id: str,
        document_id: str,
        doc_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lexon rishkrimin e ruajtur nga cases.document_rewrites.{doc_id}.
        Kthen: {"has_rewrite": bool, "rewrite": {...}}
        """
        try:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            except InvalidId:
                c_oid = case_id

            case_doc = self.db.cases.find_one(
                {"_id": c_oid},
                {"document_rewrites": 1},
            )
            if not case_doc:
                return {"has_rewrite": False}

            rewrites = case_doc.get("document_rewrites") or {}
            entry = rewrites.get(document_id)

            if not entry:
                return {"has_rewrite": False}

            # Filtro sipas doc_type nëse jepet
            if doc_type and entry.get("doc_type") != doc_type:
                logger.info(
                    f"📭 [REWRITE GET] doc_type mismatch: "
                    f"saved={entry.get('doc_type')} requested={doc_type}"
                )
                return {"has_rewrite": False}

            logger.info(
                f"📖 [REWRITE GET] Found: case={case_id}, doc={document_id}, "
                f"chars={entry.get('content_chars')}, "
                f"doc_type={entry.get('doc_type')}"
            )

            return {
                "has_rewrite": True,
                "rewrite": {
                    "case_id": case_id,
                    "document_id": document_id,
                    "doc_type": entry.get("doc_type"),
                    "doc_type_label": entry.get("doc_type_label"),
                    "file_name": entry.get("file_name"),
                    "built_at": entry.get("built_at"),
                    "content": entry.get("content"),
                    "content_chars": entry.get("content_chars"),
                    "original_chars": entry.get("original_chars"),
                    "duration_sec": entry.get("duration_sec"),
                    "score_before": entry.get("score_before"),
                    "chunks_total": entry.get("chunks_total"),
                    "chunks_failed": entry.get("chunks_failed"),
                    "input_tokens": entry.get("input_tokens"),
                    "output_tokens": entry.get("output_tokens"),
                    "validation": entry.get("validation"),
                    "structure_stats": entry.get("structure_stats"),
                    "status": "completed",
                },
            }

        except Exception as e:
            logger.error(f"❌ [REWRITE GET] Failed: {e}")
            return {"has_rewrite": False, "error": str(e)[:200]}

    # ─────────────────────────────────────────────────────────────────────
    # REWRITE (i ri ose rigjenero)
    # ─────────────────────────────────────────────────────────────────────
    def _rewrite_chunks_parallel(
        self,
        chunks: List[str],
        doc_type: str,
        findings: str,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[str], Dict[str, Any]]:
        total = len(chunks)
        results: List[str] = [""] * total
        stats = {
            "chunks_total": total,
            "chunks_failed": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "finish_reasons": [],
        }

        def _emit(event: str, payload: Dict[str, Any]) -> None:
            if not progress_callback:
                return
            try:
                progress_callback(event, payload)
            except Exception:
                pass

        def _rewrite_one(i: int) -> Dict[str, Any]:
            chunk = chunks[i]

            prompt = build_chunk_rewrite_prompt(
                chunk_content=chunk,
                chunk_index=i + 1,
                total_chunks=total,
                doc_type=doc_type,
                verification_findings=findings,
            )

            _emit("step_started", {
                "step_key": f"chunk_{i + 1}",
                "step_title": f"Duke rishkruar pjesën {i + 1}/{total}...",
            })

            try:
                llm_result = _call_llm_for_chunk(
                    system_prompt=REWRITE_SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                content = _clean_llm_content(llm_result.get("content", ""))

                _emit("chunk_completed", {
                    "chunk_index": i + 1,
                    "total_chunks": total,
                    "chars": len(content),
                    "finish_reason": llm_result.get("finish_reason", "unknown"),
                })

                return {
                    "index": i,
                    "content": content,
                    "input_tokens": llm_result.get("input_tokens", 0),
                    "output_tokens": llm_result.get("output_tokens", 0),
                    "finish_reason": llm_result.get("finish_reason", "unknown"),
                    "ok": True,
                }

            except Exception as e:
                logger.error(f"❌ [REWRITE] Chunk {i + 1}/{total} failed: {e}")
                _emit("chunk_failed", {
                    "chunk_index": i + 1,
                    "total_chunks": total,
                    "error": str(e)[:200],
                })
                return {
                    "index": i,
                    "content": f"\n\n[Pjesa {i + 1} nuk u rishkrua: {e}]\n\n",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "finish_reason": "error",
                    "ok": False,
                }

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_CHUNKS,
            thread_name_prefix="rewrite_chunk",
        ) as executor:
            futures = {executor.submit(_rewrite_one, i): i for i in range(total)}

            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    results[res["index"]] = res["content"]
                    stats["input_tokens"] += res["input_tokens"]
                    stats["output_tokens"] += res["output_tokens"]
                    stats["finish_reasons"].append(res["finish_reason"])
                    if not res["ok"]:
                        stats["chunks_failed"] += 1
                except Exception as e:
                    i = futures[fut]
                    logger.error(f"❌ [REWRITE] Future {i} crashed: {e}")
                    results[i] = f"\n\n[Pjesa {i + 1} nuk u rishkrua.]\n\n"
                    stats["chunks_failed"] += 1

        return results, stats

    def rewrite(
        self,
        case_id: str,
        document_id: str,
        doc_type: str,
        verification: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        def _emit(event: str, payload: Dict[str, Any]) -> None:
            if not progress_callback:
                return
            try:
                progress_callback(event, payload)
            except Exception:
                pass

        allowed_types = get_rewrite_doc_types()
        if doc_type not in allowed_types:
            return {
                "status": "error",
                "error_message": f"Lloj dokumenti i panjohur: '{doc_type}'. "
                                 f"Të lejuara: {sorted(allowed_types.keys())}",
            }

        doc_type_label = allowed_types[doc_type]

        _emit("step_started", {
            "step_key": "loading",
            "step_title": "Duke lexuar draftin dhe rekomandimet...",
        })

        try:
            document = load_document(self.db, case_id, document_id)
            extraction = load_extraction(self.db, case_id, document_id)
        except Exception as e:
            logger.error(f"❌ [REWRITE] Load failed: {e}")
            return {"status": "error", "error_message": f"Gabim gjatë leximit: {e}"}

        if not document and not extraction:
            return {"status": "error", "error_message": "Drafti nuk u gjet në bazë."}

        draft_text = (
            (extraction or {}).get("text")
            or (document or {}).get("content")
            or (document or {}).get("extracted_text")
            or (document or {}).get("text")
            or ""
        )
        if not draft_text.strip():
            return {"status": "error", "error_message": "Drafti nuk ka tekst për rishkrim."}

        original_full_text = draft_text
        original_chars = len(draft_text)
        file_name = (document or {}).get("file_name", "draft")

        if original_chars > DEFAULT_MAX_DRAFT_CHARS:
            draft_text = draft_text[:DEFAULT_MAX_DRAFT_CHARS]
            logger.warning(
                f"⚠️ [REWRITE V2.4] Drafti u truncua: "
                f"{original_chars} → {DEFAULT_MAX_DRAFT_CHARS} chars"
            )

        logger.info(
            f"✍️ [REWRITE V2.4] Start: case={case_id}, doc={document_id}, "
            f"file={file_name}, doc_type={doc_type}, orig_chars={original_chars}"
        )

        if verification is None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one(
                    {"_id": c_oid},
                    {"case_document_verifications": 1},
                )
                verifs = (case_doc or {}).get("case_document_verifications") or {}
                verification = verifs.get(document_id)
            except Exception as e:
                logger.warning(f"⚠️ [REWRITE] Nuk u lexua verifikimi: {e}")
                verification = None

        if not verification or not verification.get("full_report"):
            return {
                "status": "error",
                "error_message": (
                    "Duhet të bëhet verifikimi para rishkrimit. "
                    "Kliko 'Verifiko Draftin' fillimisht."
                ),
            }

        if verification.get("sections"):
            findings = _build_verification_findings(verification)
        else:
            findings = verification.get("full_report", "")[:8000]

        chunks = _split_into_chunks(draft_text, max_chars=DEFAULT_CHUNK_SIZE)
        total_chunks = len(chunks)

        _emit("step_started", {
            "step_key": "chunking",
            "step_title": f"Duke ndarë dokumentin në {total_chunks} pjesë...",
        })

        logger.info(
            f"📦 [REWRITE V2.4] Split: {original_chars} chars → "
            f"{total_chunks} chunks (max {DEFAULT_CHUNK_SIZE} chars/chunk)"
        )

        _emit("step_started", {
            "step_key": "rewriting",
            "step_title": f"Duke rishkruar {total_chunks} pjesë paralel...",
        })

        t_llm = time.time()
        chunk_results, chunk_stats = self._rewrite_chunks_parallel(
            chunks=chunks,
            doc_type=doc_type,
            findings=findings,
            progress_callback=progress_callback,
        )
        llm_time = round(time.time() - t_llm, 2)

        _emit("step_started", {
            "step_key": "assembling",
            "step_title": "Duke bashkuar pjesët...",
        })

        raw_content = "\n\n".join(
            c.strip() for c in chunk_results if c and c.strip()
        ).strip()

        if not raw_content:
            return {"status": "error", "error_message": "Dokumenti final është bosh."}

        _emit("step_started", {
            "step_key": "normalizing",
            "step_title": "Duke normalizuar strukturën...",
        })

        t_norm = time.time()
        final_content, structure_stats = _normalize_rewrite_structure(raw_content)
        normalize_time = round(time.time() - t_norm, 2)

        if not final_content:
            return {"status": "error", "error_message": "Dokumenti final është bosh."}

        _emit("step_started", {
            "step_key": "validation",
            "step_title": "Duke verifikuar për halucinacione...",
        })

        t_validation = time.time()
        try:
            validation = validate_rewrite(
                original_text=original_full_text,
                rewritten_text=final_content,
            )
        except Exception as e:
            logger.error(f"❌ [REWRITE] Validation failed: {e}")
            validation = {
                "is_safe": False,
                "severity": "warning",
                "total_issues": 0,
                "issues": [],
                "stats": {},
                "high_count": 0,
                "medium_count": 0,
                "error": str(e)[:200],
            }
        validation_time = round(time.time() - t_validation, 2)

        _emit("validation_completed", {
            "severity": validation.get("severity"),
            "total_issues": validation.get("total_issues", 0),
            "high_count": validation.get("high_count", 0),
            "medium_count": validation.get("medium_count", 0),
        })

        rewritten_chars = len(final_content)
        ratio = round(rewritten_chars / original_chars * 100, 1) if original_chars > 0 else 0.0
        duration = round(time.time() - start, 2)

        cost_estimate = round(
            (chunk_stats["input_tokens"] / 1_000_000) * 0.14
            + (chunk_stats["output_tokens"] / 1_000_000) * 0.28,
            4
        )

        logger.info(
            f"✅ [REWRITE V2.4] Complete: "
            f"output={rewritten_chars} chars ({ratio}% e origjinalit), "
            f"orig={original_chars}, chunks={total_chunks} "
            f"(failed={chunk_stats['chunks_failed']}), "
            f"structure: deduped={structure_stats['deduped']}, "
            f"releveled={structure_stats['releveled']}, "
            f"tokens_in={chunk_stats['input_tokens']}, "
            f"tokens_out={chunk_stats['output_tokens']}, "
            f"cost≈${cost_estimate}, LLM={llm_time}s, "
            f"normalize={normalize_time}s, "
            f"validation={validation.get('severity')} "
            f"({validation.get('total_issues', 0)} issues, {validation_time}s), "
            f"total={duration}s"
        )

        if ratio < 70:
            logger.warning(
                f"⚠️ [REWRITE V2.4] Dokumenti i ri është {ratio}% e origjinalit."
            )

        if validation.get("severity") == "danger":
            logger.warning(
                f"🚨 [REWRITE V2.4] HALUCINACIONE të mundshme: "
                f"{validation.get('high_count', 0)} issue kritike!"
            )

        result = {
            "case_id": case_id,
            "document_id": document_id,
            "doc_type": doc_type,
            "doc_type_label": doc_type_label,
            "file_name": file_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content": final_content,
            "content_chars": rewritten_chars,
            "original_chars": original_chars,
            "ratio_pct": ratio,
            "chunks_total": total_chunks,
            "chunks_failed": chunk_stats["chunks_failed"],
            "input_tokens": chunk_stats["input_tokens"],
            "output_tokens": chunk_stats["output_tokens"],
            "cost_estimate_usd": cost_estimate,
            "duration_sec": duration,
            "llm_time_sec": llm_time,
            "validation_time_sec": validation_time,
            "structure_stats": structure_stats,
            "score_before": verification.get("score"),
            "readiness_before": verification.get("readiness"),
            "validation": validation,
            "status": "completed",
        }

        try:
            result["persisted"] = _persist_rewrite(
                self.db, case_id, document_id, result
            )
        except Exception as e:
            logger.warning(f"⚠️ [REWRITE] Persist failed: {e}")
            result["persisted"] = False

        return result


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def get_document_rewriter(db) -> DocumentRewriter:
    return DocumentRewriter(db)