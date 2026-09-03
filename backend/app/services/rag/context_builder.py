# FILE: backend/app/services/rag/context_builder.py
# PHOENIX PROTOCOL - CONTEXT BUILDER V5.0 (MAXIMAL TEXT SELECTION & DEDUPLICATED RAG SYNTHESIS)

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Kufi i sigurt për modelet Tier-1 (GPT-4o 128K dhe Claude Sonnet 1M context)
MAX_CONTEXT_CHARS = 450_000


class ContextBuilder:
    """
    Ndërtuesi Qendror i Kontekstit Juridik (V5.0):
    - Zgjedh automatikisht tekstin më të gjatë dhe më cilësor të çdo shkrese.
    - Rendit dokumentet sipas hierarkisë gjyqësore (Vendime, Akte, Ekspertiza, Padi, etj.).
    - Deduplikon paragrafët që të mos harxhohen tokenë me përsëritje të kota.
    """

    @staticmethod
    def _get_best_document_text(doc: Dict[str, Any]) -> str:
        """
        Zgjedh tekstin më të pasur dhe më të gjatë të dokumentit,
        duke shmangur marrjen e fragmenteve të dështuara.
        """
        candidates = [
            doc.get("content") or "",
            doc.get("extracted_text") or "",
            doc.get("text_content") or "",
            doc.get("text") or "",
        ]
        
        # Filtro kandidatët e vlefshëm
        valid_candidates = [c.strip() for c in candidates if isinstance(c, str) and len(c.strip()) > 0]
        if not valid_candidates:
            return ""
        
        # Kthe tekstin më të gjatë dhe më shterrues
        return max(valid_candidates, key=len)

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
        Rendit dokumentet sipas rëndësisë dhe peshës provuese gjyqësore.
        """
        priority_keywords = {
            "aktvendim": 100,
            "aktgjykim": 100,
            "vendim": 95,
            "në emër të popullit": 95,
            "urdhër": 90,
            "urdher": 90,
            "ekspertiz": 85,
            "raport": 80,
            "procesverbal": 75,
            "padi": 70,
            "kundërpadi": 70,
            "kunderpadi": 70,
            "kallëzim": 70,
            "kallzim": 70,
            "ankes": 70,
            "kontratë": 65,
            "marrëvesh": 65,
            "korrespondenc": 40,
            "faturë": 40,
            "email": 30,
        }
        
        def get_priority(doc: Dict) -> int:
            file_name = (doc.get("file_name") or doc.get("title") or "").lower()
            max_priority = 0
            for keyword, priority in priority_keywords.items():
                if keyword in file_name:
                    max_priority = max(max_priority, priority)
            return max_priority
        
        return sorted(documents, key=get_priority, reverse=True)

    @staticmethod
    def build(
        case_docs: List[Dict],
        global_docs: List[Dict],
        db_documents: List[Dict]
    ) -> Tuple[str, str]:
        manifest_lines = ["\n<<< REGJISTRI DOKTRINAR I SHKRESAVE TË FASHIKULLIT >>>\n"]
        context_blocks: List[str] = []
        seen_texts = set()

        # 1. Renditja e dokumenteve sipas peshës ligjore
        prioritized_docs = ContextBuilder._prioritize_documents(db_documents)
        
        if prioritized_docs:
            for idx, doc in enumerate(prioritized_docs, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or f"Dokument_{idx}.pdf"
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"
                
                # Zgjedh tekstin më të plotë (content / extracted_text)
                raw_t = ContextBuilder._get_best_document_text(doc)
                
                summ = (doc.get("summary") or "").strip()
                if "sinteza" in summ.lower() or len(summ) < 20:
                    summ = ""

                dense_passport = summ or raw_t[:500] or "Shkresë e administruar në fashikull."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:250]}...")
                
                if raw_t:
                    context_blocks.append(f"\n{'='*50}\n📄 SHKRESA ZYRTARE: {doc_clickable_link}\n{'='*50}\n{raw_t}\n")
                    # Shënjo fjalitë e para për të shmangur duplikimin te kërkimi semantik
                    seen_texts.add(raw_t[:150].lower())
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        # 2. Paragrafët e veçantë nga kërkimi semantik (vetëm ato që nuk u përfshinë më sipër)
        semantic_blocks = []
        if case_docs:
            for d in case_docs:
                text = ContextBuilder._get_expanded_text(d)
                if text and len(text) > 40 and text[:150].lower() not in seen_texts:
                    src = d.get('source') or 'Dokument'
                    page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
                    semantic_blocks.append(f"📌 [{src}{page_info}]:\n{text}\n")
                    seen_texts.add(text[:150].lower())

        if semantic_blocks:
            context_blocks.append("\n<<< PROVAT KYÇE NGA KËRKIMI SEMANTIK >>>\n")
            context_blocks.extend(semantic_blocks)

        # 3. Jurisprudenca dhe Baza Ligjore Globale
        if global_docs:
            context_blocks.append("\n<<< JURISPRUDENCA DHE DITURIA GLOBALE E KOSOVËS >>>\n")
            for d in global_docs:
                source_tag = d.get('source') or 'Burim Juridik'
                text = ContextBuilder._get_expanded_text(d)
                if text and len(text) > 30:
                    context_blocks.append(f"🏛️ BURIMI: {source_tag}\n{text}\n")

        full_context = "".join(context_blocks)
        
        # Mbrojtje nga mbingarkesa ekstreme
        if len(full_context) > MAX_CONTEXT_CHARS:
            full_context = full_context[:MAX_CONTEXT_CHARS] + "\n\n[...Konteksti u optimizua për analizë maksimale...]"

        logger.info(f"📊 [ContextBuilder V5.0] U ndërtua konteksti me {len(full_context)} karaktere dhe {len(prioritized_docs)} shkresa.")
        return "\n".join(manifest_lines), full_context