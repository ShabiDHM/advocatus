# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V7 (PAGE-AWARE)
# 1. FIX: Now detects 'FAQJA X' markers and injects 'page' into metadata.
# 2. ACCURACY: Ensures citations are traceable to the exact page number.

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Pydantic Model for Type Safety
class DocumentChunk(BaseModel):
    """Represents a single chunk of text from a document."""
    content: str = Field(..., description="The chunked text content.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk.")

class EnhancedDocumentProcessor:
    """
    Advanced processor for splitting Albanian-language legal text.
    Preserves page number metadata for accurate citations.
    """

    @staticmethod
    def _get_legal_regex_separators() -> List[str]:
        """
        Regex Patterns for Kosovo Legal Structure.
        """
        return [
            r"(?=\nKREU\s+[IVX0-9]+)",    
            r"(?=\nNENI\s+\d+)",          
            r"(?=\nNeni\s+\d+)",          
            r"(?=\nArtikulli\s+\d+)",     
            r"(?=\n\d+\.)",               
            r"(?=\n[a-z]\))",             
            r"\n\n",                      
            r"\.\s+",                     
        ]

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        is_albanian: bool,
    ) -> List[DocumentChunk]:
        """
        Splits text content and enriches chunks with page number metadata.
        """
        if not text_content:
            return []

        # --- PHOENIX V7: PAGE AWARE CHUNKING ---
        # 1. Split the entire document by our page markers first.
        page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', text_content)
        
        # The first element is any text before page 1, usually empty.
        content_by_page = {}
        page_number = 1
        # Start from index 1 because the regex split gives us [text_before, page_num, text_on_page, page_num, ...]
        for i in range(1, len(page_splits), 2):
            page_num_str = page_splits[i]
            page_content = page_splits[i+1]
            try:
                page_number = int(page_num_str)
                content_by_page[page_number] = page_content
            except (ValueError, IndexError):
                continue
        
        # --- CHUNKING LOGIC (Applied per page) ---
        chunk_size = 1500 if is_albanian else 1000
        chunk_overlap = 200
        
        separators = cls._get_legal_regex_separators() if is_albanian else ["\n\n", "\n", ". ", " "]
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            is_separator_regex=is_albanian,
            keep_separator=is_albanian,
            length_function=len
        )
        
        enriched_chunks: List[DocumentChunk] = []
        global_chunk_index = 0

        # 2. Process each page's content individually
        for page_num, page_text in content_by_page.items():
            if not page_text.strip():
                continue

            raw_chunks = text_splitter.split_text(page_text)
            
            for content in raw_chunks:
                # Create a mutable copy of the base metadata
                chunk_metadata = document_metadata.copy()

                # PHOENIX FIX: Add the crucial page number metadata
                chunk_metadata.update({
                    "page": page_num,
                    "chunk_index": global_chunk_index,
                    "language": "sq" if is_albanian else "en", 
                    "processor_version": "V7.0-PAGE_AWARE",
                    "char_count": len(content)
                })

                enriched_chunks.append(
                    DocumentChunk(
                        content=content,
                        metadata=chunk_metadata
                    )
                )
                global_chunk_index += 1

        # Re-index total chunks
        for chunk in enriched_chunks:
            chunk.metadata["total_chunks"] = len(enriched_chunks)
            
        return enriched_chunks