# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - INGESTION SCRIPT V3.3 (ADVANCED NORMALIZATION)
# 1. ADDED: Robust cleaning for gazette headers, page numbers, footers.
# 2. ADDED: Multi‑pattern title extraction with filename fallback.
# 3. ADDED: Handles nested article numbers (e.g., "Neni 5.1").
# 4. STATUS: Ready for diverse Kosovo law documents.

import os
import sys
import glob
import hashlib
import argparse
import re
import uuid
from typing import List, Tuple, Optional
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

# ----------------------------------------------------------------------
# NORMALIZATION FUNCTIONS
# ----------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Aggressively remove common PDF artifacts from Kosovo legal documents.
    Handles:
      - Page numbers (various formats)
      - Gazette headers (e.g., "GAZETA ZYRTARE E REPUBLIKËS SË KOSOVËS / Nr. 17 / 18 TETOR 2018, PRISHTINË")
      - Repeated footers
      - Extra blank lines
    """
    # Remove page numbers (common patterns)
    patterns = [
        r'(?m)^\s*(?:Faqja|Page|F\.?)\s*\d+\s*(?:/\s*\d+)?\s*$',
        r'(?m)^\s*\d+\s*$',  # standalone numbers
        r'(?m)^\s*-\s*\d+\s*-\s*$',  # - 1 -
        r'(?m)^\s*\[\s*\d+\s*\]\s*$',  # [1]
    ]
    for pat in patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)

    # Remove common gazette headers (usually all caps, contain "GAZETA" and a date)
    # This regex removes lines that contain "GAZETA" and are relatively short (likely a header)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip lines that look like gazette headers: contain "GAZETA" or "ZYRTARE" and are not too long
        if re.search(r'GAZETA|ZYRTARE|PRISHTIN[ËE]', line, re.IGNORECASE) and len(line.strip()) < 100:
            continue
        # Skip lines that are all caps and contain "NR" or "VITI" (common in footers)
        if line.isupper() and re.search(r'NR\.?|VITI|FQ\.?', line, re.IGNORECASE):
            continue
        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Remove multiple blank lines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def extract_law_title(text: str, filename: str) -> str:
    """
    Extract the official law title from the beginning of the document.
    Uses multiple regex patterns to capture various formats:
      - LIGJI Nr. XXXX/YY PËR ...
      - KODI ... Nr. ...
      - GAZETA ZYRTARE ... (fallback to gazette reference)
    If all fail, returns a cleaned version of the filename.
    """
    # Take first few thousand characters for analysis
    sample = text[:5000]

    # Pattern 1: LIGJI Nr. [number] PËR [subject] (most common)
    match = re.search(r'(LIGJI\s+(?:[Nn]r\.?\s*[\d/]+)?\s*(?:PËR|MBI)\s+[A-ZËÇ][^.\n]*)', sample, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 2: KODI ... (e.g., KODI PENAL I REPUBLIKËS SË KOSOVËS)
    match = re.search(r'(KODI\s+[A-ZËÇ][^.\n]*)', sample, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 3: GAZETA ZYRTARE ... (use as fallback)
    match = re.search(r'(GAZETA\s+ZYRTARE[^.\n]*)', sample, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 4: Any line that is all caps and contains "LIGJ" or "KOD"
    lines = sample.split('\n')
    for line in lines[:30]:
        if line.isupper() and ('LIGJ' in line or 'KOD' in line):
            return line.strip()

    # Fallback: clean filename (remove extension and underscores)
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[_-]', ' ', name)
    name = ' '.join(name.split())  # normalize spaces
    return name

def split_by_article(text: str) -> List[Tuple[str, str]]:
    """
    Split document into articles based on "Neni" or "Art." markers.
    Handles nested numbering like "Neni 5.1".
    Returns list of (article_number, article_content).
    """
    # Pattern to match article headers: "Neni X" or "Art. X" at start of line (possibly after whitespace)
    # Capture the article number (which may include dots)
    pattern = r'(?m)^\s*(?:Neni|Art\.?)\s+([\d\.]+)'
    matches = list(re.finditer(pattern, text))

    if not matches:
        # No articles found; treat whole document as one article
        return [("0", text.strip())]

    articles = []
    for i, match in enumerate(matches):
        start = match.start()
        article_num = match.group(1).strip()
        # Determine end: next article start or end of text
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        # Extract content from this match's start to next start (or end)
        # To avoid including the header twice, we take from the end of the header line? Better to keep header.
        # We'll include the header in the content.
        content = text[start:end].strip()
        articles.append((article_num, content))

    return articles

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

# ----------------------------------------------------------------------
# MAIN INGESTION
# ----------------------------------------------------------------------

def ingest_legal_docs(directory_path: str, force_reingest: bool = False, chunk_size: int = 1000):
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

            # --- CLEAN THE TEXT ---
            full_text = clean_text(full_text)

            # --- EXTRACT LAW TITLE ---
            law_title = extract_law_title(full_text, filename)

            # --- SPLIT BY ARTICLE ---
            articles = split_by_article(full_text)
            print(f"     📖 Detected {len(articles)} article(s)", end="", flush=True)

            # --- PREPARE BATCHES ---
            batch_ids = []
            batch_texts = []
            batch_metadatas = []

            splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=int(chunk_size*0.1))

            for article_num, article_content in articles:
                chunks = splitter.split_text(article_content)
                for i, chunk in enumerate(chunks):
                    # Unique ID: filename + hash + article_num + chunk_index + UUID
                    chunk_id = f"{filename}_{current_hash[:8]}_art{article_num}_ch{i}_{uuid.uuid4()}"
                    batch_ids.append(chunk_id)
                    batch_texts.append(chunk)

                    metadata = {
                        "source": filename,
                        "law_title": law_title,
                        "article_number": str(article_num),
                        "type": "LAW",
                        "jurisdiction": TARGET_JURISDICTION,
                        "file_hash": current_hash,
                        "page": 0,  # optional, could be derived from original loader
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
    parser = argparse.ArgumentParser(description="Ingest Kosovo laws into ChromaDB with advanced normalization.")
    parser.add_argument("path", nargs="?", default="/app/data/laws", help="Path to documents folder")
    parser.add_argument("--force", action="store_true", help="Force re‑ingest all files")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size (default: 1000)")
    args = parser.parse_args()
    ingest_legal_docs(args.path, force_reingest=args.force, chunk_size=args.chunk_size)