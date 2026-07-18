# Phoenix Protocol: Local OCR Diagnostic (Simplified)
import os
import sys
import time
import glob
from dotenv import load_dotenv

# --- PHOENIX PATH ALIGNMENT ---
# Inject the backend folder so Python can find 'app'
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(CURRENT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.text_extraction_service import extract_text

def test():
    # Load env variables
    load_dotenv("backend/.env")
    
    # Find any PDF in the data/laws folder to test
    laws_dir = os.path.join(CURRENT_DIR, "data", "laws")
    files = glob.glob(os.path.join(laws_dir, "**", "*.pdf"), recursive=True)
    
    if not files:
        print("❌ ERROR: No PDF files found in data/laws/ to test.")
        return
        
    target = files[0]
    print(f"--- Starting Local OCR Test on: {target} ---")
    print("Engaging Google Cloud Vision... Please wait.")
    
    start_time = time.time()
    
    # Run the raw text extraction
    text = extract_text(str(target), "application/pdf")
    
    duration = time.time() - start_time
    
    print("\n--- TEST RESULTS ---")
    print(f"STATUS: SUCCESS")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Extracted Length: {len(text)} characters")
    print(f"Preview of Text:\n{text[:300]}")

if __name__ == "__main__":
    test()