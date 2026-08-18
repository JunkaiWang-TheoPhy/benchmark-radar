# Follow-up crawl prompt — OpenCompass Hub session

Paste this into the session that produced `Crawl Data from OpenCompass Hub Website.zip`.

---

Continue the OpenCompass Hub work. Round 1 produced 461 benchmark cards with validation
PASS. Round 2 is mostly **not** a hub crawl: the hub has already given us nearly all it
has, and the remaining gaps live in the GitHub, Hugging Face, and paper targets the
cards already point at.

## What round 1 already holds, so you do not re-crawl it

Measured fill rates across the 461 records in `benchmarks_full.jsonl`:

| field | fill |
|---|---|
| `card.paper_link` | 447 (96%) |
| `card.github_link` | 428 (92%) |
| `detail.basicInfo.publishOrg` | 393 (85%) |
| `detail.basicInfo.releaseDate` | 401 (86%) |
| `card.official_website_link` | 244 (52%) |
| `detail.basicInfo.downloadUrls` | 241 (52%) |
| `detail.readme` | 461 (100%) |
| `detail.leaderboard` | 94 (20%) |
| `detail.evalFileInfo` | 6 (1%) |

Identity *links* are present at high rates. That is not the same as identity being
solved: a card's `github_link` points at a repo, but nothing in the hub establishes that
the repo covers the same variant, split, or version the card describes. Treat the links as
strong leads to verify in step 3, not as settled facts.

**Do not re-crawl `getDetailV2` for fields you already have.** Where round 2 needs the hub
at all it is only for the three gaps in step 1.

## Step 1 — close the small hub gaps

- Skip the 61 blank `card.creator_info.name` values. `creator_info` is the person who
  uploaded the hub card, which is usually not the benchmark's creator, so resolving those
  names answers no question we have. `publishOrg` plus the paper is the answer to "who
  made it".
- 14 records lack `paper_link`, 33 lack `github_link`, 68 lack `publishOrg`, 60 lack
  `releaseDate`. For these, resolve externally (step 3 rules apply).
- Confirm whether `card.certificate_level` has values beyond the four observed
  (未录入 377, 开源收录 66, 合作共建 10, 官方自建 8), and capture the hub's own published
  definition of each. We need to know what 开源收录 formally certifies before we render
  it as an openness signal.

## Step 2 — parse `detail.readme`, do not re-fetch it

All 461 READMEs are already in the bundle and are the richest unexploited field.
Measured signal: 86 mention a countable size, 97 mention a licence keyword. Extract
into structured form:

- `sizes[]` as `{value, unit, split, measures, evidence_quote}`. Units: `questions |
  tasks | items | images | videos | audio_clips | hours | tokens | repos | episodes`.
  `measures` is `eval_set | train_set | total | unclear` — README numbers routinely
  describe training data, a superset, an earlier version, or a related dataset, and a count
  whose referent is unknown is worse than no count. When the sentence does not say what the
  number counts, `measures` is `unclear`. Never sum splits into one total.
- `license_mention` — the literal string found, plus surrounding sentence. Do not map it
  to an SPDX id from the README alone; step 3 does that from the authoritative source.
- `metric_mention` — the metric name(s) the README states (accuracy, pass@1, F1, Elo,
  BLEU, win rate), plus direction if stated.
- `languages[]`, `splits[]`, `version` if stated.

Every extraction carries the ≤200-character quote it came from. A regex hit with no
readable supporting sentence is not an extraction.

## Step 3 — resolve openness and size from the linked targets

This is the main body of work. For each of the 428 records with a `github_link` and the
241 with `downloadUrls` (330 records mention Hugging Face somewhere), fetch the target:

- `code_license` — from the GitHub licence API (`GET /repos/{owner}/{repo}` →
  `license.spdx_id`). This describes the **repository code**, which for most benchmarks is
  the eval harness, not the data.
- `data_license` — from the HF dataset card YAML `license:` key, the dataset page, or an
  explicit statement about the data. Never inherit it from `code_license`. Eval code is
  routinely Apache-2.0 while the data is CC-BY-NC, and that gap is exactly the thing our
  users are asking about.
- `data_located` — `found | gated | not_found_at_this_location`. `found` needs a concrete
  artifact in view (HF parquet/JSON config, release asset, populated data directory).
  A repo with only eval code is `not_found_at_this_location` — the data may live elsewhere;
  do not report it as unavailable.
- `harness_public` — `true` only when the repo contains a runnable evaluation entry point
  (a scoring script, an OpenCompass/lm-eval config, or a documented `evaluate`/`score`
  command). Name the file you saw. Do not infer it from the repo merely existing.
- `access_gate` — `none | hf_gated | request_form | registration | paywall`.
- `link_status` — `ok | redirect | 404 | 410 | timeout`, per fetched URL.
- `sizes[]` — prefer HF dataset viewer per-split row counts over any README number, and
  carry `measures` as in step 2. Where README and HF disagree, emit both and set
  `size_conflict: true`.

Then apply the openness truth table verbatim. Do not roll up by judgement:

| code public | data_located | data_license | → status |
|---|---|---|---|
| yes | found | permissive or share-alike SPDX | `open` |
| yes | found | non-commercial / no-derivs / custom | `restricted` |
| any | found | none found | `restricted` |
| any | gated | any | `restricted` |
| any | not_found_at_this_location | any | `unknown` |
| any | any, but `link_status` is 404/410/timeout | any | `unknown` |

Emit `openness_basis` naming the row that fired. We expect `unknown` to be the most common
outcome; that is the correct result, not a shortfall.

**Do not treat `public_flag` as openness.** It is `1` on all 461 records and means only
that the card is publicly visible. It carries no information about the dataset and must
not appear in any openness computation. The same applies to `certificate_level`: 开源收录
is a hub curation label with no licence attached, so it may be reported as a hub signal but
never used as a truth-table input.

## Step 4 — normalize the 94 embedded leaderboards

`detail.leaderboard` is present on 94 records as a dict of leaderboard-name → list of
free-form column dicts, with per-benchmark column names (`node(n-f1)`, `chain(e-f1)`,
`overall(n-f1)`, ...) and no shared metric vocabulary. Flatten to one row per
(benchmark, leaderboard, model, column):

```json
{"source_benchmark_id": "...", "leaderboard_name": "TaskBench-Multimedia Tools",
 "model_name": "gpt-4", "organization": "OpenAI", "column": "overall(n-f1)",
 "raw_value": "90.90", "value": 90.90, "value_kind": "number",
 "reported_date": "2023-12-09", "model_url": "...", "model_type": "API", "parameters": "N/A"}
```

**`raw_value` is mandatory and authoritative; `value` may be null.** These cells are not
reliably scores. They include ranks, "N/A", "-", percentages with and without the sign,
counts, and composite strings. `value_kind` is `number | rank | percent | text | missing`,
and you set it from the cell's own form, not from what you assume the column measures.
Coercing everything to a float turns rank columns into scores.

Do **not** guess what a column means. Keep `column` as the source's literal string and add
`metric_interpretation` only where the README or paper states it, with the quote.

Emit `leaderboard_columns_inventory.json` listing every distinct column name, its
frequency, and the distribution of `value_kind` within it. This is a build report for a
human to read once, not product data.

## Step 5 — cross-source identity, for the merge

76 benchmark names in this bundle collide with names in our LLM Stats crawl under a
case- and punctuation-folded normalizer (agieval, bbh, ceval, cmmlu, blink, mmmu,
bigcodebench, arcc, arce, boolq, collie, crag, ...). We will not auto-merge on name.

For each of the 461, emit the identity evidence that lets a human adjudicate:
`paper_id` (`arxiv:NNNN.NNNNN` where available), `repo_id` (`gh:owner/repo`), `dataset_id`
(`hf:owner/name`), and `version_reported` (the version string as the source states it,
verbatim, never parsed out of the name).

A shared `paper_id`, `repo_id`, or `dataset_id` is an anchor. A shared name is not evidence
at all, and neither is a shared organization.

Do **not** emit `aliases[]` derived from paper titles or repo names. That manufactures
generic phrases ("A Benchmark for Multimodal Understanding") and org names as aliases,
which then pollute every future name-based lookup. Aliases only come from a source
explicitly stating "also known as".

Flag `possible_variant: true` where the name differs only by a version or split suffix
(Pro, Mini, v2, Diamond, Verified, -Hard, -Lite). Those are the ones most likely to be
wrongly merged.

## Output

`opencompass_round2.jsonl`, one line per `benchmark_id`, joinable to round 1 by
`benchmark_id`, plus:

- `opencompass_leaderboard_rows.jsonl` (step 4)
- `leaderboard_columns_inventory.json` (step 4, build report)
- `opencompass_round2_validation.json` — per-field fill counts over 461, count by
  `openness.status` and by `openness_basis` row, count of `size_conflict`, count of
  `measures: unclear`, count of `access_gate` by value, count of `link_status` by value,
  and the licence distribution split by `code_license` vs `data_license`

## Rules

- `unknown` is a correct answer. Report fill rates honestly; do not pad them.
- Machine-read fields carry `evidence_url` plus a `locator` (the API field or JSON pointer
  you read). Judged fields (size extraction, licence interpretation, identity claims) carry
  `evidence_url` plus an `evidence_quote` of ≤200 characters. A regex hit with no readable
  supporting sentence is not an extraction.
- Repo licence and dataset licence stay separate fields, always.
- Apply the openness truth table as written. Do not roll up by judgement.
- Keep raw responses for everything, as round 1 did, and keep the SHA256SUMS discipline.
- Unauthenticated only. Do not touch submission, edit, vote, or evaluation-task endpoints.
  Respect GitHub and Hugging Face rate limits; use conditional requests and back off.
