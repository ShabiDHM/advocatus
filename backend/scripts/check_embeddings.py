# FILE: backend/scripts/check_embeddings.py
# PHOENIX PROTOCOL - BRAIN SCAN UTILITY
# Checks if a document has been successfully processed and embedded into the vector store.

import sys
import asyncio
from bson import ObjectId

# Add app path
sys.path.append('.')

from app.core.db import connect_to_motor, get_async_db, close_mongo_connections
from app.services.vector_store_service import get_private_collection

async def run_check(doc_id_str: str):
    print(f"🔬 Brain Scan initiated for Document ID: {doc_id_str}")

    try:
        doc_oid = ObjectId(doc_id_str)
    except:
        print(f"❌ ERROR: Invalid Document ID format: '{doc_id_str}'")
        return

    # 1. Connect to DB
    await connect_to_motor()
    db_gen = get_async_db()
    db = next(db_gen)

    # 2. Find Document in MongoDB
    print("\n[1/2] Checking MongoDB Record...")
    doc_mongo = await db.documents.find_one({"_id": doc_oid})
    if not doc_mongo:
        print(f"❌ FAILURE: Document not found in MongoDB.")
        close_mongo_connections()
        return

    user_id = str(doc_mongo.get("owner_id"))
    file_name = doc_mongo.get("file_name")
    status = doc_mongo.get("status")

    print(f"  - File Name: {file_name}")
    print(f"  - Owner ID: {user_id}")
    print(f"  - Processing Status: {status}")

    if status != "READY":
        print("  - ⚠️  Warning: Document status is not 'READY'. Processing may not have completed.")

    # 3. Check for Embeddings in ChromaDB
    print("\n[2/2] Checking ChromaDB (AI Memory)...")
    try:
        collection = get_private_collection(user_id)
        results = collection.get(
            where={"source_document_id": doc_id_str}
        )
        
        vector_count = len(results.get('ids', []))

        if vector_count > 0:
            print(f"✅ SUCCESS: Found {vector_count} vector embeddings for this document.")
            print("   The AI has successfully read and memorized this file.")
        else:
            print(f"❌ FAILURE: Found 0 vector embeddings for this document.")
            print("   The background processing task likely failed. Check the 'worker' logs.")

    except Exception as e:
        print(f"❌ CRITICAL FAILURE: Could not connect to or query ChromaDB: {e}")
    
    finally:
        close_mongo_connections()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_embeddings.py <DOCUMENT_ID>")
    else:
        document_id = sys.argv[1]
        asyncio.run(run_check(document_id))