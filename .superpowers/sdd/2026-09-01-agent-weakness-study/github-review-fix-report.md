# GitHub Review Fix Report

Date: 2026-09-01
PR: #493
Branch: `codex/issue-455-agent-weaknesses`

## Scope

Addressed the four verified review findings without changing the report result
prose in `scripts/build_system_evaluation.py` or the evidence YAML inputs.

## Changes

1. `docs/technical-report/README.md`
   Added the exact clean-checkout reproduction sequence before the issue #455
   analysis and next-draft PDF rebuild commands. The focused two-file test run
   remains as an additional check after the full repository verification pass.

2. `docs/technical-report/agent-weakness-independent-review.md`
   Moved the 4/4 agreement result, no-disagreement statement, and explicit
   four-row/sample-local limit to the top of the document while preserving the
   tracked blind-packet link and raw assignments table.

3. `scripts/analyze_agent_weaknesses.py`
   Added a one-to-one benchmark-family identity validation guard so every
   `benchmark_family_id` maps to exactly one `benchmark_family_name`, and vice
   versa, before demonstrated-scope and recurrence calculations run.

4. `scripts/build_technical_report.py`
   Exposed `build_parser()` and changed the default output path to
   `output/pdf/benchmark-radar-technical-report-next-draft.pdf`. Rebuilding the
   frozen `v0.9.0` filename now requires an explicit `--output`.

5. `tests/test_agent_weakness_study.py`
   Added regression coverage for inconsistent family identity mappings and for
   the independent-review summary ordering.

6. `tests/test_system_evaluation_report.py`
   Added parser coverage showing that both builders default to the next-draft
   path while the legacy frozen filename remains opt-in through explicit
   `--output`.

## Verification

- `uv run pytest -q tests/test_agent_weakness_study.py -k 'repository_task2 or report_records'`
- `uv run pytest -q tests/test_agent_weakness_study.py -k 'identity or deduplicates_families or requires_all_three_statuses'`
- `uv run pytest -q tests/test_system_evaluation_report.py -k 'default_output_targets_next_draft or legacy_builder_defaults_to_next_draft'`
- `uv run ruff check scripts/analyze_agent_weaknesses.py scripts/build_technical_report.py tests/test_agent_weakness_study.py tests/test_system_evaluation_report.py`
- `uv run ruff format --check scripts/analyze_agent_weaknesses.py scripts/build_technical_report.py tests/test_agent_weakness_study.py tests/test_system_evaluation_report.py`
- `uv run pytest -q tests/test_agent_weakness_study.py tests/test_system_evaluation_report.py`

## Concerns

- The requested fix set did not rerun the full clean-checkout release pipeline
  (`normalize-external`, `classify`, `build-data-release`) or regenerate the
  next-draft PDF; this commit only corrects the review findings and their
  targeted regression coverage.
