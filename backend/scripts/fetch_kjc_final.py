import requests
import json
import time

# Configuration
TARGET_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge"
OUTPUT_FILE = "kjc_judicial_data.json"

def fetch_data():
    print("🚀 STARTING: KJC Data Acquisition Protocol")
    
    # 1. Initialize Session (This acts like a Browser)
    session = requests.Session()
    
    # Set Headers to mimic Google Chrome exactly
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'sq-AL,sq;q=0.9,en-US;q=0.8,en;q=0.7',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://odp.gjyqesori-rks.org',
        'Referer': 'https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge?handler=ApplyFilters'
    })

    try:
        # 2. First Visit: "Wake up" the site and get Cookies
        print("1️⃣  Establishing Session (GET)...")
        response_init = session.get(TARGET_URL)
        print(f"   - Status: {response_init.status_code}")
        print(f"   - Cookies received: {len(session.cookies)}")

        # 3. Construct the DataTables Payload
        # We ask for 1000 rows to ensure we get almost everyone
        payload = {
            "draw": "1",
            "columns[0][data]": "CourtName",
            "columns[0][name]": "CourtName",
            "columns[0][searchable]": "true",
            "columns[0][orderable]": "true",
            "columns[0][search][value]": "",
            "columns[0][search][regex]": "false",
            
            "columns[1][data]": "JudgeFullName",
            "columns[1][name]": "JudgeFullName",
            "columns[1][searchable]": "true",
            "columns[1][orderable]": "true",
            "columns[1][search][value]": "",
            "columns[1][search][regex]": "false",
            
            "columns[2][data]": "DepartmentType",
            "columns[2][name]": "DepartmentType",
            "columns[2][searchable]": "true",
            "columns[2][orderable]": "true",
            "columns[2][search][value]": "",
            "columns[2][search][regex]": "false",
            
            "columns[3][data]": "TotalCases",
            "columns[3][name]": "TotalCases",
            "columns[3][searchable]": "true",
            "columns[3][orderable]": "true",
            "columns[3][search][value]": "",
            "columns[3][search][regex]": "false",
            
            "order[0][column]": "3", # Sort by Total Cases
            "order[0][dir]": "desc",
            "start": "0",
            "length": "500",  # Requesting 500 records
            "search[value]": "",
            "search[regex]": "false"
        }

        # 4. The Extraction: POST request
        print("2️⃣  Requesting Data (POST)...")
        response_post = session.post(TARGET_URL, data=payload)
        
        print(f"   - Status: {response_post.status_code}")
        
        if response_post.status_code == 200:
            try:
                data = response_post.json()
                
                # Verify we got real data
                if "data" in data:
                    records = data["data"]
                    count = len(records)
                    print(f"\n✅ SUCCESS! Downloaded {count} judicial records.")
                    
                    # Save to JSON
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=4, ensure_ascii=False)
                        
                    print(f"   - 💾 Saved to: {OUTPUT_FILE}")
                    
                    # Preview Data
                    print("\n📊 Sample Data (Top 3 Busiest Judges):")
                    for i, record in enumerate(records[:3]):
                        print(f"   {i+1}. {record.get('JudgeFullName')} ({record.get('CourtName')}): {record.get('TotalCases')} cases")
                        
                else:
                    print("⚠️  Response JSON format unexpected (missing 'data' key).")
                    print(data.keys())
                    
            except json.JSONDecodeError:
                print("❌ Failed to parse JSON. Server returned HTML instead.")
                # Save HTML for debugging
                with open("error_debug.html", "w", encoding="utf-8") as f:
                    f.write(response_post.text)
                print("   - Saved HTML response to 'error_debug.html'")
        else:
            print("❌ Server rejected the request.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    fetch_data()