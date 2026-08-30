# FILE: backend/app/services/rag/context_builder.py
# PHOENIX PROTOCOL - CONTEXT BUILDER V2.0 (FULL CONTEXT - NO BLINDNESS)

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# PHOENIX FIX: Konteksti i plotë — AI i sheh të gjitha dokumentet
MAX_CONTEXT_CHARS = 140_000
MAX_DOC_BUDGET = 15_000  # Maksimumi për çdo dokument individual

class ContextBuilder:
    """
    Ndërton kontekstin e plotë nga dokumentet — V2.0.
    Nuk e shkurton kontekstin — ResponseGenerator do ta ndajë në chunks nëse duhet.
    """

    @staticmethod
    def _get_expanded_text(d: Dict[str, Any]) -> str:
        metadata = d.get('metadata') or {}
        return (
            d.get('parent_text') or
            metadata.get('parent_text') or
            d.get('text') or
            metadata.get('text') or
            d.get('content') or
            metadata.get('content') or
            ""
        ).strip()

    @staticmethod
    def build(
        case_docs: List[Dict],
        global_docs: List[Dict],
        db_documents: List[Dict]
    ) -> Tuple[str, str]:
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE DHE PASAPORTA FORENZIKE E FASHIKULLIT >>>\n"]
        context_blocks = []
        
        if db_documents:
            doc_budget = int((MAX_CONTEXT_CHARS * 0.70) / max(len(db_documents), 1))
            doc_budget = max(doc_budget, 7_000)
            
            for idx, doc in enumerate(db_documents, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or f"Dokument_{idx}.pdf"
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"
                
                raw_t = (
                    doc.get("extracted_text") or
                    doc.get("text_content") or
                    doc.get("text") or
                    doc.get("content") or
                    ""
                ).strip()
                
                summ = (doc.get("summary") or "").strip()
                if summ == "Sinteza...":
                    summ = ""

                dense_passport = summ or raw_t[:1500] or "Shkresë e administruar në fashikull."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:400]}")
                
                if len(db_documents) <= 15 and raw_t:
                    context_blocks.append(f"\n--- TEKSTI I PLOTË I SHKRESËS: {doc_clickable_link} ---\n{raw_t[:doc_budget]}\n")
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        context_blocks.append("\n<<< PARAGRAFET FORENZIKE NGA KËRKIMI SEMANTIK NË FASHIKULL >>>\n")
        for d in case_docs:
            src = d.get('source') or 'Dokument'
            page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
            context_blocks.append(f"[{src}{page_info}]:\n{ContextBuilder._get_expanded_text(d)}\n")

        context_blocks.append("\n<<< BAZA STATUTARE DHE JURISPRUDENCA E GJYKATËS SUPREME >>>\n")
        for d in global_docs:
            source_tag = d.get('source') or 'Burim Juridik'
            context_blocks.append(f"BURIMI: {source_tag}\nPËRMBAJTJA: {ContextBuilder._get_expanded_text(d)}\n")

        full_context = "".join(context_blocks)
        
        if len(full_context) > MAX_CONTEXT_CHARS:
            full_context = full_context[:MAX_CONTEXT_CHARS] + "\n[TË DHËNA TË PRERA PËR SHKAK TË MADHËSISË SË FASHIKULLIT]"

        return "\n".join(manifest_lines), full_context