# Task 1 Report: Agent Weakness Coding Package

Date: 2026-09-01

## Scope delivered

Task 1 now provides the issue #455 coding package in four owned files:

- `docs/technical-report/agent-weakness-coding-guide.md`
- `data/agent_weakness_evidence.yml`
- `scripts/analyze_agent_weaknesses.py`
- `tests/test_agent_weakness_study.py`

The demonstrated family set is explicitly bounded to nine strongly evidenced families:

1. OSWorld 2.0
2. WebArena
3. Mind2Web
4. GAIA2
5. SWE-bench Verified
6. SWE-bench Science
7. FrontierChallenge
8. ResearchClawBench
9. PRBench

SciCode is included only as a measurement-instrument counterexample and does not contribute to demonstrated family recurrence. General AgentBench and ToolFailBench remain excluded because the current local Radar snapshot does not provide a stable current Radar record for them.

## Source validation notes

I did not do further broad discovery. I used only the two provided evidence packs and validated the exact source URLs and locations they cited against the authoritative pages:

- OSWorld 2.0: `https://arxiv.org/html/2606.29537v1`
- WebArena: `https://arxiv.org/html/2307.13854v4`
- Mind2Web: `https://arxiv.org/html/2306.06070v3`
- GAIA2: `https://arxiv.org/pdf/2602.11964`
- SWE-bench Verified failure study: `https://arxiv.org/abs/2509.13941`
- SWE-bench Science: `https://arxiv.org/abs/2608.19799`
- FrontierChallenge: `https://arxiv.org/html/2608.24979v1`
- ResearchClawBench: `https://arxiv.org/html/2606.07591v5`
- PRBench: `https://arxiv.org/html/2603.27646v1`
- SciCode-Verified audit: `https://arxiv.org/abs/2608.04975`

For local Radar linkage, stable record ids are stored when present:

- `osworld-2.0`
- `webarena-verified`
- `mind2web`
- `gaia2`
- `swe_bench_verified`
- `swe_bench_science`
- `scicode`

For FrontierChallenge, ResearchClawBench, and PRBench, the evidence table stores exact Radar query strings and leaves `radar_record_id` empty because the current registry snapshot lacks a dedicated benchmark-card id.

## Delivered coding table

The shipped YAML contains:

- 9 `demonstrated` rows
- 1 `design_implied` row
- 1 `unmeasured` row

The `design_implied` row is a cautious Mind2Web action-selection signal that does not inflate demonstrated recurrence. The `unmeasured` row is the SciCode benchmark-audit caution.

## Analysis output

Running the analysis script on the shipped YAML produced:

- Demonstrated family count: `9`
- Fine recurrence:
  - `verification_completion`: `3/9`
  - `environment_grounding_state_tracking`: `2/9`
  - `loop_stagnation_recovery`: `2/9`
  - `goal_plan_drift`: `1/9`
  - `tool_selection_execution`: `1/9`
- Coarse recurrence:
  - `state_control`: `7/9`
  - `decision_execution`: `2/9`
- Status counts:
  - `demonstrated`: `9`
  - `design_implied`: `1`
  - `unmeasured`: `1`

The analysis script also emits:

- deduplicated family recurrence
- counterexample rows
- measurement-gap rows
- secondary-review agreement summary
- stable JSON and CSV outputs

## Task 2 hooks

The evidence table already carries review metadata for independent secondary coding. Four rows are marked for secondary review:

- `osworld2_hidden_state`
- `swe_science_misguided_exploration`
- `researchclawbench_protocol_drift`
- `scicode_instrument_gap`

Current agreement summary from the shipped dataset:

- sampled rows: `4`
- completed secondary rows: `0`
- pending secondary rows: `4`
- percent agreement on completed rows: `null`
- Cohen's kappa on completed rows: `null`

## Verification

Executed successfully:

- `uv run pytest -q tests/test_agent_weakness_study.py`
- `uv run ruff check scripts/analyze_agent_weaknesses.py tests/test_agent_weakness_study.py`
- `uv run ruff format --check scripts/analyze_agent_weaknesses.py tests/test_agent_weakness_study.py`
- `uv run python scripts/analyze_agent_weaknesses.py --source data/agent_weakness_evidence.yml --json-output output/analysis/agent-weakness-study.json --csv-output output/analysis/agent-weakness-coded-table.csv`

Generated outputs:

- `output/analysis/agent-weakness-study.json`
- `output/analysis/agent-weakness-coded-table.csv`

These output files were left uncommitted as required.

## Fix Round 1

Reviewer findings addressed on 2026-09-01:

- removed prefilled secondary-review outcomes from the shipped YAML so every sampled row is pending for Task 2
- required `demonstrated_family_scope`, `excluded_families`, and `measurement_counterexample_only` in the analyzer, and enforced exact demonstrated-family equality against the declared 9-family scope
- rejected measurement-counterexample families such as `SciCode` from the demonstrated set
- replaced section-only demonstrated evidence locations with replayable anchors using paragraph ids, figure ids, table ids, cells, or arXiv abstract-paragraph references
- added regression tests for section-only evidence placeholders, missing scope fields, missing demonstrated families, extra demonstrated families, and SciCode-as-demonstrated

Fix-round verification output:

- `uv run pytest -q tests/test_agent_weakness_study.py` -> `13 passed in 0.18s`
- `uv run python scripts/analyze_agent_weaknesses.py --source data/agent_weakness_evidence.yml --json-output output/analysis/agent-weakness-study.json --csv-output output/analysis/agent-weakness-coded-table.csv` -> exit `0`, agreement now reports `completed_row_count: 0`, `pending_row_count: 4`
