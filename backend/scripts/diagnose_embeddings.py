# FILE: backend/scripts/diagnose_embeddings.py
# PHOENIX PROTOCOL - DIAGNOSTIC TOOL V1.0 (EMBEDDING HEALTH CHECK)

import os
import sys
import json
import logging
from pathlib import Path

# Shto backend në path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from pymongo import MongoClient
from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def diagnose():
    print("\n" + "=" * 60)
    print("🔍 DIAGNOZA E EMBEDDINGS NË MONGODB ATLAS")
    print("=" * 60 + "\n")
    
    uri = settings.DATABASE_URI
    db_name = settings.MONGO_DB_NAME or "advocatus_db"
    
    if not uri:
        print("❌ DATABASE_URI mungon në .env")
        return
    
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        db = client[db_name]
        
        # 1. KONTROLLO KOLEKSIONET
        print("📦 KOLEKSIONET NË DATABAZË:")
        collections = db.list_collection_names()
        for coll in collections:
            count = db[coll].count_documents({})
            print(f"   📁 {coll}: {count} dokumente")
        
        print("\n" + "=" * 60)
        
        # 2. KONTROLLO legal_knowledge_base
        if "legal_knowledge_base" in collections:
            total_legal = db["legal_knowledge_base"].count_documents({})
            with_embedding = db["legal_knowledge_base"].count_documents({"embedding": {"$exists": True, "$ne": []}})
            without_embedding = db["legal_knowledge_base"].count_documents({"$or": [{"embedding": {"$exists": False}}, {"embedding": []}]})
            
            print(f"📚 legal_knowledge_base:")
            print(f"   Total dokumente: {total_legal}")
            print(f"   Me embedding: {with_embedding}")
            print(f"   Pa embedding: {without_embedding}")
            
            if total_legal > 0:
                # Kontrollo një shembull
                sample = db["legal_knowledge_base"].find_one({"embedding": {"$exists": True, "$ne": []}})
                if sample:
                    emb = sample.get("embedding", [])
                    print(f"   Shembull embedding: {len(emb)} dimensione")
                    if len(emb) > 0:
                        print(f"   Vlera e parë: {emb[0]}")
                else:
                    print(f"   ❌ ASNJË dokument nuk ka embedding!")
        
        print("\n" + "=" * 60)
        
        # 3. KONTROLLO user_vectors
        if "user_vectors" in collections:
            total_uv = db["user_vectors"].count_documents({})
            with_embedding_uv = db["user_vectors"].count_documents({"embedding": {"$exists": True, "$ne": []}})
            without_embedding_uv = db["user_vectors"].count_documents({"$or": [{"embedding": {"$exists": False}}, {"embedding": []}]})
            
            print(f"📄 user_vectors:")
            print(f"   Total dokumente: {total_uv}")
            print(f"   Me embedding: {with_embedding_uv}")
            print(f"   Pa embedding: {without_embedding_uv}")
        
        print("\n" + "=" * 60)
        
        # 4. KONTROLLO INDEXES
        print("🔍 INDEXET në legal_knowledge_base:")
        try:
            indexes = db["legal_knowledge_base"].list_indexes()
            for idx in indexes:
                print(f"   📌 {idx.get('name', 'pa emër')}: {json.dumps(idx.get('key', {}))}")
        except Exception as e:
            print(f"   ❌ Gabim gjatë leximit të indexeve: {e}")
        
        print("\n" + "=" * 60)
        
        # 5. TESTO KËRKIMIN
        print("🧪 TESTIMI I KËRKIMIT:")
        try:
            # Text search test
            sample_text = db["legal_knowledge_base"].find_one({})
            if sample_text:
                print(f"   Shembull dokumenti: {sample_text.get('law_title', 'Pa titull')}")
                print(f"   Fusha e tekstit: {len(sample_text.get('text', ''))} karaktere")
                print(f"   Fusha e embedding: {'embedding' in sample_text}")
                if 'embedding' in sample_text:
                    print(f"   Madhësia e embedding: {len(sample_text.get('embedding', []))}")
            else:
                print("   ❌ ASNJË dokument në legal_knowledge_base!")
        except Exception as e:
            print(f"   ❌ Gabim: {e}")
        
        print("\n" + "=" * 60)
        print("✅ DIAGNOZA PËRFUNDOI")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"❌ Gabim gjatë lidhjes me MongoDB: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    diagnose()