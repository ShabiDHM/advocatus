import os
import requests
import fitz  # PyMuPDF
import time
import sys
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# --- AUTHENTICATION AWARE ---
# We will get the MONGO_URI from the command line for security and reliability.

DB_NAME = "juristi_knowledge"
VERDICTS_COLLECTION = "verdicts_metadata"

class KJCService:
    def __init__(self, mongo_uri):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[DB_NAME]
        self.verdicts = self.db[VERDICTS_COLLECTION]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.gjyqesori-rks.org/aktgjykimet/?r=M'
        })

    # ... (No changes to _download_pdf or _extract_text) ...
    def _download_pdf_to_memory(self, url):
        try:
            response = self.session.get(url, timeout=20)
            if response.status_code == 200:
                return response.content
            else:
                print(f"      ❌ Blocked! Status: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"      ❌ Network Error: {e}")
            return None

    def _extract_text_from_bytes(self, pdf_bytes):
        try:
            text = ""
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text() # type: ignore
            return text
        except Exception as e:
            print(f"      ⚠️ PDF Parse Error: {e}")
            return None

    def process_pending_verdicts(self, limit=50):
        print("⚙️  KJC SERVICE (v4 - Authenticated): Starting...")
        
        query = {"status": "indexed"}
        pending_count = self.verdicts.count_documents(query)
        print(f"   - Pending Queue: {pending_count} verdicts.")
        
        if pending_count == 0: return

        cursor = self.verdicts.find(query).limit(limit)
        success_count = 0
        
        for doc in cursor:
            case_number = doc.get("case_number", "Unknown")
            print(f"   📖 Processing: {case_number}...")
            
            pdf_bytes = self._download_pdf_to_memory(doc.get("pdf_url"))
            
            if pdf_bytes:
                raw_text = self._extract_text_from_bytes(pdf_bytes)
                if raw_text and len(raw_text) > 100:
                    self.verdicts.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"full_text": raw_text, "status": "ready_for_ai", "text_length": len(raw_text)}}
                    )
                    success_count += 1
                else:
                    self.verdicts.update_one({"_id": doc["_id"]}, {"$set": {"status": "failed_empty"}})
            else:
                self.verdicts.update_one({"_id": doc["_id"]}, {"$set": {"status": "failed_download"}})
            
            time.sleep(1)

        print(f"✅ Batch Complete. Processed {success_count} of {limit} attempted.")

# --- STANDALONE EXECUTION ---
if __name__ == "__main__":
    # The script now requires the MONGO_URI to be passed to it
    if len(sys.argv) < 2:
        print("❌ Error: Missing MONGO_URI.")
        print("   Usage: python3 app/services/kjc_service.py 'mongodb://user:pass@host...'")
        sys.exit(1)
        
    mongo_uri_arg = sys.argv[1]
    
    try:
        service = KJCService(mongo_uri=mongo_uri_arg)
        service.process_pending_verdicts(limit=100)
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to MongoDB. Check your URI.")
        print(f"   - Details: {e}")