# Agent Weakness Coding Guide

This guide defines the issue #455 evidence-coding package for agent weakness analysis as of 2026-09-01. It is intentionally narrow: the goal is not a field-wide census of all agent failures, but a reviewable coding frame over a bounded set of publicly released benchmark families that already have current Benchmark Radar coverage or an exact Radar query path.

## Scope

Include only public benchmark families for general-purpose computer use, web use, software engineering, tool use, and scientific workflows that were publicly available by 2026-09-01 and that provide direct failure evidence in an authoritative paper or benchmark repository.

For the demonstrated-family analysis, bound the family set to these eight families:

- OSWorld 2.0
- WebArena
- Mind2Web
- GAIA2
- SWE-bench Verified
- SWE-bench Science
- ResearchClawBench
- PRBench

The pre-registration named FrontierChallenge, but the clean 2026-09-01 Radar
corpus has neither a durable record nor a lexical query result for that family.
It is therefore excluded rather than counted through an external paper alone.
This is a documented scope correction, not a post-hoc negative finding.

Use SciCode only as a measurement-instrument counterexample. It may document benchmark defects that would misstate agent weakness prevalence, but it must not be counted as demonstrated prevalence evidence for agent failure families.

Exclude General AgentBench and ToolFailBench from this package because the current local Radar snapshot does not provide a stable current Radar record for them.

## Inclusion Rule

Add a row only when all of the following are true:

1. The row cites an exact Benchmark Radar query and, when available, a stable local Radar record id.
2. The row cites one authoritative external source URL.
3. The row names an exact evidence location inside that source.
4. The row states one primary weakness code from the study taxonomy.
5. The row includes a limitation and a plausible counter-reading.
6. The row includes a counterexample showing why the evidence should not be over-generalized.

## Statuses

- `demonstrated`: the cited source directly reports the failure pattern or a concrete quantitative result that supports the code assignment.
- `design_implied`: the benchmark design or reported split pattern makes the code assignment plausible, but the source does not directly quantify that failure mechanism as a prevalence claim.
- `unmeasured`: the benchmark or audit shows that a commonly inferred weakness cannot be treated as prevalence evidence, usually because the evaluation instrument is contaminated or the mechanism is otherwise not measured.

Every coded dataset must contain at least one row for each of the three statuses so the downstream analysis can separate demonstrated recurrence from design signals and measurement gaps.

## Fine Taxonomy

- `goal_plan_drift`: the agent departs from the target objective, protocol, or scientific intent rather than merely making a local execution error.
- `tool_selection_execution`: the agent chooses the wrong operation, explores unproductively, or performs a surface-level fix that does not correctly execute the needed repair.
- `environment_grounding_state_tracking`: the agent misses hidden state, loses constraints, or fails to ground its plan in the current interface, data, or workflow context.
- `loop_stagnation_recovery`: the agent gets trapped in deadlocks, stalls, or time-sensitive failures and does not recover.
- `verification_completion`: the agent reports, implies, or pursues completion without reliably checking whether the required end state was actually achieved.

## Coarse Grouping

- `decision_execution`: `goal_plan_drift`, `tool_selection_execution`
- `state_control`: `environment_grounding_state_tracking`, `loop_stagnation_recovery`, `verification_completion`

The coarse grouping is a sensitivity check, not a replacement for the fine codes.

## Alternative Grouping Sensitivity

The primary grouping puts verification/completion with state control. A post-hoc
alternative tests that choice by grouping the same fine codes as follows:

- `planning_state`: `goal_plan_drift`, `environment_grounding_state_tracking`,
  `loop_stagnation_recovery`
- `execution_delivery`: `tool_selection_execution`, `verification_completion`

Report both groupings. The alternative is explicitly post-hoc and must not be
described as pre-registered.

## Protocol Effects

Every row labels the relationship between protocol and observed result:

- `observed`: the source reports an ablation, alternate protocol, or instrument
  audit that changes the result.
- `plausible`: the protocol could explain part of the result, but the source does
  not isolate that effect.
- `not_isolated`: no protocol contrast supports a separate effect claim.

As a sensitivity check, recompute the primary coarse grouping after excluding
demonstrated families labelled `observed`. This does not erase those families;
it shows whether the direction of the selected-sample result depends entirely on
directly observed prompt, latency, guidance, or evaluator effects.

## Family Deduplication

Recurrence is computed on deduplicated benchmark families, not row counts. A family counts at most once per fine code and at most once per coarse group. Duplicate rows from the same family may carry additional context, counter-readings, or secondary-review hooks, but they must not inflate recurrence.

## Counterexample Rule

Every row must include one counterexample or limiting observation from the same benchmark family or source. The counterexample does not negate the coded weakness; it documents why the evidence should not be stretched into a claim that the capability is uniformly absent.

## Disagreement Adjudication

Rows marked `sampled_for_secondary_review: true` are eligible for an independent secondary code in Task 2. Until that code is filled, the row remains part of the declared sample but is treated as pending for agreement analysis. Completed secondary reviews are compared against the primary code using raw percent agreement and Cohen's kappa over the fine taxonomy.

Task 1 must not pre-fill synthetic secondary-review outcomes into the shipped study data. Any completed-code examples belong only in synthetic tests used to validate the agreement calculation.

## Measurement-Gap Rule

`unmeasured` rows belong in the final report as measurement gaps or audit-based cautions. They should appear in the analysis output, but they must not contribute to demonstrated family recurrence.
