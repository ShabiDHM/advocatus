from playwright.sync_api import sync_playwright
import json
import os

def harvest_verdicts():
    print("🐴 TROJAN HARVESTER INITIATED (Persistent Session)")
    print("------------------------------------------------")
    
    # Create a local folder to store cookies so Cloudflare remembers us
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    
    with sync_playwright() as p:
        # 1. Launch Browser with a Real User Profile
        print(f"1️⃣  Launching Chrome with profile at: {user_data_dir}")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome", # Uses your actual installed Google Chrome
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled", # Hides 'Navigator.webdriver' flag
                "--no-sandbox"
            ]
        )
        
        page = context.pages[0]
        
        # 2. Navigate
        print("2️⃣  Navigating to KJC Decisions Portal...")
        page.goto("https://www.gjyqesori-rks.org/aktgjykimet/?r=M")
        
        print("\n🛑 ACTION REQUIRED:")
        print("   1. If the Cloudflare check appears, CLICK IT.")
        print("      (It should pass now because we look like a real user).")
        print("   2. Select 'Gjykata Themelore Prishtinë'.")
        print("   3. Select Year '2024'.")
        print("   4. Click 'Kërko' and WAIT for the table.")
        
        input("\n👉 WHEN READY (Table is visible), press ENTER here...")
        
        # 3. Scrape
        print("3️⃣  Scraping data...")
        rows = page.query_selector_all("table tbody tr")
        print(f"   - Found {len(rows)} rows.")
        
        extracted_data = []
        
        for row in rows:
            try:
                cells = row.query_selector_all("td")
                if len(cells) < 8: continue
                
                case_number = cells[1].inner_text().strip()
                judge = cells[4].inner_text().strip()
                
                # Get Link safely
                link_el = cells[7].query_selector("a")
                pdf_url = ""
                if link_el:
                    raw_href = link_el.get_attribute("href")
                    if raw_href:
                        if not raw_href.startswith("http"):
                            pdf_url = "https://www.gjyqesori-rks.org" + raw_href
                        else:
                            pdf_url = raw_href
                
                if pdf_url:
                    extracted_data.append({
                        "case_number": case_number,
                        "judge": judge,
                        "court": cells[5].inner_text().strip(),
                        "pdf_url": pdf_url
                    })
                    print(f"   ✅ Captured: {case_number}")
            except:
                continue

        # 4. Save
        if extracted_data:
            with open("kjc_verdicts_raw.json", "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=4, ensure_ascii=False)
            print(f"\n💾 SUCCESS! Saved {len(extracted_data)} verdicts.")
        else:
            print("\n❌ No data captured.")

        context.close()

if __name__ == "__main__":
    harvest_verdicts()