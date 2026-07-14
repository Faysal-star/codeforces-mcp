"""Contract tests for codeforces_search_problems. Criteria A1-A6 in SPEC.md."""

from __future__ import annotations

import pytest

from codeforces_mcp.schemas import SearchProblemsInput
from codeforces_mcp.tools import search_problems


async def test_a1_respects_rating_band(client):
    """A1: every returned problem sits inside the requested band."""
    result = await search_problems(
        client, SearchProblemsInput(min_rating=1300, max_rating=1500, limit=100)
    )
    assert result.problems, "fixture should contain problems in 1300-1500"
    assert all(1300 <= p.rating <= 1500 for p in result.problems)


async def test_a2_tags_match_all_requires_every_tag(client):
    """A2: tags_match='all' means every requested tag is present."""
    result = await search_problems(
        client, SearchProblemsInput(tags=["dp", "greedy"], tags_match="all", limit=100)
    )
    for p in result.problems:
        have = {t.lower() for t in p.tags}
        assert {"dp", "greedy"}.issubset(have)


async def test_a2b_tags_match_any_requires_one_tag(client):
    result = await search_problems(
        client, SearchProblemsInput(tags=["dp", "greedy"], tags_match="any", limit=100)
    )
    for p in result.problems:
        have = {t.lower() for t in p.tags}
        assert have & {"dp", "greedy"}


async def test_a3_excludes_solved(client, handle, solved_keys_of_handle):
    """A3: nothing the handle already solved comes back. The headline feature."""
    result = await search_problems(
        client, SearchProblemsInput(exclude_solved_by=handle, limit=100)
    )
    returned = {(p.contest_id, p.index) for p in result.problems}
    assert not (returned & solved_keys_of_handle)
    assert result.excluded_solved > 0, "fixture handle has solved problems in the sample"


async def test_a3b_exclusion_actually_removes_something(client, handle):
    """The filter must change the result, or it is not being applied."""
    common = {"min_rating": 800, "max_rating": 1400, "limit": 100}
    without = await search_problems(client, SearchProblemsInput(**common))
    with_filter = await search_problems(
        client, SearchProblemsInput(**common, exclude_solved_by=handle)
    )
    assert with_filter.total_matched < without.total_matched


async def test_a4_unrated_problems_dropped_when_band_given(client):
    """A4: an unrated problem cannot satisfy a rating bound."""
    result = await search_problems(client, SearchProblemsInput(min_rating=800, limit=100))
    assert all(p.rating is not None for p in result.problems)


async def test_a5_pagination_metadata(client):
    """A5: total/count/offset/has_more must be coherent and non-overlapping."""
    page1 = await search_problems(client, SearchProblemsInput(limit=10, offset=0))
    page2 = await search_problems(client, SearchProblemsInput(limit=10, offset=10))

    assert page1.count == 10
    assert page1.has_more is True
    assert page1.offset == 0 and page2.offset == 10
    assert page1.total_matched == page2.total_matched

    ids1 = {(p.contest_id, p.index) for p in page1.problems}
    ids2 = {(p.contest_id, p.index) for p in page2.problems}
    assert not (ids1 & ids2), "pages must not overlap"


async def test_a6_unknown_tag_is_actionable_not_empty_silence(client):
    """A6: a typo should name the valid tags rather than look like 'no such problems'."""
    result = await search_problems(client, SearchProblemsInput(tags=["dynamic programming"]))
    assert result.count == 0
    assert result.note is not None
    assert "dynamic programming" in result.note
    assert "dp" in result.note, "the note should list valid tags so the agent can retry"


async def test_results_ordered_easiest_first(client):
    result = await search_problems(
        client, SearchProblemsInput(min_rating=800, max_rating=2000, limit=50)
    )
    ratings = [p.rating for p in result.problems]
    assert ratings == sorted(ratings)


async def test_every_problem_carries_a_url(client):
    result = await search_problems(client, SearchProblemsInput(limit=20))
    assert all(p.url.startswith("https://codeforces.com/") for p in result.problems)


def test_min_greater_than_max_is_rejected():
    """Cross-field validation belongs in the model, not in the caller."""
    with pytest.raises(ValueError, match="exceeds max_rating"):
        SearchProblemsInput(min_rating=1600, max_rating=1200)
