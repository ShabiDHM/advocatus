# FILE: backend/app/services/law_library/service.py
# PHOENIX PROTOCOL - LAW LIBRARY SERVICE V5.1
# V5.1: Hequr dead imports: time, AsyncGenerator, Callable.
# V5.0: Orkestrimi: Python verifikon → LLM shpjegon.

import logging
from typing import Dict, Any, Optional

from .article_fetcher import fetch_article_from_db
from .prompts import build_sokrati_prompt, build_auditor_prompt
from .post_processor import verify_explanation_output

logger = logging.getLogger(__name__)


class LawLibraryService:
    """
    V5.1 — Shërbim i Bibliotekës Ligjore.
    Arkitekturë: DB-ja jep tekstin → LLM shpjegon → Post-check.
    """

    def __init__(self, db):
        self.db = db

    # ═══════════════════════════════════════════════════════════════════
    # FETCH CONTEXT
    # ═══════════════════════════════════════════════════════════════════

    def get_article_context(
        self,
        law_title: str,
        article_number: str,
    ) -> Optional[Dict[str, Any]]:
        """Kthen tekstin e nenit nga DB."""
        return fetch_article_from_db(self.db, law_title, article_number)

    # ═══════════════════════════════════════════════════════════════════
    # BUILD PROMPT
    # ═══════════════════════════════════════════════════════════════════

    def build_explain_prompt(
        self,
        law_title: str,
        article_number: str,
        article_context: Dict[str, Any],
    ) -> str:
        """Ndërton prompt-in për Sokratin."""
        return build_sokrati_prompt(
            law_title=article_context.get("law_title", law_title),
            article_number=article_number,
            article_text=article_context.get("text", ""),
            source=article_context.get("source", ""),
            page=article_context.get("page", 0),
        )

    def build_audit_prompt(
        self,
        law_title: str,
        article_number: str,
        article_context: Dict[str, Any],
    ) -> str:
        """Ndërton prompt-in për Auditori."""
        return build_auditor_prompt(
            law_title=article_context.get("law_title", law_title),
            article_number=article_number,
            article_text=article_context.get("text", ""),
        )

    # ═══════════════════════════════════════════════════════════════════
    # POST-CHECK
    # ═══════════════════════════════════════════════════════════════════

    def verify_output(
        self,
        output_text: str,
        article_context: Dict[str, Any],
        article_number: str,
    ) -> Dict[str, Any]:
        """Verifikon që output-i nuk ka nene/lëgj të shpikura."""
        return verify_explanation_output(
            output_text=output_text,
            source_text=article_context.get("text", ""),
            source_article=article_number,
            source_law_title=article_context.get("law_title", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def get_law_library_service(db) -> LawLibraryService:
    return LawLibraryService(db)