"""Polite HTTP: max 1 request/second per host, timeouts on every call, project User-Agent."""
from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import httpx

from crux_lab.config import settings

_last: dict[str, float] = {}
_locks: dict[str, threading.Lock] = {}
_glock = threading.Lock()
MIN_INTERVAL = 1.05


def _host_lock(host: str) -> threading.Lock:
    with _glock:
        return _locks.setdefault(host, threading.Lock())


def get(url: str, *, params: dict | None = None, timeout: float = 60, retries: int = 3,
        accept: str | None = None) -> httpx.Response:
    host = urlparse(url).netloc
    headers = {"User-Agent": settings.user_agent}
    if accept:
        headers["Accept"] = accept
    last_exc: Exception | None = None
    for attempt in range(retries):
        with _host_lock(host):
            wait = _last.get(host, 0) + MIN_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                r = httpx.get(url, params=params, headers=headers, timeout=timeout,
                              follow_redirects=True)
            except httpx.HTTPError as e:
                last_exc = e
                r = None
            finally:
                _last[host] = time.monotonic()
        if r is not None and r.status_code < 400:
            return r
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
        time.sleep(2 * (attempt + 1) + (5 if r is not None and r.status_code == 429 else 0))
    if last_exc:
        raise last_exc
    r.raise_for_status()  # type: ignore[union-attr]
    return r  # type: ignore[return-value]
