"""Pydantic models for every tool input and output.

Tools return these models rather than raw upstream dicts (SPEC.md D5), so an
upstream field change surfaces as a validation error in the live tests instead of
as a silently wrong answer handed to an agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# The 38 tags Codeforces actually uses, captured from problemset.problems.
# Used to give an actionable message on a typo rather than silently returning nothing.
KNOWN_TAGS: frozenset[str] = frozenset(
    {
        "*special", "2-sat", "binary search", "bitmasks", "brute force",
        "chinese remainder theorem", "combinatorics", "communication",
        "constructive algorithms", "data structures", "dfs and similar",
        "divide and conquer", "dp", "dsu", "expression parsing", "fft", "flows",
        "games", "geometry", "graph matchings", "graphs", "greedy", "hashing",
        "implementation", "interactive", "math", "matrices", "meet-in-the-middle",
        "number theory", "probabilities", "schedules", "shortest paths", "sortings",
        "string suffix structures", "strings", "ternary search", "trees",
        "two pointers",
    }
)

MIN_RATING = 800
MAX_RATING = 3500


def epoch_to_iso(seconds: int | float | None) -> str | None:
    """Epoch seconds to an ISO 8601 UTC string. Agents read dates, not epochs."""
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class TagsMatch(str, Enum):
    ANY = "any"
    ALL = "all"


class _Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")


# ----------------------------------------------------------------------- inputs


class SearchProblemsInput(_Input):
    min_rating: int | None = Field(
        default=None, description="Lowest problem rating, inclusive (e.g. 1300)",
        ge=MIN_RATING, le=MAX_RATING,
    )
    max_rating: int | None = Field(
        default=None, description="Highest problem rating, inclusive (e.g. 1500)",
        ge=MIN_RATING, le=MAX_RATING,
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Codeforces tags, e.g. ['dp', 'greedy']. Empty means any tag.",
        max_length=10,
    )
    tags_match: TagsMatch = Field(
        default=TagsMatch.ANY,
        description="'any' returns problems with at least one tag; 'all' requires every tag",
    )
    exclude_solved_by: str | None = Field(
        default=None,
        description="Handle whose solved problems to omit, e.g. '3.141f'. "
        "This filter is the main reason to use this tool over the website.",
        max_length=24,
    )
    limit: int = Field(default=20, description="Maximum problems to return", ge=1, le=100)
    offset: int = Field(default=0, description="Problems to skip, for pagination", ge=0)
    response_format: ResponseFormat = ResponseFormat.MARKDOWN

    @field_validator("tags")
    @classmethod
    def _lower(cls, v: list[str]) -> list[str]:
        return [t.strip().lower() for t in v if t.strip()]

    @model_validator(mode="after")
    def _ordered(self) -> SearchProblemsInput:
        if (
            self.min_rating is not None
            and self.max_rating is not None
            and self.min_rating > self.max_rating
        ):
            raise ValueError(
                f"min_rating ({self.min_rating}) exceeds max_rating ({self.max_rating})"
            )
        return self


class HandleInput(_Input):
    handle: str = Field(..., description="Codeforces handle, e.g. '3.141f'", min_length=1,
                        max_length=24)
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


class TagPerformanceInput(HandleInput):
    min_attempted: int = Field(
        default=3,
        description="Ignore tags with fewer attempts than this; guards against a 0/1 tag "
        "topping the weakness ranking",
        ge=1,
    )


class RecentSubmissionsInput(HandleInput):
    verdict: str | None = Field(
        default=None,
        description="Filter by verdict, e.g. 'WRONG_ANSWER', 'TIME_LIMIT_EXCEEDED', 'OK'",
    )
    limit: int = Field(default=10, description="Maximum submissions to return", ge=1, le=100)

    @field_validator("verdict")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None


class RatingHistoryInput(HandleInput):
    limit: int | None = Field(
        default=None, description="Return only the most recent N contests", ge=1
    )


class UpcomingContestsInput(_Input):
    limit: int = Field(default=10, description="Maximum contests to return", ge=1, le=50)
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


# ---------------------------------------------------------------------- outputs


class Problem(BaseModel):
    contest_id: int | None = None
    index: str
    name: str
    rating: int | None = None
    tags: list[str] = Field(default_factory=list)
    url: str


class ProblemSearchResult(BaseModel):
    total_matched: int
    count: int
    offset: int
    has_more: bool
    excluded_solved: int = Field(default=0, description="Problems dropped by exclude_solved_by")
    problems: list[Problem]
    note: str | None = None


class TagStat(BaseModel):
    tag: str
    attempted: int
    solved: int
    solve_rate: float
    avg_rating_solved: float | None = None
    max_rating_solved: int | None = None


class TagPerformanceResult(BaseModel):
    handle: str
    total_attempted: int
    total_solved: int
    weakest_first: list[TagStat]
    insufficient_data: list[str] = Field(default_factory=list)


class Submission(BaseModel):
    id: int
    problem_name: str
    problem_index: str
    contest_id: int | None = None
    rating: int | None = None
    tags: list[str] = Field(default_factory=list)
    verdict: str | None = None
    language: str
    passed_tests: int | None = None
    submitted_at: str | None = None
    url: str


class SubmissionsResult(BaseModel):
    handle: str
    count: int
    submissions: list[Submission]
    note: str | None = None


class UserProfile(BaseModel):
    handle: str
    rating: int | None = None
    max_rating: int | None = None
    rank: str | None = None
    max_rank: str | None = None
    organization: str | None = None
    country: str | None = None
    contribution: int | None = None
    friend_of_count: int | None = None
    registered_at: str | None = None
    profile_url: str


class RatingChange(BaseModel):
    contest_id: int
    contest_name: str
    rank: int
    old_rating: int
    new_rating: int
    delta: int
    date: str | None = None


class RatingHistoryResult(BaseModel):
    handle: str
    contests: int
    current_rating: int | None = None
    max_rating: int | None = None
    history: list[RatingChange]


class Contest(BaseModel):
    id: int
    name: str
    type: str
    phase: str
    starts_at: str | None = None
    duration: str
    url: str


class UpcomingContestsResult(BaseModel):
    count: int
    contests: list[Contest]
