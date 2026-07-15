# Codeforces rating bands

Rough guide for choosing a practice target. Bands describe what a problem *demands*,
not what a person is worth.

| Band | Typically demands |
|---|---|
| 800–1000 | Direct implementation, one observation, no real algorithm |
| 1100–1300 | Sorting, greedy, prefix sums, simple two-pointer; one non-obvious step |
| 1400–1600 | Standard algorithms with a twist: binary search on answer, basic dp, graph traversal |
| 1700–1900 | Two techniques combined, or a dp whose state is the actual difficulty |
| 2000–2200 | Non-obvious modelling, heavier data structures, harder correctness proofs |
| 2300+ | Specialist topics and multi-step constructions |

## Choosing the band

Start at the current rating and extend roughly 200 above. Practising below current
rating builds speed but not range; more than about 300 above turns into reading
editorials, which is a different activity and should be named as such rather than
disguised as practice.

Solve rate is the signal to adjust on. Comfortably above ~70% in a band means move up.
Below ~30% means drop back — struggling is the point, but only when there is a path
through.

## Rating is noisy

Codeforces problem ratings are derived from contest performance, so a problem can be
rated low simply because it appeared late in a contest few people reached. Treat the
number as an estimate with real error bars. If a "1300" feels like a 1600, that happens;
do not conclude the user has regressed.

## Reading a plateau

A flat rating across many contests usually means practice has drifted toward comfortable
problems. Check `codeforces_tag_performance`: if the tags with the *most* attempts also
have the *highest* solve rates, that is the plateau, and the fix is deliberately
uncomfortable problems in a weak tag rather than more volume.
