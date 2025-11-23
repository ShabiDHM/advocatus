# scripts/ingest_laws.py
# PHOENIX PROTOCOL - MULTI-FORMAT SUPPORT
# 1. READS PDF (.pdf), Word (.docx), and Text (.txt) files.
# 2. SENDS text to Server (via Tunnel 8010) for Vectorization.
# 3. SAVES vectors to Server DB (via Tunnel 8002).

import os
import sys
import glob
import requests
from typing import List, Dict, Any

# Ensure backend is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import chromadb
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
except ImportError as e:
    print("❌ MISSING LIBRARIES! Run: pip install langchain-community langchain-text-splitters pypdf chromadb requests docx2txt")
    sys.exit(1)

# --- CONFIGURATION ---
CHROMA_HOST = "127.0.0.1"
CHROMA_PORT = 8002
AI_CORE_URL = "http://127.0.0.1:8010/embeddings/generate" # Tunneled to Server
COLLECTION_NAME = "legal_knowledge_base"

# --- CUSTOM EMBEDDING FUNCTION ---
class JuristiRemoteEmbeddings(EmbeddingFunction):
    """
    Sends text to the Juristi AI Core API to get vectors.
    Ensures local script matches server configuration.
    """
    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        print(f"🧠 Vectorizing batch of {len(input)} chunks via Remote AI Core...")
        for text in input:
            try:
                response = requests.post(AI_CORE_URL, json={"text_content": text})
                response.raise_for_status()
                data = response.json()
                vectors.append(data["embedding"])
            except Exception as e:
                print(f"❌ Embedding Failed for text: {text[:30]}... Error: {e}")
                # Return zero vector on error to prevent crash
                vectors.append([0.0] * 1024) 
        return vectors

def ingest_legal_docs(directory_path: str):
    print(f"🔌 Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # DELETE OLD COLLECTION (Optional: Comment this out if you want to append instead of overwrite)
        try:
            client.delete_collection(COLLECTION_NAME)
            print("🗑️  Deleted old collection to ensure clean state.")
        except:
            pass
            
        # Create new collection using REMOTE embeddings
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=JuristiRemoteEmbeddings()
        )
        print("✅ Connected & Ready.")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("👉 Ensure BOTH tunnels are active: ssh -L 8002:... -L 8010:...")
        return

    # Find all supported files
    supported_extensions = ['*.pdf', '*.docx', '*.txt']
    all_files = []
    for ext in supported_extensions:
        all_files.extend(glob.glob(os.path.join(directory_path, ext)))

    print(f"📚 Found {len(all_files)} documents to ingest.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for file_path in all_files:
        try:
            print(f"📄 Processing: {os.path.basename(file_path)}...")
            
            # Select appropriate loader
            ext = os.path.splitext(file_path)[1].lower()
            loader = None
            
            if ext == '.pdf':
                loader = PyPDFLoader(file_path)
            elif ext == '.docx':
                loader = Docx2txtLoader(file_path)
            elif ext == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            
            if not loader:
                print(f"⚠️ Skipping unsupported file type: {file_path}")
                continue

            # Load and Split
            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
            
            if not chunks: 
                print(f"⚠️ No text found in {file_path}")
                continue

            # Batch Processing
            BATCH_SIZE = 20 
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]
                
                ids = [f"{os.path.basename(file_path)}_{i+j}" for j in range(len(batch))]
                texts = [c.page_content for c in batch]
                metadatas: List[Dict[str, Any]] = [
                    {"source": os.path.basename(file_path), "type": "LAW"} 
                    for _ in batch
                ]
                
                collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas # type: ignore
                )
                print(f"   ↳ Ingested batch {i // BATCH_SIZE + 1} ({len(batch)} chunks)")
                
            print(f"✅ Finished: {os.path.basename(file_path)}")
            
        except Exception as e:
            print(f"❌ Failed to process {os.path.basename(file_path)}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/ingest_laws.py data/laws")
    else:
        ingest_legal_docs(sys.argv[1])