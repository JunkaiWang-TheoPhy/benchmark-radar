from datetime import UTC, datetime, timedelta

from benchmark_radar import rubric
from benchmark_radar.models import RadarItem
from benchmark_radar.pipeline import score_item

TAXONOMY = {
    "benchmark": ["benchmark", "leaderboard"],
    "evaluation": ["evaluation"],
}


def item(**overrides) -> RadarItem:
    published = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    defaults = {
        "source": "arXiv",
        "source_id": "2607.0001",
        "title": "A Benchmark and Leaderboard for Evaluation",
        "url": "https://arxiv.org/abs/2607.0001",
        "published_at": published,
        "summary": "",
    }
    return RadarItem(**{**defaults, **overrides})


def test_weights_are_a_normalized_mean_over_the_published_scale():
    assert set(rubric.WEIGHTS) == {"relevance", "evidence", "recency", "adoption"}
    assert sum(rubric.WEIGHTS.values()) == 1.0
    # Priority is presented as "x / 4.00". That only reads as a mean if a record
    # scoring the maximum on every component reaches exactly the maximum.
    assert sum(rubric.SCORE_MAX * weight for weight in rubric.WEIGHTS.values()) == rubric.SCORE_MAX


def test_published_rubric_describes_every_scored_component():
    reference = rubric.rubric_reference()
    keys = [component["key"] for component in reference["components"]]

    assert keys == list(rubric.WEIGHTS)
    assert reference["score_max"] == rubric.SCORE_MAX
    for component in reference["components"]:
        assert component["weight"] == rubric.WEIGHTS[component["key"]]
        assert component["summary"].strip()
        assert component["bands"], f"{component['key']} publishes no bands"
    assert reference["limits"]


def test_worked_example_reproduces_the_total_the_pipeline_published():
    """The dialog shows weight x component for each row and claims it sums to
    the total. If `score_item` ever weighted the components differently, that
    arithmetic would be a lie told next to the real number."""
    scored = score_item(
        item(authors=["Radar Author"], metrics={"citations": 12}),
        TAXONOMY,
        datetime(2026, 7, 28, 18, 0, tzinfo=UTC),
    )
    reference = rubric.rubric_reference()
    recomputed = sum(
        component["weight"] * getattr(scored, f"{component['key']}_score")
        for component in reference["components"]
    )

    assert round(recomputed, 2) == scored.total_score


def test_evidence_bands_match_the_credit_the_pipeline_grants():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    baseline = score_item(item(source="Brave Search"), TAXONOMY, now)
    primary = score_item(item(source="arXiv"), TAXONOMY, now)
    registry = score_item(item(source="GitHub"), TAXONOMY, now)

    assert baseline.evidence_score == rubric.EVIDENCE_BASE
    assert primary.evidence_score == rubric.EVIDENCE_BASE + rubric.EVIDENCE_PRIMARY_CREDIT
    assert registry.evidence_score == rubric.EVIDENCE_BASE + rubric.EVIDENCE_ARTIFACT_CREDIT
    for source in (*rubric.EVIDENCE_PRIMARY_SOURCES, *rubric.EVIDENCE_ARTIFACT_SOURCES):
        credited = score_item(item(source=source), TAXONOMY, now)
        assert credited.evidence_score > baseline.evidence_score


def test_recency_reaches_zero_exactly_where_the_rubric_says_it_does():
    published = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    at_publication = score_item(item(published_at=published), TAXONOMY, published)
    at_zero = score_item(
        item(published_at=published),
        TAXONOMY,
        published + timedelta(hours=rubric.RECENCY_ZERO_AT_HOURS),
    )
    one_step = score_item(
        item(published_at=published),
        TAXONOMY,
        published + timedelta(hours=rubric.RECENCY_HALF_LIFE_HOURS),
    )

    assert at_publication.recency_score == rubric.SCORE_MAX
    assert at_zero.recency_score == 0.0
    assert one_step.recency_score == rubric.SCORE_MAX - 1.0


def test_adoption_counts_every_metric_the_rubric_lists():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    for metric in rubric.ADOPTION_METRIC_WEIGHTS:
        scored = score_item(item(metrics={metric: 999}), TAXONOMY, now)
        assert scored.adoption_score > 0, f"{metric} earned no adoption credit"


def test_no_component_can_exceed_the_published_maximum():
    now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    every_term = " ".join(TAXONOMY["benchmark"] + TAXONOMY["evaluation"])
    saturated = score_item(
        item(
            title=f"{every_term} benchmark leaderboard",
            authors=["A"],
            artifact_urls=["https://example.com/a"],
            metrics={metric: 10**9 for metric in rubric.ADOPTION_METRIC_WEIGHTS},
        ),
        TAXONOMY,
        now,
    )

    for component in rubric.WEIGHTS:
        assert getattr(saturated, f"{component}_score") <= rubric.SCORE_MAX
    assert saturated.total_score <= rubric.SCORE_MAX


def test_formula_states_the_weights_it_applies():
    formula = rubric.priority_formula()

    for component, weight in rubric.WEIGHTS.items():
        assert f"{weight:.2f} {component}" in formula
