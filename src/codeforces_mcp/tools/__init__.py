"""Tool implementations, kept free of MCP so the harness can call them directly."""

from .contests import upcoming_contests
from .performance import tag_performance
from .problems import search_problems
from .submissions import recent_submissions
from .user import rating_history, user_profile

__all__ = [
    "rating_history",
    "recent_submissions",
    "search_problems",
    "tag_performance",
    "upcoming_contests",
    "user_profile",
]
