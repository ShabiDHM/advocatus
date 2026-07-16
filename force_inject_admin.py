# Phoenix Protocol: Admin Force Injector V3 (ID-Safe Version)
import os
import bcrypt
import pymongo
from datetime import datetime, timezone
from dotenv import load_dotenv

def force_inject():
    load_dotenv("backend/.env")
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")

    print(f"--- [PHOENIX] Connecting to Atlas: {db_name} ---")
    client = pymongo.MongoClient(uri)
    db = client[db_name]

    # Credentials alignment
    identity = "shabanbala@gmail.com"
    username = "shabanbala@gmail.com"
    password = "shabanbala"
    
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    # The "Master" Admin Logic
    # We define the data fields separately from the database ID
    admin_data = {
        "email": identity,
        "username": username,
        "hashed_password": hashed_password,
        "full_name": "Shaban Bala (Admin)",
        "role": "ADMIN",
        "is_active": True,
        "is_superuser": True,
        "is_staff": True,
        "is_verified": True,
        "subscription_status": "ACTIVE",
        "updated_at": datetime.now(timezone.utc)
    }

    try:
        for col_name in ["User", "users"]:
            existing = db[col_name].find_one({"email": identity})
            
            if existing:
                print(f"Found existing record in '{col_name}'. Syncing Admin status...")
                # We use a copy to avoid mutating the original dict
                update_payload = admin_data.copy()
                # Ensure we NEVER try to update the ID
                if "_id" in update_payload: del update_payload["_id"]
                
                db[col_name].update_one(
                    {"email": identity}, 
                    {"$set": update_payload}
                )
            else:
                print(f"No record in '{col_name}'. Injecting fresh Admin...")
                # Add creation timestamp for new records
                insert_payload = admin_data.copy()
                insert_payload["created_at"] = datetime.now(timezone.utc)
                db[col_name].insert_one(insert_payload)
            
        print("--- STATUS: SUCCESS ---")
        print("Database synchronized across all potential collections.")
        
    except Exception as e:
        print(f"CRITICAL INJECTION FAILURE: {e}")

if __name__ == "__main__":
    force_inject()