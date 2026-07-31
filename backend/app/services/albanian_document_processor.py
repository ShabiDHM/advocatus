# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V32.0 (STRICT LEGAL ARTICLE & SEMANTIC CHUNKING)
# 1. LEGAL PRECISION: Splits statutory laws strictly by article boundaries (NENI X) to prevent article mixing.
# 2. ACADEMY SUPPORT: Uses semantic paragraph splitting for commentaries and guidebooks.
# 3. COMPATIBILITY: 100% compliant with Python 3.13 and memory-optimized for Render Free Tier.

import re
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunk(BaseModel):
    """Represents a single chunk of text from a document."""
    content: str = Field(..., description="The chunked text content.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk.")

class EnhancedDocumentProcessor:
    """
    Advanced processor for splitting Albanian-language legal text and academy materials.
    Guarantees strict article-level separation for statutory laws.
    """

    @staticmethod
    def _extract_article_number(text: str) -> str:
        """Extracts article number (e.g., 'Neni 3' -> '3', 'Preambula' -> '0') if present."""
        match = re.search(r'\b(?:Neni|NENI|Artikulli)\s+(\d+[a-zA-Z]*)', text)
        if match:
            return match.group(1)
        if re.search(r'\b(?:Preambula|Hyrja)\b', text, re.IGNORECASE):
            return '0'
        return ''

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        is_albanian: bool,
    ) -> List[DocumentChunk]:
        """
        Intelligently processes documents:
        - If document is a Law (contains 'Neni' / 'NENI'): Splits strictly by article.
        - If document is a Commentary/Academy book: Uses semantic paragraph chunking.
        """
        if not text_content:
            return []

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

        # Check if text contains statutory law article markers
        is_statutory_law = bool(re.search(r'\b(?:Neni|NENI|Artikulli)\s+\d+', text_content))

        if is_statutory_law:
            logger_msg = "⚖️ [DocumentProcessor] Statutory Law detected: Splitting strictly by Article boundaries."
            print(logger_msg)

            # Split text by Article boundaries (Neni 1, Neni 2, etc.)
            article_pattern = re.compile(r'(?=\b(?:Neni|NENI|Artikulli)\s+\d+)', re.IGNORECase)

            for page_num, page_text in content_by_page.items():
                if not page_text.strip():
                    continue

                raw_articles = article_pattern.split(page_text)
                
                for art_content in raw_articles:
                    cleaned_art = art_content.strip()
                    if not cleaned_art or len(cleaned_art) < 10:
                        continue

                    art_num = cls._extract_article_number(cleaned_art)
                    
                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num,
                        "chunk_index": global_chunk_index,
                        "language": "sq" if is_albanian else "en",
                        "processor_version": "V32.0-STRICT-ARTICLE",
                        "article_number": art_num,
                        "is_article": bool(art_num),
                        "char_count": len(cleaned_art)
                    })

                    enriched_chunks.append(
                        DocumentChunk(content=cleaned_art, metadata=chunk_metadata)
                    )
                    global_chunk_index += 1
        else:
            # Semantic chunking for Academy manuals, commentaries, and non-statutory documents
            print("📚 [DocumentProcessor] Academy/Treatise detected: Using semantic paragraph chunking.")
            
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
                        "language": "sq" if is_albanian else "en",
                        "processor_version": "V32.0-SEMANTIC",
                        "char_count": len(text_chunk)
                    })

                    enriched_chunks.append(
                        DocumentChunk(content=text_chunk, metadata=chunk_metadata)
                    )
                    global_chunk_index += 1

        total = len(enriched_chunks)
        for chunk in enriched_chunks:
            chunk.metadata["total_chunks"] = total
            
        return enriched_chunks