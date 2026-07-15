# codeforces-mcp

An MCP server that gives coding agents access to Codeforces practice data, plus the
verification harness that keeps it honest.

Built spec-first: [`SPEC.md`](SPEC.md) defines every tool contract and its acceptance
criteria, and each criterion is asserted by a test in `tests/contract/`.

## Why it exists

The Codeforces website cannot answer the question you actually have when you sit down
to practise: *"what am I bad at, and what should I solve next that I haven't already
solved?"* Two of these tools answer exactly that.

- `codeforces_tag_performance` ranks your tags by solve rate, weakest first. Codeforces
  exposes no such endpoint; it is computed from your submission history.
- `codeforces_search_problems` filters by rating and tag **excluding problems a handle
  has already solved** — a filter the site itself does not offer.

## Tools

| Tool | What it answers |
|---|---|
| `codeforces_search_problems` | "5 unsolved dp problems rated 1300–1500" |
| `codeforces_tag_performance` | "which tags am I weakest at?" |
| `codeforces_recent_submissions` | "show my recent wrong answers" |
| `codeforces_user_profile` | rating, max rating, rank, organization |
| `codeforces_rating_history` | contest-by-contest deltas |
| `codeforces_upcoming_contests` | what is scheduled next |

All are read-only and need no authentication. Every tool takes
`response_format: "markdown" | "json"`.

## Install

```bash
pip install -e ".[dev]"
claude mcp add codeforces -- codeforces-mcp
```

## Real output

`codeforces_tag_performance(handle="3.141f", min_attempted=8)`:

```
**3.141f** — 199/209 distinct problems solved

| Tag | Solved | Attempted | Solve rate | Avg rating solved |
| --- | --- | --- | --- | --- |
| binary search | 8 | 10 | 80% | 1212.5 |
| dp | 7 | 8 | 88% | 1128.6 |
| number theory | 16 | 18 | 89% | 1000.0 |
| two pointers | 8 | 9 | 89% | 1112.5 |
| constructive algorithms | 34 | 37 | 92% | 905.9 |
| implementation | 90 | 96 | 94% | 915.6 |
| greedy | 73 | 75 | 97% | 942.5 |
| strings | 31 | 31 | 100% | 893.5 |
```

`codeforces_search_problems(min_rating=1300, max_rating=1500, tags=["dp"], exclude_solved_by="3.141f", limit=5)`:

```
**5 of 208 matching problems** (offset 0, more available)

| Rating | Problem | Tags | Link |
| --- | --- | --- | --- |
| 1300 | 189A — Cut Ribbon | brute force, dp | https://codeforces.com/problemset/problem/189/A |
| 1300 | 234C — Weather | dp, implementation | https://codeforces.com/problemset/problem/234/C |
| 1300 | 416B — Art Union | brute force, dp, implementation | https://codeforces.com/problemset/problem/416/B |
```

### What that output actually tells you

Every solve rate above sits between 80% and 100%, which looks like mastery and is not.
People attempt problems they expect to solve, so solve rate is censored upward by
selection. The column doing the real work is `avg_rating_solved`: this handle is rated
1223 but is solving mostly 900–1200 problems, which is the signature of practising
inside the comfort zone rather than above it.

This is a known limitation of the metric, not a bug, and it is why the tool reports
`avg_rating_solved` and `max_rating_solved` alongside the rate rather than ranking on
rate alone. A future version could weight by problem difficulty relative to the user's
rating; see `SPEC.md`.


## The harness

Three layers, because they fail in different ways.

**Contract tests** (`tests/contract/`) run offline against API responses recorded into
`tests/fixtures/`. Deterministic, no network, and they assert the acceptance criteria
from `SPEC.md` by name.

**Live drift tests** (`tests/live/`, `pytest -m live`) hit the real API and assert only
that the upstream contract still holds. This is the gate for a dependency nobody here
controls; it runs nightly rather than on every push.

**Agent eval** (`eval/`) checks the layer the other two cannot: given a natural-language
task, does the right tool get called with the right arguments, and does the result
satisfy a semantic assertion? Cases live in `eval/cases/*.yaml`.

```bash
pytest tests/contract -q     # offline, deterministic  (43 tests)
pytest -m live -q            # upstream contract still holds (7 tests)
python eval/run_eval.py      # writes eval/report.md          (12 cases)
python eval/run_eval.py --live   # same cases against the real API
```

The eval names the tool in each case; it does not yet drive a live model to *choose*
the tool. Model-in-the-loop selection is the obvious next layer and is not implemented.

## Design notes

Decisions and the measurements behind them are in [`SPEC.md`](SPEC.md). The three that
shaped the most code:

- **`user.status` embeds `problem.tags` inline**, so tag analysis costs exactly one
  upstream call rather than a join against the 2.25 MB problem set.
- **Cache TTLs track volatility**: 6 h for the problem set, 5 minutes for your own
  submissions, since those change while you practise.
- **Everything is read as UTF-8 explicitly.** Codeforces returns UTF-8 and Python on
  Windows defaults to cp1252, which raises `UnicodeDecodeError` on real problem titles.

## How it was built

See [`docs/AGENTIC-WORKFLOW.md`](docs/AGENTIC-WORKFLOW.md).
