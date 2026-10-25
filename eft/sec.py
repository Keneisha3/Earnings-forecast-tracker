"""SEC EDGAR access: company facts (XBRL) and the ticker list.

SEC asks every client to send a User-Agent with a name and email and to stay under 10 requests a
second. Set it with --user-agent or SEC_USER_AGENT ("Your Name you@example.com"); it is never
written to disk. offline=DIR reads saved answers instead (the tests use it); cache=DIR saves each
answer so a rebuild does not refetch.
"""

import gzip
import json
import os
import time
import urllib.error
import urllib.request

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK%s.json"


class SecError(Exception):
    pass


def cik10(cik):
    return str(int(cik)).zfill(10)


class Fetcher:
    def __init__(self, user_agent=None, offline=None, cache=None, pause=0.15, retries=3):
        self.ua = (user_agent or os.environ.get("SEC_USER_AGENT") or "").strip()
        self.offline, self.cache, self.pause, self.retries = offline, cache, pause, retries
        self._last = 0.0

    def _name(self, url):
        return url.rstrip("/").rsplit("/", 1)[-1]

    def get_json(self, url):
        name = self._name(url)
        for folder in (self.offline, self.cache):
            path = os.path.join(folder, name) if folder else None
            if path and os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    return json.load(fh)
        if self.offline:
            raise SecError("offline: no %s in %s" % (name, self.offline))
        if "@" not in self.ua:
            raise SecError("SEC needs a User-Agent with your name and email: set SEC_USER_AGENT or --user-agent")
        text = self._fetch(url)
        if self.cache:
            os.makedirs(self.cache, exist_ok=True)
            with open(os.path.join(self.cache, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        return json.loads(text)

    def _fetch(self, url):
        last = None
        for attempt in range(self.retries):
            wait = self.pause - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": self.ua, "Accept-Encoding": "gzip"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        data = gzip.decompress(data)
                    return data.decode("utf-8")
            except urllib.error.HTTPError as e:
                last = SecError("SEC answered HTTP %d for %s" % (e.code, url))
                if e.code not in (429, 500, 502, 503, 504):
                    raise last
            except (urllib.error.URLError, OSError) as e:
                last = SecError("could not reach %s: %s" % (url, getattr(e, "reason", e)))
            time.sleep(2 * (attempt + 1))
        raise last

    def tickers(self):
        """{TICKER: cik10} from the SEC's current list (BRK.B is written BRK-B)."""
        doc = self.get_json(TICKERS_URL)
        rows = doc.values() if isinstance(doc, dict) else doc
        return {r["ticker"].upper().replace(".", "-"): cik10(r["cik_str"]) for r in rows}

    def company_facts(self, cik):
        return self.get_json(FACTS_URL % cik10(cik))
