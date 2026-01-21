from playwright.sync_api import sync_playwright
import json
import time
import os

# Configuration
OUTPUT_FILE = "kjc_full_dataset.json"

def harvest_invincible():
    print("🚀 INVINCIBLE HARVESTER INITIATED")
    print("------------------------------------------------")
    
    # Use a persistent profile so Cloudflare remembers you are human
    user_data_dir = os.path.join(os.getcwd(), "chrome_data_persistent")
    
    with sync_playwright() as p:
        # 1. Launch Browser (Persistent Context)
        print(f"1️⃣  Launching Chrome Profile at: {user_data_dir}")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # Visible
            channel="chrome", # Use Real Chrome
            viewport={"width": 1600, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        page = context.pages[0]
        
        # 2. Navigate
        print("2️⃣  Navigating to KJC...")
        page.goto("https://www.gjyqesori-rks.org/aktgjykimet/?r=M")
        
        print("\n🛑 HUMAN ACTION REQUIRED:")
        print("   1. Solve the Cloudflare Checkbox (if it appears).")
        print("   2. Select filters (e.g., Year 2024, No Court selected).")
        print("   3. Click 'Kërko' (Search).")
        print("   4. Wait for the table to load.")
        
        input("\n👉 WHEN READY (Table is visible), press ENTER here...")
        
        print("3️⃣  Starting Autopilot...")
        
        all_data = []
        page_num = 1
        
        while True:
            print(f"   📄 Processing Page {page_num}...")
            
            # A. Scrape Rows
            rows = page.query_selector_all("table tbody tr")
            count = 0
            
            for row in rows:
                try:
                    cells = row.query_selector_all("td")
                    if len(cells) < 7: continue
                    
                    # Extract Data
                    case_num = cells[1].inner_text().strip()
                    judge = cells[4].inner_text().strip()
                    
                    # Find PDF Link
                    link_el = cells[7].query_selector("a")
                    pdf_url = ""
                    if link_el:
                        raw = link_el.get_attribute("href")
                        if raw and ("pdf" in raw or "download" in raw):
                            pdf_url = raw if raw.startswith("http") else "https://www.gjyqesori-rks.org" + raw
                    
                    if pdf_url:
                        all_data.append({
                            "case_number": case_num,
                            "date": cells[2].inner_text().strip(),
                            "judge": judge,
                            "court": cells[5].inner_text().strip(),
                            "pdf_url": pdf_url
                        })
                        count += 1
                except:
                    continue
            
            print(f"      + Captured {count} verdicts. (Total: {len(all_data)})")
            
            # B. Save Checkpoint
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=4, ensure_ascii=False)
            
            # C. Click Next
            try:
                # Use the selector we found in the console diagnostic
                next_button = page.query_selector("a.next-page")
                
                if next_button:
                    # Click via JS (Safer than mouse click)
                    page.evaluate("document.querySelector('a.next-page').click()")
                    
                    # Wait for Reload
                    print("      ➡️  Loading next page...")
                    time.sleep(5) # Give it time to reload fully
                    page_num += 1
                else:
                    print("🏁 End of list reached (No 'Next' button).")
                    break
            except Exception as e:
                print(f"⚠️ Error changing page: {e}")
                break

        print(f"\n✅ DONE. Saved {len(all_data)} verdicts to '{OUTPUT_FILE}'.")
        context.close()

if __name__ == "__main__":
    harvest_invincible()