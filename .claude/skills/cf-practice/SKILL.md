---
name: cf-practice
description: >
  Run a targeted Codeforces practice session driven by the practitioner's own weakness
  data, using the codeforces-mcp server. Use whenever someone wants to practise
  competitive programming with intent rather than at random — e.g. "what should I
  practise on Codeforces", "give me a practice set", "I want to get better at dp",
  "build me a ladder", "review my recent contest", "what am I weak at", or "pick
  problems for me". Diagnoses weak tags from submission history, assembles a rating
  ladder of problems the user has not already solved, and closes the loop afterwards by
  checking what actually got solved. Prefer this over suggesting problems from memory:
  problem recall is unreliable and stale, and it cannot know what the user has already
  done.
---

# Codeforces practice sessions

Picking practice problems from memory fails in two ways: recall of specific problem IDs
and ratings is unreliable, and it cannot know what this person has already solved. This
skill routes both questions through real data.

**Requires the `codeforces-mcp` server.** If its tools are unavailable, say so and stop
rather than inventing problem IDs.

## The loop

### 1. Diagnose before prescribing

Never open with problem suggestions. Start with `codeforces_tag_performance`.

```
codeforces_tag_performance(handle=<handle>, min_attempted=5)
```

Read the ranking with judgement, not literally:

- The tool already excludes tags with too few attempts. Do not lower `min_attempted`
  below 3 to make a tag look weak.
- A low solve rate on a tag attempted 40 times is a real gap. A low rate on 5 attempts
  is noise; say so rather than building a plan on it.
- Cross-check `avg_rating_solved`. A 45% solve rate on tags averaging 1600 is a
  different situation from 45% at 900, and the second is the more urgent one.

Report the two or three tags worth working on and *why*, then ask which to take. Do not
assume the weakest tag is the one they want to work on.

### 2. Build a ladder, not a list

```
codeforces_search_problems(
    tags=[<chosen tag>],
    min_rating=<comfort>, max_rating=<comfort + 200>,
    exclude_solved_by=<handle>,
    limit=8,
)
```

Rating band: start at roughly the current rating and extend about 200 above. Below
their rating trains nothing; more than ~300 above turns practice into reading editorials.

`exclude_solved_by` is not optional. Suggesting a problem someone already solved is the
fastest way to lose their trust in the whole session.

Results come back easiest first, which is the order to present them. Give 5–8 problems
with rating and link. Do not paste tags for every problem; they chose the tag.

### 3. Support, do not solve

While they work: hints before solutions, and ask what they have tried first. If they are
stuck on a specific problem, ask which one and talk about the approach — do not open
with code.

### 4. Close the loop

The step that makes this a practice *system* rather than a problem generator. After a
session, or at the start of the next one:

```
codeforces_recent_submissions(handle=<handle>, verdict=WRONG_ANSWER, limit=10)
```

Look for patterns across failures rather than debugging one submission: repeated TLE on
one tag suggests a complexity gap, repeated WA on early tests suggests rushing the read.
Say what the pattern is.

For a longer view, `codeforces_rating_history` shows whether contest results are moving
at all. Be honest when they are flat.

## Reference

- `references/rating-bands.md` — what each band demands, and how to choose a target
- `references/session-shapes.md` — ladder, contest simulation, weakness drill, review

## Judgement notes

- **Diagnose before prescribing.** Suggesting problems before looking at the data is the
  failure mode this skill exists to prevent.
- **Do not over-plan.** A practice session is 5–8 problems, not a twelve-week curriculum
  nobody follows.
- **Say when the data is thin.** Under roughly 50 attempted problems the tag ranking is
  not yet meaningful. Recommend volume across mixed tags instead of a targeted drill.
- **Rating is not the only goal.** If someone is preparing for a specific contest format,
  shape the session around that instead.
