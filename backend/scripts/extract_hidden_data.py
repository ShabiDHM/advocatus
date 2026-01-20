import requests
import re
import json

TARGET_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge"

def extract_json_blob():
    print(f"🕵️  Deep Scanning: {TARGET_URL}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers)
        html = response.text
        
        print(f"📡 Page Size: {len(html)} bytes")
        print("🔍 Searching for embedded JSON data containing 'Gjykata'...")
        
        # Regex: Find any JSON-like array [ { ... } ] that is fairly long
        # We look specifically for blocks containing the column headers we saw earlier
        potential_arrays = re.findall(r'\[\s*\{.*?\}\s*\]', html, re.DOTALL)
        
        found = False
        
        for block in potential_arrays:
            # Filter: Check if this block contains our keywords
            if "Gjykata" in block and "Gjyqtari" in block:
                print(f"\n✅ MATCH FOUND! (Block Size: {len(block)} chars)")
                
                # Save it to a file immediately so we don't lose it
                output_file = "kjc_raw_data.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(block)
                
                print(f"   - Snippet: {block[:150]}...")
                print(f"   - 💾 SAVED TO: {output_file}")
                print("   - This file contains the raw list of judges and cases.")
                found = True
                break
        
        if not found:
            print("\n❌ No data array found in the HTML source.")
            print("   Plan C: We will look for the 'Read' URL again with a broader search.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extract_json_blob()
    