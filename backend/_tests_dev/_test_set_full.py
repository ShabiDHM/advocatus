# FILE: backend/_test_set_full.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()
db = MongoClient(os.getenv("DATABASE_URI"))[os.getenv("MONGO_DB_NAME", "advocatus_db")]

shabi_id = ObjectId("6a8e129c02d1fd46ca5ab3a4")
result = db.users.update_one(
    {"_id": shabi_id},
    {"$set": {"org_access_level": "FULL"}}
)
print(f"Modified: {result.modified_count}")
print("Shabi Test tani ka org_access_level = FULL")