import os
import sys
# Shto backend/ në path (script-i është në _tests_dev/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone
from app.core.security import get_password_hash

load_dotenv()
db = MongoClient(os.getenv('DATABASE_URI'))[os.getenv('MONGO_DB_NAME','advocatus_db')]

dummy = {
    "email": "dummy_delete_test@test.local",
    "username": "DummyDeleteTest",
    "full_name": "Dummy Delete Test",
    "hashed_password": get_password_hash("Test123!"),
    "role": "STANDARD",
    "is_deleted": False,
    "subscription_status": "INACTIVE",
    "org_id": None,
    "org_access_level": None,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "consent_date": datetime.now(timezone.utc),
}

# Hiq ekzistuesin nese ka
db.users.delete_many({"email": dummy["email"]})

result = db.users.insert_one(dummy)
print(f"User dummy u krijua: {result.inserted_id}")
print(f"   Email: {dummy['email']}")
print(f"   Password: Test123!")