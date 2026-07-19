# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V31.0 (PARENT-CHILD CHUNKING)
# 1. OPTIMIZATION: Implements Parent-Child chunking (1,000 char children / 4,000 char parents).
# 2. DESIGN: Embeds parent chunk content into child metadata for zero-lookup retrieval.
# 3. COMPATIBILITY: 100% compliant with Python 3.13 and memory-optimized for Render Free Tier.

import re
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunk(BaseModel):
    """Represents a single chunk of text from a document."""
    content: str = Field(..., description="The chunked text content (Child chunk).")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk (including Parent info).")

class EnhancedDocumentProcessor:
    """
    Advanced processor for splitting Albanian-language legal text.
    Implements Parent-Child Chunking to optimize retrieval granularity and preserve context.
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
        Splits text_content using Parent-Child chunking (4,000 char parents / 1,000 char children).
        Enriches chunks with page number metadata, parent IDs, and parent chunk contents.
        """
        if not text_content:
            return []

        # --- PHOENIX V31.0: PAGE AWARE PARSING ---
        page_splits = re.split(r'--- \[FAQJA (\d+)\] ---', text_content)
        
        content_by_page = {}
        for i in range(1, len(page_splits), 2):
            try:
                page_num = int(page_splits[i])
                page_content = page_splits[i+1]
                content_by_page[page_num] = page_content
            except (ValueError, IndexError):
                continue
        
        if not content_by_page:
            content_by_page[1] = text_content

        # --- CHUNKING CONFIGURATION ---
        parent_chunk_size = 4000
        parent_chunk_overlap = 400
        
        child_chunk_size = 1000
        child_chunk_overlap = 150
        
        separators = cls._get_legal_regex_separators() if is_albanian else ["\n\n", "\n", ". ", " "]
        
        # Define Parent and Child Splitters
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
            separators=separators,
            is_separator_regex=is_albanian,
            keep_separator=is_albanian,
            length_function=len
        )
        
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_chunk_overlap,
            separators=separators,
            is_separator_regex=is_albanian,
            keep_separator=is_albanian,
            length_function=len
        )
        
        enriched_chunks: List[DocumentChunk] = []
        global_chunk_index = 0

        for page_num, page_text in content_by_page.items():
            if not page_text.strip():
                continue

            # Step 1: Divide page into Parent Chunks
            parent_chunks = parent_splitter.split_text(page_text)
            
            for parent_index, parent_content in enumerate(parent_chunks):
                # Generate a unique, structured identifier for this parent context block
                parent_id = f"parent_{page_num}_{parent_index}_{uuid.uuid4().hex[:8]}"
                
                # Step 2: Divide this parent chunk into child chunks
                child_chunks = child_splitter.split_text(parent_content)
                
                for child_content in child_chunks:
                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num,
                        "chunk_index": global_chunk_index,
                        "language": "sq" if is_albanian else "en", 
                        "processor_version": "V31.0-PARENT-CHILD",
                        "char_count": len(child_content),
                        # Parent Reference Metadata for downstream RAG retrieval
                        "parent_id": parent_id,
                        "parent_text": parent_content,
                        "parent_char_count": len(parent_content),
                        "is_parent_child": True
                    })

                    enriched_chunks.append(
                        DocumentChunk(content=child_content, metadata=chunk_metadata)
                    )
                    global_chunk_index += 1

        total = len(enriched_chunks)
        for chunk in enriched_chunks:
            chunk.metadata["total_chunks"] = total
            
        return enriched_chunks