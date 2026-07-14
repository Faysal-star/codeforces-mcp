"""Markdown renderers.

Agents read these directly, so they favour compactness: dates already converted to
ISO, ratings and URLs inline, no repeated boilerplate.
"""

from __future__ import annotations

from .schemas import (
    ProblemSearchResult,
    RatingHistoryResult,
    SubmissionsResult,
    TagPerformanceResult,
    UpcomingContestsResult,
    UserProfile,
)


def problems_md(r: ProblemSearchResult) -> str:
    if not r.problems:
        return r.note or "No problems matched those filters."
    lines = [
        f"**{r.count} of {r.total_matched} matching problems** "
        f"(offset {r.offset}{', more available' if r.has_more else ''})",
        "",
        "| Rating | Problem | Tags | Link |",
        "| --- | --- | --- | --- |",
    ]
    for p in r.problems:
        tags = ", ".join(p.tags[:4]) or "-"
        lines.append(
            f"| {p.rating or '-'} | {p.contest_id}{p.index} — {p.name} | {tags} | {p.url} |"
        )
    if r.note:
        lines += ["", f"_{r.note}_"]
    return "\n".join(lines)


def tag_performance_md(r: TagPerformanceResult) -> str:
    if not r.weakest_first:
        return (
            f"No tag has enough attempts to rank for **{r.handle}** "
            f"({r.total_attempted} problems attempted, {r.total_solved} solved)."
        )
    lines = [
        f"**{r.handle}** — {r.total_solved}/{r.total_attempted} distinct problems solved",
        "",
        "Weakest tags first (solve rate = solved / attempted, distinct problems):",
        "",
        "| Tag | Solved | Attempted | Solve rate | Avg rating solved |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s in r.weakest_first:
        lines.append(
            f"| {s.tag} | {s.solved} | {s.attempted} | {s.solve_rate:.0%} | "
            f"{s.avg_rating_solved or '-'} |"
        )
    if r.insufficient_data:
        lines += ["", f"_Too few attempts to rank: {', '.join(r.insufficient_data)}_"]
    return "\n".join(lines)


def submissions_md(r: SubmissionsResult) -> str:
    if not r.submissions:
        return r.note or f"No submissions found for {r.handle}."
    lines = [
        f"**{r.count} recent submission(s) for {r.handle}**",
        "",
        "| When | Problem | Rating | Verdict | Lang | Link |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s in r.submissions:
        when = (s.submitted_at or "")[:10]
        lines.append(
            f"| {when} | {s.contest_id}{s.problem_index} — {s.problem_name} | "
            f"{s.rating or '-'} | {s.verdict or 'PENDING'} | {s.language} | {s.url} |"
        )
    if r.note:
        lines += ["", f"_{r.note}_"]
    return "\n".join(lines)


def profile_md(p: UserProfile) -> str:
    bits = [f"# {p.handle}", ""]
    bits.append(f"- Rating: **{p.rating if p.rating is not None else 'unrated'}**"
                f" (max {p.max_rating if p.max_rating is not None else 'n/a'})")
    bits.append(f"- Rank: {p.rank or 'unrated'} (max {p.max_rank or 'n/a'})")
    if p.organization:
        bits.append(f"- Organization: {p.organization}")
    if p.country:
        bits.append(f"- Country: {p.country}")
    if p.registered_at:
        bits.append(f"- Registered: {p.registered_at[:10]}")
    bits.append(f"- Profile: {p.profile_url}")
    return "\n".join(bits)


def rating_history_md(r: RatingHistoryResult) -> str:
    if not r.history:
        return f"**{r.handle}** has no rated contest history."
    lines = [
        f"**{r.handle}** — {r.contests} rated contests, current {r.current_rating}, "
        f"max {r.max_rating}",
        "",
        "| Date | Contest | Rank | Delta | Rating |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in r.history:
        sign = "+" if c.delta > 0 else ""
        lines.append(
            f"| {(c.date or '')[:10]} | {c.contest_name} | {c.rank} | "
            f"{sign}{c.delta} | {c.new_rating} |"
        )
    return "\n".join(lines)


def contests_md(r: UpcomingContestsResult) -> str:
    if not r.contests:
        return "No upcoming contests announced."
    lines = ["**Upcoming contests**", "", "| Starts (UTC) | Contest | Duration | Link |",
             "| --- | --- | --- | --- |"]
    for c in r.contests:
        starts = (c.starts_at or "unknown").replace("T", " ")[:16]
        lines.append(f"| {starts} | {c.name} | {c.duration} | {c.url} |")
    return "\n".join(lines)
