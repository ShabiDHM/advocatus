# FILE: backend/scripts/harvest_supreme_decisions.py
# PHOENIX PROTOCOL - SUPREME COURT HARVESTER V2.0 (POST PAGINATION)
# V2.0: RISHKRIM I MADH - Paginimi kerkon POST (jo GET URL).
#       Zbuluar nga _probe_form.py: forma 'setPaged' POST-on 'paged=N' tek
#       '?r=M&courtId=12&judgeStatus=1&ordBy=v.publicationDtTm&ordDir=DESC'.
#       DB ka 21,636 aktgjykime total (~1,080 faqe).
#       Argumentet CLI:
#         python scripts/harvest_supreme_decisions.py                  -> 25 faqe (500 PDF)
#         python scripts/harvest_supreme_decisions.py 50 1000          -> 50 faqe, 1000 PDF
#         python scripts/harvest_supreme_decisions.py 5                -> 5 faqe (100 PDF)
# V1.2: Default pages_to_scan=5, downloads_limit=50.
# V1.1: FIX URL-t relative me urljoin().
# V1.0: Versioni fillestar.

import os
import sys
import re
import time
import json
import logging
import requests
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

DEST_DIR = ROOT_DIR / "data" / "case_law"
if not DEST_DIR.exists():
    DEST_DIR = BACKEND_DIR / "data" / "case_law"
DEST_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = BACKEND_DIR / "_harvest_progress.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("supreme_harvester")

# URL base + POST target
BASE_URL = "https://supreme.gjyqesori-rks.org/publikimet/aktgjykimet/"
BASE_DOMAIN = "https://supreme.gjyqesori-rks.org"
POST_URL = f"{BASE_URL}?r=M&courtId=12&judgeStatus=1&ordBy=v.publicationDtTm&ordDir=DESC"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "sq,en-US;q=0.9,en;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
}


def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', '_', name)
    clean = clean.replace(" ", "_").replace("/", "_")
    return clean.strip("_")


def absolute_url(base: str, url: str) -> str:
    """V1.1: Konverton URL relative ne absolute."""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    normalized = url.lstrip()
    normalized = re.sub(r'^/+\.\./+', '/', normalized)
    normalized = re.sub(r'^/+', '/', normalized)
    if normalized.startswith("/"):
        return urljoin(BASE_DOMAIN, normalized)
    return urljoin(base, normalized)


def load_progress() -> dict:
    """Lexon progresin e ruajtur."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_page": 0, "downloaded": 0}
    return {"last_page": 0, "downloaded": 0}


def save_progress(last_page: int, downloaded: int):
    """Ruan progresin ne disk (per resume)."""
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_page": last_page,
                "downloaded": downloaded,
                "timestamp": time.time(),
            }, f)
    except Exception as e:
        logger.warning(f"⚠️ Nuk u ruajt progresi: {e}")


def fetch_page(session: requests.Session, paged: int) -> str:
    """V2.0: POST per te marre faqen e N-te."""
    try:
        res = session.post(
            POST_URL,
            headers=HEADERS,
            data={"paged": str(paged)},
            timeout=30,
        )
        if res.status_code == 200:
            return res.text
        else:
            logger.warning(f"⚠️ paged={paged}: Status {res.status_code}")
            return ""
    except Exception as e:
        logger.error(f"❌ paged={paged}: {e}")
        return ""


def download_pdf(url: str, save_path: Path) -> bool:
    """
    Kthen:
      True  = shkarkim i re me sukses
      False = ekzistonte tashme ose deshtoi
    """
    try:
        if save_path.exists() and save_path.stat().st_size > 1000:
            return False  # ekziston, nuk numerohet si i re

        logger.info(f"📥 Duke shkarkuar: {save_path.name}...")
        response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(response.content)
            logger.info(f"   ✅ U ruajt: {save_path.name} ({len(response.content) // 1024} KB)")
            return True
        else:
            logger.warning(f"   ❌ Dështoi: {save_path.name} (Status: {response.status_code})")
            return False
    except Exception as e:
        logger.error(f"   ❌ Gabim: {save_path.name}: {e}")
        return False


def process_page(session: requests.Session, paged: int, max_downloads: int, current_total: int) -> tuple:
    """
    Perpunon nje faqe.
    Kthen: (numri_i_re, numri_total)
    """
    logger.info(f"🔍 Duke skanuar faqen {paged}...")
    html = fetch_page(session, paged)

    if not html:
        logger.warning(f"   ⚠️ Faqja {paged} bosh")
        return 0, current_total

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    rows_td = [row for row in rows if len(row.find_all("td")) >= 5]

    if not rows_td:
        logger.info(f"   ℹ️ Faqja {paged}: 0 rreshta")
        return 0, current_total

    new_downloads = 0
    for row in rows_td:
        if current_total >= max_downloads:
            break

        cols = row.find_all("td")
        lloji = cols[0].get_text(strip=True) if len(cols) > 0 else "Vendim"
        numri_rastit = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        gjyqtari = cols[4].get_text(strip=True) if len(cols) > 4 else ""

        # Gjej PDF
        links = row.find_all("a")
        sq_link = None
        for a in links:
            text_label = a.get_text(strip=True).upper()
            href = a.get("href", "")
            if href and ("SQ" in text_label or ".pdf" in href.lower()):
                sq_link = absolute_url(BASE_URL, href)
                break

        if sq_link and numri_rastit:
            clean_case = sanitize_filename(f"{lloji}_{numri_rastit}")
            clean_judge = sanitize_filename(gjyqtari.split("-")[0].strip()) if gjyqtari else "Gjykata_Supreme"
            filename = f"{clean_case}_{clean_judge}.pdf"
            save_path = DEST_DIR / filename

            success = download_pdf(sq_link, save_path)
            if success:
                new_downloads += 1
                current_total += 1

            time.sleep(0.3)  # Respekt ndaj serverit

    logger.info(f"   ✅ Faqja {paged}: {new_downloads} te reja (total: {current_total})")
    return new_downloads, current_total


def harvest(max_pages: int = 25, max_downloads: int = 500, resume: bool = True):
    print("\n" + "="*70)
    print("🏛️ PHOENIX HARVESTER V2.0 - GJYKATA SUPREME E KOSOVËS")
    print(f"📂 Destinacioni: {DEST_DIR}")
    print(f"📄 Faqe: {max_pages}  |  Limit PDF: {max_downloads}  |  Resume: {resume}")
    print("="*70 + "\n")

    # Progres
    progress = load_progress() if resume else {"last_page": 0, "downloaded": 0}
    start_page = progress.get("last_page", 0) + 1 if resume else 1
    total_downloaded = progress.get("downloaded", 0)

    if start_page > 1:
        logger.info(f"▶️ Resume nga faqja {start_page} (total tashme: {total_downloaded})")

    session = requests.Session()
    end_page = start_page + max_pages - 1

    for paged in range(start_page, end_page + 1):
        if total_downloaded >= max_downloads:
            print(f"\n🛑 U arrit limiti prej {max_downloads} PDF.")
            break

        new, total_downloaded = process_page(session, paged, max_downloads, total_downloaded)
        save_progress(paged, total_downloaded)

        time.sleep(1.0)  # Pauze mes faqeve

    print("\n" + "="*70)
    print(f"🏁 HARVESTING PËRFUNDOI")
    print(f"   • Total PDF ne dosje: {total_downloaded}")
    print(f"   • Destinacioni: {DEST_DIR}")
    if PROGRESS_FILE.exists():
        print(f"   • Progresi u ruajt: {PROGRESS_FILE}")
        print(f"     (fshij per te rifilluar nga e para: Remove-Item {PROGRESS_FILE.name})")
    print("="*70 + "\n")


if __name__ == "__main__":
    pages_to_scan = 25       # 25 faqe = 500 PDF
    downloads_limit = 500

    if len(sys.argv) > 1:
        try:
            pages_to_scan = int(sys.argv[1])
        except ValueError:
            pass

    if len(sys.argv) > 2:
        try:
            downloads_limit = int(sys.argv[2])
        except ValueError:
            pass

    harvest(max_pages=pages_to_scan, max_downloads=downloads_limit, resume=True)