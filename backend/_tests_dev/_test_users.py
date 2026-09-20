# FILE: backend/_test_users.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
db = MongoClient(os.getenv("DATABASE_URI"))[os.getenv("MONGO_DB_NAME", "advocatus_db")]

print("=" * 70)
print("TE GJITHE USERAT")
print("=" * 70)
for u in db.users.find():
    print(f"\n_id:               {u.get('_id')}")
    print(f"email:             {u.get('email')}")
    print(f"username:          {u.get('username')}")
    print(f"role:              {u.get('role')}")
    print(f"org_id:            {u.get('org_id')}")
    print(f"org_access_level:  {u.get('org_access_level')}")
    print(f"assigned_case_ids: {u.get('assigned_case_ids')}")
    print(f"product_plan:      {u.get('product_plan')}")
    print(f"account_type:      {u.get('account_type')}")