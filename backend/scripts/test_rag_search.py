# FILE: backend/scripts/test_rag_search.py

import sys
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from pymongo import MongoClient
from app.core.config import settings
from app.services.embedding_service import generate_embedding

def test_rag_search():
    uri = settings.DATABASE_URI
    db_name = settings.MONGO_DB_NAME or "advocatus_db"
    
    client = MongoClient(uri)
    db = client[db_name]
    coll = db["legal_knowledge_base"]
    
    # 1. Testo me një query specifik
    query = "Neni 145 Ligji për Familjen kontakt me prindin"
    print(f"\n🔍 QUERY: {query}\n")
    
    # 2. Gjenero embedding
    vector = generate_embedding(query)
    print(f"✅ Embedding u gjenerua: {len(vector)} dimensione")
    print(f"   Vlera e parë: {vector[0] if vector else 'BOSH'}")
    
    if not vector:
        print("❌ Embedding është BOSH! Problemi është në API key ose embedding_service.")
        return
    
    # 3. Testo $vectorSearch
    print("\n🧪 Testimi i $vectorSearch:")
    try:
        pipeline = [{
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": 150,
                "limit": 5
            }
        }]
        results = list(coll.aggregate(pipeline))
        print(f"✅ $vectorSearch ktheu: {len(results)} rezultate")
        
        for i, r in enumerate(results):
            law_title = r.get("law_title", r.get("title", "Pa titull"))
            text = r.get("text", "")[:200]
            print(f"\n   📌 Rezultati {i+1}: {law_title}")
            print(f"   {text}...")
            
    except Exception as e:
        print(f"❌ $vectorSearch DËSHTOI: {e}")
    
    # 4. Testo text search fallback
    print("\n🧪 Testimi i Text Search:")
    try:
        text_results = list(coll.find({"$text": {"$search": "Neni 145"}}).limit(5))
        print(f"✅ Text search ktheu: {len(text_results)} rezultate")
        for i, r in enumerate(text_results):
            law_title = r.get("law_title", r.get("title", "Pa titull"))
            print(f"   📌 {i+1}: {law_title}")
    except Exception as e:
        print(f"❌ Text search DËSHTOI: {e}")
    
    client.close()

if __name__ == "__main__":
    test_rag_search()