"""Shared fixtures: a fake client backed by recorded API responses.

Contract tests must not touch the network, so they never see CodeforcesClient. The
fake honours the same call signature and the same FAILED-envelope behaviour, which is
what makes the tests meaningful rather than merely green.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from codeforces_mcp.client import CodeforcesError

FIXTURES = Path(__file__).parent / "fixtures"
HANDLE = "3.141f"


def load(name: str) -> Any:
    with (FIXTURES / name).open(encoding="utf-8") as fh:
        return json.load(fh)


class FixtureClient:
    """Stands in for CodeforcesClient, serving recorded payloads."""

    def __init__(self, known_handles: set[str] | None = None) -> None:
        self.known = known_handles if known_handles is not None else {HANDLE}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call(self, method: str, **params: Any) -> Any:
        self.calls.append((method, params))

        handle = params.get("handle") or params.get("handles")
        if handle and handle not in self.known:
            raise CodeforcesError(
                f"handle: User with handle {handle} not found", method
            )

        if method == "problemset.problems":
            return load("problemset_problems.json")["result"]
        if method == "user.status":
            return load("user_status.json")["result"]
        if method == "user.info":
            return load("user_info.json")["result"]
        if method == "user.rating":
            return load("user_rating.json")["result"]
        if method == "contest.list":
            return load("contest_list.json")["result"]
        raise AssertionError(f"no fixture for method {method!r}")


@pytest.fixture
def client() -> FixtureClient:
    return FixtureClient()


@pytest.fixture
def handle() -> str:
    return HANDLE


@pytest.fixture
def solved_keys_of_handle() -> set[tuple[int | None, str]]:
    """Ground truth for the exclude_solved_by assertions."""
    return {
        (s["problem"].get("contestId"), s["problem"].get("index"))
        for s in load("user_status.json")["result"]
        if s.get("verdict") == "OK"
    }
