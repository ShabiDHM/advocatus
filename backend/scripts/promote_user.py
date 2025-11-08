# FILE: backend/scripts/promote_user.py
# DEFINITIVE VERSION 1.0 - FEATURE: Script to promote a standard user to 'admin' role.

import os
import sys
import asyncio
import argparse
from bson import ObjectId
import pymongo
from pymongo import MongoClient

# --- Configuration Loader (Assumed from Project Structure) ---
# NOTE: Replace with your actual configuration loading mechanism if different
def get_mongo_client(db_uri: str) -> MongoClient:
    try:
        client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster') 
        return client
    except pymongo.errors.ConnectionFailure as e:
        print(f"ERROR: Failed to connect to MongoDB at {db_uri}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        sys.exit(1)


def promote_user(username: str, db_uri: str, db_name: str = "phoenix_protocol_db"):
    """
    Finds a user by username and updates their role to 'admin'.
    """
    client = get_mongo_client(db_uri)
    db = client[db_name]
    
    # 1. Find the user
    user_query = {"username": username}
    user_doc = db.users.find_one(user_query)
    
    if not user_doc:
        print(f"ERROR: User '{username}' not found in the database.")
        client.close()
        sys.exit(1)
        
    current_role = user_doc.get("role", "user")
    
    if current_role == "admin":
        print(f"SUCCESS: User '{username}' is already an 'admin'. No change made.")
        client.close()
        sys.exit(0)
    
    # 2. Update the user's role
    update_result = db.users.update_one(
        user_query,
        {"$set": {"role": "admin"}}
    )
    
    if update_result.modified_count == 1:
        print("="*60)
        print(f"SUCCESS: User '{username}' promoted to 'admin' role.")
        print(f"ID: {user_doc['_id']}")
        print(f"Old Role: {current_role.upper()} -> New Role: ADMIN")
        print("="*60)
    else:
        print(f"WARNING: User '{username}' found, but role was not updated. (Modified count: 0)")

    client.close()


if __name__ == "__main__":
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Promote a user to 'admin' role in the Advocatus AI platform.")
    parser.add_argument("username", type=str, help="The username of the user to promote.")
    args = parser.parse_args()
    
    # --- Environment Variable Check ---
    # NOTE: These must be available in the execution environment (e.g., docker compose exec)
    db_uri = os.environ.get("DATABASE_URI")
    db_name = os.environ.get("DATABASE_NAME", "phoenix_protocol_db") # Use default if name not specified
    
    if not db_uri:
        print("CRITICAL ERROR: DATABASE_URI environment variable is not set. Cannot connect to MongoDB.")
        sys.exit(1)
        
    promote_user(args.username, db_uri, db_name)