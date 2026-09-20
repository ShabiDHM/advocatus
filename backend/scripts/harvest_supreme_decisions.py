# FILE: backend/scripts/harvest_supreme_decisions.py
# PHOENIX PROTOCOL - SUPREME COURT HARVESTER V2.1 (RETRY 429)
# V2.1: Retry per HTTP 429 (rate limiting):
#       - Backoff exponential: 5s, 10s, 20s
#       - Max 3 tentativa per PDF
#       - Rrit pauza: 1.5s mes PDF-ve, 3s mes faqeve
#       - Log ne file per monitoring (per harvest te gjate)
#       - Skip total per PDF ekzistues
# V2.0: POST pagination (i zbuluar nga _probe_form.py).
# V1.1: FIX URL relative me urljoin().
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
from datetime import datetime
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

DEST_DIR = ROOT_DIR / "data" / "case_law"
if not DEST_DIR.exists():
    DEST_DIR = BACKEND_DIR / "data" / "case_law"
DEST_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = BACKEND_DIR / "_harvest_progress.json"

# V2.1: Log ne file
LOG_FILE = BACKEND_DIR / f"_harvest_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
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

# V2.1: Timings
PAUSE_BETWEEN_PDFS = 1.5       # sekonda
PAUSE_BETWEEN_PAGES = 3.0      # sekonda
RETRY_BACKOFFS = [5, 10, 20]   # sekonda per 429


def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', '_', name)
    clean = clean.replace(" ", "_").replace("/", "_")
    return clean.strip("_")


def absolute_url(base: str, url: str) -> str:
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
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_page": 0, "downloaded": 0}


def save_progress(last_page: int, downloaded: int):
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
    V2.1: Shkarkon PDF me retry per 429.
    Kthen:
      True  = shkarkim i re me sukses
      False = ekzistonte, deshtoi, ose u hoq
    """
    if save_path.exists() and save_path.stat().st_size > 1000:
        return False  # ekziston, nuk numerohet

    for attempt in range(1, 4):  # 3 tentativa
        try:
            response = requests.get(url, headers=HEADERS, timeout=30, stream=True)

            if response.status_code == 200 and len(response.content) > 1000:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                logger.info(
                    f"   ✅ U ruajt: {save_path.name} ({len(response.content) // 1024} KB)"
                )
                return True

            elif response.status_code == 429:
                backoff = RETRY_BACKOFFS[min(attempt - 1, len(RETRY_BACKOFFS) - 1)]
                logger.warning(
                    f"   ⚠️ 429 Rate limit për {save_path.name}, "
                    f"prit {backoff}s (tentativa {attempt}/3)"
                )
                time.sleep(backoff)
                continue

            elif response.status_code == 404:
                logger.warning(f"   ❌ 404 për {save_path.name} - skip")
                return False

            else:
                logger.warning(
                    f"   ❌ Status {response.status_code} për {save_path.name}"
                )
                if attempt < 3:
                    time.sleep(3)
                    continue
                return False

        except requests.exceptions.Timeout:
            logger.warning(f"   ⏱️ Timeout për {save_path.name} (tentativa {attempt}/3)")
            if attempt < 3:
                time.sleep(3)
                continue
            return False

        except Exception as e:
            logger.error(f"   ❌ Gabim për {save_path.name}: {e}")
            if attempt < 3:
                time.sleep(3)
                continue
            return False

    logger.error(f"   ❌ Dështoi pas 3 tentativave: {save_path.name}")
    return False


def process_page(session, paged: int, max_downloads: int, current_total: int) -> tuple:
    """Perpunon nje faqe. Kthen (new_downloads, total)."""
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
    skipped = 0
    failed = 0

    for row in rows_td:
        if current_total >= max_downloads:
            break

        cols = row.find_all("td")
        lloji = cols[0].get_text(strip=True) if len(cols) > 0 else "Vendim"
        numri_rastit = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        gjyqtari = cols[4].get_text(strip=True) if len(cols) > 4 else ""

        links = row.find_all("a")
        sq_link = None
        for a in links:
            text_label = a.get_text(strip=True).upper()
            href = a.get("href", "")
            if href and ("SQ" in text_label or ".pdf" in href.lower()):
                sq_link = absolute_url(BASE_URL, href)
                break

        if not (sq_link and numri_rastit):
            continue

        clean_case = sanitize_filename(f"{lloji}_{numri_rastit}")
        clean_judge = (
            sanitize_filename(gjyqtari.split("-")[0].strip())
            if gjyqtari else "Gjykata_Supreme"
        )
        filename = f"{clean_case}_{clean_judge}.pdf"
        save_path = DEST_DIR / filename

        if save_path.exists() and save_path.stat().st_size > 1000:
            skipped += 1
            continue

        success = download_pdf(sq_link, save_path)
        if success:
            new_downloads += 1
            current_total += 1
        else:
            failed += 1

        time.sleep(PAUSE_BETWEEN_PDFS)

    logger.info(
        f"   ✅ Faqja {paged}: +{new_downloads} te reja, "
        f"{skipped} skipped, {failed} deshtuan (total: {current_total})"
    )
    return new_downloads, current_total


def harvest(max_pages: int = 200, max_downloads: int = 5000, resume: bool = True):
    print("\n" + "="*70)
    print("🏛️ PHOENIX HARVESTER V2.1 - GJYKATA SUPREME E KOSOVËS")
    print(f"📂 Destinacioni: {DEST_DIR}")
    print(f"📄 Faqe: {max_pages}  |  Limit PDF: {max_downloads}  |  Resume: {resume}")
    print(f"📝 Log: {LOG_FILE.name}")
    print("="*70 + "\n")

    progress = load_progress() if resume else {"last_page": 0, "downloaded": 0}
    start_page = progress.get("last_page", 0) + 1 if resume else 1
    total_downloaded = progress.get("downloaded", 0)

    if start_page > 1:
        logger.info(f"▶️  Resume nga faqja {start_page} (total tashme: {total_downloaded})")

    session = requests.Session()
    end_page = start_page + max_pages - 1

    for paged in range(start_page, end_page + 1):
        if total_downloaded >= max_downloads:
            print(f"\n🛑 U arrit limiti prej {max_downloads} PDF.")
            break

        new, total_downloaded = process_page(
            session, paged, max_downloads, total_downloaded
        )
        save_progress(paged, total_downloaded)

        time.sleep(PAUSE_BETWEEN_PAGES)

    print("\n" + "="*70)
    print(f"🏁 HARVESTING PËRFUNDOI")
    print(f"   • Total PDF ne dosje: {total_downloaded}")
    print(f"   • Destinacioni: {DEST_DIR}")
    print(f"   • Log: {LOG_FILE}")
    if PROGRESS_FILE.exists():
        print(f"   • Progresi: {PROGRESS_FILE}")
        print(f"     Fshije per rifillim: Remove-Item {PROGRESS_FILE.name}")
    print("="*70 + "\n")


if __name__ == "__main__":
    pages_to_scan = 200       # default per sesion te gjate
    downloads_limit = 5000

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