import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import MongoClient
from app.models.user import UserInDB

load_dotenv()
db = MongoClient(os.getenv('DATABASE_URI'))[os.getenv('MONGO_DB_NAME','advocatus_db')]

doc = db.users.find_one({'email': 'dummy-delete-test@example.com'})
if not doc:
    print("❌ Dummy nuk ekziston")
    sys.exit(1)

print(f"Raw doc keys: {sorted(doc.keys())}")
print()

try:
    user = UserInDB.model_validate(doc)
    print(f"✅ Valid: {user.email} | id={user.id}")
except Exception as e:
    print(f"❌ INVALID: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()