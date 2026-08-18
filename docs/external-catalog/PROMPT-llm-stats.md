# LLM Stats session — what to send (very little)

**Short answer: do not re-run the llm-stats session on a big brief.** Almost none of the
remaining llm-stats work is crawl work, so a long prompt was the wrong instrument. Send the
three-sentence ask in "A1" below, or send nothing at all; the rest is a script in this repo.

## Why the big brief was cut

- **The API is exhausted.** The per-benchmark payload at
  `https://api.zeroeval.com/leaderboard/benchmarks/{id}?top_n=500` has exactly eight keys:
  `benchmark_id, benchmark_name, benchmark_description, max_score, categories, modality,
  total_models, entries`. No author, institution, paper, repo, licence, size or version
  field exists anywhere in it. Round 1 already extracted all eight.
- **The data is already checked in.** `origin/legacy/leaderboard-snapshots` carries
  `data/leaderboard_snapshots/llm_stats_benchmarks_2026-08-17.csv` (687) and
  `llm_stats_benchmark_scores_2026-08-17.csv` (5,544), with a loader that already validates
  the row counts. Reshaping those into our schema is a local transform, not an agent task.
- **The unique long tail is thin.** The 606 names present in llm-stats and absent from the
  OpenCompass crawl have a **median of 2 score rows**. Half the catalog (343 benchmarks)
  holds 8% of all rows, while 148 benchmarks hold 75%. Of those 148, 55 are already in the
  curated registry and 37 are in the OpenCompass crawl, leaving 74 that are both
  score-dense and unmatched.
- **Resolving identity for 687 benchmarks is fuzzy matching at scale**, which is where
  confident wrong attributions get manufactured. Aimed at a one-score-row long tail, it is
  the highest-risk lowest-value work available.

llm-stats is our **score layer** and it is the only frontier-model score source in either
crawl (4,608 of 5,544 rows are 2025-26 models; the OpenCompass embedded leaderboards are
2023-24 era). It is not going to be our identity layer.

## A1 — the only thing worth sending to that session

> One small follow-up, no bulk crawling. Fetch a handful of
> `https://llm-stats.com/benchmarks/{benchmark_id}` pages (`gpqa-diamond`,
> `swe-bench-verified`, `vending-bench-2`, `aa-briefcase`) plus one community-ID page, and
> tell me whether the rendered page or its embedded JSON payload (`__NEXT_DATA__`,
> `self.__next_f`, or equivalent) carries any field the leaderboard API does not: paper
> link, repo link, dataset link, author, institution, version, licence, size, methodology.
> Report what you find and stop there. Do not crawl the full catalogue on the strength of
> it. "The pages carry nothing beyond the API" is a useful answer, not a failure.

That is the whole ask. It settles permanently whether llm-stats identity is obtainable, and
costs five page fetches.

## A2 — repo work, not session work

Do these in `benchmark-radar` against the checked-in CSVs:

1. **Normalize** the 687 benchmarks and 5,544 score rows into `source_records.jsonl`,
   `score_series.jsonl` and `score_observations.jsonl` per `STRUCTURE.md`. Key points:
   `publisher`, `artifacts`, `sizes: []`, `openness: unknown` and `released: null` are the
   **correct** values for llm-stats records and must be emitted as such; `obs_id` must be
   unique and stable so a re-crawl cannot silently duplicate 5,544 rows;
   `comparable_group` is `null` on every row; the crawl timestamp is named `crawled_at`,
   never `observed_at`; drop the `verified` column, which is `False` on all 5,544 rows.
2. **Record the two known defects** rather than papering over them. Eight benchmarks have
   zero score rows (six `community:*` UUIDs plus `cvtg-2k` and `longtext-bench`). Five rows
   exceed `max_score`: `frontier-swe-impl` (3.4 vs 1.0) and four `vending-bench-2` rows (up
   to 8017.59 vs 1.0). Emit `declared_max`, `observed_max` and `max_score_contradicted`,
   which are mechanically checkable, and no `max_score_trustworthy` judgement, which would
   launder a model opinion into a fact. Establishing the true metric and bounds for those
   two benchmarks needs two paper lookups a human can do in ten minutes.

---

# Part B — DEFERRED. Do not start unless explicitly asked.

Kept here so the reasoning is not lost. If we ever run this, it is scoped to the **74
benchmarks that are both score-dense (≥10 score rows) and unmatched** in the registry and
in the OpenCompass crawl — not 687. We will supply that list.

### B1 — external identity resolution

For each of the 74 benchmarks in the scoped list, resolve identity from outside llm-stats using the name
and the `description` field already in `benchmarks.csv`. For each benchmark produce:

- `paper_url` — arXiv/ACL/OpenReview/DOI, plus `paper_title` and `paper_year`
- `repo_url` — the canonical GitHub/GitLab repo for the benchmark itself
- `dataset_url` — Hugging Face dataset, Zenodo, or direct download
- `site_url` — project or leaderboard homepage
- `publisher` — `{name, role, evidence_url}` where role is `paper_org | maintainer`.
  The organization behind the benchmark, not a full author list: "who made it" is answered
  by an org plus a paper link, and hundreds of author-affiliation assertions are hundreds
  of chances to be wrong for no added answer.
- `dates` — not one "release date". Paper submission, repo creation, and dataset
  publication routinely differ by months and there is no authority that reconciles them.
  Emit `{paper_first_version, repo_created, dataset_published}`, each ISO 8601 or null,
  each with its own `evidence_url`. The site picks a display date; you do not.
- `version_reported` — the version string **as the source states it**, verbatim, or null.
  Do not parse a version out of the name. `Diamond` is a split, `Verified` is a filtered
  subset, `Pro` may be marketing, `v5` may be a harness version. Guessing which of those a
  suffix means is how two different instruments get merged.

**Two-anchor rule for identity. This is the hard gate.** A match is only written into
the output when you have **two independent anchors** agreeing:

- the paper explicitly names the benchmark AND the repo README self-identifies with that
  same name, or
- the repo links the paper (or vice versa) AND the name matches, or
- the HF dataset card names the paper and the benchmark.

A fetched quote proves only that some page contains some words. It does not prove the page
is about *this* benchmark. One anchor is not enough: "a page exists that mentions this
string" is exactly the evidence shape that produces confident wrong matches for acronyms,
renamed benchmarks, and generic names.

Anything with one anchor or zero goes into `candidate_matches[]` with the anchors you did
find and `resolution_status: "needs_review"`. It is not written into the resolved fields.
We would rather review 300 candidates than publish 300 wrong attributions, because a
wrong attribution is invisible to a reader and an empty field is not.

Every populated field also carries `evidence_url` plus, for anything you *judged* rather
than read from a structured API field, an `evidence_quote` of ≤200 characters.

A small number of round-1 descriptions are themselves disclaimers: 4 are worded as
"No official academic documentation found for this benchmark" or similar (see `aa-index`),
6 are empty, and 45 are under 80 characters.

A disclaimer means **the aggregator did not find a source**. It is not evidence that no
source exists, and there is no `no_source_exists` status for you to write. Search normally;
if you also find nothing, the answer is `not_found`, same as everywhere else.

For the empty and short descriptions: search them, but hold the two-anchor rule harder,
not softer. Least evidence is where fuzzy matching is most likely to invent a match, so
expect most of these to land in `candidate_matches[]`. Do not treat a thin description as
licence to accept a weaker anchor.

### B2 — openness and size, for resolved benchmarks only

Where B1 produced a `repo_url` or `dataset_url`, fetch it and extract:

- `code_license` — SPDX id from the GitHub licence API. Describes the **repository code**,
  which for most benchmarks is the eval harness, not the data.
- `data_license` — SPDX id from the HF dataset card YAML, the dataset page, or an explicit
  statement about the data. Never inherit it from `code_license`; eval code is routinely
  Apache-2.0 while the data is CC-BY-NC, and that gap is the thing users are asking about.
  A file named LICENSE whose contents you did not parse is `null` with
  `license_evidence: "file_present_unparsed"`.
- `data_located` — `found | gated | not_found_at_this_location`. `found` needs a concrete
  artifact in view (HF parquet/JSON config, a release asset, a populated data directory).
  A repo with only eval code is `not_found_at_this_location`, **not** "the data is
  unavailable" — the data may live somewhere you did not look, and a `false` here would be
  read downstream as "closed".
- `harness_public` — is the evaluation code itself public and in that repo
- `sizes[]` — `{value, unit, split, measures, evidence_url}`. Units: `questions | tasks |
  items | images | videos | audio_clips | hours | tokens | repos | episodes`. `measures` is
  `eval_set | train_set | total | unclear` — a count whose referent is unknown is worse
  than no count. Prefer HF dataset viewer row counts (exact, per split) over a number in a
  README abstract. If both exist and disagree, emit both rows and set `size_conflict: true`.
  Never sum across splits into a single total.

Then apply the openness truth table from `STRUCTURE.md` verbatim; do not roll up by
judgement. `unknown` is expected to be the most common outcome.

