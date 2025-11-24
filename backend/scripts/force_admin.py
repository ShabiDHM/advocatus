import pymongo

# Credentials from your server .env
MONGO_URL = "mongodb://advocatus_admin:681wRsFTiffSw7G%2BJxyEnceWHIpFg%2FhyvcbcN4ECwpA=@mongo:27017/phoenix_protocol_db?authSource=admin"
DB_NAME = "phoenix_protocol_db"
TARGET_EMAIL = "shabanbala@gmail.com"

def promote():
    print("🔧 Connecting to Database...")
    client = pymongo.MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # The Magic Switch: Turn this user into a God
    update_data = {
        "$set": {
            "role": "ADMIN",
            "is_superuser": True,
            "is_staff": True,
            "subscription_status": "ACTIVE"
        }
    }
    
    # Try the standard Beanie collection name 'User' first
    for col in ["User", "users"]:
        res = db[col].update_one({"email": TARGET_EMAIL}, update_data)
        if res.matched_count > 0:
            print(f"✅ SUCCESS! User '{TARGET_EMAIL}' in collection '{col}' is now an ADMIN.")
            return

    print("❌ Error: User not found in DB. Are you sure you registered with 'shabanbala@gmail.com'?")

if __name__ == "__main__":
    promote()