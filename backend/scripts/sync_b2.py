# FILE: backend/scripts/sync_b2.py
# PHOENIX PROTOCOL - INCREMENTAL B2 LAW PDF SYNC SCRIPT (STANDALONE SCRIPTS FOLDER)

import os
import sys

# Calculate absolute paths relative to script location
script_dir = os.path.dirname(os.path.abspath(__file__))      # backend/scripts
backend_dir = os.path.dirname(script_dir)                   # backend
project_root = os.path.dirname(backend_dir)                # ADVOCATUS (Root)

# Add backend directory to Python path
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables from backend/.env
env_path = os.path.join(backend_dir, '.env')
try:
    from dotenv import load_dotenv
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

from app.services import storage_service

def upload_new_laws_only():
    print("🚀 Connecting to Backblaze B2 Storage...")
    s3 = storage_service.get_s3_client()
    bucket = storage_service.B2_BUCKET_NAME

    # Step 1: Fetch list of files already stored in Backblaze B2 under 'laws/'
    print("🔍 Checking existing cloud files in Backblaze B2...")
    existing_b2_files = set()
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
        for obj in response.get('Contents', []):
            key = obj.get('Key', '')
            filename = os.path.basename(key)
            if filename:
                existing_b2_files.add(filename)
                existing_b2_files.add(key)
        print(f"📦 Found {len(existing_b2_files)} existing files in Backblaze B2.")
    except Exception as e:
        print(f"⚠️ Warning during existing B2 inspection: {e}")

    # Step 2: Locate local laws directory
    candidate_laws_dirs = [
        os.path.join(project_root, "data", "laws"),
        os.path.join(backend_dir, "data", "laws"),
        "data/laws"
    ]

    laws_dir = None
    for cand in candidate_laws_dirs:
        if os.path.exists(cand):
            laws_dir = cand
            break

    if not laws_dir:
        print(f"❌ Could not find data/laws directory in {candidate_laws_dirs}")
        return

    print(f"📂 Scanning local directory: {laws_dir}")

    uploaded_count = 0
    skipped_count = 0

    # Step 3: Scan and upload ONLY new PDF files
    for root, _, files in os.walk(laws_dir):
        rel_path = os.path.relpath(root, laws_dir)
        subfolder = '' if rel_path == '.' else rel_path.replace('\\', '/')

        for f in files:
            if f.lower().endswith('.pdf'):
                filepath = os.path.join(root, f)
                b2_key = f"laws/{subfolder}/{f}".replace('//', '/') if subfolder else f"laws/{f}"

                # Skip if file already exists in cloud
                if f in existing_b2_files or b2_key in existing_b2_files:
                    print(f"  ⏭ Skipped (Already in B2): {f}")
                    skipped_count += 1
                    continue

                print(f"Uploading NEW law [{f}] -> B2 Key: '{b2_key}'...")
                s3.upload_file(
                    filepath,
                    bucket,
                    b2_key,
                    ExtraArgs={'ContentType': 'application/pdf'}
                )
                print(f"  ✓ Success!")
                uploaded_count += 1

    print(f"\n🎉 SYNC COMPLETE! Uploaded: {uploaded_count} new file(s) | Skipped: {skipped_count} existing file(s).")

if __name__ == '__main__':
    upload_new_laws_only()