"""MCP server exposing the Codeforces tools.

This layer only declares tool signatures, validates them through the pydantic input
models in `schemas.py`, dispatches to `tools/`, and formats the result. Keeping the
logic out of here is what lets the contract tests and the eval harness exercise real
behaviour without standing up a server.

Tool parameters are declared flat rather than as one model argument: the SDK builds
the input schema from the signature, and a flat schema gives the agent named,
individually described, individually constrained arguments instead of a single opaque
nested object.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, ValidationError

# SDK 2.x renamed FastMCP to MCPServer; keep 1.x working so the repo is not pinned to
# a single SDK generation.
try:  # pragma: no cover - whichever SDK is installed decides this
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.types import ToolAnnotations

    def _annotations(title: str) -> Any:
        return ToolAnnotations(
            title=title,
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        )

except ImportError:  # pragma: no cover
    from mcp.server.fastmcp import (  # type: ignore[import-not-found,no-redef]
        FastMCP as _Server,
    )

    def _annotations(title: str) -> Any:
        return {
            "title": title,
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }


from . import formatting as fmt  # noqa: E402
from . import tools  # noqa: E402
from .client import CodeforcesError, get_client  # noqa: E402
from .schemas import (  # noqa: E402
    HandleInput,
    RatingHistoryInput,
    RecentSubmissionsInput,
    ResponseFormat,
    SearchProblemsInput,
    TagPerformanceInput,
    UpcomingContestsInput,
)

mcp = _Server(name="codeforces_mcp")

# Shared annotations so descriptions stay identical across tools.
HandleArg = Annotated[str, Field(description="Codeforces handle, e.g. '3.141f'", max_length=24)]
FormatArg = Annotated[
    str, Field(description="'markdown' for a readable table, 'json' for structured data")
]


def _render(model: Any, markdown: str, response_format: str) -> str:
    if response_format == ResponseFormat.JSON.value:
        return str(model.model_dump_json(indent=2))
    return markdown


def _bad_input(exc: ValidationError) -> str:
    """Turn pydantic's report into one actionable line naming each offending field."""
    problems = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    return f"Invalid arguments: {problems}"


@mcp.tool(
    name="codeforces_search_problems",
    annotations=_annotations("Search Codeforces Problems"),
)
async def codeforces_search_problems(
    min_rating: Annotated[
        int | None, Field(description="Lowest problem rating, inclusive", ge=800, le=3500)
    ] = None,
    max_rating: Annotated[
        int | None, Field(description="Highest problem rating, inclusive", ge=800, le=3500)
    ] = None,
    tags: Annotated[
        list[str],
        Field(description="Codeforces tags, e.g. ['dp','greedy']. Empty means any.", max_length=10),
    ] = [],  # noqa: B006 - the SDK reads signature defaults to build the input schema
    tags_match: Annotated[
        str, Field(description="'any' = at least one tag, 'all' = every tag")
    ] = "any",
    exclude_solved_by: Annotated[
        str | None,
        Field(description="Hide problems this handle already solved, e.g. '3.141f'", max_length=24),
    ] = None,
    limit: Annotated[int, Field(description="Maximum problems to return", ge=1, le=100)] = 20,
    offset: Annotated[int, Field(description="Problems to skip, for pagination", ge=0)] = 0,
    response_format: FormatArg = "markdown",
) -> str:
    """Find Codeforces problems by rating band and tags, easiest first.

    Set `exclude_solved_by` to a handle to hide problems that handle has already solved.
    The Codeforces website cannot express that filter, which is the main reason to reach
    for this tool: it turns "problems tagged dp rated 1300-1500" into "problems I could
    actually still practise".
    """
    try:
        params = SearchProblemsInput(
            min_rating=min_rating,
            max_rating=max_rating,
            tags=tags,
            tags_match=tags_match,  # type: ignore[arg-type]
            exclude_solved_by=exclude_solved_by,
            limit=limit,
            offset=offset,
            response_format=response_format,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return _bad_input(exc)
    try:
        result = await tools.search_problems(get_client(), params)
    except CodeforcesError as exc:
        return f"Error: {exc.comment} (method: {exc.method})"
    return _render(result, fmt.problems_md(result), response_format)


@mcp.tool(
    name="codeforces_tag_performance",
    annotations=_annotations("Codeforces Tag Performance"),
)
async def codeforces_tag_performance(
    handle: HandleArg,
    min_attempted: Annotated[
        int,
        Field(
            description="Ignore tags with fewer attempts than this, so a 0/1 tag cannot "
            "top the weakness ranking",
            ge=1,
        ),
    ] = 3,
    response_format: FormatArg = "markdown",
) -> str:
    """Rank a handle's problem tags by solve rate, weakest first.

    Computed from full submission history and deduplicated per problem, so grinding one
    problem twelve times counts once. Use it to decide what to practise: the lowest solve
    rates with a meaningful number of attempts are the real gaps. Codeforces exposes no
    endpoint for this.
    """
    try:
        params = TagPerformanceInput(
            handle=handle,
            min_attempted=min_attempted,
            response_format=response_format,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return _bad_input(exc)
    try:
        result = await tools.tag_performance(get_client(), params)
    except CodeforcesError as exc:
        return f"Error: {exc.comment} (method: {exc.method})"
    return _render(result, fmt.tag_performance_md(result), response_format)


@mcp.tool(
    name="codeforces_recent_submissions",
    annotations=_annotations("Recent Codeforces Submissions"),
)
async def codeforces_recent_submissions(
    handle: HandleArg,
    verdict: Annotated[
        str | None,
        Field(description="Filter by verdict, e.g. 'WRONG_ANSWER', 'TIME_LIMIT_EXCEEDED', 'OK'"),
    ] = None,
    limit: Annotated[int, Field(description="Maximum submissions to return", ge=1, le=100)] = 10,
    response_format: FormatArg = "markdown",
) -> str:
    """List a handle's most recent submissions, newest first.

    Filter by `verdict` to pull up recent failures for review. Each row links to the
    submission on Codeforces so the code itself can be read.
    """
    try:
        params = RecentSubmissionsInput(
            handle=handle,
            verdict=verdict,
            limit=limit,
            response_format=response_format,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return _bad_input(exc)
    try:
        result = await tools.recent_submissions(get_client(), params)
    except CodeforcesError as exc:
        return f"Error: {exc.comment} (method: {exc.method})"
    return _render(result, fmt.submissions_md(result), response_format)


@mcp.tool(
    name="codeforces_user_profile",
    annotations=_annotations("Codeforces User Profile"),
)
async def codeforces_user_profile(
    handle: HandleArg,
    response_format: FormatArg = "markdown",
) -> str:
    """Public profile for a Codeforces handle: rating, max rating, rank, organization."""
    try:
        params = HandleInput(
            handle=handle,
            response_format=response_format,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return _bad_input(exc)
    try:
        result = await tools.user_profile(get_client(), params)
    except CodeforcesError as exc:
        return f"Error: {exc.comment} (method: {exc.method})"
    return _render(result, fmt.profile_md(result), response_format)


@mcp.tool(
    name="codeforces_rating_history",
    annotations=_annotations("Codeforces Rating History"),
)
async def codeforces_rating_history(
    handle: HandleArg,
    limit: Annotated[
        int | None, Field(description="Return only the most recent N contests", ge=1)
    ] = None,
    response_format: FormatArg = "markdown",
) -> str:
    """Contest-by-contest rating changes for a handle, oldest first, with deltas."""
    try:
        params = RatingHistoryInput(
            handle=handle,
            limit=limit,
            response_format=response_format,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return _bad_input(exc)
    try:
        result = await tools.rating_history(get_client(), params)
    except CodeforcesError as exc:
        return f"Error: {exc.comment} (method: {exc.method})"
    return _render(result, fmt.rating_history_md(result), response_format)


@mcp.tool(
    name="codeforces_upcoming_contests",
    annotations=_annotations("Upcoming Codeforces Contests"),
)
async def codeforces_upcoming_contests(
    limit: Annotated[int, Field(description="Maximum contests to return", ge=1, le=50)] = 10,
    response_format: FormatArg = "markdown",
) -> str:
    """Contests that have not started yet, soonest first, with start time and duration."""
    try:
        params = UpcomingContestsInput(
            limit=limit,
            response_format=response_format,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return _bad_input(exc)
    try:
        result = await tools.upcoming_contests(get_client(), params)
    except CodeforcesError as exc:
        return f"Error: {exc.comment} (method: {exc.method})"
    return _render(result, fmt.contests_md(result), response_format)


def main() -> None:
    """stdio entry point, used by `claude mcp add`."""
    mcp.run()


if __name__ == "__main__":
    main()
