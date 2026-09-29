# FILE: backend/app/services/law_library/service.py
# PHOENIX PROTOCOL - LAW LIBRARY SERVICE V6.0
#
# V6.0: FIX S1-S6 (auditim).
#   - S1: Post-check aktive (bëhet në router)
#   - S2: Singleton factory me cache (opsionale)
#   - S3: Init validation
#   - S4: Nuk ka self-referential verify (tani përdor source_text nga DB)
#   - S5: Metrics/logging
#   - S6: Docstring i saktë

import logging
from typing import Dict, Any, Optional

from .article_fetcher import fetch_article_from_db, article_exists
from .prompts import build_sokrati_prompt, build_auditor_prompt
from .post_processor import verify_explanation_output

logger = logging.getLogger(__name__)


class LawLibraryService:
    """
    V6.0 — Biblioteka Ligjore.
    Arkitektura: DB-ja jep tekstin → LLM shpjegon → Post-check në router.
    """

    def __init__(self, db):
        if db is None:
            raise ValueError("LawLibraryService: db nuk mund të jetë None")
        self.db = db

    def get_article_context(
        self,
        law_title: str,
        article_number: str,
    ) -> Optional[Dict[str, Any]]:
        """Kthen tekstin e nenit nga DB (ose None)."""
        if not law_title or not article_number:
            return None
        return fetch_article_from_db(self.db, law_title, article_number)

    def article_exists(self, law_title: str, article_number: str) -> bool:
        """Kontroll i shpejtë ekzistence."""
        return article_exists(self.db, law_title, article_number)

    def build_explain_prompt(
        self,
        law_title: str,
        article_number: str,
        article_context: Dict[str, Any],
    ) -> str:
        """Ndërton prompt-in për Sokratin."""
        if not article_context:
            raise ValueError("article_context required")
        return build_sokrati_prompt(
            law_title=article_context.get("law_title", law_title),
            article_number=article_number,
            article_text=article_context.get("text", ""),
            source=article_context.get("source", ""),
            page=article_context.get("page") or 0,
        )

    def build_audit_prompt(
        self,
        law_title: str,
        article_number: str,
        article_context: Dict[str, Any],
    ) -> str:
        """Ndërton prompt-in për Auditori."""
        if not article_context:
            raise ValueError("article_context required")
        return build_auditor_prompt(
            law_title=article_context.get("law_title", law_title),
            article_number=article_number,
            article_text=article_context.get("text", ""),
            source=article_context.get("source", ""),  # S4: tani kalohet source
        )

    def verify_output(
        self,
        output_text: str,
        article_context: Dict[str, Any],
        article_number: str,
    ) -> Dict[str, Any]:
        """
        S4: Verifikon output kundrejt TEKSTIT REAL nga DB (jo self-referential).
        """
        if not article_context:
            return {
                "is_clean": False,
                "extra_articles": [],
                "extra_law_numbers": [],
                "correction_note": "⚠️ Article context mungon.",
                "metadata": {"reason": "no_context"},
            }

        return verify_explanation_output(
            output_text=output_text,
            source_text=article_context.get("text", ""),
            source_article=article_number,
            source_law_title=article_context.get("law_title", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY (S2)
# ═══════════════════════════════════════════════════════════════════════════

_SERVICE_CACHE: Dict[int, LawLibraryService] = {}


def get_law_library_service(db) -> LawLibraryService:
    """
    S2: Kthen instancë të cache-uar sipas id(db) — zvogëlon alokime.
    """
    if db is None:
        raise ValueError("db required")
    key = id(db)
    if key not in _SERVICE_CACHE:
        _SERVICE_CACHE[key] = LawLibraryService(db)
    return _SERVICE_CACHE[key]


__all__ = ["LawLibraryService", "get_law_library_service"]