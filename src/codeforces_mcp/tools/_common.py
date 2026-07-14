"""Helpers shared by the tool implementations."""

from __future__ import annotations

from typing import Any

ProblemKey = tuple[int | None, str]


def problem_key(problem: dict[str, Any]) -> ProblemKey:
    """Identity of a problem: (contestId, index). See SPEC.md D4."""
    return (problem.get("contestId"), problem.get("index", ""))


def problem_url(contest_id: int | None, index: str) -> str:
    if contest_id is None:
        return "https://codeforces.com/problemset"
    return f"https://codeforces.com/problemset/problem/{contest_id}/{index}"


def submission_url(contest_id: int | None, submission_id: int) -> str:
    if contest_id is None:
        return f"https://codeforces.com/submissions/{submission_id}"
    return f"https://codeforces.com/contest/{contest_id}/submission/{submission_id}"


def solved_keys(submissions: list[dict[str, Any]]) -> set[ProblemKey]:
    """Problems with at least one OK verdict."""
    return {
        problem_key(s["problem"])
        for s in submissions
        if s.get("verdict") == "OK" and "problem" in s
    }


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "unknown"
    hours, remainder = divmod(int(seconds), 3600)
    minutes = remainder // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"
