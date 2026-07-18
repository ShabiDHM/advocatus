# Phoenix Protocol: Final Database Status Alignment
import os
from dotenv import load_dotenv
from pymongo import MongoClient

def align():
    load_dotenv("backend/.env")
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    print("Connecting to Atlas...")
    client = MongoClient(uri)
    db = client[db_name]
    
    # We find all records for your uploaded PDF and set them to READY (the correct enum)
    print("Aligning all 'Seanca e par Get_com.pdf' records to 'READY'...")
    res = db.documents.update_many(
        {"file_name": "Seanca e par Get_com.pdf"},
        {"$set": {"status": "READY"}}
    )
    
    print(f"--- STATUS: SUCCESS ---")
    print(f"Aligned {res.modified_count} document records to 'READY'.")

if __name__ == "__main__":
    align()