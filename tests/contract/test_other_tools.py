"""Contract tests for submissions, profile, rating history and contests.

Criteria C1-C4, D1-D3, E1-E3, F1-F3 in SPEC.md.
"""

from __future__ import annotations

import pytest

from codeforces_mcp.client import CodeforcesError
from codeforces_mcp.schemas import (
    HandleInput,
    RatingHistoryInput,
    RecentSubmissionsInput,
    UpcomingContestsInput,
)
from codeforces_mcp.tools import (
    rating_history,
    recent_submissions,
    upcoming_contests,
    user_profile,
)

# ------------------------------------------------------------- recent_submissions


async def test_c1_newest_first(client, handle):
    result = await recent_submissions(client, RecentSubmissionsInput(handle=handle, limit=50))
    stamps = [s.submitted_at for s in result.submissions]
    assert stamps == sorted(stamps, reverse=True)


async def test_c2_verdict_filter_applies(client, handle):
    result = await recent_submissions(
        client, RecentSubmissionsInput(handle=handle, verdict="WRONG_ANSWER", limit=50)
    )
    assert result.submissions
    assert all(s.verdict == "WRONG_ANSWER" for s in result.submissions)


async def test_c2b_verdict_is_case_insensitive(client, handle):
    lower = await recent_submissions(
        client, RecentSubmissionsInput(handle=handle, verdict="wrong_answer", limit=5)
    )
    assert lower.submissions and all(s.verdict == "WRONG_ANSWER" for s in lower.submissions)


async def test_c3_submissions_link_back(client, handle):
    result = await recent_submissions(client, RecentSubmissionsInput(handle=handle, limit=10))
    assert all(s.url.startswith("https://codeforces.com/") for s in result.submissions)


async def test_c4_unknown_verdict_names_the_real_ones(client, handle):
    """C4: don't just return nothing -- say which verdicts this handle actually has."""
    result = await recent_submissions(
        client, RecentSubmissionsInput(handle=handle, verdict="NO_SUCH_VERDICT", limit=10)
    )
    assert result.count == 0
    assert result.note is not None
    assert "OK" in result.note


async def test_limit_is_respected(client, handle):
    result = await recent_submissions(client, RecentSubmissionsInput(handle=handle, limit=7))
    assert result.count == 7


# ------------------------------------------------------------------- user_profile


async def test_d1_unknown_handle_raises_with_upstream_comment(client):
    """D1: surface the API's own explanation, which is the actionable part."""
    with pytest.raises(CodeforcesError) as excinfo:
        await user_profile(client, HandleInput(handle="definitely_not_a_user"))
    assert "not found" in excinfo.value.comment


async def test_d3_timestamps_are_iso(client, handle):
    profile = await user_profile(client, HandleInput(handle=handle))
    assert profile.registered_at is not None
    assert profile.registered_at.startswith("20")
    assert "T" in profile.registered_at, "ISO 8601, not an epoch integer"


async def test_profile_has_expected_shape(client, handle):
    profile = await user_profile(client, HandleInput(handle=handle))
    assert profile.handle == handle
    assert profile.profile_url.endswith(handle)
    assert profile.max_rating is not None and profile.max_rating >= 0


# ----------------------------------------------------------------- rating_history


async def test_e1_delta_matches_ratings(client, handle):
    result = await rating_history(client, RatingHistoryInput(handle=handle))
    assert result.history
    for change in result.history:
        assert change.delta == change.new_rating - change.old_rating


async def test_e2_chronological_oldest_first(client, handle):
    result = await rating_history(client, RatingHistoryInput(handle=handle))
    dates = [c.date for c in result.history]
    assert dates == sorted(dates)


async def test_e3_limit_keeps_the_most_recent(client, handle):
    full = await rating_history(client, RatingHistoryInput(handle=handle))
    trimmed = await rating_history(client, RatingHistoryInput(handle=handle, limit=3))
    assert len(trimmed.history) == 3
    assert trimmed.history == full.history[-3:]
    assert trimmed.contests == full.contests, "contests counts all, not just the window"


async def test_current_and_max_rating_derived(client, handle):
    result = await rating_history(client, RatingHistoryInput(handle=handle))
    assert result.current_rating == result.history[-1].new_rating
    assert result.max_rating == max(c.new_rating for c in result.history)


# -------------------------------------------------------------- upcoming_contests


async def test_f1_only_before_phase(client):
    result = await upcoming_contests(client, UpcomingContestsInput(limit=50))
    assert result.contests, "fixture includes upcoming contests"
    assert all(c.phase == "BEFORE" for c in result.contests)


async def test_f2_soonest_first(client):
    result = await upcoming_contests(client, UpcomingContestsInput(limit=50))
    starts = [c.starts_at for c in result.contests]
    assert starts == sorted(starts)


async def test_f3_human_readable_duration(client):
    result = await upcoming_contests(client, UpcomingContestsInput(limit=5))
    for contest in result.contests:
        assert contest.duration != "unknown"
        assert contest.duration[-1] in "hm"
