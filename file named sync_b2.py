import os
import sys

# Ensure backend directory is in Python path
sys.path.insert(0, 'backend')

try:
    from dotenv import load_dotenv
    load_dotenv('backend/.env')
except ImportError:
    pass

from app.services import storage_service

def upload_all_laws():
    print("🚀 Connecting to Backblaze B2 Storage...")
    s3 = storage_service.get_s3_client()
    bucket = storage_service.B2_BUCKET_NAME
    
    laws_dir = os.path.join('data', 'laws', 'ks')
    if not os.path.exists(laws_dir):
        laws_dir = os.path.join('backend', 'data', 'laws', 'ks')

    if not os.path.exists(laws_dir):
        print(f"❌ Could not find directory: {laws_dir}")
        return

    count = 0
    for root, _, files in os.walk(laws_dir):
        for f in files:
            if f.lower().endswith('.pdf'):
                filepath = os.path.join(root, f)
                b2_key = f"laws/ks/{f}"
                print(f"Uploading [{f}] -> B2 Key: '{b2_key}'...")
                s3.upload_file(
                    filepath, 
                    bucket, 
                    b2_key, 
                    ExtraArgs={'ContentType': 'application/pdf'}
                )
                print(f"  ✓ Success!")
                count += 1

    print(f"\n🎉 SUCCESS! All {count} law PDF files are now live in Backblaze B2 Cloud!")

if __name__ == '__main__':
    upload_all_laws()