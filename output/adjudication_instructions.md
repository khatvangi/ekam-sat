# adjudication instructions

## purpose

this is a stratified random sample of 100 echoes from the v3 scan (43,303 total).
the goal is to estimate the pipeline's precision at each strength level.

## sample composition

| strength | count | population | notes |
|----------|-------|------------|-------|
| >= 3 (high) | 2 | 2 | all available (only 2 exist) |
| 2 (medium) | 49 | 2,350 | random sample, seed=42 |
| 1 (low) | 49 | 40,951 | random sample, seed=42 |

rows are shuffled to avoid order bias during review.

## how to review

open `adjudication_sample.csv`. for each row:

1. read the `text` column (the actual verse in Harvard-Kyoto transliteration)
2. check `matched_terms` — which terms triggered the match
3. check `node_name` — the BG doctrine this echo is claimed to support
4. assign one of three judgments in the `judgment` column:

| judgment | meaning |
|----------|---------|
| `TRUE_ECHO` | the verse genuinely teaches or illustrates this doctrine |
| `PARTIAL_ECHO` | the verse is thematically related but does not teach the same point |
| `FALSE_POSITIVE` | term overlap only — the verse is unrelated in meaning |

## guidelines

- a verse about a warrior's `krodha` (anger) in battle context is a FALSE_POSITIVE for a node about `krodha` as a spiritual obstacle, unless the verse explicitly frames anger as something to be overcome
- common Sanskrit words (`nitya`, `aja`, `dharma`) will produce many false positives at strength 1 — this is expected
- when uncertain between TRUE_ECHO and PARTIAL_ECHO, prefer PARTIAL_ECHO
- when uncertain between PARTIAL_ECHO and FALSE_POSITIVE, consider whether the verse would make sense as a cross-reference in commentary

## after review

precision at each strength level = (TRUE_ECHO + PARTIAL_ECHO) / total in that stratum.
use this to calibrate confidence intervals for the full 43,303 echo count.

seed used: 42 (for reproducibility).
