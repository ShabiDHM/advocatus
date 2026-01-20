import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge"
HANDLER_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge?handler=ApplyFilters"

def intercept_and_post():
    print("🚀 Initiating Form Interceptor Protocol...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })

    try:
        # Phase 1: Reconnaissance (Get the Token and Form Fields)
        print("1️⃣  Fetching Main Page to find Form Fields & Security Token...")
        response = session.get(TARGET_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Security Token
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if not token_input:
            print("❌ CRITICAL: Could not find Anti-Forgery Token. The site is heavily protected.")
            return
            
        token = token_input['value']
        print(f"   🔑 Token Acquired: {token[:15]}...")

        # Phase 2: Identify Form Parameters
        print("\n2️⃣  Scanning for Input Fields...")
        inputs = soup.find_all(['input', 'select'])
        form_data = {}
        
        # Build a default payload
        for inp in inputs:
            name = inp.get('name')
            if name and name != '__RequestVerificationToken':
                # Try to guess default values
                if 'Year' in name:
                    form_data[name] = "2024" # Target last year for data
                elif 'Court' in name:
                    form_data[name] = "" # Leave empty to get all?
                else:
                    form_data[name] = ""
                print(f"   - Found Field: {name}")

        # Add the token to our payload
        form_data['__RequestVerificationToken'] = token
        
        print(f"\n   📦 Constructed Payload: {form_data}")

        # Phase 3: The Attack (Simulate the Button Click)
        print("\n3️⃣  Sending POST Request to Handler...")
        response_post = session.post(HANDLER_URL, data=form_data)
        
        print(f"   📡 Response Status: {response_post.status_code}")
        print(f"   📡 Response Size: {len(response_post.text)} bytes")
        
        # Analyze the result
        if response_post.status_code == 200:
            # Check if we got data back (look for judge names or JSON)
            if "Gjyqtari" in response_post.text:
                print("✅ SUCCESS: The server accepted our fake form!")
                
                # Check for embedded JSON data in the new response
                import re
                # Look for the data array again in the RESPONSE
                matches = re.findall(r"data\s*:\s*(\[\s*\{.*?\}\s*\])", response_post.text, re.DOTALL)
                if matches:
                    largest = max(matches, key=len)
                    print(f"🎉 FOUND DATA PAYLOAD ({len(largest)} chars)!")
                    with open("kjc_final_data.json", "w", encoding="utf-8") as f:
                        f.write(largest)
                    print("   - 💾 Saved to 'kjc_final_data.json'")
                else:
                    print("⚠️  Request worked, but couldn't auto-extract JSON. Saving HTML for review.")
                    with open("kjc_response.html", "w", encoding="utf-8") as f:
                        f.write(response_post.text)
            else:
                print("❌ The server returned a page, but it looks like the default page (no filter applied).")
        else:
            print("❌ Server rejected the request.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    intercept_and_post()