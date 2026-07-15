# Session shapes

Pick one deliberately. Mixing them in a single sitting produces a session that
accomplishes none of them.

## Ladder — building range in one topic

5–8 problems, one tag, ascending rating across roughly a 200-point band. Best when tag
performance shows a clear single weakness.

Present easiest first, which is the order `codeforces_search_problems` already returns.
If the user wants them blind, withhold the ratings — knowing a problem is rated 1600
changes how long people persist before giving up.

## Contest simulation — practising under pressure

3–4 problems, mixed tags, ascending difficulty, solved in one timed block with no hints.
Best in the week before an actual contest.

Build it with `codeforces_search_problems` and no tag filter, spanning current rating to
about +300. Set the time expectation up front and then stay quiet. Do the review
afterwards, not mid-session — interrupting defeats the purpose.

## Weakness drill — one technique, repeated

4–6 problems in the same tag at nearly the same rating, deliberately narrow. Best when
the failure is a specific technique rather than general range.

Use a tight band, roughly 100 points. The repetition is the point: the same idea seen
from several angles is what makes it stick.

## Review — learning from failures already made

No new problems at all. Pull `codeforces_recent_submissions` with `verdict=WRONG_ANSWER`
or `TIME_LIMIT_EXCEEDED` and work through what went wrong.

The most valuable session type and the one people skip. Look for patterns across
submissions rather than debugging each in isolation:

- Repeated TLE within one tag → a complexity gap, not a coding bug
- WA on tests 1–3 → misread statements; slow down on the read
- Many attempts on a single problem → the approach was wrong, and persistence made it worse
- Failures clustered at one rating → that is the current ceiling, and it is where to work
