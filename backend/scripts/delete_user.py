import pymongo
import os
import urllib.parse

# --- CONFIGURATION (Matches your Server .env) ---
def get_mongo_connection_string():
    # Force the specific credentials from your .env
    return "mongodb://advocatus_admin:681wRsFTiffSw7G%2BJxyEnceWHIpFg%2FhyvcbcN4ECwpA=@mongo:27017/phoenix_protocol_db?authSource=admin"

MONGO_URL = get_mongo_connection_string()
DB_NAME = "phoenix_protocol_db"
TARGET_EMAIL = "shabanbala@gmail.com"

def delete_user():
    print(f"🔧 Connecting to DB...")
    try:
        client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # Delete from ALL possible collections to be safe
        total_deleted = 0
        for col_name in ["User", "users", "user"]:
            result = db[col_name].delete_many({"email": TARGET_EMAIL})
            if result.deleted_count > 0:
                print(f"🗑️ Deleted {result.deleted_count} user(s) from collection '{col_name}'")
                total_deleted += result.deleted_count
        
        if total_deleted > 0:
            print("✅ User deleted successfully. The email is now free.")
        else:
            print("⚠️ User was not found (already deleted?).")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    delete_user()