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
