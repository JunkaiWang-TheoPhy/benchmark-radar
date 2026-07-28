# Benchmark Radar

An evidence-first daily radar for newly released AI benchmarks, evaluation methods,
datasets, leaderboards, and data-quality work.

Every day, GitHub Actions queries primary or structured sources, deduplicates records,
classifies them with a transparent taxonomy, ranks them using explainable signals, and
publishes a GitHub Issue and a
[cumulative dashboard](https://ktwu01.github.io/benchmark-radar/). It is inspired by
[agents-radar](https://github.com/duanyytop/agents-radar), with sources and scoring
redesigned for benchmark and AI-data research.

## What it tracks

- New AI/LLM benchmarks and challenge sets
- Evaluation frameworks, judge models, safety/capability evals, and leaderboards
- Public AI datasets, preference data, synthetic data, and data releases
- Data contamination, leakage, provenance, deduplication, and annotation-quality work

Default sources:

| Source | Required secret | Role |
|---|---|---|
| arXiv | No | Primary paper discovery |
| Hugging Face Hub | No | Dataset repository discovery |
| GitHub | No in Actions | Code and artifact discovery |
| OpenAlex | `OPENALEX_API_KEY` | Scholarly metadata enrichment |
| Brave Search | `BRAVE_API_KEY` | Web and lab-blog discovery |

The report remains useful without optional secrets. Missing optional sources are shown
as warnings in the source-health table instead of being silently ignored.

## How ranking works

Each item receives four visible scores:

- **Relevance**: matches against benchmark, evaluation, dataset, and data-quality taxonomy
- **Evidence**: primary/structured source, authorship, and cross-source artifact evidence
- **Recency**: time since publication or material update
- **Adoption**: logarithmically scaled stars, downloads, likes, or citations

The default priority is:

```text
0.40 relevance + 0.25 evidence + 0.20 recency + 0.15 adoption
```

This is triage, not scientific quality adjudication or endorsement.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
benchmark-radar
```

Outputs:

- `out/report.md`: the exact GitHub Issue body
- `out/items.json`: machine-readable evidence and source-health snapshot
- `data/snapshots/YYYY-MM-DD.json`: versioned, idempotent UTC snapshot
- `site/data/radar.json`: deterministic browser-ready history generated for deployment

Validated snapshots are the canonical corpus and live on `main` beside the code and
schema that interpret them. A dedicated snapshot-writer GitHub App may append only
validated daily snapshots through the protected-branch bypass; human changes remain
pull-request-only. Dashboard builds derive `site/data/radar.json` without tracking it.

Rebuild the dashboard data without collecting again:

```bash
benchmark-radar rebuild
```

Run checks:

```bash
ruff check .
pytest -q
```

## Configure

Edit [`config.yml`](config.yml) to change the lookback, threshold, queries, taxonomy, and
report size. Copy `.env.example` to `.env` only for local use; never commit credentials.

Record volume is controlled by three separate keys, so the daily Issue stays readable
without discarding the corpus behind it:

| Key | Effect |
|---|---|
| `max_items_per_source` | Upper bound on records fetched from each source |
| `report_limit` | Records scored, snapshotted, and published to the dashboard |
| `issue_item_limit` | Records written into the daily Issue body |

Every run records its own drop-off (`fetched → deduplicated → qualified → published`) in
the snapshot and at the top of the Issue, so the gap between what a source returned and
what was published is always auditable.

GitHub search is rate-limited to 10 requests per minute without a token and 30 with one,
so pagination is bounded by `sources.github.max_requests` and spaced by
`request_delay_seconds`. Both default by whether `GITHUB_TOKEN` is present; raising
`max_items_per_source` well beyond the defaults on a tokenless run risks a 403.

Trend comparisons only run between snapshots collected under the same `report_limit`.
Changing the cap lifts every count at once, and reporting that as domain momentum would
present a change in collection policy as a change in the field.

The `watchlist` block pins named artifacts, matched on title and source id by word
boundary. A hit is routed to the top and labelled with a one-line note; it never changes
a score, so the ranking stays explainable.

Optional repository secrets:

```text
OPENALEX_API_KEY
BRAVE_API_KEY
```

Daily snapshot persistence also requires a private GitHub App with **Contents: read and
write** access to this repository. Add the App to the `main-protect` ruleset's bypass
list with **Always allow**, then configure:

```text
Repository variable: RADAR_APP_ID
Actions secret:      RADAR_APP_PRIVATE_KEY
```

The built-in `GITHUB_TOKEN` continues to authenticate discovery and Issue publishing;
the snapshot push uses the App token so its `main` push can trigger deployment.

## Daily publishing

`.github/workflows/daily-radar.yml` runs at 12:15 UTC and can also be started manually.
It:

1. collects and renders with read-only repository permission;
2. validates and uses the snapshot-writer App to persist one snapshot on `main`;
3. creates or updates the date-filtered daily Issue;
4. lets that App-authenticated push trigger the standalone Pages workflow;
5. prevents duplicate snapshots and daily Issues on reruns.

The workflow needs repository Issues enabled. The labels `daily-radar` and `automated`
must exist; they are created during initial repository setup.

## Provenance and limitations

- Every entry links to its discovered primary or structured record.
- Optional-source failures are visible.
- Persisted snapshots omit raw API payloads and credentials.
- Public attention feeds are displayed separately and never contribute to quality scores.
- Reports can contain false positives; always inspect the source.
- A repository update is not necessarily a new release.
- Publication dates differ across preprints, code, datasets, and formal publications.
- This system does not automatically create ANX-Bench events or research claims.

## Public observation feeds

The collector ingests compatible public attention observations from separate, read-only
repositories before persisting the daily snapshot. Feed producers must follow
[`docs/public-observation-feed.schema.json`](docs/public-observation-feed.schema.json).
The collector validates the feed version and HTTP(S) links, records producer health
separately from radar ingest health, and stamps publication, producer discovery, and
first radar observation independently. The dashboard renders source text as plain text
and labels these records as unranked attention rather than evidence.

## License

MIT
