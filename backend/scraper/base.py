# 爬虫基类

import time
import requests
from backend.config import SCRAPER_USER_AGENT, SCRAPER_TIMEOUT, SCRAPER_RETRY, SCRAPER_DELAY


class BaseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SCRAPER_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < SCRAPER_DELAY:
            time.sleep(SCRAPER_DELAY - elapsed)
        self.last_request = time.time()

    def fetch(self, url, params=None, encoding="utf-8"):
        self._rate_limit()
        for attempt in range(SCRAPER_RETRY):
            try:
                resp = self.session.get(url, params=params,
                                        timeout=SCRAPER_TIMEOUT)
                resp.encoding = encoding
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt == SCRAPER_RETRY - 1:
                    raise
                time.sleep(2 ** attempt)
        return None
