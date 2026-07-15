"""Agent-behaviour evaluation harness.

Contract tests prove the tool functions are correct. This proves something they
cannot: that a tool call an agent would plausibly make, dispatched through the real
MCP layer, comes back with a result that actually satisfies the intent behind it.

Each case in eval/cases/*.yaml pins an intent, the tool call that serves it, and
assertions about the response. Cases run against recorded fixtures by default so the
result is deterministic and CI-safe; --live runs the same cases against the real API.

    python eval/run_eval.py            # offline, deterministic
    python eval/run_eval.py --live     # against codeforces.com
    python eval/run_eval.py --case unsolved-dp-ladder

Exits non-zero if any case fails, so it can gate a merge.

Scope, stated plainly: this checks tool-call correctness and response semantics. It
does not drive a live model to *choose* the tool -- the tool is named in the case.
Adding model-in-the-loop selection is the obvious next step and is tracked in the
README.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeforces_mcp import client as client_mod  # noqa: E402
from codeforces_mcp.server import mcp  # noqa: E402

ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"
REPORT = ROOT / "report.md"


# ----------------------------------------------------------------- fixture client


def _fixture_client() -> Any:
    """Reuse the test fake so eval and contract tests see identical data."""
    from tests.conftest import FixtureClient

    return FixtureClient()


async def _solved_set(handle: str, use_live: bool) -> set[tuple[Any, str]]:
    source = client_mod.get_client() if use_live else _fixture_client()
    submissions = await source.call("user.status", handle=handle)
    return {
        (s["problem"].get("contestId"), s["problem"].get("index"))
        for s in submissions
        if s.get("verdict") == "OK" and "problem" in s
    }


# --------------------------------------------------------------------- assertions


class CheckFailed(Exception):
    pass


def _dig(payload: Any, path: str) -> Any:
    node = payload
    for part in path.split("."):
        node = node[part]
    return node


async def _check(name: str, want: Any, payload: Any, text: str, ctx: dict[str, Any]) -> None:
    """Run one assertion. Raises CheckFailed with a message a human can act on."""
    is_error = payload is None

    if name == "is_text_error":
        if is_error != bool(want):
            raise CheckFailed(f"expected error={want}, got error={is_error}: {text[:120]}")
        return
    if name == "text_contains":
        if want.lower() not in text.lower():
            raise CheckFailed(f"expected {want!r} in response, got: {text[:160]}")
        return

    if is_error:
        raise CheckFailed(f"tool returned an error, cannot check {name}: {text[:160]}")

    if name == "count_between":
        low, high = want
        count = payload.get("count", len(payload.get("problems", [])))
        if not low <= count <= high:
            raise CheckFailed(f"count {count} outside [{low}, {high}]")
    elif name == "count_equals":
        if payload.get("count") != want:
            raise CheckFailed(f"count {payload.get('count')} != {want}")
    elif name == "all_ratings_between":
        low, high = want
        bad = [p for p in payload["problems"] if not low <= (p["rating"] or -1) <= high]
        if bad:
            raise CheckFailed(
                f"{len(bad)} problem(s) outside [{low}, {high}], e.g. {bad[0]['name']}"
            )
    elif name == "all_have_tags":
        wanted = {t.lower() for t in want}
        bad = [p for p in payload["problems"] if not wanted <= {t.lower() for t in p["tags"]}]
        if bad:
            raise CheckFailed(
                f"{len(bad)} problem(s) missing {sorted(wanted)}, e.g. {bad[0]['name']}"
            )
    elif name == "none_solved_by":
        solved = await _solved_set(want, ctx["live"])
        leaked = [p for p in payload["problems"] if (p["contest_id"], p["index"]) in solved]
        if leaked:
            raise CheckFailed(
                f"{len(leaked)} already-solved problem(s) leaked through, e.g. {leaked[0]['name']}"
            )
    elif name == "sorted_ascending_by":
        if isinstance(want, list):
            key_list, field = want
            values = [row[field] for row in payload[key_list]]
        else:
            values = [p[want] for p in payload["problems"]]
        if values != sorted(values):
            raise CheckFailed(f"not ascending by {want}: {values[:6]}")
    elif name == "list_non_empty":
        if not payload.get(want):
            raise CheckFailed(f"{want} is empty")
    elif name == "field_equals":
        field, expected = want
        if _dig(payload, field) != expected:
            raise CheckFailed(f"{field} = {_dig(payload, field)!r}, expected {expected!r}")
    elif name == "field_at_least":
        field, minimum = want
        actual = _dig(payload, field)
        if actual is None or actual < minimum:
            raise CheckFailed(f"{field} = {actual}, expected >= {minimum}")
    elif name == "field_is_iso_date":
        value = _dig(payload, want)
        try:
            datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise CheckFailed(f"{want} = {value!r} is not ISO 8601") from exc
    elif name == "all_field_equals":
        key_list, field, expected = want
        bad = [r for r in payload[key_list] if r[field] != expected]
        if bad:
            raise CheckFailed(f"{len(bad)} row(s) with {field} != {expected}")
    elif name == "all_urls_are_codeforces":
        bad = [r for r in payload[want] if not r["url"].startswith("https://codeforces.com/")]
        if bad:
            raise CheckFailed(f"{len(bad)} row(s) with a non-Codeforces url")
    elif name == "each_solved_at_most_attempted":
        bad = [r for r in payload[want] if r["solved"] > r["attempted"]]
        if bad:
            raise CheckFailed(f"{len(bad)} tag(s) report solved > attempted, e.g. {bad[0]['tag']}")
    elif name == "deltas_consistent":
        bad = [c for c in payload[want] if c["delta"] != c["new_rating"] - c["old_rating"]]
        if bad:
            raise CheckFailed(f"{len(bad)} contest(s) with delta != new - old")
    elif name == "note_contains":
        note = payload.get("note") or ""
        if want.lower() not in note.lower():
            raise CheckFailed(f"expected {want!r} in note, got: {note[:160]!r}")
    else:
        raise CheckFailed(f"unknown assertion {name!r}")


# --------------------------------------------------------------------- case runner


async def run_case(case: dict[str, Any], live: bool) -> dict[str, Any]:
    args = dict(case["args"])
    args["response_format"] = "json"

    # Two distinct failure surfaces, and a robust agent meets both:
    # the SDK rejects schema violations by raising, while our own validation and
    # upstream errors come back as an ordinary text response.
    try:
        result = await mcp.call_tool(case["tool"], args)
        text = "".join(block.text for block in result.content if getattr(block, "text", None))
    except Exception as exc:  # noqa: BLE001 - any tool failure is a result to assert on
        text = f"{type(exc).__name__}: {exc}"
        payload: Any | None = None
    else:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None  # tools return a plain sentence on error, by design

    failures: list[str] = []
    for assertion in case.get("assert", []):
        (name, want), = assertion.items()
        try:
            await _check(name, want, payload, text, {"live": live})
        except CheckFailed as exc:
            failures.append(f"{name}: {exc}")

    return {
        "id": case["id"],
        "intent": case["intent"],
        "tool": case["tool"],
        "passed": not failures,
        "failures": failures,
        "preview": text[:200].replace("\n", " "),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="run against the real API")
    parser.add_argument("--case", help="run a single case by id")
    args = parser.parse_args()

    if not args.live:
        client_mod.set_client(_fixture_client())

    cases: list[dict[str, Any]] = []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            cases.extend(yaml.safe_load(fh) or [])
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"no case with id {args.case!r}")
            return 2

    mode = "live" if args.live else "fixtures"
    print(f"running {len(cases)} eval case(s) against {mode}\n")

    results = [await run_case(case, args.live) for case in cases]

    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['id']}")
        for failure in r["failures"]:
            print(f"          {failure}")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{passed}/{total} passed")

    lines = [
        "# Eval report",
        "",
        f"_generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} against {mode}_",
        "",
        f"**{passed}/{total} cases passed**",
        "",
        "| Case | Tool | Result | Intent |",
        "| --- | --- | --- | --- |",
    ]
    for r in results:
        lines.append(
            f"| `{r['id']}` | `{r['tool']}` | {'pass' if r['passed'] else '**FAIL**'} "
            f"| {r['intent']} |"
        )
    failed = [r for r in results if not r["passed"]]
    if failed:
        lines += ["", "## Failures", ""]
        for r in failed:
            lines.append(f"**{r['id']}**")
            lines += [f"- {f}" for f in r["failures"]]
            lines.append("")
    with REPORT.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {REPORT}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
