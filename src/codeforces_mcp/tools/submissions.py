"""codeforces_recent_submissions — recent submissions, optionally filtered by verdict."""

from __future__ import annotations

from typing import Any

from ..client import CodeforcesClient
from ..schemas import (
    RecentSubmissionsInput,
    Submission,
    SubmissionsResult,
    epoch_to_iso,
)
from ._common import submission_url


async def recent_submissions(
    client: CodeforcesClient, params: RecentSubmissionsInput
) -> SubmissionsResult:
    """Return a handle's most recent submissions, newest first."""
    raw: list[dict[str, Any]] = await client.call("user.status", handle=params.handle)

    rows = sorted(raw, key=lambda s: s.get("creationTimeSeconds", 0), reverse=True)

    note: str | None = None
    if params.verdict:
        filtered = [s for s in rows if s.get("verdict") == params.verdict]
        if not filtered and rows:
            observed = sorted({s.get("verdict") or "PENDING" for s in rows})
            note = (
                f"No submissions with verdict {params.verdict}. "
                f"Verdicts seen for this handle: {', '.join(observed)}"
            )
        rows = filtered

    window = rows[: params.limit]

    return SubmissionsResult(
        handle=params.handle,
        count=len(window),
        note=note,
        submissions=[
            Submission(
                id=s.get("id", 0),
                problem_name=s.get("problem", {}).get("name", ""),
                problem_index=s.get("problem", {}).get("index", ""),
                contest_id=s.get("problem", {}).get("contestId"),
                rating=s.get("problem", {}).get("rating"),
                tags=list(s.get("problem", {}).get("tags", [])),
                verdict=s.get("verdict"),
                language=s.get("programmingLanguage", ""),
                passed_tests=s.get("passedTestCount"),
                submitted_at=epoch_to_iso(s.get("creationTimeSeconds")),
                url=submission_url(s.get("problem", {}).get("contestId"), s.get("id", 0)),
            )
            for s in window
        ],
    )
