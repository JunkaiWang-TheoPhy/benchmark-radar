from datetime import UTC, datetime

import pytest

from benchmark_radar.models import RadarItem
from benchmark_radar.pipeline import (
    assert_no_boilerplate_summaries,
    canonical_url,
    deduplicate,
    normalized_title,
    score_item,
)


def item(**overrides):
    values = {
        "source": "arXiv",
        "source_id": "1234.5678",
        "title": "A New LLM Evaluation Benchmark",
        "url": "https://arxiv.org/abs/1234.5678",
        "published_at": datetime(2026, 7, 27, tzinfo=UTC),
        "summary": "We release a benchmark dataset for language model evaluation.",
    }
    values.update(overrides)
    return RadarItem(**values)


def test_url_canonicalization_removes_tracking():
    assert (
        canonical_url("HTTPS://Example.COM/a/?utm_source=x&keep=y")
        == "https://example.com/a?keep=y"
    )


def test_title_normalization():
    assert normalized_title("  New: AI-Bench! ") == "new ai bench"


def test_dedupe_merges_cross_source_urls():
    first = item()
    second = item(source="GitHub", source_id="org/repo", url="https://github.com/org/repo")
    result = deduplicate([first, second])
    assert len(result) == 1
    assert result[0].artifact_urls == ["https://github.com/org/repo"]


def test_scoring_is_explainable_and_bounded():
    taxonomy = {
        "benchmark": ["benchmark"],
        "evaluation": ["evaluation"],
        "dataset": ["dataset"],
    }
    scored = score_item(item(), taxonomy, datetime(2026, 7, 27, 1, tzinfo=UTC))
    assert scored.categories == ["benchmark", "evaluation", "dataset"]
    assert 0 <= scored.total_score <= 4
    assert any("Matched:" in reason for reason in scored.rationale)


def test_templated_summaries_fail_the_run():
    """Regression: 26/30 records once shared 'Dataset repository updated on
    Hugging Face.', which told the reader nothing and inflated relevance
    because score_item reads `summary`."""
    templated = [
        item(source_id=f"org/repo-{n}", summary="Dataset repository updated on Hugging Face.")
        for n in range(5)
    ]
    with pytest.raises(RuntimeError, match="templated descriptions"):
        assert_no_boilerplate_summaries(templated)


def test_distinct_and_empty_summaries_are_allowed():
    varied = [item(source_id=f"org/repo-{n}", summary=f"Distinct finding {n}.") for n in range(5)]
    # Many empty summaries are legitimate: those repos published no card.
    varied.extend(item(source_id=f"org/bare-{n}", summary="") for n in range(5))
    assert_no_boilerplate_summaries(varied)


def test_boilerplate_summary_cannot_earn_relevance():
    """The old template contained taxonomy words, so every Hugging Face record
    scored a free `dataset` category regardless of its content."""
    taxonomy = {"benchmark": ["benchmark"], "dataset": ["dataset"]}
    bare = score_item(
        item(source="Hugging Face", title="Weyaxi/followers-leaderboard", summary=""),
        taxonomy,
        datetime(2026, 7, 27, 1, tzinfo=UTC),
    )
    assert "dataset" not in bare.categories
