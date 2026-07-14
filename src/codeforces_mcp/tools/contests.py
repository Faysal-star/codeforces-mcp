"""codeforces_upcoming_contests."""

from __future__ import annotations

from typing import Any

from ..client import CodeforcesClient
from ..schemas import Contest, UpcomingContestsInput, UpcomingContestsResult, epoch_to_iso
from ._common import format_duration


async def upcoming_contests(
    client: CodeforcesClient, params: UpcomingContestsInput
) -> UpcomingContestsResult:
    """Contests that have not started yet, soonest first."""
    contests: list[dict[str, Any]] = await client.call("contest.list")

    upcoming = [c for c in contests if c.get("phase") == "BEFORE"]
    upcoming.sort(key=lambda c: c.get("startTimeSeconds") or 0)
    window = upcoming[: params.limit]

    return UpcomingContestsResult(
        count=len(window),
        contests=[
            Contest(
                id=c.get("id", 0),
                name=c.get("name", ""),
                type=c.get("type", ""),
                phase=c.get("phase", ""),
                starts_at=epoch_to_iso(c.get("startTimeSeconds")),
                duration=format_duration(c.get("durationSeconds")),
                url=f"https://codeforces.com/contest/{c.get('id', 0)}",
            )
            for c in window
        ],
    )
