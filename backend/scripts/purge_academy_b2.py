# FILE: backend/scripts/purge_academy_b2.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

for p in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)

sys.path.append(str(BACKEND_DIR))

from app.services import storage_service

def purge_b2_academy():
    print("--- [PHOENIX] Purging Academic Files from Backblaze B2 ---")
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        
        response = s3.list_objects_v2(Bucket=bucket)
        contents = response.get('Contents', [])
        
        deleted_count = 0
        for obj in contents:
            key = obj.get('Key', '')
            filename_upper = key.upper()
            
            if any(k in filename_upper for k in ["AKADEMIA", "KOMMENTAR", "DORACAK"]) or key.startswith("academic/"):
                s3.delete_object(Bucket=bucket, Key=key)
                print(f"🗑️ Deleted from Backblaze B2: {key}")
                deleted_count += 1
                
        print(f"✅ Successfully purged {deleted_count} academic files from Backblaze B2!")
    except Exception as e:
        print(f"❌ Error purging Backblaze B2: {e}")

if __name__ == "__main__":
    purge_b2_academy()