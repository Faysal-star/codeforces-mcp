# codeforces-mcp — Specification

Written before implementation. Every tool below has an explicit contract and
acceptance criteria; a tool is not "done" until its criteria are asserted by a
test in `tests/contract/`.

## Upstream

Codeforces public API, `https://codeforces.com/api/`. No authentication.

Response envelope:

```json
{"status": "OK",     "result": ...}
{"status": "FAILED", "comment": "handle: User with handle xyz not found"}
```

`comment` is human-readable and worth surfacing verbatim — it is usually the most
actionable error text available.

### Measured characteristics

| Endpoint | Size | Latency | Notes |
|---|---|---|---|
| `user.info` | <2 KB | ~0.26 s | cheap |
| `user.rating` | small | ~0.3 s | 21 entries for a 3-year-old account |
| `user.status` | 187 KB / 338 subs | ~0.85 s | **`problem.tags` embedded inline** |
| `problemset.problems` | 2.25 MB / 11,363 problems | ~1.4 s | 11,080 rated, 38 tags, ratings 800–3500 |
| `contest.list` | ~1 MB | ~1 s | all contests, filter client-side |

Rate limit: Codeforces documents roughly 1 request / 2 s. The client enforces this
with a token bucket; the disk cache absorbs most repeat calls.

## Design decisions

**D1 — `user.status` carries tags inline.** Per-tag performance therefore needs no
join against the 2.25 MB problemset. `codeforces_tag_performance` makes exactly one
upstream call.

**D2 — Cache TTLs differ by volatility.** `problemset.problems` changes on contest
cadence, so 6 h. A user's submissions change during practice, so 5 min. `user.info`
1 h.

**D3 — Always force `encoding="utf-8"`.** Codeforces returns UTF-8; Python on Windows
defaults to cp1252 and raises `UnicodeDecodeError` on problem titles. Applies to every
file read/write and cache operation.

**D4 — "Solved" means a verdict of `OK`**, keyed on `(contestId, index)`. A problem
attempted 8 times and eventually solved counts once as solved and once as attempted.

**D5 — Typed output.** Every tool returns a pydantic model serialised by the tool
layer, never a raw upstream dict. Upstream field changes surface as validation
errors in the live tests rather than as silently wrong agent answers.

## Tools

All are read-only: `readOnlyHint: true`, `destructiveHint: false`,
`idempotentHint: true`, `openWorldHint: true`. All support
`response_format: "markdown" | "json"` (default markdown).

---

### `codeforces_search_problems`

Find problems by rating band and tag, **optionally excluding those a handle has
already solved**. The Codeforces website cannot express that filter, which makes this
the tool with the clearest reason to exist.

| Param | Type | Default | Constraint |
|---|---|---|---|
| `min_rating` | int? | none | 800–3500 |
| `max_rating` | int? | none | 800–3500, `>= min_rating` |
| `tags` | list[str]? | `[]` | max 10; matched against the 38 known tags |
| `tags_match` | `"any"\|"all"` | `"any"` | |
| `exclude_solved_by` | str? | none | a handle |
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | >= 0 |

**Acceptance criteria**

- A1 Every returned problem has `min_rating <= rating <= max_rating` when supplied.
- A2 With `tags_match="all"`, every result carries every requested tag.
- A3 With `exclude_solved_by=H`, no result appears in H's solved set.
- A4 Unrated problems (283 of 11,363) are excluded whenever a rating bound is given.
- A5 Response carries `total_matched`, `count`, `offset`, `has_more`.
- A6 An unknown tag returns an empty result **and** names the valid tags in the message,
  rather than erroring.

---

### `codeforces_tag_performance`

Solve rate per tag for one handle, ranked weakest-first. Computed from submission
history, not proxied from any endpoint.

| Param | Type | Default | Constraint |
|---|---|---|---|
| `handle` | str | required | 1–24 chars |
| `min_attempted` | int | 3 | >= 1; tags below this are pooled into `insufficient_data` |
| `response_format` | enum | markdown | |

Per tag: `attempted`, `solved`, `solve_rate`, `avg_rating_solved`,
`max_rating_solved`.

**Acceptance criteria**

- B1 `solved <= attempted` for every tag.
- B2 Problems are deduplicated by `(contestId, index)` before counting.
- B3 Tags with `attempted < min_attempted` are excluded from the ranking.
- B4 Ranking is ascending by `solve_rate`, ties broken by `attempted` descending.
- B5 Exactly one upstream call is made (see D1).
- B6 A handle with zero submissions returns an empty ranking, not an error.

---

### `codeforces_recent_submissions`

Recent submissions for a handle, optionally filtered by verdict. Intended for
reviewing recent failures.

| Param | Type | Default | Constraint |
|---|---|---|---|
| `handle` | str | required | |
| `verdict` | str? | none | e.g. `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `OK` |
| `limit` | int | 10 | 1–100 |

**Acceptance criteria**

- C1 Results are sorted by submission time, newest first.
- C2 With `verdict=V`, every result has that verdict.
- C3 Each result includes a problem URL.
- C4 An unknown verdict returns empty plus the list of observed verdicts.

---

### `codeforces_user_profile`

| Param | Type | Constraint |
|---|---|---|
| `handle` | str | required |

Returns handle, rating, max rating, rank, max rank, organization, country,
contribution, registration date (ISO 8601, not epoch).

**Acceptance criteria**

- D1 An unknown handle raises an actionable error carrying the upstream `comment`.
- D2 Unrated users (no `rating` field) return `null`, not 0.
- D3 Timestamps are ISO 8601 strings.

---

### `codeforces_rating_history`

| Param | Type | Default |
|---|---|---|
| `handle` | str | required |
| `limit` | int? | all |

Per contest: name, rank, old rating, new rating, delta, ISO date.

**Acceptance criteria**

- E1 `delta == newRating - oldRating` for every entry.
- E2 Chronological order, oldest first.
- E3 A user who has never competed returns an empty list, not an error.

---

### `codeforces_upcoming_contests`

| Param | Type | Default |
|---|---|---|
| `limit` | int | 10 |

**Acceptance criteria**

- F1 Only contests with `phase == "BEFORE"`.
- F2 Sorted by start time, soonest first.
- F3 Includes ISO start time and human-readable duration.

## Out of scope for v1

- **Problem statement text.** Codeforces has no statement API. Scraping is fragile and
  ToS-risky; tools return the problem URL instead.
- **Submitting solutions.** No API exists.
- **Authenticated endpoints.** v1 uses public data only, so there are no secrets to manage.

## Definition of done

1. `pytest tests/contract` passes with no network access.
2. `pytest -m live` passes against the real API.
3. `python eval/run_eval.py` reports every case passing.
4. `ruff check` and `mypy --strict src/` are clean.
5. README shows real output for handle `3.141f`.
