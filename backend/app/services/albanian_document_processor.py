# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V36.0 (UNIVERSAL ZERO-DISCARD CHUNKER FOR CASE EVIDENCE & STATUTES)

import re
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunk(BaseModel):
    content: str = Field(..., description="The chunked text content.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk.")

class EnhancedDocumentProcessor:

    @staticmethod
    def _extract_article_number(text: str) -> str:
        """Extracts article number strictly if a section starts with 'Neni X'."""
        match = re.search(r'^(?:Neni|NENI|Artikulli|Article)\s+(\d+[a-zA-Z]*)', text.strip(), re.IGNORECASE)
        if match:
            return match.group(1)
        return ''

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        language: str = "sq",
    ) -> List[DocumentChunk]:
        if not text_content or not text_content.strip():
            return []

        source_filename = str(document_metadata.get("source") or document_metadata.get("file_name") or "").upper()
        is_official_statute = document_metadata.get("is_official_statute", False) or "LIGJI" in source_filename or "KODI" in source_filename

        # Hapi 1: Nxjerrja e faqeve sipas shënuesve '--- [FAQJA X] ---'
        page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', text_content)
        content_by_page: Dict[int, str] = {}
        for i in range(1, len(page_splits), 2):
            try:
                page_num = int(page_splits[i])
                content_by_page[page_num] = page_splits[i+1]
            except (ValueError, IndexError):
                continue
        
        if not content_by_page:
            content_by_page[1] = text_content

        enriched_chunks: List[DocumentChunk] = []
        global_chunk_index = 0

        # PHOENIX FIX: Për të gjitha shkresat e lëndës (Vendime, Padi, Kontrata, etj.) përdoret ndarje e plotë pa fshirë asnjë fjalë!
        if not is_official_statute:
            chunk_size = 1200
            chunk_overlap = 200
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""], 
                length_function=len
            )

            for page_num, page_text in content_by_page.items():
                clean_page = page_text.strip()
                if not clean_page: 
                    continue

                for text_chunk in splitter.split_text(clean_page):
                    cleaned_chunk = text_chunk.strip()
                    if not cleaned_chunk or len(cleaned_chunk) < 15: 
                        continue

                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num, 
                        "chunk_index": global_chunk_index,
                        "language": language, 
                        "processor_version": "V36.0-CASE-EVIDENCE",
                        "article_number": f"Faqja {page_num}", 
                        "is_article": False,
                        "char_count": len(cleaned_chunk)
                    })
                    enriched_chunks.append(DocumentChunk(content=cleaned_chunk, metadata=chunk_metadata))
                    global_chunk_index += 1

        else:
            # Vetëm për Librat e Gazetës Zyrtare (Kodet dhe Ligjet e miratuara nga Kuvendi)
            article_pattern = re.compile(r'(?m)^(?=Neni\s+\d+|NENI\s+\d+|Artikulli\s+\d+)', re.IGNORECASE)

            for page_num, page_text in content_by_page.items():
                if not page_text.strip(): 
                    continue

                raw_articles = article_pattern.split(page_text)
                for art_content in raw_articles:
                    cleaned_art = art_content.strip()
                    if not cleaned_art or len(cleaned_art) < 15: 
                        continue

                    art_num = cls._extract_article_number(cleaned_art)
                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num, 
                        "chunk_index": global_chunk_index,
                        "language": language, 
                        "processor_version": "V36.0-STATUTORY",
                        "article_number": art_num or f"Pjesa {global_chunk_index + 1}", 
                        "is_article": bool(art_num),
                        "char_count": len(cleaned_art)
                    })

                    enriched_chunks.append(DocumentChunk(content=cleaned_art, metadata=chunk_metadata))
                    global_chunk_index += 1

        total = len(enriched_chunks)
        for chunk in enriched_chunks:
            chunk.metadata["total_chunks"] = total
            
        return enriched_chunks