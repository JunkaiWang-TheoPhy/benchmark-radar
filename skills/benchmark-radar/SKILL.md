---
name: benchmark-radar
description: Find, inspect, and check AI benchmark records with the Benchmark Radar CLI. Use when a request needs benchmark discovery, details, recent Radar evidence, or local data health; do not assume why the user needs the results.
---

# Benchmark Radar

Use the local `benchmark-radar` CLI as the source of truth. Keep the user's purpose,
selection criteria, and desired output open unless they specify them.

## Prepare the data

1. Check availability with `benchmark-radar status --json`.
2. If the command is missing, report that the CLI is required. Offer installation,
   but do not install it without permission:

   ```bash
   python -m pip install 'git+https://github.com/ktwu01/benchmark-radar.git'
   ```

3. If the CLI reports `not_initialized`, run `benchmark-radar init --json`; that
   successful init is already current, so do not immediately sync again.
4. Otherwise, when the request depends on current data, run
   `benchmark-radar sync --json` once before querying. Skip sync when the user asks
   to stay offline or retain a fixed local version. If sync fails, report it instead
   of silently presenting stale data as current.

## Choose the smallest command

- Discover records:
  `benchmark-radar search "<query>" --scope catalog|radar|all --json`
- Inspect one known key or slug:
  `benchmark-radar show "<identifier>" --json`
- Inspect the newest Radar evidence:
  `benchmark-radar recent --json`
- Check local data and provenance:
  `benchmark-radar status --json`
- Start the local HTTP interface only when requested:
  `benchmark-radar serve --host 127.0.0.1 --port 8765`

Use `catalog` for normalized benchmark records, `radar` for observed recent
evidence, and `all` when both are relevant. Search is deterministic lexical/token
matching, not semantic search. If the first query is weak, try a small number of
short, discriminative query variants rather than claiming no relevant benchmark
exists.

Use `--json` for agent work; omit it only when the user wants terminal-friendly
text. Apply supported filters only when they come from the request. Do not run
maintainer commands such as `normalize-external`, `classify`, or
`build-data-release` for ordinary use.

Return the relevant records and their match reasons. Preserve the reported
`data_version` and `retrieval_mode`, distinguish catalog records from Radar
evidence, and do not turn search results into a recommendation unless the user
asked for one.
