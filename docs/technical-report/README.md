# Benchmark Radar v0.9.0 technical report

This directory tracks the source and deposit metadata for the citable Benchmark
Radar technical report. The report evaluates software version 0.9.0, its full
collection and publication pipeline, all 37 public collection sources, the
1,242-entry web search surface, and the public data snapshot dated 2026-08-29.

Build the PDF after installing ReportLab:

```bash
python3 scripts/build_system_evaluation.py \
  --doi 10.5281/zenodo.22167102
```

The builder writes
`output/pdf/benchmark-radar-technical-report-v0.9.0.pdf`. The reserved DOI appears
in the PDF itself. Upload that PDF to the Zenodo record described by
`zenodo-metadata.json`, then publish the record.

The published v0.9.0 PDF is frozen. Do not overwrite it when preparing a new
manuscript or adding a contributor. Build the working next draft explicitly:

```bash
python3 scripts/build_system_evaluation.py \
  --next-draft \
  --doi 10.5281/zenodo.22167102
```

This writes `output/pdf/benchmark-radar-technical-report-next-draft.pdf` and
uses the draft byline and contributor affiliations. Do not change the frozen
`zenodo-metadata.json` for draft work; prepare release metadata only when the
next report version is approved for deposit.

The draft byline is provisional until the contributor has reviewed and approved
the integrated manuscript, supplied a contribution statement, and accepted
accountability for the work, as described in
`docs/designs/technical-report-collaboration-scoring.md` and issue #447.

The software remains under the MIT License. The technical report and original
editorial content use CC BY-NC 4.0. Commercial republication, resale, paid
newsletters, dataset packaging, or commercial product integration requires
prior written permission from Koutian Wu. Third-party source material remains
under its original terms.

The report derives its quantitative claims from these versioned files and from
the current README and report documentation:

- `site/data/radar.json` (generated from the dated snapshots)
- `site/data/benchmark-index.json` (generated from normalized catalogs)
- `data/snapshots/2026-08-29.json`
- `data/model_cards.yml`
- `data/benchmark_scores.yml`
- `site/data/models.json`
- `config.yml`
- `docs/reports/ai-benchmark-landscape-report.md`
- `docs/source-probe-evidence.md`

Regenerate and review the report when any of those inputs or the report text
changes.
