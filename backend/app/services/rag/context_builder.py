# FILE: backend/app/services/rag/context_builder.py
# PHOENIX PROTOCOL - CONTEXT BUILDER V2.0 (TOKEN-LIMIT AWARE)

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# PHOENIX FIX: Reduktuar nga 140_000 në 25_000 për të shmangur tejkalimin e token-eve
MAX_CONTEXT_CHARS = 25_000
MAX_DOC_BUDGET = 5_000  # Maksimumi për çdo dokument individual

class ContextBuilder:
    """
    Ndërton kontekstin nga dokumentet — V2.0 Token-Limit Aware.
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
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE >>>\n"]
        context_blocks = []
        
        if db_documents:
            # PHOENIX FIX: Dokumente më të shkurtra
            doc_budget = min(MAX_DOC_BUDGET, int(MAX_CONTEXT_CHARS * 0.50 / max(len(db_documents), 1)))
            doc_budget = max(doc_budget, 2_000)
            
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

                dense_passport = summ or raw_t[:800] or "Shkresë e administruar në fashikull."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:300]}")
                
                # PHOENIX FIX: Vetëm dokumentet më të rëndësishme marrin tekst të plotë
                if len(db_documents) <= 8 and raw_t:
                    context_blocks.append(f"\n--- TEKSTI I SHKRESËS: {doc_clickable_link} ---\n{raw_t[:doc_budget]}\n")
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        context_blocks.append("\n<<< PARAGRAFET NGA KËRKIMI SEMANTIK >>>\n")
        for d in case_docs[:10]:  # PHOENIX FIX: Vetëm 10 më të mirat
            src = d.get('source') or 'Dokument'
            page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
            text = ContextBuilder._get_expanded_text(d)
            context_blocks.append(f"[{src}{page_info}]:\n{text[:1500]}\n")  # PHOENIX FIX: 1500 karaktere max

        context_blocks.append("\n<<< BAZA STATUTORE DHE JURISPRUDENCA >>>\n")
        for d in global_docs[:8]:  # PHOENIX FIX: Vetëm 8 më të mirat
            source_tag = d.get('source') or 'Burim Juridik'
            text = ContextBuilder._get_expanded_text(d)
            context_blocks.append(f"BURIMI: {source_tag}\nPËRMBAJTJA: {text[:1500]}\n")  # PHOENIX FIX: 1500 karaktere max

        full_context = "".join(context_blocks)
        
        # PHOENIX FIX: Kontrolli përfundimtar — mos tejkalo 25_000
        if len(full_context) > MAX_CONTEXT_CHARS:
            full_context = full_context[:MAX_CONTEXT_CHARS] + "\n[KONTEKSTI U SHKURTUA PËR SHKAK TË MADHËSISË]"

        return "\n".join(manifest_lines), full_context