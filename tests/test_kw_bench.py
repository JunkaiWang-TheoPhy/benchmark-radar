import pytest

from benchmark_radar import kw_bench
from benchmark_radar.kw_bench import (
    KW_BENCH_VERSION,
    UNCLASSIFIED,
    KwBenchError,
    assign_level,
    classify_track,
    coverage,
    evidence_hash,
    is_publishable,
    level_counts,
    review_status_for,
    track_id,
)


def evidence(**overrides):
    value = {
        "scored_outcome": "The returned answer string is compared to the gold answer.",
        "agent_visible_target": "The question is given to the agent in full.",
        "evaluator_knowledge": "The gold answer is stored in the benchmark.",
        "verifier_modality": "exact",
        "verifier_procedure": "Exact string match against the gold answer.",
    }
    value.update(overrides)
    return value


# --- L0 / L1 boundary ----------------------------------------------------


def test_copied_span_is_retrieval():
    decision = assign_level(
        evidence(
            scored_outcome="The answer span is copied verbatim from the supplied document.",
            verifier_procedure="Exact match against the annotated span.",
        )
    )

    assert decision["level"] == "L0"
    assert decision["boundary"] == "L0 to L1"


def test_synthesis_across_sources_is_closed_form_reasoning():
    decision = assign_level(
        evidence(
            scored_outcome="The agent must synthesize retrieved passages into a derived total.",
            verifier_procedure="The computed value is compared to the reference value.",
        )
    )

    assert decision["level"] == "L1"


def test_retrieval_followed_by_derivation_is_l1_not_l0():
    """A task that looks up and then reasons is L1: derivation wins over lookup."""
    decision = assign_level(
        evidence(
            scored_outcome=(
                "The agent retrieves the passage from the source and then computes the "
                "resulting figure."
            ),
        )
    )

    assert decision["level"] == "L1"


# --- L1 / L2 boundary ----------------------------------------------------


def test_environment_end_state_is_execution():
    decision = assign_level(
        evidence(
            scored_outcome="The verifier checks the end state of the repository after the run.",
            verifier_procedure="The test suite is executed against the modified repository.",
            verifier_modality="executable",
        )
    )

    assert decision["level"] == "L2"
    assert decision["boundary"] == "L1 to L2"


def test_read_only_shell_use_stays_at_reasoning():
    """The rubric is explicit: read-only tool use preserves L1."""
    decision = assign_level(
        evidence(
            scored_outcome=(
                "The agent may query the database read-only; the verifier checks only the "
                "returned answer, which it must derive from the query results."
            ),
            verifier_procedure="The returned answer is compared to the reference answer.",
        )
    )

    assert decision["level"] == "L1"


# --- L2 / L3 boundary ----------------------------------------------------


def test_reproducing_a_named_result_is_replication():
    decision = assign_level(
        evidence(
            scored_outcome=(
                "The agent must reproduce the reported accuracy from the referenced paper."
            ),
            agent_visible_target="The paper and its reported result are provided to the agent.",
            verifier_procedure="Reproduced metrics are compared within a stated tolerance.",
        )
    )

    assert decision["level"] == "L3"
    assert decision["boundary"] == "L2 to L3"


# --- L3 / L4 boundary ----------------------------------------------------


def test_undisclosed_finding_known_to_evaluator_is_rediscovery():
    decision = assign_level(
        evidence(
            scored_outcome="The agent reports a defect it located without being told where.",
            agent_visible_target=(
                "An open-ended repository; the target bug is undisclosed to the agent."
            ),
            evaluator_knowledge="The evaluator already knows the recorded bug and its location.",
            verifier_procedure="The reported defect is matched against the recorded bug.",
        )
    )

    assert decision["level"] == "L4"
    assert decision["boundary"] == "L3 to L4"


def test_stated_question_with_withheld_answer_is_not_rediscovery():
    """Withholding only the answer is every ordinary benchmark, not L4."""
    decision = assign_level(
        evidence(
            scored_outcome="The agent computes the answer, which is derived from the input.",
            agent_visible_target="The question is stated in full; only the answer is withheld.",
            evaluator_knowledge="The evaluator holds the gold answer.",
        )
    )

    assert decision["level"] == "L1"


def test_a_withheld_answer_alone_never_reaches_rediscovery():
    """Every benchmark withholds its answer; only a withheld *target* is L4."""
    decision = assign_level(
        evidence(
            scored_outcome="The agent returns the answer, derived from the supplied table.",
            agent_visible_target="The prompt names the task; the gold answer is withheld.",
            evaluator_knowledge="The evaluator already knows the recorded answer.",
        )
    )

    assert decision["level"] == "L1"


def test_open_ended_read_only_bug_hunt_is_l4_not_l1():
    """Discovery status takes precedence over output form, per the rubric."""
    decision = assign_level(
        evidence(
            scored_outcome=(
                "The agent returns a written description of the undisclosed failure mechanism."
            ),
            agent_visible_target=(
                "Raw observations only; the agent must choose what to investigate."
            ),
            evaluator_knowledge="The evaluator already knows the recorded mechanism.",
            verifier_modality="human expert",
            verifier_procedure="An expert matches the report against the recorded mechanism.",
        )
    )

    assert decision["level"] == "L4"


# --- L4 / L5 boundary ----------------------------------------------------


def l5_evidence(**overrides):
    value = evidence(
        scored_outcome="A novel result produced during the run is validated externally.",
        agent_visible_target="An open-ended frontier problem; no target is disclosed.",
        evaluator_knowledge="No prior result is known to the evaluator at the cutoff.",
        verifier_modality="human expert",
        verifier_procedure=(
            "A new experiment provides prospective validation and experts adjudicate."
        ),
        evaluation_cutoff="2026-07-01T00:00:00+00:00",
        novelty_check="Prior-art search across arXiv and Scopus on 2026-07-01; no prior result.",
    )
    value.update(overrides)
    return value


def test_prospectively_validated_novel_result_is_frontier_advancement():
    decision = assign_level(l5_evidence())

    assert decision["level"] == "L5"
    assert decision["boundary"] == "L4 to L5"


@pytest.mark.parametrize("field", ["evaluation_cutoff", "novelty_check"])
def test_l5_without_its_extra_fields_is_unclassified_not_l4(field):
    """The rubric: an L5 assignment missing a cutoff or novelty check is unclassified."""
    decision = assign_level(l5_evidence(**{field: ""}))

    assert decision["level"] == UNCLASSIFIED
    assert field in decision["missing_evidence"]


def test_prior_art_known_to_the_evaluator_caps_at_l4():
    decision = assign_level(
        l5_evidence(
            evaluator_knowledge=(
                "A provenance check found the evaluator already knew this recorded result."
            ),
        )
    )

    assert decision["level"] == "L4"


# --- Unclassified --------------------------------------------------------


def test_missing_required_fields_is_unclassified_with_the_list():
    decision = assign_level({"scored_outcome": "Something happens."})

    assert decision["level"] == UNCLASSIFIED
    assert "verifier_procedure" in decision["missing_evidence"]
    assert "agent_visible_target" in decision["missing_evidence"]


def test_empty_evidence_is_unclassified():
    assert assign_level({})["level"] == UNCLASSIFIED


def test_whitespace_only_field_counts_as_missing():
    decision = assign_level(evidence(verifier_procedure="   "))

    assert decision["level"] == UNCLASSIFIED
    assert "verifier_procedure" in decision["missing_evidence"]


def test_present_but_vague_evidence_is_unclassified_rather_than_guessed():
    decision = assign_level(
        evidence(
            scored_outcome="The submission is scored.",
            verifier_procedure="A score is produced.",
            agent_visible_target="A task.",
            evaluator_knowledge="Reference material.",
        )
    )

    assert decision["level"] == UNCLASSIFIED
    assert decision["missing_evidence"] == []


def test_title_keywords_never_set_a_level():
    """`agentic` in a title must not produce a level; only evidence can."""
    record = classify_track(
        {
            "canonical_artifact_id": "artifact:arxiv:2607.00001",
            "track_name": "default",
            "title": "AgenticBench: An Agentic Agent Benchmark for Autonomous Agents",
            "evidence": {},
        },
        classified_at="2026-08-06T00:00:00+00:00",
    )

    assert record["level"] == UNCLASSIFIED


# --- Record construction -------------------------------------------------


def test_classification_record_is_auditable():
    record = classify_track(
        {
            "canonical_artifact_id": "artifact:github:org/bench",
            "track_name": "execution",
            "title": "Bench",
            "url": "https://github.com/org/bench",
            "event_kind": "released",
            "evidence": evidence(
                scored_outcome="The verifier checks the end state of the repository.",
                verifier_modality="executable",
            ),
            "tags": {"horizon": "multi-turn", "not_an_axis": "ignored"},
        },
        classified_at="2026-08-06T00:00:00+00:00",
    )

    assert record["level"] == "L2"
    assert record["kw_bench_version"] == KW_BENCH_VERSION
    assert record["level_rationale"]
    assert record["evidence_hash"].startswith("sha256:")
    assert record["tags"] == {"horizon": "multi-turn"}
    assert record["evidence"]["verifier_procedure"]


def test_track_ids_are_stable_and_distinct_per_track():
    first = track_id("artifact:arxiv:2607.00001", "retrieval")
    second = track_id("artifact:arxiv:2607.00001", "execution")

    assert first == track_id("artifact:arxiv:2607.00001", "Retrieval  ")
    assert first != second


def test_evidence_hash_changes_with_the_evidence():
    assert evidence_hash(evidence()) == evidence_hash(evidence())
    assert evidence_hash(evidence()) != evidence_hash(evidence(scored_outcome="Different."))


def test_invalid_verifier_modality_is_rejected():
    with pytest.raises(KwBenchError):
        classify_track(
            {
                "canonical_artifact_id": "artifact:x",
                "track_name": "default",
                "evidence": evidence(verifier_modality="vibes"),
            },
            classified_at="2026-08-06T00:00:00+00:00",
        )


def test_missing_canonical_id_is_rejected():
    with pytest.raises(KwBenchError):
        classify_track(
            {"canonical_artifact_id": "", "track_name": "default"},
            classified_at="2026-08-06T00:00:00+00:00",
        )


# --- Review gates and counting -------------------------------------------


@pytest.mark.parametrize("level", ["L0", "L1", "L2", "L3"])
def test_low_levels_publish_automatically(level):
    assert review_status_for(level) == kw_bench.REVIEW_AUTO


@pytest.mark.parametrize("level", ["L4", "L5"])
def test_discovery_levels_require_human_review(level):
    assert review_status_for(level) == kw_bench.REVIEW_REQUIRED
    assert not is_publishable({"level": level, "review_status": kw_bench.REVIEW_REQUIRED})


def test_human_approval_makes_l5_publishable():
    assert is_publishable({"level": "L5", "review_status": kw_bench.REVIEW_APPROVED})


def test_unclassified_is_published_as_a_visible_outcome():
    assert is_publishable({"level": UNCLASSIFIED, "review_status": kw_bench.REVIEW_AUTO})


def record(level, **overrides):
    value = {
        "track_id": f"track:{level}",
        "level": level,
        "review_status": review_status_for(level),
        "event_kind": "released",
    }
    value.update(overrides)
    return value


def test_level_counts_include_every_bar_even_at_zero():
    counts = level_counts([record("L1")])

    assert set(counts) == set(kw_bench.CHART_LEVELS)
    assert counts["L1"] == 1
    assert counts["L4"] == 0


def test_a_track_is_counted_once_however_many_rows_it_has():
    counts = level_counts([record("L2"), record("L2")])

    assert counts["L2"] == 1


def test_released_only_excludes_update_sightings():
    counts = level_counts(
        [record("L1"), record("L2", track_id="track:b", event_kind="updated")],
        released_only=True,
    )

    assert counts["L1"] == 1
    assert counts["L2"] == 0


def test_unreviewed_l5_is_excluded_from_counts():
    counts = level_counts([record("L5")])

    assert counts["L5"] == 0


def test_coverage_reports_the_unclassified_share():
    report = coverage([record("L1"), record(UNCLASSIFIED, track_id="track:u"), record("L5")])

    assert report["classified_count"] == 1
    assert report["unclassified_count"] == 1
    assert report["classified_rate"] == 0.5
    assert report["awaiting_human_review"] == 1


def test_coverage_of_an_empty_corpus_has_no_rate():
    assert coverage([])["classified_rate"] is None


def test_reference_lists_all_six_levels():
    reference = kw_bench.kw_bench_reference()

    assert [entry["level"] for entry in reference["levels"]] == list(kw_bench.LEVELS)
    assert reference["kw_bench_version"] == KW_BENCH_VERSION
