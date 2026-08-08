from datetime import UTC, datetime

import pytest

from benchmark_radar import questions
from benchmark_radar.briefing import BriefingError
from benchmark_radar.models import RadarItem, RadarRun
from benchmark_radar.snapshots import snapshot_for_run
from benchmark_radar.stats import build_registry, stat_index


def _item(index: int, *, day: int = 4, downloads: float | None = None) -> RadarItem:
    return RadarItem(
        source="Hugging Face",
        source_id=f"org/dataset-{index}",
        title=f"Benchmark dataset {index}",
        url=f"https://huggingface.co/datasets/org/dataset-{index}",
        published_at=datetime(2026, 8, day, tzinfo=UTC),
        categories=["benchmark"],
        summary="A scored evaluation dataset with documented verifier behaviour.",
        event_kind="released",
        metrics={"downloads": downloads} if downloads is not None else {},
    )


def _run(items, *, day: int = 4) -> RadarRun:
    return RadarRun(
        generated_at=datetime(2026, 8, day, 12, tzinfo=UTC),
        since=datetime(2026, 8, day - 1, 12, tzinfo=UTC),
        items=items,
        health=[],
        selection={"taxonomy_version": "taxonomy-v2", "lookback_hours": 48},
    )


def _group():
    return {"id": "arrivals", "title": "What arrived", "questions": ("Q1?",)}


def _answer(**overrides):
    answer = {
        "question": "Q1?",
        "signal": "Three datasets arrived.",
        "plain_english": "Three new scored datasets showed up today.",
        "takeaway": "Check whether they document a verifier.",
        "counter_view": "No credible counter-view found.",
        "stat_ids": ["S001"],
        "evidence_ids": [],
        "confidence": "medium",
        "sufficient_evidence": True,
    }
    answer.update(overrides)
    return answer


def _fixture():
    current = snapshot_for_run(_run([_item(1), _item(2)]))
    registry = build_registry([current], current)
    return _group(), stat_index(registry), {"E001", "E002"}


def test_an_answer_citing_an_unknown_statistic_is_rejected():
    # The registry is the only source of numbers. A model that invents one must
    # not be able to publish it.
    group, stats_by_id, evidence = _fixture()

    with pytest.raises(BriefingError, match="unknown statistics"):
        questions._validate([_answer(stat_ids=["S999"])], group, stats_by_id, evidence)


def test_an_answer_citing_unknown_evidence_is_rejected():
    group, stats_by_id, evidence = _fixture()

    with pytest.raises(BriefingError, match="unknown evidence"):
        questions._validate([_answer(evidence_ids=["E404"])], group, stats_by_id, evidence)


def test_a_confident_answer_that_cites_nothing_is_rejected():
    # This is the generic-filler failure mode: confident prose grounded in
    # nothing at all.
    group, stats_by_id, evidence = _fixture()

    with pytest.raises(BriefingError, match="citing none"):
        questions._validate([_answer(stat_ids=[], evidence_ids=[])], group, stats_by_id, evidence)


def test_an_insufficient_evidence_answer_may_cite_nothing():
    # Saying "the data does not show this" is a useful answer, not a failure.
    group, stats_by_id, evidence = _fixture()

    validated = questions._validate(
        [_answer(stat_ids=[], evidence_ids=[], sufficient_evidence=False)],
        group,
        stats_by_id,
        evidence,
    )

    assert validated[0]["sufficient_evidence"] is False


def test_a_short_answer_set_is_rejected():
    group = {"id": "arrivals", "title": "t", "questions": ("Q1?", "Q2?")}
    _, stats_by_id, evidence = _fixture()

    with pytest.raises(BriefingError, match="answered 1 of 2"):
        questions._validate([_answer()], group, stats_by_id, evidence)


def test_validated_answers_carry_the_registry_values_not_model_prose():
    # The renderer prints from cited_stats, so the published number is the
    # computed one even if the model described it loosely.
    group, stats_by_id, evidence = _fixture()

    validated = questions._validate([_answer(stat_ids=["S001"])], group, stats_by_id, evidence)

    assert validated[0]["cited_stats"][0]["id"] == "S001"
    assert validated[0]["cited_stats"][0]["value"] == 2


def test_registry_refuses_trend_language_without_a_comparable_window():
    current = snapshot_for_run(_run([_item(1)]))

    registry = build_registry([current], current)

    assert registry["comparable"] is False
    assert "Do not use trend language" in registry["comparability_note"]


def test_registry_marks_category_counts_as_overlapping():
    item = _item(1)
    item.categories = ["benchmark", "agentic"]
    current = snapshot_for_run(_run([item]))

    registry = build_registry([current], current)
    tagged = [stat for stat in registry["stats"] if stat["label"].startswith("records tagged")]

    assert len(tagged) == 2
    assert all("do not sum to 100%" in stat["detail"]["note"] for stat in tagged)


def test_question_set_omits_questions_the_corpus_cannot_answer():
    # The corpus keeps no query identity, rank, or per-query volume, so a
    # "which searches surged" question could only be answered by invention.
    asked = " ".join(
        question for group in questions.QUESTION_GROUPS for question in group["questions"]
    ).casefold()

    assert "search" not in asked
    assert "surge" not in asked


def test_report_prints_statistic_values_from_the_registry():
    # The published number is the computed one. A model that wrote "thousands"
    # in its prose still yields the registry's exact value on the page.
    from benchmark_radar.report import render_markdown

    run = _run([_item(1), _item(2)])
    current = snapshot_for_run(run)
    registry = build_registry([current], current)
    by_id = {stat["id"]: stat for stat in registry["stats"]}
    payload = {
        "model": "gpt-5.6",
        "calls": 1,
        "comparable": registry["comparable"],
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "groups": [
            {
                "title": "What arrived",
                "answers": [
                    {
                        "question": "What arrived today?",
                        "signal": "Two datasets arrived.",
                        "plain_english": "Two new test sets showed up.",
                        "takeaway": "Check their verifiers.",
                        "counter_view": "One connector supplied both.",
                        "stat_ids": ["S001"],
                        "evidence_ids": [],
                        "confidence": "medium",
                        "sufficient_evidence": True,
                        "cited_stats": [by_id["S001"]],
                    }
                ],
            }
        ],
    }

    markdown = render_markdown(run, dashboard_url="https://x.test", daily_questions=payload)

    assert "## Questions for today" in markdown
    assert "**Counter-view:** One connector supplied both" in markdown
    assert "`S001` evidence records captured today: **2**" in markdown
    # No certified window today, so the report must not imply a trend.
    assert "No certified comparison window today" in markdown


def test_a_day_never_loses_answers_it_already_had():
    from benchmark_radar.snapshots import merge_snapshots

    morning_run = _run([_item(1)])
    morning_run.daily_questions = {"groups": [{"title": "t", "answers": []}]}
    morning = snapshot_for_run(morning_run)

    merged = merge_snapshots(morning, snapshot_for_run(_run([_item(2)])))

    assert merged["questions"]["groups"][0]["title"] == "t"
