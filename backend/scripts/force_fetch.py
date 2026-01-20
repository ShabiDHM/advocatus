import requests
from bs4 import BeautifulSoup
import json

# The base URL where the user sees the page
BASE_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge"

# Common Kendo UI endpoints for data fetching
POSSIBLE_ENDPOINTS = [
    "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge",       # Often it's just a POST to the same URL
    "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge_Read",  # Common convention
    "https://odp.gjyqesori-rks.org/PredefinedReports/Read",             # Another convention
]

def force_fetch_data():
    print("🚀 Starting Operation 'Knock on Door' (v2)...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',  # Tells server "I am a script, not a human"
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    })

    try:
        # 1. GET request to establish session and get Cookies
        print("1️⃣  Visiting page to get Cookies...")
        response_get = session.get(BASE_URL)
        
        # Try to find Anti-Forgery Token (Security Key)
        soup = BeautifulSoup(response_get.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        
        payload = {
            "sort": "", 
            "group": "", 
            "filter": ""
        }
        
        if token_input:
            # Safe extraction of the value
            token_val = token_input.get('value')
            # If it's a list (rare), take the first item
            if isinstance(token_val, list):
                token_val = token_val[0]
                
            print(f"   🔑 Found Security Token: {str(token_val)[:15]}...")
            payload['__RequestVerificationToken'] = str(token_val)
        
        # 2. Try POST requests to likely endpoints
        print("\n2️⃣  Attempting to fetch data via POST...")
        
        for url in POSSIBLE_ENDPOINTS:
            print(f"   👉 Trying: {url}")
            try:
                # Send the POST request
                response_post = session.post(url, data=payload)
                
                # Check if we got JSON back
                try:
                    data = response_post.json()
                    # Kendo usually wraps data in {"Data": [...], "Total": 50}
                    if "Data" in data or isinstance(data, list):
                        print(f"\n✅ SUCCESS! URL '{url}' returned data!")
                        
                        # Save it
                        with open("kjc_judges.json", "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        print("   - 💾 Saved to 'kjc_judges.json'")
                        return # Stop if we found it
                    else:
                        print("      (Got JSON, but it looks empty or wrong format)")
                except ValueError:
                    print("      ❌ Not JSON (likely returned HTML error page).")
                    
            except Exception as e:
                print(f"      ❌ Connection Failed: {e}")

        print("\n🏁 Operation Finished.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    force_fetch_data()