# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V5 (KOSOVO CONTEXT)
# 1. SCOPE: Optimization for ALBANIAN LANGUAGE legal texts (Kosovo Jurisdiction).
# 2. LOGIC: Recursive splitting with legal delimiters (Neni, Kreu, Pika).
# 3. METADATA: Tags chunks with language='sq' to distinguish from jurisdiction.

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
    Advanced processor for splitting Albanian-language legal text (Kosovo Context)
    while preserving semantic boundaries (Articles, Paragraphs, Sentences).
    """

    @staticmethod
    def _get_legal_separators() -> List[str]:
        """
        Separators ordered by priority for Kosovo Legal Texts.
        """
        return [
            "\n\n",             # Paragraphs
            "\nKREU ",          # Chapter headers
            "\nNENI ",          # Article headers (Uppercase)
            "\nNeni ",          # Article headers (Titlecase)
            "\nArtikulli ",     # Alternative
            "\nPika ",          # Points/Clauses (Common in Kosovo Law)
            ". ",               # Sentences
            "; ",               # List items
            "\n",               # Line breaks
            " ",                # Words
            ""                  # Characters
        ]

    @classmethod
    def process_document(
        cls,
        text_content: str,
        document_metadata: Dict[str, Any],
        is_albanian: bool, # Refers to LANGUAGE (sq), not State.
    ) -> List[DocumentChunk]:
        """
        Splits text content and enriches chunks based on language detection.
        """
        if not text_content:
            return []

        # Configuration based on language
        chunk_size = 1200 if is_albanian else 1000
        chunk_overlap = 200
        
        # Select appropriate separators
        separators = cls._get_legal_separators() if is_albanian else ["\n\n", "\n", ". ", " ", ""]

        # Initialize Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False
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
                # PHOENIX: Use standard ISO code to avoid confusion with Jurisdiction
                "language": "sq" if is_albanian else "en", 
                "processor_version": "V5.0-KOSOVO_EXCLUSIVE",
                "char_count": len(content)
            })

            enriched_chunks.append(
                DocumentChunk(
                    content=content,
                    metadata=chunk_metadata
                )
            )

        return enriched_chunks