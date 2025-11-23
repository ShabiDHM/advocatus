# scripts/ingest_laws.py
# Usage: python backend/scripts/ingest_laws.py "C:/Path/To/Laws"

import os
import sys
import glob
from typing import List, Dict, Any

# Ensure backend is in path to find other modules if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# --- IMPORTS WITH ERROR HANDLING ---
try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import chromadb
except ImportError as e:
    print("❌ MISSING LIBRARIES!")
    print(f"Error: {e}")
    print("👉 Please run: pip install langchain-community pypdf chromadb")
    sys.exit(1)

# Configuration
# We connect to the ChromaDB running in your Docker Container
CHROMA_HOST = "localhost"
CHROMA_PORT = 8002 
COLLECTION_NAME = "legal_knowledge_base"

def ingest_legal_docs(directory_path: str):
    print(f"🔌 Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        client.heartbeat() # Verify connection
        print("✅ Connected to ChromaDB.")
    except Exception as e:
        print(f"❌ Could not connect to ChromaDB: {e}")
        print("👉 Ensure your Docker containers are running (docker compose up -d).")
        return

    # Create or Get the Global Collection
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # Find PDFs
    pdf_files = glob.glob(os.path.join(directory_path, "*.pdf"))
    print(f"📚 Found {len(pdf_files)} PDF laws to ingest.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    for pdf_path in pdf_files:
        try:
            print(f"📄 Processing: {os.path.basename(pdf_path)}...")
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            chunks = text_splitter.split_documents(pages)
            
            if not chunks:
                print(f"⚠️ No text found in {pdf_path}. Skipped.")
                continue

            # Prepare Data
            ids = [f"{os.path.basename(pdf_path)}_{i}" for i in range(len(chunks))]
            texts = [c.page_content for c in chunks]
            
            # FIX: Explicit type hint to satisfy Pylance
            metadatas: List[Dict[str, Any]] = [
                {"source": os.path.basename(pdf_path), "type": "LAW"} 
                for _ in chunks
            ]
            
            # Embed & Store
            # We use 'type: ignore' to silence Pylance strict covariance checks
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas  # type: ignore
            )
            print(f"✅ Added {len(chunks)} chunks to Knowledge Base.")
            
        except Exception as e:
            print(f"❌ Failed to ingest {pdf_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("⚠️ Usage: python backend/scripts/ingest_laws.py <path_to_laws_folder>")
    else:
        ingest_legal_docs(sys.argv[1])