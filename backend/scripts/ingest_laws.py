# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - JURISDICTION-AWARE INGESTION
# 1. FEATURE: Added '--jurisdiction' (ks/al) flag.
# 2. METADATA: Tags every chunk with 'jurisdiction' for RAG filtering.
# 3. LOGIC: Re-indexes if jurisdiction changes, even if content is same.

import os
import sys
import glob
import requests
import hashlib
import argparse
from typing import List, Dict, Any, Optional

# Ensure backend is in path to find modules if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    try:
        from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
    except ImportError:
        from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    import chromadb
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
except ImportError as e:
    print(f"❌ MISSING LIBRARIES: {e}")
    print("Run: pip install langchain-community langchain-text-splitters pypdf chromadb requests docx2txt")
    sys.exit(1)

# --- CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

AI_CORE_HOST = os.getenv("AI_CORE_SERVICE_HOST", "ai-core-service")
AI_CORE_PORT = int(os.getenv("AI_CORE_SERVICE_PORT", 8000))
AI_CORE_URL = f"http://{AI_CORE_HOST}:{AI_CORE_PORT}/embeddings/generate"

COLLECTION_NAME = "legal_knowledge_base"

print(f"⚙️  CONFIG: Chroma={CHROMA_HOST}:{CHROMA_PORT} | AI-Core={AI_CORE_URL}")

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

# --- EMBEDDING FUNCTION ---
class JuristiRemoteEmbeddings(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for text in input:
            try:
                response = requests.post(AI_CORE_URL, json={"text_content": text}, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    vectors.append(data["embedding"])
                else:
                    print(f"⚠️ AI Core Error ({response.status_code}): {response.text}")
                    vectors.append([0.0] * 768) 
            except Exception as e:
                print(f"❌ Embedding Failed: {e}")
                vectors.append([0.0] * 768)
        return vectors

def ingest_legal_docs(directory_path: str, jurisdiction: str):
    print(f"🔌 Connecting to ChromaDB (Target: {jurisdiction.upper()})...")
    
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

    print(f"📚 Scanning {len(all_files)} files in library for Jurisdiction: {jurisdiction.upper()}...")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    stats = {"skipped": 0, "added": 0, "updated": 0, "failed": 0}

    for file_path in all_files:
        filename = os.path.basename(file_path)
        
        try:
            current_hash = calculate_file_hash(file_path)
            
            # Check existing records
            existing_records = collection.get(
                where={"source": filename},
                limit=1,
                include=["metadatas"]
            )
            
            ids = existing_records.get('ids', [])
            metas = existing_records.get('metadatas', [])
            
            should_update = False
            is_existing = len(ids) > 0
            
            if is_existing:
                first_meta = metas[0] if metas and len(metas) > 0 else {}
                stored_hash = first_meta.get("file_hash", "") if first_meta else ""
                stored_jur = first_meta.get("jurisdiction", "") if first_meta else ""
                
                # Update if content changed OR jurisdiction tag changed
                if stored_hash == current_hash and stored_jur == jurisdiction:
                    print(f"⏭️  Skipped: {filename}")
                    stats["skipped"] += 1
                    continue
                else:
                    should_update = True
                    print(f"🔄 Updating ({'Hash' if stored_hash != current_hash else 'Jur'} Change): {filename}", end=" ", flush=True)
                    collection.delete(where={"source": filename})
                    stats["updated"] += 1
            else:
                print(f"➕ Adding: {filename}", end=" ", flush=True)
                stats["added"] += 1

            # Load & Process
            ext = os.path.splitext(file_path)[1].lower()
            loader = None
            if ext == '.pdf': loader = PyPDFLoader(file_path)
            elif ext == '.docx': loader = Docx2txtLoader(file_path)
            elif ext == '.txt': loader = TextLoader(file_path, encoding='utf-8')
            
            if not loader: 
                print(" -> ⚠️ Unknown format")
                continue

            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
            
            if not chunks: 
                print(" -> ⚠️  Empty content")
                continue

            BATCH_SIZE = 20 
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]
                
                ids_batch = [f"{filename}_{i+j}_{jurisdiction}" for j in range(len(batch))] # Unique ID includes Jur
                texts_batch = [c.page_content for c in batch]
                
                # PHOENIX: Tag with Jurisdiction
                metadatas_batch: List[Dict[str, Any]] = [
                    {
                        "source": filename, 
                        "type": "LAW", 
                        "file_hash": current_hash,
                        "jurisdiction": jurisdiction, # <--- CRITICAL TAG
                        "page": c.metadata.get("page", 0)
                    } 
                    for c in batch
                ]
                
                collection.add(ids=ids_batch, documents=texts_batch, metadatas=metadatas_batch) # type: ignore
                print(".", end="", flush=True)
                
            print(" ✅")
            
        except Exception as e:
            print(f" -> ❌ Error: {e}")
            stats["failed"] += 1

    print("-" * 50)
    print(f"🏁 Ingestion Complete [{jurisdiction.upper()}].")
    print(f"   Added:   {stats['added']}")
    print(f"   Updated: {stats['updated']}")
    print(f"   Skipped: {stats['skipped']}")
    print("-" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest laws into ChromaDB with Jurisdiction tagging.")
    parser.add_argument("path", nargs="?", default="/app/data/laws", help="Path to documents folder")
    parser.add_argument("--jurisdiction", choices=['ks', 'al'], default='ks', help="Jurisdiction tag (ks=Kosovo, al=Albania)")
    
    args = parser.parse_args()
    
    ingest_legal_docs(args.path, args.jurisdiction)