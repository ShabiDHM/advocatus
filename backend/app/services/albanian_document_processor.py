# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V4.1
# 1. LOGIC: Replaced naïve slicing with LangChain's RecursiveCharacterTextSplitter.
# 2. ALBANIAN: Added specific separators (Neni, Pika, Kreu) to keep legal clauses intact.
# 3. METADATA: Enriches chunks with semantic context.

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
    Advanced processor for splitting Albanian legal text while preserving 
    semantic boundaries (Articles, Paragraphs, Sentences).
    """

    @staticmethod
    def _get_legal_separators() -> List[str]:
        """
         separators ordered by priority. 
         Keeps 'Neni X' or 'Kreu Y' at the start of chunks.
        """
        return [
            "\n\n",             # Paragraphs
            "\nKREU ",          # Chapter headers
            "\nNENI ",          # Article headers (Uppercase)
            "\nNeni ",          # Article headers (Titlecase)
            "\nArtikulli ",     # Alternative
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
        is_albanian: bool,
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
                "is_albanian_content": is_albanian,
                "processor_version": "V4.1-DEEPSEEK_READY",
                "char_count": len(content)
            })

            enriched_chunks.append(
                DocumentChunk(
                    content=content,
                    metadata=chunk_metadata
                )
            )

        return enriched_chunks