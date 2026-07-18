# Phoenix Protocol: Final User Schema Alignment
import os
import bcrypt
import pymongo
from datetime import datetime, timezone
from dotenv import load_dotenv

def align_db():
    load_dotenv("backend/.env")
    client = pymongo.MongoClient(os.getenv("DATABASE_URI"))
    db = client[os.getenv("MONGO_DB_NAME")]

    identity = "shabanbala@gmail.com"
    password = "shabanbala"
    
    # Generate fresh hash
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

    # This dictionary matches your UserInDB model EXACTLY
    perfect_user_record = {
        "username": identity,
        "email": identity,
        "hashed_password": hashed,
        "full_name": "Shaban Bala (Admin)",
        "role": "ADMIN",
        "org_role": "OWNER",
        "account_type": "SOLO",
        "subscription_tier": "PRO",
        "product_plan": "SOLO_PLAN",
        "subscription_status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    try:
        for col in ["User", "users"]:
            # We delete the messy old record and insert a clean one
            db[col].delete_many({"email": identity})
            db[col].insert_one(perfect_user_record)
            print(f"✅ Collection '{col}' is now perfectly aligned with user.py")
        
        print("--- STATUS: DATABASE READY ---")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    align_db()