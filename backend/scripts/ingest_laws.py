# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - INGESTION SCRIPT V2 (KOSOVO EXCLUSIVE)
# 1. JURISDICTION: Removed CLI argument. STRICTLY hardcoded to 'ks'.
# 2. TYPE SAFETY: Preserved Metadata typing fix from previous version.
# 3. LOGIC: Tags all ingested documents as Kosovo Law.

import os
import sys
import glob
import hashlib
import argparse
from typing import List, Dict

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    try:
        from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
    except ImportError:
        from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    import chromadb
    from app.core.embeddings import JuristiRemoteEmbeddings 
    from chromadb.api.types import Metadata
except ImportError as e:
    print(f"❌ MISSING LIBRARIES: {e}")
    print("Run: pip install langchain-community langchain-text-splitters pypdf chromadb requests docx2txt")
    sys.exit(1)

# --- CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
COLLECTION_NAME = "legal_knowledge_base"
# PHOENIX: STRICT ENFORCEMENT
TARGET_JURISDICTION = 'ks'

print(f"⚙️  CONFIG: Chroma={CHROMA_HOST}:{CHROMA_PORT}")

# --- HELPERS ---
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

def ingest_legal_docs(directory_path: str):
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

    supported_extensions = ['*.pdf', '*.docx', '*.txt']
    all_files = []
    
    if os.path.isdir(directory_path):
        for ext in supported_extensions:
            all_files.extend(glob.glob(os.path.join(directory_path, "**", ext), recursive=True))
    else:
        print(f"❌ Directory not found: {directory_path}")
        return

    if not all_files:
        print(f"⚠️ No documents found in {directory_path}")
        return

    print(f"📚 Scanning {len(all_files)} files in library for Jurisdiction: {TARGET_JURISDICTION.upper()}...")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    stats = {"skipped": 0, "added": 0, "updated": 0, "failed": 0}

    for file_path in all_files:
        filename = os.path.basename(file_path)
        
        try:
            current_hash = calculate_file_hash(file_path)
            
            existing_records = collection.get(
                where={"source": filename},
                limit=1,
                include=["metadatas"]
            )
            
            ids = existing_records.get('ids', [])
            metas = existing_records.get('metadatas', [])
            
            # Check for hash match AND strict jurisdiction match
            if ids and metas and metas[0].get("file_hash") == current_hash and metas[0].get("jurisdiction") == TARGET_JURISDICTION:
                print(f"⏭️  Skipped: {filename}")
                stats["skipped"] += 1
                continue
            
            if ids:
                print(f"🔄 Updating: {filename}", end=" ", flush=True)
                collection.delete(where={"source": filename})
                stats["updated"] += 1
            else:
                print(f"➕ Adding: {filename}", end=" ", flush=True)
                stats["added"] += 1

            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf': loader = PyPDFLoader(file_path)
            elif ext == '.docx': loader = Docx2txtLoader(file_path)
            elif ext == '.txt': loader = TextLoader(file_path, encoding='utf-8')
            else: continue

            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
            if not chunks: continue

            BATCH_SIZE = 20
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]
                ids_batch = [f"{filename}_{i+j}_{TARGET_JURISDICTION}" for j in range(len(batch))]
                texts_batch = [c.page_content for c in batch]
                
                metadatas_batch: List[Metadata] = [
                    {
                        "source": filename, 
                        "type": "LAW", 
                        "file_hash": current_hash, 
                        "jurisdiction": TARGET_JURISDICTION, 
                        "page": c.metadata.get("page", 0)
                    } 
                    for c in batch
                ]
                
                collection.add(ids=ids_batch, documents=texts_batch, metadatas=metadatas_batch)
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
    parser = argparse.ArgumentParser(description="Ingest laws into ChromaDB (KOSOVO EXCLUSIVE).")
    parser.add_argument("path", nargs="?", default="/app/data/laws", help="Path to documents folder")
    # PHOENIX: Removed --jurisdiction argument
    
    args = parser.parse_args()
    ingest_legal_docs(args.path)