# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - SMART INCREMENTAL INGESTION (TYPE SAFE)
# 1. FIX: Added safety checks for ChromaDB return values.
# 2. LOGIC: Preserves MD5 fingerprinting and incremental updates.

import os
import sys
import glob
import requests
import hashlib
from typing import List, Dict, Any, Optional

# Ensure backend is in path
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

# --- SMART CONFIGURATION ---
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
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# --- CUSTOM EMBEDDING FUNCTION ---
class JuristiRemoteEmbeddings(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for text in input:
            try:
                response = requests.post(AI_CORE_URL, json={"text_content": text})
                response.raise_for_status()
                data = response.json()
                vectors.append(data["embedding"])
            except Exception as e:
                print(f"❌ Embedding Failed: {e}")
                vectors.append([0.0] * 768)
        return vectors

def ingest_legal_docs(directory_path: str):
    print(f"🔌 Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    
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

    # Find files
    supported_extensions = ['*.pdf', '*.docx', '*.txt']
    all_files = []
    if os.path.isdir(directory_path):
        for ext in supported_extensions:
            all_files.extend(glob.glob(os.path.join(directory_path, "**", ext), recursive=True))
    else:
        print(f"❌ Directory not found: {directory_path}")
        return

    print(f"📚 Scanning {len(all_files)} files in library...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    stats = {"skipped": 0, "added": 0, "updated": 0}

    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            current_hash = calculate_file_hash(file_path)
            
            # --- INCREMENTAL CHECK ---
            existing_records = collection.get(
                where={"source": filename},
                limit=1,
                include=["metadatas"]
            )
            
            # PHOENIX FIX: Safe Access
            ids = existing_records.get('ids', []) if existing_records else []
            metas = existing_records.get('metadatas', []) if existing_records else []
            
            is_existing = len(ids) > 0
            
            if is_existing:
                # Check if hash matches (Safely handle nested list/None)
                first_meta = metas[0] if metas and len(metas) > 0 else {}
                stored_hash = first_meta.get("file_hash", "") if first_meta else ""
                
                if stored_hash == current_hash:
                    print(f"⏭️  Skipped (Unchanged): {filename}")
                    stats["skipped"] += 1
                    continue
                else:
                    print(f"🔄 Updating (Modified): {filename}", end=" ", flush=True)
                    collection.delete(where={"source": filename})
                    stats["updated"] += 1
            else:
                print(f"➕ Adding (New): {filename}", end=" ", flush=True)
                stats["added"] += 1

            # --- PROCESSING ---
            ext = os.path.splitext(file_path)[1].lower()
            loader = None
            if ext == '.pdf': loader = PyPDFLoader(file_path)
            elif ext == '.docx': loader = Docx2txtLoader(file_path)
            elif ext == '.txt': loader = TextLoader(file_path, encoding='utf-8')
            
            if not loader: continue

            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
            
            if not chunks: 
                print(" -> ⚠️  Empty")
                continue

            # Batch Ingest
            BATCH_SIZE = 20 
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]
                
                ids = [f"{filename}_{i+j}" for j in range(len(batch))]
                texts = [c.page_content for c in batch]
                metadatas: List[Dict[str, Any]] = [
                    {"source": filename, "type": "LAW", "file_hash": current_hash} 
                    for _ in batch
                ]
                
                collection.add(ids=ids, documents=texts, metadatas=metadatas) # type: ignore
                print(".", end="", flush=True)
                
            print(" ✅")
            
        except Exception as e:
            print(f" -> ❌ Error: {e}")

    print(f"\n🏁 Ingestion Summary: {stats['added']} Added, {stats['updated']} Updated, {stats['skipped']} Skipped.")

if __name__ == "__main__":
    default_dir = "/app/data/laws"
    target_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    ingest_legal_docs(target_dir)