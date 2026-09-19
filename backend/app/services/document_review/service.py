# FILE: backend/app/services/document_review/service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE V5.1 (REBUILD)
# Arkitekturë e re: Regex (Laborator) + MongoDB (Arkiva) + LLM (Narrative).
# V5.1: Hequr import i vjetër MAX_KB_LOOKUPS (nuk përdoret më).
# V5.0: Rishkruar nga e para.

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Set, Tuple

from .citation_extractor import build_citation_profile
from .fact_extractor import build_fact_profile
from .mongo_verifier import verify_all
from .prompts import DOCUMENT_REVIEW_PROMPTS, build_verified_context
from .streaming import synthesize_section_streaming
from .report_builder import build_full_report
from .persistence import (
    load_document,
    load_extraction,
    persist,
    empty_result,
)

logger = logging.getLogger(__name__)


class DocumentReviewService:
    """
    V5.1 (rebuild) — Orkestruesi.
    Arkitekturë: Fakte nga Python → Narrative nga LLM.
    """

    def __init__(self, db):
        self.db = db

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC — review
    # ═══════════════════════════════════════════════════════════════════

    def review(
        self,
        case_id: str,
        user_id: str,
        document_id: str,
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        # ═══ 1. LOAD ═══
        document = load_document(self.db, case_id, document_id)
        extraction = load_extraction(self.db, case_id, document_id)

        if not document and not extraction:
            return empty_result(case_id, document_id, "Document not found.")

        doc_text = (
            (extraction or {}).get("text")
            or document.get("content")
            or document.get("extracted_text")
            or document.get("text")
            or ""
        )
        if not doc_text.strip():
            return empty_result(case_id, document_id, "No text content.")

        document_type = (
            (extraction or {}).get("document_type")
            or document.get("document_type")
            or "Dokument"
        )
        file_name = document.get("file_name", "Dokument")

        logger.info(
            f"🔍 [DOC_REVIEW V5] Starting: doc={document_id}, "
            f"file={file_name}, type={document_type}, "
            f"len={len(doc_text)} chars"
        )

        # ═══ 2. LABORATORI — Ekstraktim deterministik ═══
        if progress_callback:
            try:
                progress_callback("section_started", {
                    "section_key": "extraction",
                    "section_title": "Duke nxjerrë citimet nga dokumenti...",
                })
            except Exception:
                pass

        citation_profile = build_citation_profile(doc_text)
        fact_profile = build_fact_profile(doc_text)

        logger.info(
            f"🔬 [EXTRACT] Articles={citation_profile['stats']['total_articles']}, "
            f"Laws={citation_profile['stats']['total_laws_by_number']}, "
            f"CaseNumbers={citation_profile['stats']['total_case_numbers']}, "
            f"Dates={fact_profile['stats']['total_dates']}, "
            f"Parties={fact_profile['stats']['total_parties']}"
        )

        # ═══ 3. ARKIVA — Verifikim në MongoDB ═══
        if progress_callback:
            try:
                progress_callback("section_started", {
                    "section_key": "verification",
                    "section_title": "Duke verifikuar citimet në bazën ligjore...",
                })
            except Exception:
                pass

        verification_report = verify_all(self.db, citation_profile)

        logger.info(
            f"📚 [VERIFY] Articles {verification_report['stats']['articles_verified']}/"
            f"{verification_report['stats']['articles_total']}, "
            f"Laws {verification_report['stats']['laws_verified']}/"
            f"{verification_report['stats']['laws_total']}, "
            f"Precedents {verification_report['stats']['precedents_verified']}/"
            f"{verification_report['stats']['case_numbers_cited']}"
        )

        # ═══ 4. NARRATIVE — Gjenero section by section ═══
        verified_context = build_verified_context(
            citation_profile=citation_profile,
            fact_profile=fact_profile,
            verification_report=verification_report,
            document_type=document_type,
            file_name=file_name,
        )

        logger.info(f"📝 [CONTEXT] Verified context built: {len(verified_context)} chars")

        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}

        for section_key, section_cfg in DOCUMENT_REVIEW_PROMPTS.items():
            section_start = time.time()
            section_title = section_cfg["title"]

            if progress_callback:
                try:
                    progress_callback("section_started", {
                        "section_key": section_key,
                        "section_title": section_title,
                    })
                except Exception:
                    pass

            try:
                content = synthesize_section_streaming(
                    section_key=section_key,
                    section_cfg=section_cfg,
                    verified_context=verified_context,
                    file_name=file_name,
                    document_type=document_type,
                    stream_callback=section_stream_callback,
                )

                sections[section_key] = {
                    "title": section_title,
                    "content": content,
                }
                section_stats[section_key] = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "content_length": len(content),
                }

                if progress_callback:
                    try:
                        progress_callback("section_completed", {
                            "section_key": section_key,
                            "section_title": section_title,
                            "content_length": len(content),
                        })
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"❌ [DOC_REVIEW] Section {section_key} failed: {e}")
                sections[section_key] = {
                    "title": section_title,
                    "content": "",
                    "error": str(e),
                }
                section_stats[section_key] = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "error": str(e),
                }

        # ═══ 5. MONTIMI FINAL — Report i plotë ═══
        document_meta = {
            "file_name": file_name,
            "document_type": document_type,
        }

        full_report = build_full_report(
            sections=sections,
            citation_profile=citation_profile,
            fact_profile=fact_profile,
            verification_report=verification_report,
            document_meta=document_meta,
        )

        duration = round(time.time() - start, 2)

        # ═══ 6. RESULT ═══
        result = {
            "case_id": case_id,
            "document_id": document_id,
            "scope": "document",
            "document_ids": [document_id],
            "document_type": document_type,
            "file_name": file_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "full_report": full_report,
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "scope": "document",
                "document_id": document_id,
                "file_name": file_name,
                "document_type": document_type,
                "text_length": len(doc_text),
                "citation_stats": citation_profile.get("stats", {}),
                "fact_stats": fact_profile.get("stats", {}),
                "verification_stats": verification_report.get("stats", {}),
                "sections_generated": len([s for s in sections.values() if s.get("content")]),
                "sections_total": len(DOCUMENT_REVIEW_PROMPTS),
                "report_chars": len(full_report),
                "duration_sec": duration,
            },
            "verification_details": {
                "citation_profile": citation_profile,
                "fact_profile": fact_profile,
                "verification_report": verification_report,
            },
            "section_stats": section_stats,
            "status": "completed",
        }

        # ═══ 7. PERSIST ═══
        persist(self.db, result)

        logger.info(
            f"✅ [DOC_REVIEW V5] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"articles_verified={verification_report['stats']['articles_verified']}, "
            f"report_chars={len(full_report)}, "
            f"duration={duration}s"
        )

        return result


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def get_document_review_service(db) -> DocumentReviewService:
    return DocumentReviewService(db)