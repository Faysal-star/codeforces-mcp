# Working in this repo

Reusable context for agents. Read this before changing anything.

## The rule that matters most

**`SPEC.md` is the contract, and it is written before the code.** Every tool has
acceptance criteria there, labelled `A1`, `B2`, and so on. Every criterion has a test
in `tests/contract/` that names it in the docstring.

Changing behaviour means:

1. Edit `SPEC.md` first, including the acceptance criteria.
2. Add or update the contract test that asserts the new criterion.
3. Only then change the implementation.

A pull request that changes behaviour without touching `SPEC.md` is wrong even if the
tests pass.

## Layout

| Path | Role |
|---|---|
| `src/codeforces_mcp/client.py` | HTTP, disk cache, rate limiting, envelope unwrapping |
| `src/codeforces_mcp/schemas.py` | every input and output model |
| `src/codeforces_mcp/tools/` | tool logic — **no MCP imports here** |
| `src/codeforces_mcp/server.py` | MCP registration, validation, formatting only |
| `tests/contract/` | offline, fixture-backed, deterministic |
| `tests/live/` | opt-in, asserts upstream shape |
| `eval/` | agent-behaviour cases |

`tools/` must stay free of MCP imports. That separation is what lets the contract
tests and the eval harness call real logic without standing up a server; do not
collapse it for convenience.

## Conventions

- **Always pass `encoding="utf-8"` explicitly** on file reads and writes. Codeforces
  returns UTF-8 and Python on Windows defaults to cp1252, which raises
  `UnicodeDecodeError` on real problem titles. This has bitten this project twice.
- **Return pydantic models, never raw upstream dicts.** An upstream field rename should
  surface as a validation error, not as a silently wrong answer to an agent.
- **Error messages must be actionable.** Surface the upstream `comment` verbatim; when
  rejecting input, name the valid alternatives (see the unknown-tag path in
  `tools/problems.py`).
- **Tool parameters stay flat** in `server.py` signatures. A single model argument
  nests the whole schema under `params`, which is worse for the calling agent.
- `datetime.UTC` is Python 3.11+; this package supports 3.10, so use `timezone.utc`.

## Before you claim a change works

```bash
ruff check . && mypy src/ && pytest tests/contract -q && python eval/run_eval.py
```

If you touched the client or added a tool, also run `pytest -m live -q`.

## Refreshing fixtures

`python tests/record_fixtures.py` re-records from the live API and re-trims the
problem set. The trim is seeded, so an unchanged upstream produces an unchanged file.
Expect the diff to be large when Codeforces adds contests; review it rather than
rubber-stamping.
