import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge"

def scrape_table():
    print(f"🕵️  Downloading HTML from: {TARGET_URL}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Look for standard tables
        tables = soup.find_all('table')
        
        print(f"\n📊 Found {len(tables)} tables.")
        
        if tables:
            # Get the first table (usually the data grid)
            main_table = tables[0]
            rows = main_table.find_all('tr')
            print(f"   - Table has {len(rows)} rows.")
            
            print("\n📝 Sample Data (First 3 Rows):")
            for i, row in enumerate(rows[:3]):
                cols = row.find_all(['th', 'td'])
                # Clean text and join with " | "
                row_text = " | ".join([ele.text.strip() for ele in cols if ele.text.strip()])
                print(f"   Row {i}: {row_text}")
                
            print("\n✅ VERDICT: If you see judge names above, we can scrape this easily.")
        else:
            print("❌ No HTML tables found. The data might be in a JavaScript variable.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    scrape_table()