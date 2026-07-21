"""Bibliographic Cache and rate limiting — Derived State plumbing.

Cache entries live under ``<state_dir>/bibliographic-cache/<provider>/`` as
one JSON file per request URL (sha256 key): ``{url, fetched_at, payload}``.
Dated observations, deletable, rebuilt by the next live refresh. The rate
limiter takes injectable clock/sleep so tests never wait on wall time.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIRNAME = "bibliographic-cache"


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BibliographicCache:
    def __init__(self, state_dir, now=_now_iso):
        self._base = Path(state_dir) / CACHE_DIRNAME
        self._now = now

    def _path(self, provider, url):
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._base / provider / (key + ".json")

    def get(self, provider, url):
        path = self._path(provider, url)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, provider, url, payload):
        fetched_at = self._now()
        path = self._path(provider, url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"url": url, "fetched_at": fetched_at, "payload": payload},
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return fetched_at


class RateLimiter:
    """At least ``min_interval`` seconds between live calls per provider."""

    def __init__(self, min_interval=1.0, clock=time.monotonic, sleep=time.sleep):
        self._interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last = {}

    def wait(self, provider):
        now = self._clock()
        last = self._last.get(provider)
        if last is not None:
            remaining = self._interval - (now - last)
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last[provider] = now
