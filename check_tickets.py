import os
import requests
from bs4 import BeautifulSoup

# ── Keywords ─────────────────────────────────────────────────────────────────

DISTRICT_KEYWORDS_LIVE     = ["sale is live", "pre-sale is live", "book now", "buy tickets", "book tickets"]
DISTRICT_KEYWORDS_WAITING  = ["tickets available in", "coming soon"]
DISTRICT_KEYWORDS_NOT_OPEN = ["be the first to know when sale begins"]

BMS_KEYWORDS_LIVE          = ["book now", "login to book"]
BMS_KEYWORDS_WAITING       = ["coming soon"]
BMS_KEYWORDS_NOT_OPEN      = ["coming soon"]

RCB_KEYWORDS_LIVE          = ["buy tickets", "book now", "add to cart"]
RCB_KEYWORDS_WAITING       = ["coming soon", "notify me", "register interest"]

URLS_FILE = "urls.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_bookmyshow_url(url):
    return "bookmyshow.com" in url

def is_rcb_url(url):
    return "royalchallengers.com" in url.split("|")[0]

def get_match_title(page_text):
    for line in page_text.splitlines():
        line = line.strip()
        if line:
            return line[:100]
    return "Unknown Match"

def load_urls():
    if not os.path.exists(URLS_FILE):
        print(f"{URLS_FILE} not found — nothing to check.")
        return []
    with open(URLS_FILE) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    print(f"Loaded {len(urls)} URL(s) to check.")
    return urls


# ── RCB check ─────────────────────────────────────────────────────────────────

def check_rcb_match(raw_url):
    parts     = raw_url.split("|")
    page_url  = parts[0].strip()
    match_label = parts[1].strip() if len(parts) == 3 else None
    match_date  = parts[2].strip() if len(parts) == 3 else ""

    if not match_label:
        print("RCB URL missing match label — skipping.")
        return "error"

    response = requests.get(page_url, headers=HEADERS, timeout=15)
    if response.status_code == 403:
        print(f"403 Forbidden — RCB site is blocking automated requests.")
        return "blocked"

    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_lower = soup.get_text(separator="\n").lower()

    idx = page_lower.find(match_label.lower())
    if idx == -1:
        away = match_label.split("vs")[-1].strip().lower()
        idx = page_lower.find(away)

    if idx == -1:
        print(f"  [{match_label}] Not listed on RCB page yet.")
        return "not_open"

    surrounding = page_lower[max(0, idx - 100): idx + 400]
    is_live     = any(kw in surrounding for kw in RCB_KEYWORDS_LIVE)
    is_waiting  = any(kw in surrounding for kw in RCB_KEYWORDS_WAITING)

    if is_live and not is_waiting:
        print(f"  [{match_label}] LIVE — tickets available now! {page_url}")
        return "live"
    elif is_waiting:
        print(f"  [{match_label}] Coming soon. {page_url}")
        return "soon"
    else:
        print(f"  [{match_label}] Not open yet.")
        return "not_open"


# ── Generic check ─────────────────────────────────────────────────────────────

def check_url(url):
    if is_rcb_url(url):
        return check_rcb_match(url)

    response = requests.get(url, headers=HEADERS, timeout=15)
    if response.status_code == 403:
        print(f"  403 Forbidden — {url}")
        return "blocked"

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text  = soup.get_text()
    page_lower = page_text.lower()
    title      = get_match_title(page_text)

    if is_bookmyshow_url(url):
        keywords_live    = BMS_KEYWORDS_LIVE
        keywords_waiting = BMS_KEYWORDS_WAITING
        keywords_closed  = BMS_KEYWORDS_NOT_OPEN
        platform = "BookMyShow"
    else:
        keywords_live    = DISTRICT_KEYWORDS_LIVE
        keywords_waiting = DISTRICT_KEYWORDS_WAITING
        keywords_closed  = DISTRICT_KEYWORDS_NOT_OPEN
        platform = "District"

    is_live    = any(kw in page_lower for kw in keywords_live)
    is_waiting = any(kw in page_lower for kw in keywords_waiting)
    is_closed  = any(kw in page_lower for kw in keywords_closed)

    print(f"  [{platform}] {title[:60]}")
    print(f"    live={is_live} | waiting={is_waiting} | closed={is_closed}")

    if is_live and not is_waiting and not is_closed:
        print(f"    STATUS: LIVE — {url}")
        return "live"
    elif is_waiting and not is_closed:
        print(f"    STATUS: Coming soon — {url}")
        return "soon"
    else:
        print(f"    STATUS: Not open yet.")
        return "not_open"


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    urls = load_urls()
    if not urls:
        print("No URLs to check. Add match URLs to urls.txt.")
        raise SystemExit(0)

    results = {"live": [], "soon": [], "not_open": [], "blocked": [], "error": []}

    for url in urls:
        print(f"\nChecking: {url}")
        try:
            status = check_url(url)
            results[status].append(url)
        except Exception as e:
            print(f"  Error: {e}")
            results["error"].append(url)

    print("\n── Summary ─────────────────────────────────────")
    print(f"  Live now : {len(results['live'])}")
    print(f"  Coming soon : {len(results['soon'])}")
    print(f"  Not open : {len(results['not_open'])}")
    print(f"  Blocked  : {len(results['blocked'])}")
    print(f"  Errors   : {len(results['error'])}")

    if results["live"]:
        print("\nLIVE MATCHES:")
        for u in results["live"]:
            print(f"  {u}")
