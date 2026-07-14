"""Record trimmed Codeforces API responses into tests/fixtures/.

Run this to refresh fixtures; contract tests then run offline and deterministically.
problemset.problems is 2.25 MB upstream, so it is trimmed to a sample that still
exercises every filter: everything HANDLE has touched (so exclude_solved_by has real
work to do) plus a stratified spread across rating bands and tags.

    python tests/record_fixtures.py
"""

from __future__ import annotations

import json
import random
import urllib.request
from pathlib import Path

API = "https://codeforces.com/api"
HANDLE = "3.141f"
FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PER_BAND = 40


def fetch(method: str, **params: str) -> dict:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API}/{method}" + (f"?{query}" if query else "")
    with urllib.request.urlopen(url, timeout=60) as response:
        # Explicit UTF-8: problem titles contain non-ASCII and Windows defaults to cp1252.
        return json.loads(response.read().decode("utf-8"))


def write(name: str, payload: object) -> None:
    path = FIXTURES / name
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"  {name:34s} {path.stat().st_size / 1024:8.1f} KB")


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    random.seed(20260816)  # deterministic trim, so refreshing does not churn the diff

    print("recording fixtures...")

    write("user_info.json", fetch("user.info", handles=HANDLE))
    write("user_rating.json", fetch("user.rating", handle=HANDLE))

    status = fetch("user.status", handle=HANDLE, **{"from": "1", "count": "100000"})
    write("user_status.json", status)

    touched = {
        (s["problem"].get("contestId"), s["problem"].get("index"))
        for s in status["result"]
        if "problem" in s
    }

    problems = fetch("problemset.problems")["result"]["problems"]
    keep = [p for p in problems if (p.get("contestId"), p.get("index")) in touched]

    by_band: dict[int, list[dict]] = {}
    for p in problems:
        rating = p.get("rating")
        if rating is None:
            by_band.setdefault(-1, []).append(p)
        else:
            by_band.setdefault(rating // 200 * 200, []).append(p)

    chosen = {id(p) for p in keep}
    for band in sorted(by_band):
        pool = [p for p in by_band[band] if id(p) not in chosen]
        for p in random.sample(pool, min(SAMPLE_PER_BAND, len(pool))):
            keep.append(p)
            chosen.add(id(p))

    write("problemset_problems.json", {"status": "OK", "result": {"problems": keep}})
    print(f"    (trimmed {len(problems)} -> {len(keep)} problems, "
          f"{len(touched)} of them touched by {HANDLE})")

    contests = fetch("contest.list")["result"]
    upcoming = [c for c in contests if c.get("phase") == "BEFORE"]
    finished = [c for c in contests if c.get("phase") == "FINISHED"][:20]
    write("contest_list.json", {"status": "OK", "result": upcoming + finished})

    # The FAILED envelope, captured rather than hand-written so the error path is
    # tested against the shape Codeforces actually sends.
    try:
        fetch("user.info", handles="this_handle_does_not_exist_zzz")
    except urllib.error.HTTPError as exc:  # noqa: F821
        write("user_info_failed.json", json.loads(exc.read().decode("utf-8")))


if __name__ == "__main__":
    main()
