"""codeforces_search_problems — rating/tag search with an unsolved-by filter."""

from __future__ import annotations

from typing import Any

from ..client import CodeforcesClient
from ..schemas import (
    KNOWN_TAGS,
    Problem,
    ProblemSearchResult,
    SearchProblemsInput,
    TagsMatch,
)
from ._common import problem_key, problem_url, solved_keys


async def search_problems(
    client: CodeforcesClient, params: SearchProblemsInput
) -> ProblemSearchResult:
    """Find problems matching a rating band and tags, optionally excluding solved ones."""
    note: str | None = None

    unknown = [t for t in params.tags if t not in KNOWN_TAGS]
    if unknown:
        # A typo should not look like "no such problems exist" (SPEC.md A6).
        return ProblemSearchResult(
            total_matched=0,
            count=0,
            offset=params.offset,
            has_more=False,
            problems=[],
            note=(
                f"Unknown tag(s): {', '.join(unknown)}. "
                f"Valid tags are: {', '.join(sorted(KNOWN_TAGS))}"
            ),
        )

    payload = await client.call("problemset.problems")
    problems: list[dict[str, Any]] = payload["problems"]

    rating_filtered = params.min_rating is not None or params.max_rating is not None
    wanted = set(params.tags)

    matched: list[dict[str, Any]] = []
    for problem in problems:
        rating = problem.get("rating")
        if rating_filtered and rating is None:
            continue  # unrated problems cannot satisfy a rating band (SPEC.md A4)
        if params.min_rating is not None and (rating is None or rating < params.min_rating):
            continue
        if params.max_rating is not None and (rating is None or rating > params.max_rating):
            continue
        if wanted:
            have = {t.lower() for t in problem.get("tags", [])}
            if params.tags_match is TagsMatch.ALL:
                if not wanted.issubset(have):
                    continue
            elif not wanted & have:
                continue
        matched.append(problem)

    excluded = 0
    if params.exclude_solved_by:
        submissions = await client.call("user.status", handle=params.exclude_solved_by)
        solved = solved_keys(submissions)
        before = len(matched)
        matched = [p for p in matched if problem_key(p) not in solved]
        excluded = before - len(matched)
        if excluded and note is None:
            note = f"Excluded {excluded} problem(s) already solved by {params.exclude_solved_by}."

    # Easiest first: a practice ladder is more useful than an arbitrary order.
    matched.sort(key=lambda p: (p.get("rating") or 0, p.get("contestId") or 0, p.get("index", "")))

    total = len(matched)
    window = matched[params.offset : params.offset + params.limit]

    return ProblemSearchResult(
        total_matched=total,
        count=len(window),
        offset=params.offset,
        has_more=params.offset + len(window) < total,
        excluded_solved=excluded,
        note=note,
        problems=[
            Problem(
                contest_id=p.get("contestId"),
                index=p.get("index", ""),
                name=p.get("name", ""),
                rating=p.get("rating"),
                tags=list(p.get("tags", [])),
                url=problem_url(p.get("contestId"), p.get("index", "")),
            )
            for p in window
        ],
    )
