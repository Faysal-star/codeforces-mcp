"""codeforces_tag_performance — per-tag solve rate, ranked weakest-first.

The analytical tool of the set. Codeforces exposes no such endpoint; this is
computed from submission history. It costs exactly one upstream call, because
user.status embeds problem.tags inline (SPEC.md D1).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..client import CodeforcesClient
from ..schemas import TagPerformanceInput, TagPerformanceResult, TagStat
from ._common import ProblemKey, problem_key


async def tag_performance(
    client: CodeforcesClient, params: TagPerformanceInput
) -> TagPerformanceResult:
    """Rank a handle's tags by solve rate, weakest first."""
    submissions: list[dict[str, Any]] = await client.call("user.status", handle=params.handle)

    # Collapse to one record per distinct problem before counting, so grinding one
    # problem twelve times does not read as twelve attempts (SPEC.md B2).
    attempts: dict[ProblemKey, dict[str, Any]] = {}
    solved: set[ProblemKey] = set()
    for sub in submissions:
        problem = sub.get("problem")
        if not problem:
            continue
        key = problem_key(problem)
        attempts.setdefault(key, problem)
        if sub.get("verdict") == "OK":
            solved.add(key)

    attempted_by_tag: dict[str, int] = defaultdict(int)
    solved_by_tag: dict[str, int] = defaultdict(int)
    ratings_by_tag: dict[str, list[int]] = defaultdict(list)

    for key, problem in attempts.items():
        was_solved = key in solved
        rating = problem.get("rating")
        for tag in problem.get("tags", []):
            attempted_by_tag[tag] += 1
            if was_solved:
                solved_by_tag[tag] += 1
                if rating is not None:
                    ratings_by_tag[tag].append(rating)

    stats: list[TagStat] = []
    thin: list[str] = []
    for tag, attempted in attempted_by_tag.items():
        if attempted < params.min_attempted:
            thin.append(tag)
            continue
        hits = solved_by_tag.get(tag, 0)
        ratings = ratings_by_tag.get(tag, [])
        stats.append(
            TagStat(
                tag=tag,
                attempted=attempted,
                solved=hits,
                solve_rate=round(hits / attempted, 3),
                avg_rating_solved=round(sum(ratings) / len(ratings), 1) if ratings else None,
                max_rating_solved=max(ratings) if ratings else None,
            )
        )

    # Weakest first; on a tie the tag you have attempted more often matters more.
    stats.sort(key=lambda s: (s.solve_rate, -s.attempted))

    return TagPerformanceResult(
        handle=params.handle,
        total_attempted=len(attempts),
        total_solved=len(solved),
        weakest_first=stats,
        insufficient_data=sorted(thin),
    )
