# Audit: crawled aggregator catalogs vs. issue #240

Audited 2026-08-17 against the two zips in `../dev/` and against `main` at 1de0a23.

## 1. What is actually in the zips

### `How to Crawl Data from llm-stats.zip`

- 687 catalog benchmarks, 5,544 score rows, 681 detail responses (6 community IDs 404'd).
- Source is the ZeroEval public API, not llm-stats HTML:
  - catalog: `https://api.zeroeval.com/leaderboard/benchmarks`
  - detail: `https://api.zeroeval.com/leaderboard/benchmarks/{id}?top_n=500`
- **The raw API payload has exactly 8 keys**: `benchmark_id, benchmark_name,
  benchmark_description, max_score, categories, modality, total_models, entries`.
  There is no paper, no repo, no licence, no size, no author, no institution.
  The existing crawl already extracted 100% of the available benchmark-level fields.
  A "deeper API crawl" of llm-stats would return nothing new.
- Per-score fields are rich (rank, score, normalized_score, org, price, speed,
  context window, release date, param count) but carry **no protocol**: no shots,
  no harness, no tool access, no attempts, no eval date.
- `verified` is `False` on all 687 benchmarks and all 5,544 scores. One value,
  zero information. 5,410/5,544 are `self_reported=True`.
- 5 rows exceed `max_score`. `vending-bench-2` declares `max_score=1.0` and carries
  scores of 8017.59, 5634.41, 5478.16, 3635.0. `max_score` is not a ceiling and
  must never be used as a saturation denominator.
- 8 benchmarks have zero score rows (6 community UUIDs + `cvtg-2k` + `longtext-bench`).

### `Crawl Data from OpenCompass Hub Website.zip`

461 cards, validation PASS, no duplicate IDs or names. Field fill rates:

| field | fill | field | fill |
|---|---|---|---|
| `card.paper_link` | 447/461 (96%) | `detail.basicInfo.publishOrg` | 393/461 (85%) |
| `card.github_link` | 428/461 (92%) | `detail.basicInfo.releaseDate` | 401/461 (86%) |
| `card.official_website_link` | 244/461 (52%) | `detail.basicInfo.downloadUrls` | 241/461 (52%) |
| `card.creator_info.name` | 400/461 (86%) | `detail.readme` | 461/461 (100%) |
| `detail.basicInfo.desc.en-US` | 458/461 (99%) | `detail.leaderboard` | 94/461 (20%) |
| `detail.basicInfo.dimensions` | 461/461 (100%) | `detail.evalFileInfo` | 6/461 (1%) |

- `certificate_level`: 未录入 377, 开源收录 66, 合作共建 10, 官方自建 8.
- `public_flag` is `1` on all 461. Like llm-stats `verified`, one value, zero information.
  It means the card is publicly visible, not that the dataset is open.
- 408 records link to github.com; 330 mention huggingface somewhere.
- README free text mentions a countable size in 86/461 and a licence keyword in 97/461.
- 94 records carry an embedded `detail.leaderboard`: a dict of leaderboard-name →
  free-form column dicts (e.g. `node(n-f1)`, `chain(e-f1)`), per-leaderboard schema,
  no shared metric vocabulary.

## 2. Corrections to issue #240

1. **`leaderboard_snapshots` exists, but not on `main`.** It lives on
   `origin/legacy/leaderboard-snapshots` (5 commits, 8,011 insertions):
   `src/benchmark_radar/leaderboard_snapshots.py` (474 lines),
   `data/leaderboard_snapshots.yml`, and the three crawl CSVs checked in under
   `data/leaderboard_snapshots/`. The issue's claims are accurate **relative to that
   branch**. On `main` the key is absent from `site/data/radar.json` and grepping
   `src/ site/ scripts/ tests/ data/ config.yml` returns nothing.

   So the merge is not unbuilt, it is unlanded. That branch is the starting point, not a
   blank page, and the plan below is written to extend it rather than replace it.
2. **`tests/test_leaderboard_snapshots.py` exists** on the same branch (387 lines).
   Acceptance criterion 4 is satisfiable; the file just is not on `main`. `main` has
   `tests/test_leaderboard_workbench.py`, which is a different thing.
3. **`radar.json` is 22 MB**, not 33 MB. The argument against inflating it still holds.
4. **The unmatched counts are normalizer-dependent and should not be an AC.**
   Re-running the join against the 79 registry benchmarks (id + name + aliases,
   case/punctuation-folded) gives LLM Stats 93 rows → 72 canonical, 594 unmatched;
   OpenCompass 19 → 19, 442 unmatched. The earlier session reported 90 → 65 / 597 and
   19 → 19 / 442. OpenCompass is stable; llm-stats moves with the normalizer.
   That instability is the argument for a checked-in identity file rather than a
   number in an acceptance criterion.
5. **The navigator claim is correct.** `site/assets/app.js:3098` filters to
   `card_count > 0` then `.slice(0, stageId === "emerging" ? 4 : 3)` over 4 stages,
   so at most 13 buttons. The registry itself only holds 79 benchmarks.
6. **The two sources are not symmetric, and the issue treats them as if they were.**
   llm-stats has scores and no identity fields at all. OpenCompass has identity
   *links* (paper 96%, repo 92%, org 85%, release 86%) and almost no scores.
   Merging them as two interchangeable "aggregator leaderboard snapshots" throws
   away the thing that actually answers the stated user question. OpenCompass
   should be the identity backbone; llm-stats should be the score backbone.

   With one caveat: `publishOrg` identifies whoever published the hub card, which
   is frequently not the benchmark's creator, and a `github_link` does not
   establish that the repo covers the same variant or split the card describes.
   These are strong leads to verify, not settled attributions. Rendering
   `publishOrg` as "who made it" would credit OpenCompass for MMMU.
7. **76 benchmark names appear in both crawls** under a folded normalizer
   (agieval, bbh, ceval, cmmlu, blink, mmmu, bigcodebench, ...). Auto-merging by name
   across sources is exactly where a wrong join gets baked in silently.

## 2b. What the legacy branch already gives us

`origin/legacy/leaderboard-snapshots` is further along than the issue text suggests, and
it removes most of the work I had scoped as "layer 1":

- **The crawl CSVs are already checked in** under `data/leaderboard_snapshots/`:
  llm-stats benchmarks (687) and scores (5,544), and the OpenCompass catalog (461 records;
  the file is 604 lines because descriptions wrap). Verified against the zips: the
  OpenCompass flattening carries `paper_url` 447, `github_url` 428,
  `official_website_url` 244, `creator_name` 400, `detail_download_urls` 241,
  `detail_description_en` 458, `dimensions` and `certificate_level` 461. Identical fill
  rates to the raw bundle, so nothing was lost in the flattening.
- **`data/leaderboard_snapshots.yml` is a real integrity contract**, not a manifest: it
  declares `benchmark_count` and `score_row_count` per snapshot and the loader refuses to
  publish a file whose counts drift, plus an explicit `columns` map so the loader never
  guesses which header means what. That is the "strict loader" requirement already met.
- **The honesty framing is already written down** in that file's header, including the
  rule that this layer never joins to `benchmark_scores.yml` because a leaderboard row
  carries no protocol, and the commit-don't-refetch rationale for snapshot immutability.

What that branch does *not* do is what the discussion actually cares about: it publishes
only canonical-matched rows, counts the unmatched instead of addressing them, and drops
the OpenCompass identity columns downstream even though the CSV carries them. It also has
no openness, size, or search surface.

So the revision to my own earlier framing: this is not "build the ingest, then add the
view". The ingest exists. The work is (a) stop discarding unmatched rows and OpenCompass
identity columns on the way to the site, (b) add openness and size, which no crawl has yet,
and (c) build the search surface. Rebasing that branch onto current `main` is the first
step, not writing a new loader.

## 3. Source overlap

Checked three ways, because "should we crawl both?" turns on which overlap you mean.

**Crawl-to-crawl coverage, small.** After case- and punctuation-folding:

| | count |
|---|---|
| llm-stats distinct names | 682 |
| OpenCompass distinct names | 460 |
| in both | 76 |
| llm-stats only | 606 |
| OpenCompass only | 384 |
| union | 1,066 |

**llm-stats upstream vs. our own curated layer, heavy.** 5,410 of 5,544 llm-stats scores
are `self_reported=True` and every organization is a model vendor (Qwen 1,652, OpenAI 662,
Google 611, Anthropic 292, DeepSeek 276, ...). Those are vendor-announced numbers, the same
upstream `model_cards.yml` and `benchmark_scores.yml` already read from primary documents
with protocol attached and a join rule enforced. 1,944 of the 5,544 rows come from the 7
organizations the curated progression already tracks. llm-stats is a lower-fidelity copy of
a stream we already collect at higher fidelity.

**Score layer between the crawls, different eras, not redundant.** OpenCompass's 94
embedded leaderboards hold 5,708 rows, comparable in volume to llm-stats' 5,544, but they
are ChatGLM3-6B, Baichuan2-13B, Qwen-72B-Chat and GPT-4: a 2023-24 snapshot. llm-stats is
4,608 of 5,544 rows from 2025-26 models across 339 distinct models. Only 27 of the 94
OpenCompass leaderboards are also scored by llm-stats. llm-stats is the only frontier-model
score source in either crawl.

**Where llm-stats value sits.** 148 benchmarks hold 75% of all score rows; 343 benchmarks
(half the catalog) hold 8%. The 606 llm-stats-only names have a median of 2 score rows. Of
the 148 dense ones, 55 are already in the curated 79-benchmark registry and 37 are in the
OpenCompass crawl, leaving **74** that are both score-dense and unmatched anywhere.

## 4. Sequencing decision

1. **OpenCompass round 2, as briefed.** Identity 90% → 100%, plus openness and size
   resolved from the GitHub and Hugging Face targets the cards already point at. Mostly
   parsing what is already in the bundle rather than crawling. This is the identity backbone.
2. **llm-stats: ingest, do not crawl.** The API is exhausted and cannot yield identity at
   all. Reshape the existing 5,544 rows into the score-observation schema and attach them
   through `identity.yml`. llm-stats-only benchmarks will show a name, a description, a
   score table and `unknown` everywhere else, which is honest and is what the schema was
   built to hold.
3. **Deferred:** external identity resolution for llm-stats, scoped to the 74 dense-and-
   unmatched benchmarks if we ever want it. Not 687. A 687-row fuzzy-matching campaign
   aimed at a long tail of one-score-row entries is the highest-risk, lowest-value work in
   the plan.

The earlier draft listed "official identity: paper, GitHub, dataset, project URL,
release/version" as priority 1 for both sources. That splits: for OpenCompass it is ~90%
already present and needs parsing; for llm-stats it is 0% present and unobtainable from the
source. Openness and size will be `unknown` for most rows after this round, and the schema
has to say so rather than defaulting to a boolean.
