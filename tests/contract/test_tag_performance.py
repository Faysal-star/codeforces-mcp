"""Contract tests for codeforces_tag_performance. Criteria B1-B6 in SPEC.md."""

from __future__ import annotations

from codeforces_mcp.schemas import TagPerformanceInput
from codeforces_mcp.tools import tag_performance

from ..conftest import FixtureClient


async def test_b1_solved_never_exceeds_attempted(client, handle):
    result = await tag_performance(client, TagPerformanceInput(handle=handle))
    assert result.weakest_first
    for stat in result.weakest_first:
        assert stat.solved <= stat.attempted
        assert 0.0 <= stat.solve_rate <= 1.0


async def test_b2_problems_deduplicated(client, handle, solved_keys_of_handle):
    """B2: counting submissions instead of problems would inflate every number."""
    result = await tag_performance(client, TagPerformanceInput(handle=handle, min_attempted=1))
    assert result.total_solved == len(solved_keys_of_handle)
    # 338 submissions in the fixture collapse to far fewer distinct problems.
    assert result.total_attempted < 338


async def test_b3_min_attempted_filters_thin_tags(client, handle):
    strict = await tag_performance(client, TagPerformanceInput(handle=handle, min_attempted=10))
    assert all(s.attempted >= 10 for s in strict.weakest_first)
    assert strict.insufficient_data, "some tags must fall below a threshold of 10"

    loose = await tag_performance(client, TagPerformanceInput(handle=handle, min_attempted=1))
    assert len(loose.weakest_first) > len(strict.weakest_first)


async def test_b4_ranked_weakest_first(client, handle):
    """B4: ascending solve rate, ties broken by attempts descending."""
    result = await tag_performance(client, TagPerformanceInput(handle=handle))
    keys = [(s.solve_rate, -s.attempted) for s in result.weakest_first]
    assert keys == sorted(keys)


async def test_b5_exactly_one_upstream_call(client, handle):
    """B5: tags are inline in user.status, so no join is needed (SPEC.md D1)."""
    await tag_performance(client, TagPerformanceInput(handle=handle))
    assert len(client.calls) == 1
    assert client.calls[0][0] == "user.status"


async def test_b6_handle_with_no_submissions(handle):
    """B6: an empty history is an empty ranking, not an exception."""

    class Empty(FixtureClient):
        async def call(self, method, **params):
            self.calls.append((method, params))
            return []

    result = await tag_performance(Empty(), TagPerformanceInput(handle=handle))
    assert result.weakest_first == []
    assert result.total_attempted == 0
    assert result.total_solved == 0


async def test_avg_rating_only_counts_solved(client, handle):
    result = await tag_performance(client, TagPerformanceInput(handle=handle, min_attempted=1))
    for stat in result.weakest_first:
        if stat.solved == 0:
            assert stat.avg_rating_solved is None
            assert stat.max_rating_solved is None
        elif stat.avg_rating_solved is not None:
            assert 800 <= stat.avg_rating_solved <= 3500
