# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - INCREMENTAL INGESTION
# 1. SMART CHECK: Checks DB for existing files before processing.
# 2. NO WIPE: Preserves existing data (does NOT delete collection).
# 3. EFFICIENCY: Only processes new files.

import os
import sys
import glob
import requests
from typing import List, Dict, Any, Set

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
    sys.exit(1)

# --- CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

AI_CORE_HOST = os.getenv("AI_CORE_SERVICE_HOST", "ai-core-service")
AI_CORE_PORT = int(os.getenv("AI_CORE_SERVICE_PORT", 8000))
AI_CORE_URL = f"http://{AI_CORE_HOST}:{AI_CORE_PORT}/embeddings/generate"

COLLECTION_NAME = "legal_knowledge_base"

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

def get_existing_sources(collection) -> Set[str]:
    """Fetches the list of filenames already inside the database."""
    try:
        # Fetch only metadata to be fast
        result = collection.get(include=["metadatas"])
        existing = set()
        if result and result["metadatas"]:
            for meta in result["metadatas"]:
                if meta and "source" in meta:
                    existing.add(meta["source"])
        return existing
    except Exception:
        return set()

def ingest_legal_docs(directory_path: str):
    print(f"🔌 Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # PHOENIX FIX: Removed 'delete_collection'. We append now.
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=JuristiRemoteEmbeddings()
        )
        print("✅ Connected to Database.")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # 1. Get list of already ingested files
    print("🔍 Checking existing database records...")
    existing_files = get_existing_sources(collection)
    print(f"ℹ️  Database currently contains {len(existing_files)} unique documents.")

    # 2. Find files on disk
    supported_extensions = ['*.pdf', '*.docx', '*.txt']
    all_files = []
    if os.path.isdir(directory_path):
        for ext in supported_extensions:
            all_files.extend(glob.glob(os.path.join(directory_path, "**", ext), recursive=True))
    else:
        print(f"❌ Directory not found: {directory_path}")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    new_files_count = 0

    for file_path in all_files:
        filename = os.path.basename(file_path)
        
        # PHOENIX FIX: Skip if already exists
        if filename in existing_files:
            print(f"⏩ Skipping: {filename} (Already Ingested)")
            continue

        new_files_count += 1
        try:
            print(f"👉 Processing: {filename}", end=" ", flush=True)
            
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
                    {"source": filename, "type": "LAW"} 
                    for _ in batch
                ]
                
                collection.add(ids=ids, documents=texts, metadatas=metadatas) # type: ignore
                print(".", end="", flush=True)
                
            print(" ✅")
            
        except Exception as e:
            print(f" -> ❌ Error: {e}")

    if new_files_count == 0:
        print("\n✨ No new documents to ingest. Database is up to date.")
    else:
        print(f"\n✅ Finished. Ingested {new_files_count} new documents.")

if __name__ == "__main__":
    default_dir = "/app/data/laws"
    target_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    ingest_legal_docs(target_dir)