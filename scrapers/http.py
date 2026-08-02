import logging
import random
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-ZA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch(url: str, retries: int = 3) -> Optional[str]:
    session = requests.Session()
    for attempt in range(retries):
        try:
            response = session.get(url, headers=HEADERS, timeout=25)
            if response.status_code == 200:
                return response.text
            logger.warning("HTTP %s for %s", response.status_code, url)
            if response.status_code in (403, 429):
                time.sleep(20 * (attempt + 1) + random.uniform(0, 5))
        except requests.RequestException as exc:
            logger.warning("Request error for %s: %s", url, exc)
            time.sleep(5 * (attempt + 1))
    return None
