# FILE: backend/_tests_dev/_test_cleanup_orphans.py
# Pastron vektoret orphan (document_id pa dokument/media ekzistues)
# Kujdes: ekzekuto pasi te verifikosh listen!

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()
db = MongoClient(os.getenv("DATABASE_URI"))[os.getenv("MONGO_DB_NAME", "advocatus_db")]

# Merr te gjitha document_id unike
vector_doc_ids = db.user_vectors.distinct("document_id")
print(f"Total document_id unike ne user_vectors: {len(vector_doc_ids)}")

orphans = []
for doc_id_str in vector_doc_ids:
    if not doc_id_str:
        continue
    doc_id_str = str(doc_id_str)
    
    found = False
    try:
        if ObjectId.is_valid(doc_id_str):
            if db.documents.find_one({"_id": ObjectId(doc_id_str)}, {"_id": 1}):
                found = True
            if not found and db.media_evidence.find_one({"_id": ObjectId(doc_id_str)}, {"_id": 1}):
                found = True
    except Exception:
        pass
    
    if not found:
        orphans.append(doc_id_str)

print(f"\nOrphan document_ids: {len(orphans)}")

if not orphans:
    print("Asnje orphan. Dalje.")
    sys.exit(0)

# Kontrollo sa chunks do fshihen
total_chunks_to_delete = 0
for oid in orphans:
    total_chunks_to_delete += db.user_vectors.count_documents({"document_id": oid})

print(f"Total chunks per fshirje: {total_chunks_to_delete}")

confirm = input(f"\nVazhdojme? Shkruaj 'PO': ").strip()
if confirm != "PO":
    print("Anuluar.")
    sys.exit(0)

# Fshi
result = db.user_vectors.delete_many({"document_id": {"$in": orphans}})
print(f"\n✅ U fshinë: {result.deleted_count} chunks nga {len(orphans)} document_id orphan")

# Rikontrollo
remaining_doc_ids = db.user_vectors.distinct("document_id")
print(f"Document_id unike pas: {len(remaining_doc_ids)}")
print(f"Total user_vectors tani: {db.user_vectors.count_documents({})}")