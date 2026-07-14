"""Codeforces API client: transport, disk cache, rate limiting, envelope handling.

Every design choice here traces to a measured characteristic of the upstream API;
see SPEC.md "Measured characteristics" for the numbers.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx

API_ROOT = "https://codeforces.com/api"

# Codeforces documents roughly one request per two seconds.
_MIN_INTERVAL_S = 2.0

# TTLs differ by how fast the underlying data actually moves (SPEC.md D2).
CACHE_TTL_S: dict[str, float] = {
    "problemset.problems": 6 * 3600,  # changes on contest cadence; 2.25 MB, worth keeping
    "contest.list": 3600,
    "user.info": 3600,
    "user.rating": 900,
    "user.status": 300,  # changes while you practise
}
_DEFAULT_TTL_S = 600.0


class CodeforcesError(RuntimeError):
    """An upstream failure, carrying the API's own explanation.

    Codeforces returns {"status": "FAILED", "comment": "..."} where the comment is
    genuinely actionable ("User with handle xyz not found"). Surfacing it verbatim
    beats any message we could invent.
    """

    def __init__(self, comment: str, method: str) -> None:
        super().__init__(f"Codeforces API call '{method}' failed: {comment}")
        self.comment = comment
        self.method = method


class _RateLimiter:
    """Serialises calls so consecutive requests are at least _MIN_INTERVAL_S apart."""

    def __init__(self, min_interval_s: float = _MIN_INTERVAL_S) -> None:
        self._min_interval = min_interval_s
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


class _DiskCache:
    """Newline-free JSON blobs on disk, keyed by method+params, with per-method TTL.

    Always UTF-8: Codeforces returns UTF-8 problem titles and Python on Windows
    defaults to cp1252, which raises UnicodeDecodeError on real data (SPEC.md D3).
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.home() / ".cache" / "codeforces-mcp"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, method: str, params: dict[str, Any]) -> Path:
        key = json.dumps({"m": method, "p": params}, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
        return self.root / f"{method}.{digest}.json"

    def get(self, method: str, params: dict[str, Any]) -> Any | None:
        path = self._path(method, params)
        if not path.exists():
            return None
        ttl = CACHE_TTL_S.get(method, _DEFAULT_TTL_S)
        if time.time() - path.stat().st_mtime > ttl:
            return None
        try:
            with path.open(encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None  # a corrupt cache entry is a cache miss, never a crash

    def put(self, method: str, params: dict[str, Any], result: Any) -> None:
        path = self._path(method, params)
        tmp = path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(result, fh)
            tmp.replace(path)  # atomic, so a killed process cannot leave a half-file
        except OSError:
            pass  # caching is an optimisation; never fail a call because it did not work


class CodeforcesClient:
    """Async client returning the unwrapped `result` payload."""

    def __init__(
        self,
        cache: _DiskCache | None = None,
        limiter: _RateLimiter | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._cache = cache if cache is not None else _DiskCache()
        self._limiter = limiter or _RateLimiter()
        self._timeout = timeout_s

    async def call(self, method: str, **params: Any) -> Any:
        """Call one API method and return its `result`, using the cache when warm.

        Raises CodeforcesError when the API reports FAILED.
        """
        clean = {k: v for k, v in params.items() if v is not None}

        cached = self._cache.get(method, clean)
        if cached is not None:
            return cached

        await self._limiter.acquire()
        url = f"{API_ROOT}/{method}"
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            response = await http.get(url, params=clean)

        # A FAILED envelope arrives with HTTP 400, and its body is more useful than
        # the status code, so parse before raising for status.
        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise CodeforcesError("upstream returned non-JSON", method) from None

        if payload.get("status") != "OK":
            raise CodeforcesError(payload.get("comment", "unknown error"), method)

        result = payload["result"]
        self._cache.put(method, clean, result)
        return result


_client: CodeforcesClient | None = None


def get_client() -> CodeforcesClient:
    """Process-wide client, so cache and rate limiter are shared across tools."""
    global _client
    if _client is None:
        _client = CodeforcesClient()
    return _client


def set_client(client: CodeforcesClient) -> None:
    """Swap the client. Used by tests to inject a fixture-backed fake."""
    global _client
    _client = client
