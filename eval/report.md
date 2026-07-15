# Eval report

_generated 2026-08-23T16:38:48+00:00 against fixtures_

**12/12 cases passed**

| Case | Tool | Result | Intent |
| --- | --- | --- | --- |
| `unsolved-dp-ladder` | `codeforces_search_problems` | pass | Find 5 dp problems rated 1300-1500 that 3.141f has not solved yet |
| `weakest-tags` | `codeforces_tag_performance` | pass | Which Codeforces topics is 3.141f weakest at? |
| `hard-unsolved-graphs` | `codeforces_search_problems` | pass | Give me graph problems above 1600 I have not solved |
| `recent-failures` | `codeforces_recent_submissions` | pass | Show my recent wrong answers so I can review them |
| `profile-lookup` | `codeforces_user_profile` | pass | What is 3.141f's current and peak rating? |
| `rating-trajectory` | `codeforces_rating_history` | pass | How has 3.141f's rating moved across contests? |
| `tags-match-all-is-strict` | `codeforces_search_problems` | pass | Problems that are both dp AND greedy, not either |
| `typo-tag-is-recoverable` | `codeforces_search_problems` | pass | Agent guesses 'dynamic programming' instead of the real tag 'dp' |
| `unknown-verdict-lists-real-ones` | `codeforces_recent_submissions` | pass | Agent filters on a verdict that does not exist |
| `inverted-rating-band-rejected` | `codeforces_search_problems` | pass | Agent swaps the bounds |
| `unknown-handle-is-actionable` | `codeforces_user_profile` | pass | Agent mistypes a handle |
| `limit_out_of_range_rejected` | `codeforces_search_problems` | pass | Agent asks for 5000 problems |
