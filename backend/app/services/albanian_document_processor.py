# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V6 (SEMANTIC INTELLIGENCE)
# 1. INTELLIGENCE: Uses Regex Look-Ahead to split text exactly at 'Neni/Article' boundaries.
# 2. ACCURACY: Ensures an Article header (e.g. "Neni 5") is never separated from its content.
# 3. CONTEXT: Increased chunk size to 1500 chars to capture full legal clauses in one go.

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
    Advanced processor for splitting Albanian-language legal text (Kosovo Context).
    Uses Semantic Regex splitting to ensure Legal Articles remain intact.
    """

    @staticmethod
    def _get_legal_regex_separators() -> List[str]:
        """
        Regex Patterns for Kosovo Legal Structure.
        The '(?=...)' syntax is a Look-Ahead. It splits BEFORE the match,
        keeping the header attached to its content.
        """
        return [
            # 1. Major Divisions (Chapters)
            r"(?=\nKREU\s+[IVX0-9]+)",    
            
            # 2. Primary Legal Units (Articles) - The most critical split
            r"(?=\nNENI\s+\d+)",          # Uppercase: NENI 10
            r"(?=\nNeni\s+\d+)",          # Titlecase: Neni 10
            r"(?=\nArtikulli\s+\d+)",     # Alternative: Artikulli 10
            
            # 3. Sub-divisions (Paragraphs/Points)
            r"(?=\n\d+\.)",               # Numbered lists: 1. (Start of line)
            r"(?=\n[a-z]\))",             # Lettered lists: a) (Start of line)
            
            # 4. Fallbacks
            r"\n\n",                      # Standard paragraph break
            r"\.\s+",                     # Sentence end
        ]

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        is_albanian: bool,
    ) -> List[DocumentChunk]:
        """
        Splits text content and enriches chunks based on language detection.
        """
        if not text_content:
            return []

        # PHOENIX OPTIMIZATION:
        # Kosovo laws are dense. We need larger chunks to keep "Neni" and all its "Pika" together.
        # 1500 chars is approx 300-400 words, usually enough for one full legal article.
        chunk_size = 1500 if is_albanian else 1000
        chunk_overlap = 200 # Overlap ensures context flows if an article is huge
        
        if is_albanian:
            # SEMANTIC REGEX SPLITTER
            separators = cls._get_legal_regex_separators()
            is_separator_regex = True
            keep_separator = True # Important: Don't delete the "Neni" text during split
        else:
            # Standard Splitter for English/Other
            separators = ["\n\n", "\n", ". ", " ", ""]
            is_separator_regex = False
            keep_separator = False

        # Initialize Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            is_separator_regex=is_separator_regex,
            keep_separator=keep_separator,
            length_function=len
        )

        # Perform Split
        raw_chunks = text_splitter.split_text(text_content)

        enriched_chunks: List[DocumentChunk] = []
        for i, content in enumerate(raw_chunks):
            # Create a mutable copy of the base metadata
            chunk_metadata = document_metadata.copy()

            # Add context enrichment
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(raw_chunks),
                "language": "sq" if is_albanian else "en", 
                "processor_version": "V6.0-SEMANTIC_REGEX",
                "char_count": len(content)
            })

            enriched_chunks.append(
                DocumentChunk(
                    content=content,
                    metadata=chunk_metadata
                )
            )

        return enriched_chunks