# FILE: backend/app/services/albanian_document_processor.py
# PHOENIX PROTOCOL - DOCUMENT PROCESSOR V35.0 (STRICT STATUTORY LINE-START PARSER)

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
        """Extracts true article number strictly from 'Neni X' headings."""
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

        if is_academy_file:
            chunk_size = 1500
            chunk_overlap = 200
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""], length_function=len
            )

            for page_num, page_text in content_by_page.items():
                if not page_text.strip(): continue
                for text_chunk in splitter.split_text(page_text):
                    if not text_chunk.strip(): continue
                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num, "chunk_index": global_chunk_index,
                        "language": language, "processor_version": "V35.0-ACADEMY",
                        "article_number": f"Pjesa {global_chunk_index + 1}", "is_article": False,
                        "char_count": len(text_chunk)
                    })
                    enriched_chunks.append(DocumentChunk(content=text_chunk, metadata=chunk_metadata))
                    global_chunk_index += 1
        else:
            # Statutory Laws: Split ONLY when a line starts with "Neni X"
            # This completely ignores internal paragraphs like "2.1", "2.2", "121.1", etc.
            article_pattern = re.compile(r'(?m)^(?=Neni\s+\d+|NENI\s+\d+|Artikulli\s+\d+)', re.IGNORECASE)

            for page_num, page_text in content_by_page.items():
                if not page_text.strip(): continue

                raw_articles = article_pattern.split(page_text)
                
                for art_content in raw_articles:
                    cleaned_art = art_content.strip()
                    if not cleaned_art or len(cleaned_art) < 15: continue

                    art_num = cls._extract_article_number(cleaned_art)
                    if not art_num:
                        # Capture Preamble at the very beginning of the document
                        if global_chunk_index == 0 and ("Kuvendi" in cleaned_art or "Miraton" in cleaned_art or "PËR" in cleaned_art):
                            art_num = '0'
                        else:
                            continue

                    chunk_metadata = document_metadata.copy()
                    chunk_metadata.update({
                        "page": page_num, "chunk_index": global_chunk_index,
                        "language": language, "processor_version": "V35.0-STATUTORY",
                        "article_number": art_num, "is_article": art_num != '0',
                        "char_count": len(cleaned_art)
                    })

                    enriched_chunks.append(DocumentChunk(content=cleaned_art, metadata=chunk_metadata))
                    global_chunk_index += 1

        total = len(enriched_chunks)
        for chunk in enriched_chunks:
            chunk.metadata["total_chunks"] = total
            
        return enriched_chunks