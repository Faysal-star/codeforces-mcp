# How this repo was built

Built with Claude Code, deliberately as a pipeline rather than a conversation:
**spec → agent → harness → verification**. This document records the process and, more
usefully, what the gates actually caught.

## The order

Commits follow the pipeline, and the order is the point.

1. **`SPEC.md` first, no implementation.** Six tool contracts with named acceptance
   criteria (`A1`…`F3`). Writing acceptance criteria before code is what makes "done"
   checkable by something other than opinion.
2. **Measure the upstream before designing against it.** Every number in the
   "Measured characteristics" table came from actually calling the API, not from
   reading docs. That measurement changed the design — see below.
3. **Client, cache, rate limiter, recorded fixtures.**
4. **Per tool: contract test naming its criterion, then implementation.**
5. **Eval harness** for the layer tests cannot reach.
6. **CI gates**, then the consuming skill.

## What measuring first changed

The plan assumed `tag_performance` would need to join submission history against
`problemset.problems` — 2.25 MB and ~1.4 s per call. Probing the API first showed that
`user.status` **already embeds `problem.tags` inline**.

That single observation removed the join, cut the tool to one upstream call, and made
the most analytically interesting tool also the cheapest. It is recorded as design
decision D1 in `SPEC.md`, and `tests/contract/test_tag_performance.py::test_b5_exactly_one_upstream_call`
asserts it stays true.

## What the gates caught

The value of a harness is measured in defects it catches, so here are the real ones.

**mypy caught a portability bug.** `datetime.UTC` is Python 3.11+, but `pyproject.toml`
declares `requires-python = ">=3.10"`. Every test passed on 3.12 while the package was
simply broken on the oldest version it claimed to support. Replaced with
`timezone.utc`. CI now runs the matrix on 3.10 and 3.12 so this cannot recur.

**The eval harness caught an integration mismatch.** The `limit_out_of_range_rejected`
case failed on first run — not because the tool misbehaved, but because the MCP SDK
rejects schema violations by *raising* `ToolError`, while our own validation and
upstream errors return an ordinary text response. Two different failure surfaces that
a calling agent has to handle. The contract tests could not have found this: they call
the tool functions directly and never cross the MCP boundary. `run_case` now treats
both as results to assert on.

**Designing against the schema caught a usability defect.** The first server followed
the single-model-argument pattern (`async def tool(params: InputModel)`). Inspecting
the generated schema showed every tool exposing exactly one property, `params`, with
the real arguments nested inside — so an agent would have to construct
`{"params": {...}}` with no per-argument descriptions or constraints visible. Rewritten
to flat signatures, which is why `codeforces_search_problems` now advertises eight
named, individually constrained arguments.

**A cp1252 decode error, twice.** Codeforces serves UTF-8; Python on Windows defaults
to cp1252 and raises `UnicodeDecodeError` on real problem titles. It bit once while
probing the API and once while trimming fixtures. Now a documented convention in
`CLAUDE.md` and asserted by `test_cache_handles_non_ascii`.

## What reusable context exists here

Two artifacts, aimed at different readers:

- **`CLAUDE.md`** is context for an agent working *on* this repo: the spec-first rule,
  the "no MCP imports in `tools/`" boundary, the UTF-8 convention, and the exact
  command that must pass before claiming a change works.
- **`.claude/skills/cf-practice/`** is context for an agent working *with* this
  server: a packaged skill with a trigger contract and two reference documents loaded
  on demand, encoding how to run a practice session — diagnose before prescribing,
  build a ladder not a list, close the loop on failures.

The pair is the actual point. An MCP server exposes capability; the skill encodes the
judgement for using it well. Shipping only the first leaves every calling agent to
reinvent the second, badly, on every invocation.

## Honest limits

- The eval names the tool in each case. It verifies the call and the semantics of the
  result, but does not yet drive a live model to *choose* the tool. That is the next
  layer and it is not built.
- Solve rate is censored upward by self-selection — people attempt what they expect to
  solve. `tag_performance` reports `avg_rating_solved` alongside it for that reason,
  but the ranking itself is still rate-ordered.
- Coverage is not enforced by a threshold. The contract tests track acceptance criteria
  rather than lines, which is the more useful target but does not produce a number.
