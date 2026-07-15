"""Live tests: does the real Codeforces API still honour the contract we built on?

Deselected by default (`addopts = -m 'not live'`) and run nightly in CI. They assert
the *shape* of upstream responses, not our logic -- that is what the contract tests
are for. When one of these fails, the API changed and the fixtures are stale.

    pytest -m live -q
"""

from __future__ import annotations

import pytest

from codeforces_mcp.client import CodeforcesClient, CodeforcesError, _DiskCache
from codeforces_mcp.schemas import KNOWN_TAGS

pytestmark = pytest.mark.live

HANDLE = "3.141f"


@pytest.fixture
def live_client(tmp_path):
    """A client with a throwaway cache, so a live run never reads stale data."""
    return CodeforcesClient(cache=_DiskCache(root=tmp_path))


async def test_envelope_is_still_status_result(live_client):
    result = await live_client.call("user.info", handles=HANDLE)
    assert isinstance(result, list) and result


async def test_failed_envelope_still_carries_comment(live_client):
    with pytest.raises(CodeforcesError) as excinfo:
        await live_client.call("user.info", handles="not_a_real_handle_zzzz_9999")
    assert excinfo.value.comment


async def test_user_status_still_embeds_problem_tags(live_client):
    """The assumption the whole tag_performance design rests on (SPEC.md D1).

    If Codeforces ever stops inlining tags here, that tool needs a join against
    problemset.problems and its cost model changes completely.
    """
    submissions = await live_client.call("user.status", handle=HANDLE)
    assert submissions
    with_problem = [s for s in submissions if "problem" in s]
    assert with_problem
    assert any("tags" in s["problem"] for s in with_problem)


async def test_problem_fields_unchanged(live_client):
    payload = await live_client.call("problemset.problems")
    problems = payload["problems"]
    assert len(problems) > 5000
    sample = problems[0]
    for field in ("contestId", "index", "name", "tags"):
        assert field in sample


async def test_known_tag_list_still_covers_upstream(live_client):
    """If Codeforces adds a tag, our 'unknown tag' message would wrongly reject it."""
    payload = await live_client.call("problemset.problems")
    upstream = {t for p in payload["problems"] for t in p.get("tags", [])}
    assert upstream <= KNOWN_TAGS, f"new upstream tags: {sorted(upstream - KNOWN_TAGS)}"


async def test_rating_bounds_unchanged(live_client):
    payload = await live_client.call("problemset.problems")
    ratings = [p["rating"] for p in payload["problems"] if "rating" in p]
    assert min(ratings) >= 800
    assert max(ratings) <= 3500


async def test_contest_phases_include_before(live_client):
    contests = await live_client.call("contest.list")
    assert any(c.get("phase") == "BEFORE" for c in contests)
