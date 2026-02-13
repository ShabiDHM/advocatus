# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - INGESTION SCRIPT V3.0 (ARTICLE‑LEVEL METADATA)
# 1. ADDED: Law title extraction from document content (Kosovo standard).
# 2. ADDED: Article‑aware splitting – each chunk corresponds to one article.
# 3. ADDED: Metadata fields: law_title, article_number, source, jurisdiction, page.
# 4. FIXED: Now enables precise citations [Ligji, Neni XX](doc://ligji) in downstream RAG.
# 5. STATUS: Full article metadata extraction – no more “Neni përkatës” hallucinations.

import os
import sys
import glob
import hashlib
import argparse
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    try:
        from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
        from langchain_community.document_loaders import UnstructuredMarkdownLoader
    except ImportError:
        from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader, UnstructuredMarkdownLoader

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    import chromadb
    from app.core.embeddings import JuristiRemoteEmbeddings
    from chromadb.api.types import Metadata
except ImportError as e:
    print(f"❌ MISSING LIBRARIES: {e}")
    print("Run: pip install langchain-community langchain-text-splitters pypdf chromadb requests docx2txt unstructured")
    sys.exit(1)

# --- CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
COLLECTION_NAME = "legal_knowledge_base"
TARGET_JURISDICTION = 'ks'

print(f"⚙️  CONFIG: Chroma={CHROMA_HOST}:{CHROMA_PORT}")

# --- KOSOVO LAW PARSER (Article‑Aware) ---
def extract_law_title(full_text: str) -> str:
    """
    Attempts to extract the official law title from the beginning of a Kosovo law document.
    Common pattern: "LIGJI Nr. 2004/32 PËR FAMILJEN" or similar.
    """
    lines = full_text.split('\n')
    for line in lines[:20]:  # scan first 20 lines
        # Look for patterns: "LIGJI Nr. ..." or "LIGJI PËR ..."
        if re.match(r'^\s*LIGJI(\s+[Nn]r\.?\s*\d+)?(\s+PËR|\s+[A-Z])', line, re.IGNORECASE):
            # Clean up the line: strip, remove multiple spaces
            title = ' '.join(line.strip().split())
            return title
    # Fallback: use the first non‑empty line if it looks like a title
    for line in lines[:10]:
        if line.strip() and len(line.strip()) > 15 and not line.strip()[0].isdigit():
            return line.strip()
    return "Ligji i Republikës së Kosovës"  # ultimate fallback

def split_by_article(text: str) -> List[Tuple[str, str]]:
    """
    Splits a legal document into articles.
    Returns list of (article_number, article_content).
    """
    # Kosovo laws use "Neni [numri]" as article header
    pattern = r'(Neni\s+(\d+(?:\.\d+)?))'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    
    if len(matches) <= 1:
        # No clear article boundaries – treat whole document as one article (Neni 1)
        return [("1", text.strip())]
    
    articles = []
    for i, match in enumerate(matches):
        start = match.start()
        article_num = match.group(2).strip()
        # End is start of next article, or end of text
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        article_content = text[start:end].strip()
        articles.append((article_num, article_content))
    
    return articles

# --- FILE HASH (unchanged) ---
def calculate_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"⚠️ Could not hash file {filepath}: {e}")
        return ""

# --- MAIN INGESTION ---
def ingest_legal_docs(directory_path: str, force_reingest: bool = False):
    abs_path = os.path.abspath(directory_path)
    print(f"📂 Scanning Directory: {abs_path}")
    
    if not os.path.isdir(directory_path):
        print(f"❌ Directory not found: {directory_path}")
        print("   -> Did you mount the volume correctly in Docker?")
        return

    print(f"🔌 Connecting to ChromaDB (Target: {TARGET_JURISDICTION.upper()})...")
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=JuristiRemoteEmbeddings()
        )
        print("✅ Connected to Knowledge Base.")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    supported_extensions = ['*.pdf', '*.PDF', '*.docx', '*.DOCX', '*.txt', '*.TXT', '*.md', '*.MD']
    all_files = []
    for ext in supported_extensions:
        found = glob.glob(os.path.join(directory_path, "**", ext), recursive=True)
        all_files.extend(found)

    all_files = sorted(list(set(all_files)))

    if not all_files:
        print(f"⚠️ No documents found in {directory_path}")
        print(f"   -> Searched for: {supported_extensions}")
        return

    print(f"📚 Found {len(all_files)} files. Starting processing...")
    
    stats = {"skipped": 0, "added": 0, "updated": 0, "failed": 0}

    for file_path in all_files:
        filename = os.path.basename(file_path)
        
        try:
            current_hash = calculate_file_hash(file_path)
            
            # --- SKIP if unchanged AND not forced ---
            if not force_reingest:
                existing_records = collection.get(
                    where={"source": filename},
                    limit=1,
                    include=["metadatas"]
                )
                ids = existing_records.get('ids', [])
                metas = existing_records.get('metadatas', [])
                
                if ids and metas and metas[0].get("file_hash") == current_hash and metas[0].get("jurisdiction") == TARGET_JURISDICTION:
                    print(f"⏭️  Skipped (Unchanged): {filename}")
                    stats["skipped"] += 1
                    continue
            
            # --- DELETE OLD VECTORS IF EXIST ---
            collection.delete(where={"source": filename})
            if 'ids' in locals() and ids:
                stats["updated"] += 1
                print(f"🔄 Re‑ingesting: {filename}")
            else:
                stats["added"] += 1
                print(f"➕ Adding: {filename}")

            # --- LOAD DOCUMENT ---
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf':
                loader = PyPDFLoader(file_path)
            elif ext == '.docx':
                loader = Docx2txtLoader(file_path)
            elif ext == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif ext == '.md':
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                continue

            docs = loader.load()
            if not docs:
                print(" -> ⚠️ Empty Document")
                continue

            # --- COMBINE ALL PAGES INTO ONE TEXT ---
            full_text = "\n".join([d.page_content for d in docs])

            # --- EXTRACT LAW TITLE ---
            law_title = extract_law_title(full_text)

            # --- SPLIT BY ARTICLE ---
            articles = split_by_article(full_text)
            print(f"     📖 Detected {len(articles)} article(s)", end="", flush=True)

            # --- EMBEDDING BATCH PREPARATION ---
            batch_ids = []
            batch_texts = []
            batch_metadatas = []

            for article_num, article_content in articles:
                # Further split article if it's too long (preserve article boundaries)
                # Use small chunks with overlap but keep article number on all chunks
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                chunks = splitter.split_text(article_content)
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{filename}_art{article_num}_ch{i}_{TARGET_JURISDICTION}_{current_hash[:8]}"
                    batch_ids.append(chunk_id)
                    batch_texts.append(chunk)
                    
                    metadata = {
                        "source": filename,
                        "law_title": law_title,
                        "article_number": str(article_num),
                        "type": "LAW",
                        "jurisdiction": TARGET_JURISDICTION,
                        "file_hash": current_hash,
                        "page": 0,  # page info is lost after combining; could be improved
                    }
                    batch_metadatas.append(metadata)

            # --- ADD TO CHROMA IN BATCHES ---
            BATCH_SIZE = 50
            for i in range(0, len(batch_ids), BATCH_SIZE):
                collection.add(
                    ids=batch_ids[i:i+BATCH_SIZE],
                    documents=batch_texts[i:i+BATCH_SIZE],
                    metadatas=batch_metadatas[i:i+BATCH_SIZE]  # type: ignore
                )
                print(".", end="", flush=True)
            print(" ✅")
            
        except Exception as e:
            print(f" -> ❌ Error: {e}")
            stats["failed"] += 1

    print("-" * 50)
    print(f"🏁 Ingestion Complete [{TARGET_JURISDICTION.upper()}].")
    print(f"   Added:   {stats['added']}")
    print(f"   Updated: {stats['updated']}")
    print(f"   Skipped: {stats['skipped']}")
    print("-" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Kosovo laws into ChromaDB with article‑level metadata.")
    parser.add_argument("path", nargs="?", default="/app/data/laws", help="Path to documents folder")
    parser.add_argument("--force", action="store_true", help="Force re‑ingest all files")
    
    args = parser.parse_args()
    ingest_legal_docs(args.path, force_reingest=args.force)