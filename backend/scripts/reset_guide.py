# FILE: backend/scripts/reset_guide.py
import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# Bootstrap env
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env", override=True)

uri = os.getenv("DATABASE_URI")
db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")

client = MongoClient(uri)
db = client[db_name]
coll = db["legal_knowledge_base"]

# Delete the old incorrectly-cased entries
result = coll.delete_many({"source": "Udhëzues-Praktik-mbi-Qasjen-në-Drejtësi-ALB03.pdf"})
print(f"🧹 Successfully cleared {result.deleted_count} old chunks from MongoDB Atlas.")