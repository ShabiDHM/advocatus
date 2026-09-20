import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
db = MongoClient(os.getenv('DATABASE_URI'))[os.getenv('MONGO_DB_NAME','advocatus_db')]

# Fshij direkt nga DB (pa validim Pydantic)
result = db.users.delete_many({"email": "dummy_delete_test@test.local"})
print(f"✅ U fshinë: {result.deleted_count} user")

print(f"\nUsers total tani: {db.users.count_documents({})}")
for u in db.users.find():
    print(f"  {u['_id']} | {u.get('email')}")