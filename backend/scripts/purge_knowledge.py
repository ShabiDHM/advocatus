# FILE: backend/scripts/purge_knowledge.py
# PHOENIX PROTOCOL - KNOWLEDGE BASE PURGE TOOL
# Usage: python -m scripts.purge_knowledge "filename.pdf"

import os
import sys
import chromadb

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
COLLECTION_NAME = "legal_knowledge_base"

def run():
    if len(sys.argv) < 2:
        print("❌ Error: Missing filename.")
        print("Usage: python -m scripts.purge_knowledge 'filename.pdf'")
        return

    filename = sys.argv[1]
    print(f"🔌 Connecting to ChromaDB ({CHROMA_HOST}:{CHROMA_PORT})...")
    
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # We retrieve the collection loosely (without embedding function) just for deletion
        collection = client.get_collection(name=COLLECTION_NAME)
        
        # Check existence
        existing = collection.get(where={"source": filename}, limit=1)
        if not existing['ids']:
            print(f"⚠️  File '{filename}' not found in AI Memory. Nothing to do.")
        else:
            # DELETE
            collection.delete(where={"source": filename})
            print(f"✅ SUCCESSFULLY PURGED: '{filename}' from Knowledge Base.")
            
    except Exception as e:
        print(f"❌ DB Error: {e}")

if __name__ == "__main__":
    run()