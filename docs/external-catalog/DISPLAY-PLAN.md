# Display plan

How the merged catalog reaches the reader. Deliberately small: this is a search box, a
result row, and a detail panel over data that already exists. If a step here starts
looking like a framework, cut it.

Prerequisite state: `benchmark-radar normalize-external` emits the llm-stats layer today
(687 records, 5,544 observations). OpenCompass round 2 is still running and supplies the
identity column. See `AUDIT.md` §4 for why the two sources are not interchangeable.

## What the reader is trying to do

From #227 and the #240 discussion: facing hundreds of benchmarks, find the relevant one,
then in a few seconds judge **who made it, whether it is open, how large it is, and what
scores exist**.

Today `renderBenchmarkNavigator` (`site/assets/app.js:3098`) filters to entries with
`card_count > 0`, then `.slice(0, stageId === "emerging" ? 4 : 3)` across four stages. At
most 13 benchmarks are ever selectable, out of a 79-benchmark registry and ~1,066 distinct
crawled benchmarks. That is the gap.

## Step 1: build artifacts

Extend `normalize-external` to emit two more things from data it already has in memory.

`site/data/benchmark-index.json`, one entry per source record, not per merged group.
Merging happens at render time from `identity.yml`, so a bad group is a display bug rather
than baked-in data loss.

```json
{"slug":"llm-stats-gpqa-diamond","key":"llm-stats:gpqa-diamond","name":"GPQA",
 "source":"llm_stats","group_id":null,"canonical_id":null,"publisher":null,
 "released":null,"openness":"unknown","modality":"text","score_count":239,
 "has_paper":false,"has_repo":false}
```

At ~180 bytes across ~1,148 records this is roughly 200 KB, small enough to load up front
and search client-side with no backend.

`site/data/benchmarks/<slug>.json`, one shard per record: the full source record, its
identity siblings, and its score rows **already partitioned by source in the file**:

```json
{"record": {...}, "siblings": [...], "scores_by_source": {"llm_stats": {"series": {...}, "rows": [...]}}}
```

The partition lives in the payload rather than in render code. A flat array with a
`source` field on each row is one `.sort()` away from a cross-source ranking; a keyed
object is not sortable into one without deliberately writing the merge.

Both are gitignored like `radar.json` and the existing `leaderboard.*` exports, per the
policy already stated in `.gitignore`. `data/external/` is already covered.

## Step 2: search surface

Add a search input above the existing shortlist in the leaderboard view. The stage-grouped
shortlist stays exactly as it is; search is the additive "choose anyone" path, not a
replacement. Editors curate the shortlist and that curation is worth keeping.

- Bind to `state.lq`, which already exists and is already serialized by `writeUrl`
  (`app.js:983`). No new URL parameter.
- Match on name and aliases, case and punctuation folded, prefix matches ranked above
  substring matches. Records already in the curated registry rank above crawled-only ones,
  because a curated record can answer more of the reader's four questions.
- Cap the rendered list at 50 with a count of what was hidden. Do not paginate.

No fuzzy matching library. 1,148 records is small enough that a filter over an array is
instant, and fuzzy matching on benchmark names is how MMLU-Pro and MMLU get conflated.

## Step 3: result row

`name · publisher · release year · source badges · openness chip · score-row count`

That is the STRUCTURE.md list and it holds up: it is exactly the four questions plus
enough to disambiguate. One revision, stated rather than made silently: **score-row count
is a count and must never be rendered as a quality signal.** 239 rows for GPQA means
llm-stats collected 239 numbers, not that GPQA is 239 times better attested than a
benchmark with 2 rows. Label it "239 reported scores", not a bare number.

The openness chip has three states, `open` / `restricted` / `unknown`, and `unknown` is
expected to be the most common. It renders as a neutral chip reading "openness not
established", never as a warning colour. The reader is being told what we know, not
that something is wrong with the benchmark.

## Step 4: detail panel

`renderAdoptionFrontier` (`app.js:4440`) already owns the per-benchmark workbench. Extend
it rather than adding a second panel.

Order, top to bottom:

1. **Identity block.** Name and aliases, description, publisher with its role, artifact
   links (paper / repo / dataset / site).
2. **Openness and size.** Status with its evidence link, licence split into code and data,
   sizes with units and splits.
3. **Scores**, one table per source under its own heading, each labelled with what the
   source actually recorded (for llm-stats: "self-reported, no protocol recorded").
4. **Adoption chart**, unchanged, for canonical benchmarks only.

Fields with no data render an explicit **"not established"**, not a hidden row. This is
the one visual decision worth being firm about. Hiding an empty field reads as "not
applicable"; the reader's question is precisely whether these things are known, and today
the answer is usually no. A benchmark page that honestly says "publisher not established,
openness not established, size not established, 239 reported scores with no protocol" has
answered the reader's question. One that shows only the score table has dodged it.

For a benchmark in both layers, the curated adoption chart and the crawled tables appear
in the same panel under separate headings and are never interleaved.

## Step 5: collapse defaults

Per #240: "Benchmarks by model card adoption", "Model cards in the registry", and "What the
two layers say - Stated findings" all default collapsed but **visible**. The findings panel
is currently hidden entirely when empty; collapsed-by-default means present and closed when
findings exist. Use the existing `<details>` pattern already in `index.html`.

## Step 6: URL state

`state.lfrontier` currently holds a canonical `benchmark_id` (`app.js:1024`). Widen it to
hold a slug, and resolve in this order: exact slug, then canonical id (so existing shared
links keep working), then nothing.

This is what makes "unmatched benchmarks are addressable, not merely counted" true. Today
594 llm-stats benchmarks have no URL at all. After this, `?view=leaderboard&lfrontier=llm-stats-vending-bench-2`
resolves.

Keep the existing `lfrontierExplicit` behaviour: an auto-picked default stays out of the
URL, only a reader's choice is serialized.

## Step 7: loading

- Index fetched once when the leaderboard view first renders, cached on `state`.
- Shard fetched on selection, cached in a `Map` keyed by slug. Never evicted; the payloads
  are small and a session will open a handful.
- A failed shard fetch renders "could not load details for this benchmark" in the panel and
  leaves the index row intact. It does not clear the selection or throw into the router.
- No prefetch, no service worker, no bundling. If the panel feels slow with a real shard,
  measure before adding anything.

## Where the honesty rules are enforced

Each of these is a build-time or payload-shape property, not a request to the renderer.
This is the part that most needs to survive implementation.

| Rule | Enforced by |
|---|---|
| No cross-source ranking | `scores_by_source` is a keyed object in the shard, so there is no flat array to sort |
| Null protocol never joins | `comparable_group` is `null` on all 5,544 rows; render code only draws a line within a non-null group, so the branch is never taken |
| No percentage bars | `display_scale` is `null` on all 687 series; the bar component takes a scale and returns nothing without one |
| Saturation stays editorial | Never computed from crawled scores. It remains the per-benchmark `caveat` in `model_cards.yml`, per the header of `data/benchmark_scores.yml` |
| Third-party HTML is escaped | Descriptions and README excerpts go through `element({text})`, never `innerHTML` |

The first three are already pinned at 100% by `tests/test_external_catalog.py`. The render
side needs its own tests, below.

## Tests

Following `tests/test_site.py` and `tests/test_leaderboard_workbench.py`:

- The index contains every source record, including the 8 with zero scores.
- Selecting a crawled-only slug renders the detail panel with its score table.
- A record with no publisher renders "not established", and that string is present in the
  DOM rather than the row being absent.
- No rendered table contains rows from two sources.
- No percentage or `%` is rendered for a series whose `display_scale` is null.
- The three sections are present and closed on first load.
- A shared `?lfrontier=<canonical_id>` link still resolves after the widening.

## Sequence and cut line

Ship: steps 1, 2, 3, 6, 7, and the identity/scores parts of 4.

Defer: step 5 (collapse defaults, independent and can land separately), the adoption-chart
integration in step 4 for benchmarks in both layers, and any filtering beyond text search.

**Do not demo before OpenCompass lands.** With only llm-stats loaded, every record shows
"publisher not established, openness not established, size not established". That is
correct behaviour and terrible evidence. Slimshilin and alina-lllu were asked what minimum
information they need to decide whether to keep reading; showing them 687 benchmarks of
unknowns answers that question in the worst possible way and would reasonably read as the
whole direction being wrong. llm-stats is the score column. OpenCompass is the identity
column. The demo needs both.

## Disagreements with issue #240

- The issue says the payload "is already in `site/data/radar.json` (`leaderboard_snapshots`
  key, 2512 matched entries)". It is not, on `main`. That work is preserved on the tag
  `archive/leaderboard-snapshots-2026-08-17`. See `AUDIT.md` §1-2.
- The issue proposes putting the merged data into `radar.json`. This plan keeps it in a
  separate index plus shards. `radar.json` is 22 MB already and the search index needs to
  load before the reader types, while shards must not.
- The issue's acceptance criterion 4 names `tests/test_leaderboard_snapshots.py`. Replace
  with `tests/test_external_catalog.py` plus the render tests above.
