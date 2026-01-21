import os
import requests
import fitz  # PyMuPDF
import time
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "juristi_knowledge"
VERDICTS_COLLECTION = "verdicts_metadata"

class KJCService:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.verdicts = self.db[VERDICTS_COLLECTION]
        # Define a session to reuse headers and connections
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.gjyqesori-rks.org/aktgjykimet/?r=M'
        })

    def _download_pdf_to_memory(self, url):
        """Internal: Downloads PDF bytes with robust headers and error logging."""
        try:
            response = self.session.get(url, timeout=20)
            if response.status_code == 200:
                return response.content
            else:
                # This is the new, important log message
                print(f"      ❌ Blocked! Server returned Status Code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            # This will print network errors like timeouts
            print(f"      ❌ Network Error: {e}")
            return None

    def _extract_text_from_bytes(self, pdf_bytes):
        """Internal: OCR/Text Extraction using PyMuPDF."""
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
        """Main Worker Function to process the queue."""
        print("⚙️  KJC SERVICE (v2): Starting Verdict Processor...")
        
        query = {"status": "indexed"} 
        pending_count = self.verdicts.count_documents(query)
        
        print(f"   - Pending Queue: {pending_count} verdicts.")
        
        if pending_count == 0:
            return

        cursor = self.verdicts.find(query).limit(limit)
        success_count = 0
        
        for doc in cursor:
            case_number = doc.get("case_number", "Unknown")
            pdf_url = doc.get("pdf_url")
            
            print(f"   📖 Processing: {case_number}...")
            
            pdf_bytes = self._download_pdf_to_memory(pdf_url)
            
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
                # The download function now prints the specific error
                self.verdicts.update_one({"_id": doc["_id"]}, {"$set": {"status": "failed_download"}})
            
            time.sleep(1) # Be polite

        print(f"✅ Batch Complete. Successfully processed {success_count} of {limit} attempted verdicts.")

if __name__ == "__main__":
    service = KJCService()
    service.process_pending_verdicts(limit=100)