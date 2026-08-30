# FILE: backend/app/services/rag/context_builder.py
# PHOENIX PROTOCOL - CONTEXT BUILDER V4.0 (SMART DOCUMENT PRIORITIZATION)

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 140_000  # Ende i plotë

class ContextBuilder:
    """
    V4.0: Rendit dokumentet sipas rëndësisë.
    AI i sheh të gjitha dokumentet — jo i verbër.
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
    def _prioritize_documents(documents: List[Dict]) -> List[Dict]:
        """
        Rendit dokumentet sipas rëndësisë juridike.
        """
        priority_keywords = {
            "vendim": 100,
            "aktgjykim": 100,
            "aktvendim": 100,
            "urdhër": 90,
            "urdher": 90,
            "ekspertiz": 90,
            "raport": 80,
            "test": 80,
            "procesverbal": 75,
            "deklarat": 70,
            "marrëvesh": 70,
            "padi": 65,
            "kallëzim": 65,
            "kallzim": 65,
            "ankes": 65,
            "apel": 65,
            "korrespondenc": 40,
            "email": 30,
        }
        
        def get_priority(doc: Dict) -> int:
            file_name = (doc.get("file_name") or "").lower()
            title = (doc.get("title") or "").lower()
            combined = f"{file_name} {title}"
            
            max_priority = 0
            for keyword, priority in priority_keywords.items():
                if keyword in combined:
                    max_priority = max(max_priority, priority)
            
            return max_priority
        
        # Sorto sipas prioritetit (më i lartë i pari)
        return sorted(documents, key=get_priority, reverse=True)

    @staticmethod
    def build(
        case_docs: List[Dict],
        global_docs: List[Dict],
        db_documents: List[Dict]
    ) -> Tuple[str, str]:
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE >>>\n"]
        context_blocks = []
        
        # PHOENIX FIX V4.0: Rendit dokumentet sipas rëndësisë
        prioritized_docs = ContextBuilder._prioritize_documents(db_documents)
        
        if prioritized_docs:
            for idx, doc in enumerate(prioritized_docs, 1):
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

                dense_passport = summ or raw_t[:800] or "Shkresë e administruar."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:300]}")
                
                # PHOENIX FIX: Të gjitha dokumentet përfshihen — të plota
                if raw_t:
                    context_blocks.append(f"\n--- SHKRESA: {doc_clickable_link} ---\n{raw_t}\n")
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura.\n\n")

        context_blocks.append("\n<<< PARAGRAFET NGA KËRKIMI SEMANTIK >>>\n")
        for d in case_docs:
            src = d.get('source') or 'Dokument'
            page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
            text = ContextBuilder._get_expanded_text(d)
            context_blocks.append(f"[{src}{page_info}]:\n{text}\n")

        context_blocks.append("\n<<< BAZA STATUTORE DHE JURISPRUDENCA >>>\n")
        for d in global_docs:
            source_tag = d.get('source') or 'Burim Juridik'
            text = ContextBuilder._get_expanded_text(d)
            context_blocks.append(f"BURIMI: {source_tag}\nPËRMBAJTJA: {text}\n")

        full_context = "".join(context_blocks)
        
        logger.info(f"📊 [Context] Gjithsej: {len(full_context)} karaktere")
        return "\n".join(manifest_lines), full_context