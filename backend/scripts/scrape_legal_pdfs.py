# FILE: backend/scripts/scrape_legal_pdfs.py
# JURISTI AI - ACADEMY OF JUSTICE CLEAN PDF ONLY SCRAPER V1.4

import os
import sys
import re
import urllib.request
import urllib.parse
from pathlib import Path

# --- DIRECTORY PATHS ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
TARGET_DIR = BACKEND_DIR.parent / "data" / "laws" / "ks"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# --- FOCUS ONLY ON ACADEMY OF JUSTICE 2025 ---
TARGETS = {
    "Akademia_e_Drejt_2025": "https://ad.rks-gov.net/sq/doracak-dhe-udhezues?selectedYear=2025"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def sanitize_filename(name: str) -> str:
    name = re.sub(r'<[^>]*>', '', name)
    name = name.replace(" ", "_").replace("/", "-")
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '', name)

def get_safe_url(url_str: str) -> str:
    """Safely percent-encodes spaces and special characters inside URL paths."""
    parsed = urllib.parse.urlparse(url_str)
    # Quote/encode only the path portion of the URL (e.g., spaces to %20)
    safe_path = urllib.parse.quote(parsed.path)
    safe_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        safe_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    return safe_url

def download_file(url: str, filename: str):
    save_path = TARGET_DIR / filename
    if save_path.exists():
        print(f"   ⏭️  Skipped: {filename} (Already exists locally)")
        return True

    safe_url = get_safe_url(url)
    print(f"   📥 Downloading: {filename}...")
    try:
        req = urllib.request.Request(safe_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(save_path, 'wb') as f:
                f.write(response.read())
        print(f"   ✅ Saved: {save_path.name}")
        return True
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return False

def scrape_portal(name: str, url: str):
    print(f"\n📡 Scanning Portal: {name} ({url})")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # Find all href links on the page
        raw_links = re.findall(r'href=["\']([^"\']+)["\']', html, re.I)
        raw_links = list(set([l.strip() for l in raw_links if l.strip() and not l.startswith('#')]))
        
        pdf_count = 0
        for href in raw_links:
            parsed_href = urllib.parse.urlparse(href)
            path_lower = parsed_href.path.lower()
            
            # STRICT FILTER: Only download actual PDFs or documents (usually stored in /media/)
            is_file = path_lower.endswith('.pdf') or path_lower.endswith('.docx') or '/media/' in path_lower
            
            if is_file:
                absolute_url = urllib.parse.urljoin(url, href)
                
                # Extract clean official filename from the URL path
                base_name = urllib.parse.unquote(os.path.basename(parsed_href.path))
                if not base_name or base_name == "page.aspx" or not base_name.endswith('.pdf'):
                    base_name = f"document_{hash(href)}.pdf"
                
                clean_text = sanitize_filename(base_name)
                filename = f"{name.upper()}_{clean_text}"
                
                download_file(absolute_url, filename)
                pdf_count += 1
                
        print(f"\n🏁 Scan Finished. Downloaded {pdf_count} clean official PDFs.")
        
    except Exception as e:
        print(f"❌ Scraper failure on portal '{name}': {e}")

if __name__ == "__main__":
    print("--- [JURISTI AI] Starting Clean Official PDF Scraper ---")
    for portal_name, url in TARGETS.items():
        scrape_portal(portal_name, url)