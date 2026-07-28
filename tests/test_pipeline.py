from datetime import UTC, datetime

import pytest

from benchmark_radar.models import RadarItem
from benchmark_radar.pipeline import (
    apply_watchlist,
    assert_no_boilerplate_summaries,
    canonical_url,
    deduplicate,
    normalized_title,
    run_pipeline,
    score_item,
)

WATCHLIST = [
    {"name": "MLE-bench", "aliases": ["mlebench", "mle-bench"], "note": "ML engineering tasks."},
    {"name": "PaperBench", "aliases": ["paperbench"], "note": "Paper replication."},
]


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


def test_watchlist_matches_aliases_across_fields():
    by_title = item(title="PaperBench: replicating research")
    by_source_id = item(source="GitHub", source_id="openai/mle-bench", title="openai/mle-bench")
    unrelated = item(title="An unrelated corpus release")

    tagged = apply_watchlist([by_title, by_source_id, unrelated], WATCHLIST)

    assert [record.watchlist for record in tagged] == ["PaperBench", "MLE-bench", None]
    assert tagged[0].watchlist_note == "Paper replication."
    assert "Watchlist: PaperBench" in tagged[0].rationale


def test_watchlist_ignores_passing_mentions_in_the_summary():
    # A watchlisted name inside an abstract is related work, not a release.
    mention = item(
        title="A survey of agent evaluation practice",
        summary="We compare against PaperBench and other suites.",
    )

    assert apply_watchlist([mention], WATCHLIST)[0].watchlist is None


def test_watchlist_matches_on_word_boundaries_and_separators():
    spaced = item(title="MLE bench results", source_id="a/b")
    underscored = item(title="mle_bench harness", source_id="a/c")
    embedded = item(title="Nonmlebenchmarking of models", source_id="a/d")

    tagged = apply_watchlist([spaced, underscored, embedded], WATCHLIST)

    assert [record.watchlist for record in tagged] == ["MLE-bench", "MLE-bench", None]


def test_watchlist_does_not_alter_scores():
    taxonomy = {"benchmark": ["benchmark"]}
    scored = score_item(item(title="PaperBench"), taxonomy, datetime(2026, 7, 27, tzinfo=UTC))
    before = scored.total_score

    apply_watchlist([scored], WATCHLIST)

    assert scored.watchlist == "PaperBench"
    assert scored.total_score == before


def test_watchlist_record_publishes_below_threshold(monkeypatch):
    # Named artifacts are published even when the generic score would drop them.
    tracked = item(title="mlebench release", summary="", source="GitHub", source_id="o/mlebench")
    monkeypatch.setitem(
        __import__("benchmark_radar.pipeline", fromlist=["SOURCE_FETCHERS"]).SOURCE_FETCHERS,
        "github",
        lambda config, since, limit: [tracked],
    )
    config = {
        "radar": {
            "lookback_hours": 48,
            "max_items_per_source": 10,
            "report_limit": 10,
            "minimum_score": 99,
        },
        "taxonomy": {"benchmark": ["benchmark"]},
        "sources": {"github": {"enabled": True, "required": True}},
        "watchlist": WATCHLIST,
    }

    run = run_pipeline(config, datetime(2026, 7, 27, tzinfo=UTC))

    assert [record.watchlist for record in run.items] == ["MLE-bench"]


def test_selection_counts_expose_the_published_gap(monkeypatch):
    records = [
        item(
            source="GitHub",
            source_id=f"org/repo{index}",
            title=f"A distinct benchmark repository number {index}",
            url=f"https://github.com/org/repo{index}",
            summary=f"Benchmark suite number {index} for language model evaluation.",
        )
        for index in range(5)
    ]
    monkeypatch.setitem(
        __import__("benchmark_radar.pipeline", fromlist=["SOURCE_FETCHERS"]).SOURCE_FETCHERS,
        "github",
        lambda config, since, limit: records,
    )
    config = {
        "radar": {
            "lookback_hours": 48,
            "max_items_per_source": 10,
            "report_limit": 2,
            "minimum_score": 0,
        },
        "taxonomy": {"benchmark": ["benchmark"]},
        "sources": {"github": {"enabled": True, "required": True}},
    }

    run = run_pipeline(config, datetime(2026, 7, 27, tzinfo=UTC))

    assert run.selection["fetched"] == 5
    assert run.selection["qualified"] == 5
    assert run.selection["published"] == 2
    assert len(run.items) == 2


def test_funnel_counts_suppressed_arxiv_records_as_fetched(monkeypatch):
    # Source health counts these as fetched, so the funnel must agree rather
    # than reporting zero for a source that plainly returned records.
    seen = item(source_id="2607.12345", updated_at=datetime(2026, 7, 26, 18, tzinfo=UTC))
    monkeypatch.setitem(
        __import__("benchmark_radar.pipeline", fromlist=["SOURCE_FETCHERS"]).SOURCE_FETCHERS,
        "arxiv",
        lambda config, since, limit: [seen],
    )
    config = {
        "radar": {
            "lookback_hours": 48,
            "max_items_per_source": 10,
            "report_limit": 10,
            "minimum_score": 0,
        },
        "taxonomy": {"benchmark": ["benchmark"]},
        "sources": {"arxiv": {"enabled": True, "required": True}},
    }
    previous = {
        "discovery_state": {
            "arxiv": {
                "2607.12345": {
                    "discovered_at": "2026-07-26T19:00:00+00:00",
                    "last_activity_at": "2026-07-26T18:00:00+00:00",
                }
            }
        }
    }

    run = run_pipeline(config, datetime(2026, 7, 27, tzinfo=UTC), previous_snapshot=previous)

    assert run.items == []
    assert run.health[0].item_count == 1
    assert run.selection["fetched"] == 1
    assert run.selection["suppressed_as_seen"] == 1


def test_funnel_names_watchlist_bypasses_separately(monkeypatch):
    tracked = item(title="mlebench release", summary="", source="GitHub", source_id="o/mlebench")
    monkeypatch.setitem(
        __import__("benchmark_radar.pipeline", fromlist=["SOURCE_FETCHERS"]).SOURCE_FETCHERS,
        "github",
        lambda config, since, limit: [tracked],
    )
    config = {
        "radar": {
            "lookback_hours": 48,
            "max_items_per_source": 10,
            "report_limit": 10,
            "minimum_score": 99,
        },
        "taxonomy": {"benchmark": ["benchmark"]},
        "sources": {"github": {"enabled": True, "required": True}},
        "watchlist": WATCHLIST,
    }

    run = run_pipeline(config, datetime(2026, 7, 27, tzinfo=UTC))

    assert run.selection["qualified"] == 1
    assert run.selection["watchlisted"] == 1


def test_every_required_source_must_return_records(monkeypatch):
    def empty_fetcher(config, since, limit):
        return []

    monkeypatch.setitem(
        __import__("benchmark_radar.pipeline", fromlist=["SOURCE_FETCHERS"]).SOURCE_FETCHERS,
        "required_fixture",
        empty_fetcher,
    )
    config = {
        "radar": {
            "lookback_hours": 48,
            "max_items_per_source": 10,
            "report_limit": 10,
            "minimum_score": 0,
        },
        "taxonomy": {"benchmark": ["benchmark"]},
        "sources": {"required_fixture": {"enabled": True, "required": True}},
    }

    with pytest.raises(
        RuntimeError,
        match="required_fixture returned no records",
    ):
        run_pipeline(config, datetime(2026, 7, 27, tzinfo=UTC))


def test_arxiv_discovery_state_suppresses_unchanged_overlap(monkeypatch):
    unchanged = item(
        source_id="2607.12345",
        updated_at=datetime(2026, 7, 26, 18, tzinfo=UTC),
    )
    monkeypatch.setitem(
        __import__("benchmark_radar.pipeline", fromlist=["SOURCE_FETCHERS"]).SOURCE_FETCHERS,
        "arxiv",
        lambda config, since, limit: [unchanged],
    )
    config = {
        "radar": {
            "lookback_hours": 48,
            "max_items_per_source": 10,
            "report_limit": 10,
            "minimum_score": 0,
        },
        "taxonomy": {"benchmark": ["benchmark"]},
        "sources": {"arxiv": {"enabled": True, "required": True}},
    }
    previous = {
        "discovery_state": {
            "arxiv": {
                "2607.12345": {
                    "discovered_at": "2026-07-26T19:00:00+00:00",
                    "last_activity_at": "2026-07-26T18:00:00+00:00",
                }
            }
        }
    }

    run = run_pipeline(
        config,
        datetime(2026, 7, 27, tzinfo=UTC),
        previous_snapshot=previous,
    )

    assert run.items == []
    assert run.health[0].item_count == 1
    assert run.discovery_state["arxiv"]["2607.12345"]["discovered_at"] == (
        "2026-07-26T19:00:00+00:00"
    )
