# Benchmark Radar v0.9.0 technical report

This directory tracks the source and deposit metadata for the citable Benchmark
Radar technical report. The report evaluates software version 0.9.0, its full
collection and publication pipeline, all 37 public collection sources, the
1,242-entry web search surface, and the public data snapshot dated 2026-08-29.

Rebuild the issue #455 agent-weakness inputs, verify the report text, then build the next draft after installing ReportLab:

```bash
uv run pytest -q tests/test_agent_weakness_study.py tests/test_system_evaluation_report.py
uv run python scripts/analyze_agent_weaknesses.py \
  --source data/agent_weakness_evidence.yml \
  --json-output output/analysis/agent-weakness-study.json \
  --csv-output output/analysis/agent-weakness-coded-table.csv
uv run --with reportlab python scripts/build_system_evaluation.py \
  --doi 10.5281/zenodo.22167102 \
  --output output/pdf/benchmark-radar-technical-report-next-draft.pdf
```

The draft builder must write
`output/pdf/benchmark-radar-technical-report-next-draft.pdf` and leave the frozen
`output/pdf/benchmark-radar-technical-report-v0.9.0.pdf` artifact untouched. The
reserved DOI appears in the PDF itself. Upload only the reviewed release PDF to
the Zenodo record described by `zenodo-metadata.json`, then publish the record.

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

Regenerate and review the report when any of those inputs, the issue #455 study
artifacts, or the report text changes.
