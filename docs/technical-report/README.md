# Benchmark Radar technical report

This directory tracks the source and deposit metadata for the citable Benchmark
Radar technical report. The report describes software version 0.9.0 and the
public data snapshot dated 2026-08-29.

Build the PDF after installing ReportLab:

```bash
python3 scripts/build_technical_report.py \
  --doi 10.5281/zenodo.22167102
```

The builder writes
`output/pdf/benchmark-radar-technical-report-v1.0.pdf`. The reserved DOI appears
in the PDF itself. Upload that PDF to the Zenodo record described by
`zenodo-metadata.json`, then publish the record.

The report derives its quantitative claims from these versioned files:

- `site/data/radar.json` (generated from the dated snapshots)
- `site/data/benchmark-index.json` (generated from normalized catalogs)
- `data/snapshots/2026-08-29.json`
- `data/model_cards.yml`
- `data/benchmark_scores.yml`

Regenerate and review the report when any of those inputs or the report text
changes.
