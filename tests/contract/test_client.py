"""Contract tests for the client: cache behaviour, rate limiting, error envelope."""

from __future__ import annotations

import time

from codeforces_mcp.client import CodeforcesError, _DiskCache, _RateLimiter


def test_cache_roundtrip(tmp_path):
    cache = _DiskCache(root=tmp_path)
    cache.put("user.info", {"handle": "x"}, {"rating": 1200})
    assert cache.get("user.info", {"handle": "x"}) == {"rating": 1200}


def test_cache_is_keyed_on_params(tmp_path):
    """Two handles must not share one cache entry."""
    cache = _DiskCache(root=tmp_path)
    cache.put("user.info", {"handle": "a"}, {"rating": 1})
    assert cache.get("user.info", {"handle": "b"}) is None


def test_cache_expires(tmp_path, monkeypatch):
    import codeforces_mcp.client as mod

    monkeypatch.setitem(mod.CACHE_TTL_S, "user.status", 0.0)
    cache = _DiskCache(root=tmp_path)
    cache.put("user.status", {}, [1, 2, 3])
    time.sleep(0.01)
    assert cache.get("user.status", {}) is None


def test_corrupt_cache_entry_is_a_miss_not_a_crash(tmp_path):
    """A truncated file must degrade to a refetch, never take the server down."""
    cache = _DiskCache(root=tmp_path)
    cache.put("user.info", {}, {"ok": True})
    path = cache._path("user.info", {})
    path.write_text("{not json", encoding="utf-8")
    assert cache.get("user.info", {}) is None


def test_cache_write_is_atomic(tmp_path):
    """No .tmp file should survive a completed write."""
    cache = _DiskCache(root=tmp_path)
    cache.put("contest.list", {}, [{"id": 1}])
    assert not list(tmp_path.glob("*.tmp"))


def test_cache_handles_non_ascii(tmp_path):
    """Codeforces problem titles are UTF-8; Windows defaults to cp1252 (SPEC.md D3)."""
    cache = _DiskCache(root=tmp_path)
    payload = [{"name": "Zoltán and the Café — Ürümqi 日本"}]
    cache.put("problemset.problems", {}, payload)
    assert cache.get("problemset.problems", {}) == payload


async def test_rate_limiter_spaces_calls():
    limiter = _RateLimiter(min_interval_s=0.05)
    start = time.monotonic()
    for _ in range(3):
        await limiter.acquire()
    assert time.monotonic() - start >= 0.10  # first is free, next two wait


def test_error_carries_comment_and_method():
    exc = CodeforcesError("handle: User with handle zzz not found", "user.info")
    assert exc.comment.startswith("handle:")
    assert exc.method == "user.info"
    assert "user.info" in str(exc)


def test_failed_envelope_fixture_shape():
    """Guards the assumption the error path is built on."""
    from .. import conftest

    payload = conftest.load("user_info_failed.json")
    assert payload["status"] == "FAILED"
    assert "comment" in payload
