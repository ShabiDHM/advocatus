import os
import glob
from bs4 import BeautifulSoup
import json
from datetime import datetime

def find_and_parse():
    print("🕵️  SEARCHING FOR HTML FILE...")
    
    # 1. Define Paths
    user_home = os.path.expanduser("~")
    desktop_path = os.path.join(user_home, "Desktop")
    current_dir = os.getcwd()
    
    # 2. Look for HTML files
    search_patterns = [
        os.path.join(current_dir, "*.html"),
        os.path.join(desktop_path, "*.html")
    ]
    
    candidates = []
    for pattern in search_patterns:
        files = glob.glob(pattern)
        for f in files:
            try:
                stats = os.stat(f)
                mod_time = stats.st_mtime
                # Keep if recent (last 24 hours) or has key keywords
                if "kjc" in f.lower() or "aktgjykimet" in f.lower() or (datetime.now().timestamp() - mod_time < 86400):
                    candidates.append((f, mod_time))
            except:
                continue
    
    if not candidates:
        print("❌ No likely HTML files found on Desktop or Backend folder.")
        print("   Please save the webpage as 'kjc_results.html' on your Desktop.")
        return

    # Sort by newest first
    candidates.sort(key=lambda x: x[1], reverse=True)
    target_file = candidates[0][0]
    
    print(f"📂 FOUND FILE: {target_file}")
    print("   (Parsing this file...)")

    # 3. Parse
    with open(target_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    print("🔍 EXTRACTING VERDICTS...")
    rows = soup.find_all("tr")
    print(f"   - Scanning {len(rows)} table rows...")
    
    extracted_data = []
    
    for row in rows:
        try:
            cells = row.find_all("td")
            if len(cells) < 7: continue 
            
            # Extract basic text
            case_number = cells[1].get_text(strip=True)
            date = cells[2].get_text(strip=True)
            judge = cells[4].get_text(strip=True)
            court = cells[5].get_text(strip=True)
            
            # Extract PDF Link safely
            pdf_url = ""
            link_tag = row.find("a")
            
            if link_tag:
                # Get the raw attribute
                raw_href = link_tag.get("href")
                
                # Type Conversion: Ensure it is a string
                href_str = ""
                if isinstance(raw_href, list):
                    href_str = str(raw_href[0])
                elif raw_href is not None:
                    href_str = str(raw_href)
                
                # Check link validity
                if "pdf" in href_str.lower() or "download" in href_str.lower():
                    if href_str.startswith("http"):
                        pdf_url = href_str
                    else:
                        pdf_url = "https://www.gjyqesori-rks.org" + href_str
            
            # Save only valid entries
            if pdf_url:
                extracted_data.append({
                    "case_number": case_number,
                    "date": date,
                    "judge": judge,
                    "court": court,
                    "pdf_url": pdf_url
                })
                
        except Exception:
            continue
            
    # 4. Save Result
    if extracted_data:
        output_file = os.path.join(current_dir, "kjc_verdicts_final.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=4, ensure_ascii=False)
        print(f"\n🎉 SUCCESS! Extracted {len(extracted_data)} verdicts.")
        print(f"   - 💾 Saved to: {output_file}")
        print("   - This file will now be used for AI Training.")
    else:
        print("\n❌ Found the HTML file, but couldn't find any PDF links inside it.")

if __name__ == "__main__":
    find_and_parse()