"""
ingestion/image_scraper.py
-----------------------------
Skeleton scraper for retailer/brand product packaging images.

IMPORTANT (see brief Section 6, Constraints):
  - Many data sources will not offer API access; this module scrapes public
    HTML pages directly and must respect each site's robots.txt and terms
    of service. It includes basic rate limiting and a User-Agent string,
    but a production rollout must add per-domain legal/compliance review
    before enabling this against any real retailer site.
  - This is a Phase 1 utility only for packaging image discovery -- it does
    NOT scrape or analyze marketing copy text, consistent with Strategic
    Decision #2 (images prioritized over website copy).

Usage is opt-in and off by default; main.py's demo does not call this
against live sites, it uses locally supplied sample data instead.
"""

import os
import time
import sys
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models import ProductImage, new_id

REQUEST_DELAY_SECONDS = 2.0
USER_AGENT = "MarketTrendAssistant/0.1 (research prototype; contact: data-team@example.com)"


def _get_requests_session():
    import requests
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def check_robots_allowed(url: str) -> bool:
    """Best-effort robots.txt check before scraping any page."""
    try:
        from urllib.robotparser import RobotFileParser
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        # If robots.txt can't be read, default to NOT scraping (safe default).
        return False


def discover_product_image_urls(page_url: str, img_selector_hint: str = "img"):
    """Fetches a product page and returns candidate image URLs.
    Requires bs4/requests to be installed. Respects robots.txt."""
    if not check_robots_allowed(page_url):
        raise PermissionError(f"robots.txt disallows fetching {page_url}")

    from bs4 import BeautifulSoup

    session = _get_requests_session()
    resp = session.get(page_url, timeout=15)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)

    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for img in soup.select(img_selector_hint):
        src = img.get("src") or img.get("data-src")
        if src:
            urls.append(src)
    return urls


def download_image(url: str, product_id: str) -> ProductImage:
    """Downloads an image to the local cache and returns a ProductImage
    record (OCR text populated separately by the Product Claims Agent)."""
    session = _get_requests_session()
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)

    filename = os.path.join(config.IMAGE_CACHE_DIR, f"{new_id('img')}.jpg")
    with open(filename, "wb") as f:
        f.write(resp.content)

    return ProductImage(
        image_id=new_id("img"),
        product_id=product_id,
        source_url=url,
        local_path=filename,
    )
