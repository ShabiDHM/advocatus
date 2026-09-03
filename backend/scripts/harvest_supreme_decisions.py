# FILE: backend/scripts/harvest_supreme_decisions.py
# PHOENIX PROTOCOL - AUTOMATED SUPREME COURT DECISION HARVESTER V1.0

import os
import sys
import re
import time
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

DEST_DIR = ROOT_DIR / "data" / "case_law"
if not DEST_DIR.exists():
    DEST_DIR = BACKEND_DIR / "data" / "case_law"
DEST_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("supreme_harvester")

BASE_URL = "https://supreme.gjyqesori-rks.org/publikimet/aktgjykimet/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "sq,en-US;q=0.9,en;q=0.8",
}

def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', '_', name)
    clean = clean.replace(" ", "_").replace("/", "_")
    return clean.strip("_")

def download_pdf(url: str, save_path: Path) -> bool:
    try:
        if save_path.exists() and save_path.stat().st_size > 1000:
            logger.info(f"⏭️  Ekziston tashmë: {save_path.name}")
            return True

        logger.info(f"📥 Duke shkarkuar: {save_path.name}...")
        response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(response.content)
            logger.info(f"   ✅ U ruajt me sukses: {save_path.name} ({len(response.content) // 1024} KB)")
            return True
        else:
            logger.warning(f"   ❌ Dështoi shkarkimi nga {url} (Status: {response.status_code})")
            return False
    except Exception as e:
        logger.error(f"   ❌ Gabim gjatë shkarkimit të {url}: {e}")
        return False

def harvest_supreme_decisions(max_pages: int = 3, max_downloads: int = 20):
    print("\n" + "="*65)
    print("🏛️ PHOENIX HARVESTER - GJYKATA SUPREME E KOSOVËS")
    print(f"📂 Dosja e destinacionit: {DEST_DIR}")
    print(f"📄 Faqe për skanim: {max_pages} | Limiti i shkarkimeve: {max_downloads}")
    print("="*65 + "\n")

    downloaded_count = 0
    session = requests.Session()

    for page in range(1, max_pages + 1):
        page_url = f"{BASE_URL}page/{page}/" if page > 1 else BASE_URL
        logger.info(f"🔍 Duke skanuar faqen {page}: {page_url}")

        try:
            res = session.get(page_url, headers=HEADERS, timeout=20)
            if res.status_code != 200:
                logger.warning(f"Nuk u arrit dot faqja {page} (Status: {res.status_code})")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.find_all("tr")

            if not rows or len(rows) <= 1:
                logger.info("Nuk u gjetën më rreshta me aktgjykime.")
                break

            page_found = 0
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                # Nxirren të dhënat e kolonave
                lloji = cols[0].get_text(strip=True) if len(cols) > 0 else "Vendim"
                numri_rastit = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                gjyqtari = cols[4].get_text(strip=True) if len(cols) > 4 else ""

                # Gjej lidhjet PDF për versionin shqip (SQ)
                links = row.find_all("a")
                sq_link = None
                for a in links:
                    text_label = a.get_text(strip=True).upper()
                    href = a.get("href", "")
                    if href and ("SQ" in text_label or ".pdf" in href.lower()):
                        sq_link = href
                        break

                if sq_link and numri_rastit:
                    clean_case = sanitize_filename(f"{lloji}_{numri_rastit}")
                    clean_judge = sanitize_filename(gjyqtari.split("-")[0].strip()) if gjyqtari else "Gjykata_Supreme"
                    
                    filename = f"{clean_case}_{clean_judge}.pdf"
                    save_path = DEST_DIR / filename

                    success = download_pdf(sq_link, save_path)
                    if success:
                        downloaded_count += 1
                        page_found += 1

                    if downloaded_count >= max_downloads:
                        print(f"\n🛑 U arrit limiti prej {max_downloads} shkarkimesh.")
                        break

                    time.sleep(0.5)  # Mbrojtje nga mbingarkimi i serverit zyrtar

            logger.info(f"✅ Faqja {page} përfundoi: {page_found} aktgjykime të reja.")

            if downloaded_count >= max_downloads:
                break

        except Exception as e:
            logger.error(f"Gabim në faqen {page}: {e}")
            break

    print("\n" + "="*65)
    print(f"🏁 HARVESTING PËRFUNDOI ME SUKSES!")
    print(f"   • Gjithsej të shkarkuara: {downloaded_count} aktgjykime të reja")
    print(f"   • Të ruajtura te: {DEST_DIR}")
    print("="*65 + "\n")

if __name__ == "__main__":
    # Test me 2 faqe dhe deri në 10 vendime të reja
    pages_to_scan = 2
    downloads_limit = 10

    if len(sys.argv) > 1:
        try:
            pages_to_scan = int(sys.argv[1])
        except ValueError:
            pass

    harvest_supreme_decisions(max_pages=pages_to_scan, max_downloads=downloads_limit)