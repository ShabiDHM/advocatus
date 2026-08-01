# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V32.1 (MULTI-LANGUAGE & STRICT ARTICLE CHUNKING)
# 1. MULTI-LANGUAGE SUPPORT: Fully supports Albanian (sq), English (en), and Serbian/Regional (sr).
# 2. LEGAL PRECISION: Splits statutory laws strictly by article boundaries across supported languages.
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
    Advanced multi-language processor for splitting legal text and documents.
    Supports Albanian (sq), English (en), and Serbian/Regional (sr).
    """

    @staticmethod
    def _extract_article_number(text: str) -> str:
        """Extracts article number across multiple languages."""
        match = re.search(r'\b(?:Neni|NENI|Artikulli|Article|Artikel|Član|Članak)\s+(\d+[a-zA-Z]*)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        if re.search(r'\b(?:Preambula|Hyrja|Preamble|Uvod)\b', text, re.IGNORECASE):
            return '0'
        return ''

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        language: str = "sq",
    ) -> List[DocumentChunk]:
        """
        Intelligently processes documents based on language ('sq', 'en', 'sr'):
        - Statutory laws: Splits strictly by article/section boundaries.
        - Commentaries/manuals: Uses semantic paragraph chunking.
        """
        if not text_content:
            return []

        lang = language.lower() if language else "sq"

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

        # Check if text contains statutory law article markers in any supported language
        is_statutory_law = bool(re.search(r'\b(?:Neni|NENI|Artikulli|Article|Artikel|Član|Članak)\s+\d+', text_content, re.IGNORECASE))

        if is_statutory_law:
            print(f"⚖️ [DocumentProcessor] Statutory Law detected ({lang}): Splitting strictly by Article boundaries.")

            # Split text by Article boundaries across languages
            article_pattern = re.compile(r'(?=\b(?:Neni|NENI|Artikulli|Article|Artikel|Član|Članak)\s+\d+)', re.IGNORECASE)

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
                        "language": lang,
                        "processor_version": "V32.1-MULTI-ARTICLE",
                        "article_number": art_num,
                        "is_article": bool(art_num),
                        "char_count": len(cleaned_art)
                    })

                    enriched_chunks.append(
                        DocumentChunk(content=cleaned_art, metadata=chunk_metadata)
                    )
                    global_chunk_index += 1
        else:
            print(f"📚 [DocumentProcessor] Commentary/Manual detected ({lang}): Using semantic paragraph chunking.")
            
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
                        "language": lang,
                        "processor_version": "V32.1-MULTI-SEMANTIC",
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