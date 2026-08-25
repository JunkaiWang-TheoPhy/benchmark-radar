"""Artificial Analysis: what the reshape had to decide, pinned.

The source arrived as three normalized tables joined by id. It is committed as
two denormalized CSVs in the llm-stats header vocabulary, reshaped by
`scripts/reshape_artificial_analysis.py`, and read by the same normalizer every
other crawl goes through. These tests pin the decisions that reshape made, so a
recrawl that quietly rejoins two metrics, respells a vendor, or renames an
already-published model fails here rather than on the site.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from benchmark_radar.external_catalog import (
    ARTIFICIAL_ANALYSIS_KEY_PREFIX,
    ARTIFICIAL_ANALYSIS_SNAPSHOT_ID,
    ARTIFICIAL_ANALYSIS_SOURCE,
    LLM_STATS_SOURCE,
    normalize_snapshot,
)
from benchmark_radar.leaderboard_snapshots import DEFAULT_SNAPSHOTS_PATH, load_snapshots

SCORES_CSV = Path("data/leaderboard_snapshots/artificial_analysis_benchmark_scores_2026-08-25.csv")

GDPVAL_ELO = f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:gdpval-aa-v2:raw_elo"
GDPVAL_NORMALIZED = f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:gdpval-aa-v2:normalized_score"


@pytest.fixture(scope="module")
def normalized() -> dict:
    snapshots = load_snapshots(DEFAULT_SNAPSHOTS_PATH)
    snapshot = next(
        item for item in snapshots["snapshots"] if item["id"] == ARTIFICIAL_ANALYSIS_SNAPSHOT_ID
    )
    return normalize_snapshot(snapshot)


def test_counts_match_the_registered_snapshot(normalized: dict) -> None:
    report = normalized["validation"]
    # 24 evaluations, one of which publishes two metrics and so is two rows.
    assert report["source_record_count"] == 25
    assert report["score_series_count"] == 25
    assert report["score_observation_count"] == 7050
    assert report["value_kind_distribution"] == {"number": 7050}
    assert len({obs["model_id"] for obs in normalized["score_observations"]}) == 595


def test_the_shared_normalizer_reads_this_source(normalized: dict) -> None:
    """No second module: the only thing this source varies is three strings."""
    for record in normalized["source_records"]:
        assert record["source"] == ARTIFICIAL_ANALYSIS_SOURCE
        assert record["key"].startswith(f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:")
        assert record["provenance"]["crawl_bundle"] == ARTIFICIAL_ANALYSIS_SNAPSHOT_ID


def test_every_row_is_measured_by_the_aggregator_not_the_vendor(normalized: dict) -> None:
    """The opposite of llm-stats, and the reason the point card reads the row."""
    assert normalized["validation"]["reported_by_distribution"] == {"third_party": 7050}


def test_the_curated_comparability_field_stays_null(normalized: dict) -> None:
    """This source ran the tests itself, which is a fact about who measured, not
    a protocol. No crawled row may join a curated line.
    """
    assert normalized["validation"]["comparable_group_null_fraction"] == 1.0
    assert normalized["validation"]["display_scale_null_fraction"] == 1.0


def test_dates_are_labelled_as_model_releases_not_measurements(normalized: dict) -> None:
    for obs in normalized["score_observations"]:
        assert obs["date_precision"] == "model_announcement"


def test_a_new_source_cannot_rename_an_existing_model() -> None:
    """`model_key` folds punctuation and case, so "GPT-5 High" and "GPT-5 (high)"
    are one model with two spellings, and whoever is read first names it. Left
    to the shard glob that was alphabetical by filename, which silently renamed
    22 already-published models and orphaned their frozen logo IDs.
    """
    from benchmark_radar.models_registry import _CRAWLED_SOURCE_PRECEDENCE

    # llm-stats is the incumbent: its spellings are already published and
    # already carry logo IDs, so it names the models it shares with a newcomer.
    assert _CRAWLED_SOURCE_PRECEDENCE.index(LLM_STATS_SOURCE) < _CRAWLED_SOURCE_PRECEDENCE.index(
        ARTIFICIAL_ANALYSIS_SOURCE
    )


def test_vendor_spellings_fold_into_one_organization(normalized: dict) -> None:
    """Confirmed by reading the model lines on both sides, not by name shape:
    unmapped, these were 20 duplicate models, one under each spelling.
    """
    organizations = {obs["organization"] for obs in normalized["score_observations"]}
    for spelling in ("Alibaba", "Kimi", "SpaceXAI", "Z AI"):
        assert spelling not in organizations
    for canonical in ("Qwen", "Moonshot AI", "xAI", "Z.ai"):
        assert canonical in organizations


def test_a_two_metric_evaluation_is_two_benchmarks(normalized: dict) -> None:
    """A chart draws one metric per axis. GDPval-AA v2's Elo runs past 1,800 and
    its normalized score stops below 1, so on one axis the normalized half
    collapses onto the baseline and the best score reads off the Elo half. The
    split happens in the crawl, so the two never share a series to be picked
    apart downstream.
    """
    by_key = {item["key"]: item for item in normalized["score_series"]}
    assert {GDPVAL_ELO, GDPVAL_NORMALIZED} <= set(by_key)
    assert f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:gdpval-aa-v2" not in by_key

    elo = [obs for obs in normalized["score_observations"] if obs["key"] == GDPVAL_ELO]
    normal = [obs for obs in normalized["score_observations"] if obs["key"] == GDPVAL_NORMALIZED]
    assert len(elo) == len(normal) == 213
    # Two scales, which is why they are two rows and not one.
    assert max(obs["value"] for obs in elo) > 1000
    assert max(obs["value"] for obs in normal) <= 1

    # Each half names the metric it carries, so a reader comparing this against
    # the source's own page knows which number they are looking at.
    records = {item["key"]: item["name"] for item in normalized["source_records"]}
    assert records[GDPVAL_ELO].endswith("(Elo)")
    assert records[GDPVAL_NORMALIZED].endswith("(normalized score)")


def test_single_metric_evaluations_keep_their_own_id(normalized: dict) -> None:
    """The split shows up only where the source published a second number."""
    split = {
        record["key"]
        for record in normalized["source_records"]
        if ":" in record["source_benchmark_id"]
    }
    assert split == {GDPVAL_ELO, GDPVAL_NORMALIZED}


def test_the_crawl_holds_one_row_per_benchmark_and_model() -> None:
    """The invariant the registry format requires and the three-table crawl
    could not satisfy. Checked on the committed CSV, because that is the file
    the loader reads.
    """
    with SCORES_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    pairs = {(row["benchmark_id"], row["model_id"]) for row in rows}
    assert len(rows) == 7050
    assert len(pairs) == len(rows)


def test_no_record_claims_provenance_the_source_does_not_publish(normalized: dict) -> None:
    assert normalized["validation"]["empty_provenance_fraction"] == 1.0
    for record in normalized["source_records"]:
        assert record["openness"]["status"] == "unknown"
        assert record["publisher"] is None
