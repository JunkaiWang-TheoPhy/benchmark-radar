# Search evaluation dataset

`tests/fixtures/search_evaluation.yml` is the versioned regression dataset for local
Catalog retrieval. It tests the ranking as a retrieval component for an agent, not as
a final benchmark recommendation system.

## Dataset and label policy

Version 1 contains 18 short English queries:

- 4 navigational queries for known benchmark names;
- 10 topical discovery queries grounded in normalized Catalog metadata;
- 4 known Catalog-gap queries used to detect newly introduced full lexical matches.

Positive queries list manually reviewed Catalog keys in `relevant_keys`. The labels
are sparse: an unlisted result is **unjudged**, not irrelevant. This matters because
counting every unlisted record as negative would make precision and NDCG look exact
without a completely judged result pool.

Gap queries separately list `expected_partial_keys`. These are reviewed lexical
candidates, not suitable benchmark labels. They ensure that a future all-terms gate
cannot earn a perfect gap score by deleting the evidence an agent should inspect. The
weather-forecasting case is the explicit zero-overlap control and has no expected
partial candidate.

The gap cases do not assert that the wider world lacks the benchmark. They assert
only that the current normalized Catalog has no reviewed full-token match. If a
source refresh introduces one, the failing case requests human or agent review of the
underlying record before changing the label.

## Metrics and protocol

The evaluator reports:

- Hit@5: whether each positive query retrieves at least one labelled record;
- MRR@20: how early the first labelled record appears within the evaluation window;
- macro Recall@20: the mean fraction of sparse positive labels retrieved;
- navigational Hit@1: whether a known-name query leads with a labelled identity;
- Catalog-gap full-match rate at 20: the fraction of gap queries with an unreviewed
  result in the evaluation window whose `missing_tokens` is empty.
- Catalog-gap partial retention at 20: the fraction of reviewed partial lexical
  candidates preserved in the agent's evaluation window.

Run the deterministic local evaluation after generated Catalog data exists:

```bash
python scripts/evaluate_search.py
```

The command exits non-zero when a versioned threshold fails and prints per-query
evidence for review. It is deliberately not part of CI while judgments remain
LLM-assisted and sparsely human-reviewed. Ranking changes must still run the
repository's complete CI sequence; this dataset supplements structural tests rather
than replacing them.

## Current limitation

This is a regression dataset, not a hidden benchmark-quality test set. The queries
were assembled from confirmed user intents and inspected local records, so they are
useful for preventing regressions but insufficient for claiming general search
quality. A later version should add independently authored intents and pooled human
judgments before reporting Precision@K or NDCG.

## Qualitative judge set

`evaluation/search_judge_cases.yml` contains twenty-three additional navigational,
topical, ambiguous, wrapper-language, and out-of-catalog intents. It has no executable thresholds and
is not loaded by product code or CI. A human or LLM reviewer runs every case through
the same `QueryService`, then judges leading candidates, status honesty, and match
evidence using the shared rubric. The ranking implementation must never branch on a
case ID or query string from this file.
