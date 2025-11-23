# FILE: backend/scripts/ingest_laws.py
# PHOENIX PROTOCOL - HYBRID INGESTION
# 1. SMART CONFIG: Automatically works inside Docker ('chroma') OR Locally ('localhost').
# 2. ROBUSTNESS: Skips bad files instead of crashing.

import os
import sys
import glob
import requests
from typing import List, Dict, Any

# Ensure backend is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    # Try modern import first, fall back to legacy if needed
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
# Check environment variables. Default to DOCKER INTERNAL values.
# If running locally, you can export CHROMA_HOST=127.0.0.1
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

# AI Core Configuration
AI_CORE_HOST = os.getenv("AI_CORE_SERVICE_HOST", "ai-core-service")
AI_CORE_PORT = int(os.getenv("AI_CORE_SERVICE_PORT", 8000))
AI_CORE_URL = f"http://{AI_CORE_HOST}:{AI_CORE_PORT}/embeddings/generate"

COLLECTION_NAME = "legal_knowledge_base"

print(f"⚙️  CONFIG: Chroma={CHROMA_HOST}:{CHROMA_PORT} | AI-Core={AI_CORE_URL}")

# --- CUSTOM EMBEDDING FUNCTION ---
class JuristiRemoteEmbeddings(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        # print(f"🧠 Vectorizing batch of {len(input)} chunks...") 
        for text in input:
            try:
                response = requests.post(AI_CORE_URL, json={"text_content": text})
                response.raise_for_status()
                data = response.json()
                vectors.append(data["embedding"])
            except Exception as e:
                print(f"❌ Embedding Failed: {e}")
                vectors.append([0.0] * 768) # Default zero vector to prevent crash
        return vectors

def ingest_legal_docs(directory_path: str):
    print(f"🔌 Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # Reset Collection
        try:
            client.delete_collection(COLLECTION_NAME)
            print("🗑️  Deleted old collection.")
        except:
            pass
            
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=JuristiRemoteEmbeddings()
        )
        print("✅ Connected to Database.")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # Find files
    supported_extensions = ['*.pdf', '*.docx', '*.txt']
    all_files = []
    # Handle recursive or flat directory
    if os.path.isdir(directory_path):
        for ext in supported_extensions:
            all_files.extend(glob.glob(os.path.join(directory_path, "**", ext), recursive=True))
    else:
        print(f"❌ Directory not found: {directory_path}")
        return

    print(f"📚 Found {len(all_files)} documents.")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for file_path in all_files:
        try:
            print(f"👉 Processing: {os.path.basename(file_path)}", end=" ", flush=True)
            
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
                
                ids = [f"{os.path.basename(file_path)}_{i+j}" for j in range(len(batch))]
                texts = [c.page_content for c in batch]
                metadatas: List[Dict[str, Any]] = [
                    {"source": os.path.basename(file_path), "type": "LAW"} 
                    for _ in batch
                ]
                
                collection.add(ids=ids, documents=texts, metadatas=metadatas) # type: ignore
                print(".", end="", flush=True)
                
            print(" ✅")
            
        except Exception as e:
            print(f" -> ❌ Error: {e}")

if __name__ == "__main__":
    # Default directory inside container if not specified
    default_dir = "/app/data/laws"
    target_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    
    ingest_legal_docs(target_dir)