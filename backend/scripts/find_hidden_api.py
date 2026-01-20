import requests
import re

# The target URL we are analyzing
TARGET_URL = "https://odp.gjyqesori-rks.org/PredefinedReports/CourtJudge"

def extract_api_endpoint():
    print(f"🕵️  Connecting to: {TARGET_URL}")
    print("    (This might take a few seconds...)")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 1. Get the raw HTML from the website
        response = requests.get(TARGET_URL, headers=headers)
        response.raise_for_status()
        html_content = response.text
        
        print("✅ Connected. Scanning for Kendo UI configurations...")

        # 2. Define patterns to find the data URL
        # Pattern A: Standard Kendo MVC wrapper (read: { url: "/Path" })
        pattern_a = r"read:\s*\{\s*url:\s*['\"]([^'\"]+)['\"]"
        
        # Pattern B: Generic AJAX call inside the script
        pattern_b = r"\.ajax\(\{\s*url:\s*['\"]([^'\"]+)['\"]"

        matches_a = re.findall(pattern_a, html_content)
        matches_b = re.findall(pattern_b, html_content)
        
        found = False

        if matches_a:
            print("\n🎯 MATCH FOUND (Type A - Kendo):")
            for url in matches_a:
                print(f"   -> {url}")
            found = True

        if matches_b:
            print("\n🎯 MATCH FOUND (Type B - Generic AJAX):")
            for url in matches_b:
                # Filter out common junk like google analytics
                if "google" not in url and "http" not in url: 
                    print(f"   -> {url}")
            found = True

        if not found:
            print("\n⚠️  No direct API URL found in the HTML.")
            print("   This likely means the data is 'Server-Side Rendered' (baked into the HTML table).")
            print("   We will need to use a Scraper strategy.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extract_api_endpoint()