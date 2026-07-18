# Phoenix Protocol: Admin User Injection (Direct Database Access)
import os
import asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Security Alignment: Must match the backend's encryption
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def inject_admin():
    # 1. Load your verified Cloud Credentials
    load_dotenv("backend/.env")
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME")

    print(f"Connecting to Atlas: {uri.split('@')[1]}...")
    client = AsyncIOMotorClient(uri)
    db = client[db_name]

    # 2. Define the Admin Identity
    email = "shabanbala@gmail.com"
    plain_password = "shabanbala"
    
    # 3. Create the Database Record
    # We include all common security flags to ensure the Gatekeeper lets you in
    admin_user = {
        "email": email,
        "hashed_password": pwd_context.hash(plain_password),
        "full_name": "Shaban Bala (Admin)",
        "is_active": True,
        "is_superuser": True,
        "is_verified": True,
        "created_at": None # Most FastAPI apps handle this, we keep it empty for safety
    }

    try:
        # Check if user already exists
        existing = await db.users.find_one({"email": email})
        if existing:
            print(f"User {email} already exists. Updating password...")
            await db.users.update_one(
                {"email": email}, 
                {"$set": {"hashed_password": admin_user["hashed_password"], "is_superuser": True}}
            )
        else:
            await db.users.insert_one(admin_user)
            print(f"SUCCESS: Admin account '{email}' injected into MongoDB Atlas.")
            
        print("--- STATUS: ACCESS GRANTED ---")
        print("You can now log in at https://juristi.tech")
        
    except Exception as e:
        print(f"CRITICAL INJECTION FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(inject_admin())