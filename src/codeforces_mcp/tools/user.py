"""codeforces_user_profile and codeforces_rating_history."""

from __future__ import annotations

from typing import Any

from ..client import CodeforcesClient, CodeforcesError
from ..schemas import (
    HandleInput,
    RatingChange,
    RatingHistoryInput,
    RatingHistoryResult,
    UserProfile,
    epoch_to_iso,
)


async def user_profile(client: CodeforcesClient, params: HandleInput) -> UserProfile:
    """Public profile for one handle."""
    users: list[dict[str, Any]] = await client.call("user.info", handles=params.handle)
    if not users:
        raise CodeforcesError(f"no user returned for handle '{params.handle}'", "user.info")
    u = users[0]
    return UserProfile(
        handle=u.get("handle", params.handle),
        # Unrated users have no 'rating' key at all; None is the honest answer, not 0.
        rating=u.get("rating"),
        max_rating=u.get("maxRating"),
        rank=u.get("rank"),
        max_rank=u.get("maxRank"),
        organization=u.get("organization") or None,
        country=u.get("country") or None,
        contribution=u.get("contribution"),
        friend_of_count=u.get("friendOfCount"),
        registered_at=epoch_to_iso(u.get("registrationTimeSeconds")),
        profile_url=f"https://codeforces.com/profile/{u.get('handle', params.handle)}",
    )


async def rating_history(
    client: CodeforcesClient, params: RatingHistoryInput
) -> RatingHistoryResult:
    """Contest-by-contest rating changes, oldest first."""
    changes: list[dict[str, Any]] = await client.call("user.rating", handle=params.handle)

    entries = [
        RatingChange(
            contest_id=c.get("contestId", 0),
            contest_name=c.get("contestName", ""),
            rank=c.get("rank", 0),
            old_rating=c.get("oldRating", 0),
            new_rating=c.get("newRating", 0),
            delta=c.get("newRating", 0) - c.get("oldRating", 0),
            date=epoch_to_iso(c.get("ratingUpdateTimeSeconds")),
        )
        for c in changes
    ]
    entries.sort(key=lambda e: e.date or "")

    trimmed = entries[-params.limit :] if params.limit else entries

    return RatingHistoryResult(
        handle=params.handle,
        contests=len(entries),
        current_rating=entries[-1].new_rating if entries else None,
        max_rating=max((e.new_rating for e in entries), default=None),
        history=trimmed,
    )
