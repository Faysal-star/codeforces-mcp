# codeforces-mcp

An MCP server that gives coding agents access to Codeforces practice data. It helps
you understand your weak tags and find problems you have not already solved.

The server is read-only, uses the public Codeforces API, and requires no Codeforces
authentication. It works with VS Code Copilot, Claude Desktop/Code, and other MCP
clients that support stdio servers.

## Features

- Find problems by rating and tag, optionally excluding a user's solved problems.
- Rank a handle's tags by solve rate and average solved rating.
- Review recent submissions and filter by verdict.
- Inspect a user's profile and rating history.
- List upcoming contests.
- Return results as readable Markdown or structured JSON.
- Cache upstream responses locally and enforce a polite request rate.

## Requirements

- Python 3.10 or newer
- A Codeforces handle for user-specific tools
- VS Code with GitHub Copilot Agent mode, Claude, or another MCP-compatible client

No API key is required.

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/<owner>/codeforces-mcp.git
cd codeforces-mcp
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Install the package:

```bash
python -m pip install -e .
```

For development, install the test and lint dependencies too:

```bash
python -m pip install -e ".[dev]"
```

The installation creates the `codeforces-mcp` command in the virtual environment.

## Use With VS Code Copilot

The repository includes a workspace configuration at `.vscode/mcp.json`. On Windows,
it can point directly to the checked-out venv:

```json
{
  "servers": {
    "codeforces": {
      "type": "stdio",
      "command": "E:\\path\\to\\codeforces-mcp\\.venv\\Scripts\\codeforces-mcp.exe"
    }
  }
}
```

Replace the path with the actual location of your clone. For macOS/Linux, use:

```json
{
  "servers": {
    "codeforces": {
      "type": "stdio",
      "command": "/path/to/codeforces-mcp/.venv/bin/codeforces-mcp"
    }
  }
}
```

In VS Code:

1. Run `MCP: Open Workspace Folder Configuration` from the Command Palette.
2. Add or update the `codeforces` server entry.
3. Open Copilot Chat and switch to **Agent** mode.
4. Open the tools menu, start or enable the `codeforces` server, and allow the tools.

Then ask Copilot something like:

> Find me 5 unsolved DP problems rated 1300-1500 for handle `3.141f`.

The server uses stdio, so VS Code starts and stops it as needed. Do not start a second
copy manually while Copilot is connected.

## Use With Claude

After activating the venv, register the command with Claude Code:

```bash
claude mcp add codeforces -- codeforces-mcp
```

If the command is not on your PATH, use the executable directly.

```powershell
claude mcp add codeforces -- .\.venv\Scripts\codeforces-mcp.exe
```

The equivalent macOS/Linux command is:

```bash
claude mcp add codeforces -- .venv/bin/codeforces-mcp
```

## Tools

All tools are read-only and support `response_format`, which is either `"markdown"`
(the default) or `"json"`.

### `codeforces_search_problems`

Find problems, easiest first. Set `exclude_solved_by` to hide problems whose verdict
for that handle is `OK`.

| Parameter | Default | Description |
| --- | --- | --- |
| `min_rating` | none | Minimum rating, from 800 to 3500 |
| `max_rating` | none | Maximum rating, from 800 to 3500 |
| `tags` | `[]` | Up to 10 Codeforces tags |
| `tags_match` | `"any"` | Use `"all"` to require every tag |
| `exclude_solved_by` | none | Codeforces handle whose solved problems are excluded |
| `limit` | `20` | Number of results, from 1 to 100 |
| `offset` | `0` | Number of matching results to skip |
| `response_format` | `"markdown"` | `"markdown"` or `"json"` |

Example request:

```text
Find 5 unsolved dp problems rated 1300-1500 for 3.141f.
```

Equivalent arguments:

```json
{
  "min_rating": 1300,
  "max_rating": 1500,
  "tags": ["dp"],
  "exclude_solved_by": "3.141f",
  "limit": 5
}
```

### `codeforces_tag_performance`

Compute per-tag attempts, solves, solve rate, and ratings for a handle. Results are
ordered from weakest solve rate first. `min_attempted` prevents very small samples
from dominating the ranking.

```json
{
  "handle": "3.141f",
  "min_attempted": 8,
  "response_format": "markdown"
}
```

### `codeforces_recent_submissions`

List a handle's newest submissions. Use `verdict` such as `WRONG_ANSWER`,
`TIME_LIMIT_EXCEEDED`, or `OK` to filter the list.

```json
{
  "handle": "3.141f",
  "verdict": "WRONG_ANSWER",
  "limit": 10
}
```

### `codeforces_user_profile`

Show a handle's current rating, maximum rating, rank, and organization.

```json
{
  "handle": "3.141f"
}
```

### `codeforces_rating_history`

Show contest-by-contest rating changes, oldest first. Set `limit` to return only the
most recent contests.

```json
{
  "handle": "3.141f",
  "limit": 10
}
```

### `codeforces_upcoming_contests`

List contests that have not started yet, soonest first.

```json
{
  "limit": 5
}
```

## Output Example

```text
**5 of 208 matching problems** (offset 0, more available)

| Rating | Problem | Tags | Link |
| --- | --- | --- | --- |
| 1300 | 189A - Cut Ribbon | brute force, dp | https://codeforces.com/problemset/problem/189/A |
| 1300 | 234C - Weather | dp, implementation | https://codeforces.com/problemset/problem/234/C |
| 1300 | 416B - Art Union | brute force, dp, implementation | https://codeforces.com/problemset/problem/416/B |
```

The JSON format contains the same typed data for applications that need to process
the result programmatically.

## Cache and Rate Limits

The Codeforces API documents approximately one request every two seconds. The client
enforces a rate limit and stores responses in `~/.cache/codeforces-mcp` by default.
Cache lifetimes reflect how often data changes: six hours for the problem set, five
minutes for submissions, and one hour for user profiles.

## Troubleshooting

### Server does not start

Check that the executable exists in the environment used by your MCP configuration:

```powershell
Test-Path .\.venv\Scripts\codeforces-mcp.exe
```

```bash
./.venv/bin/codeforces-mcp
```

If you installed into a different venv, update the `command` path in `mcp.json`.

### Codeforces returns an error

Check the handle spelling and try again later. The server passes actionable Codeforces
error comments through to the client. The public API can also be temporarily rate
limited or unavailable.

## Development

Run the deterministic checks before submitting a change:

```bash
ruff check .
mypy src/
pytest tests/contract -q
python eval/run_eval.py
```

Live tests call Codeforces and are opt-in:

```bash
pytest -m live -q
```

### Rewrite Local Commit Dates

The repository includes `rebase-commits-to-july.sh` for rewriting all commits
on the current branch across 14 and 15 July 2026. It creates a backup branch before
changing history:

```bash
bash rebase-commits-to-july.sh
```

The working tree must be clean, and the script must be run from a named branch. It
rewrites commit IDs, so do not use it on a shared branch without coordination. To
restore the original tip, use the backup branch printed by the script:

```bash
git reset --hard backup/pre-date-rebase-<timestamp>
```

Read [SPEC.md](SPEC.md) before changing tool behavior. It defines the contracts and
acceptance criteria, and each criterion has a corresponding contract test.

## Project Layout

| Path | Purpose |
| --- | --- |
| `src/codeforces_mcp/client.py` | HTTP client, caching, rate limiting |
| `src/codeforces_mcp/schemas.py` | Typed input and output models |
| `src/codeforces_mcp/tools/` | MCP-independent tool logic |
| `src/codeforces_mcp/server.py` | MCP registration and formatting |
| `tests/contract/` | Offline fixture-backed contract tests |
| `tests/live/` | Opt-in upstream drift tests |
| `eval/` | Agent behavior evaluation cases |

## Contributing

1. Open an issue for a bug or proposed behavior change.
2. Update `SPEC.md` and its contract test before changing behavior.
3. Keep tool logic in `src/codeforces_mcp/tools/` free of MCP imports.
4. Run the development checks and include relevant test output in the pull request.

Please avoid committing virtual environments, caches, build output, or API recordings
containing personal data. The repository `.gitignore` already excludes the local
development artifacts created by this project.

## Related Documentation

- [SPEC.md](SPEC.md) - tool contracts and design decisions
- [docs/TECHNICAL-OVERVIEW.md](docs/TECHNICAL-OVERVIEW.md) - architecture and implementation details
