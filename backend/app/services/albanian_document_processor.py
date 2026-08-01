# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V33.0 (ACADEMY vs STATUTORY SEPARATION)
# 1. INTELLIGENT CLASSIFICATION: Distinguishes between formal statutory laws and Academy training manuals.
# 2. STATUTORY LAWS: Split strictly by true article boundaries (Neni X).
# 3. ACADEMY MANUALS: Split using clean semantic paragraph/page chunking without false article triggers.

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
        """Extracts true article numbers starting at the beginning of a line/heading."""
        match = re.search(r'^(?:Neni|NENI|Artikulli|Article)\s+(\d+[a-zA-Z]*)', text.strip(), re.IGNORECASE)
        if match:
            return match.group(1)
        if re.search(r'^(?:Preambula|Hyrja|Preamble)\b', text.strip(), re.IGNORECASE):
            return '0'
        return ''

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        language: str = "sq",
    ) -> List[DocumentChunk]:
        if not text_content:
            return []

        source_filename = str(document_metadata.get("source", "")).upper()
        is_academy_file = "AKADEMIA" in source_filename or "KOMMENTAR" in source_filename or "DORACAK" in source_filename

        # Step 1: Extract pages if page markers exist
        page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', text_content)
        content_by_page = {}
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

        # If it's an Academy file or commentary, use pure semantic chunking (no false Neni splits)
        if is_academy_file:
            print(f"📚 [DocumentProcessor] Academy/Commentary file detected: Using semantic pagination.")
            chunk_size = 1500
            chunk_overlap = 200
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=len
            )

            for page_num, page_text in content_by_page.items():
                if not page_text.strip():
                    continue

                split_texts = splitter.split_text(page_text)
                
                for text_chunk in split_texts:
                    if not text_chunk.strip():
                        continue

                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num,
                        "chunk_index": global_chunk_index,
                        "language": language,
                        "processor_version": "V33.0-ACADEMY-SEMANTIC",
                        "article_number": f"Pjesa {global_chunk_index + 1}",
                        "is_article": False,
                        "char_count": len(text_chunk)
                    })

                    enriched_chunks.append(
                        DocumentChunk(content=text_chunk, metadata=chunk_metadata)
                    )
                    global_chunk_index += 1
        else:
            # Formal Statutory Law: Split strictly by true Article boundaries at line starts
            print(f"⚖️ [DocumentProcessor] Statutory Law detected: Splitting strictly by Article boundaries.")
            article_pattern = re.compile(r'(?=\b(?:Neni|NENI|Artikulli|Article)\s+\d+)', re.IGNORECASE)

            for page_num, page_text in content_by_page.items():
                if not page_text.strip():
                    continue

                raw_articles = article_pattern.split(page_text)
                
                for art_content in raw_articles:
                    cleaned_art = art_content.strip()
                    if not cleaned_art or len(cleaned_art) < 10:
                        continue

                    art_num = cls._extract_article_number(cleaned_art)
                    if not art_num:
                        continue # Skip non-article fragments to keep table of contents clean

                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num,
                        "chunk_index": global_chunk_index,
                        "language": language,
                        "processor_version": "V33.0-STATUTORY-STRICT",
                        "article_number": art_num,
                        "is_article": True,
                        "char_count": len(cleaned_art)
                    })

                    enriched_chunks.append(
                        DocumentChunk(content=cleaned_art, metadata=chunk_metadata)
                    )
                    global_chunk_index += 1

        total = len(enriched_chunks)
        for chunk in enriched_chunks:
            chunk.metadata["total_chunks"] = total
            
        return enriched_chunks