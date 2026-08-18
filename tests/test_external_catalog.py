"""Tests for the external catalog normalizer.

The assertions here are deliberately about invariants rather than about field
values. Three of them (`comparable_group` always null, `display_scale` always
null, provenance always empty for llm-stats) are the properties the site is
allowed to rely on when it refuses to rank across sources, refuses to draw a
percentage bar, and renders "not established" instead of a guess. If one of
those ever becomes merely usually true, the honesty rules downstream become
advisory, so they are pinned here at 100%.
"""

from pathlib import Path

import pytest
import yaml

from benchmark_radar.external_catalog import (
    ExternalCatalogError,
    normalize_llm_stats,
    slugify,
    write_llm_stats_catalog,
)
from benchmark_radar.leaderboard_snapshots import (
    DEFAULT_SNAPSHOTS_PATH,
    LeaderboardSnapshotError,
    load_snapshots,
)

LLM_STATS_SNAPSHOT_ID = "llm_stats_2026-08-17"

# Known defects in the 2026-08-17 crawl, asserted rather than tolerated so a
# future recrawl that silently changes them fails loudly.
ZERO_OBSERVATION_KEYS = {
    "llm-stats:community:07c9946d-dcf0-4977-a640-a6b1356b4f0b",
    "llm-stats:community:2256e9c9-b256-4444-b639-7cc3b1855d96",
    "llm-stats:community:5f95f778-c521-43fa-b80e-6a55465601e3",
    "llm-stats:community:64d67847-06bd-423a-923c-c2acfab82281",
    "llm-stats:community:ed90e889-4678-4fbd-98ab-0e654f4bf35e",
    "llm-stats:community:fd462fc2-283c-4967-bd7d-b39d7c661807",
    "llm-stats:cvtg-2k",
    "llm-stats:longtext-bench",
}
CONTRADICTED_KEYS = {"llm-stats:frontier-swe-impl", "llm-stats:vending-bench-2"}


@pytest.fixture(scope="module")
def normalized() -> dict:
    snapshots = load_snapshots(DEFAULT_SNAPSHOTS_PATH)
    snapshot = next(
        item for item in snapshots["snapshots"] if item["id"] == LLM_STATS_SNAPSHOT_ID
    )
    return normalize_llm_stats(snapshot)


def test_counts_match_the_declared_snapshot(normalized: dict) -> None:
    assert len(normalized["source_records"]) == 687
    assert len(normalized["score_series"]) == 687
    assert len(normalized["score_observations"]) == 5544


def test_obs_id_is_unique(normalized: dict) -> None:
    """Without this a rerun silently duplicates every score row."""
    obs_ids = [row["obs_id"] for row in normalized["score_observations"]]
    assert len(set(obs_ids)) == len(obs_ids)
    assert normalized["validation"]["obs_id_unique"] is True


def test_no_observation_carries_a_comparability_class(normalized: dict) -> None:
    """Null never joins to null, so nothing here can be ranked or trended."""
    assert all(row["comparable_group"] is None for row in normalized["score_observations"])
    assert normalized["validation"]["comparable_group_null_fraction"] == 1.0


def test_no_series_offers_a_display_scale(normalized: dict) -> None:
    """vending-bench-2 declares max 1.0 and carries 8017.59; no bar is drawable."""
    assert all(row["display_scale"] is None for row in normalized["score_series"])
    assert normalized["validation"]["display_scale_null_fraction"] == 1.0


def test_llm_stats_records_claim_no_provenance(normalized: dict) -> None:
    """The API has no author, paper, licence or size field. Empty is the answer."""
    for record in normalized["source_records"]:
        assert record["publisher"] is None
        assert record["artifacts"] == []
        assert record["sizes"] == []
        assert record["openness"]["status"] == "unknown"
        assert record["openness"]["code_license"] is None
        assert record["openness"]["data_license"] is None
        assert record["released"] is None
    assert normalized["validation"]["empty_provenance_fraction"] == 1.0


def test_metric_and_direction_are_never_guessed(normalized: dict) -> None:
    for row in normalized["score_series"]:
        assert row["metric"] is None
        assert row["direction"] is None
        assert row["bounds"]["basis"] == "aggregator_declared"


def test_verified_column_is_dropped(normalized: dict) -> None:
    """It is False on all 5544 rows, so carrying it implies a distinction."""
    assert all("verified" not in row for row in normalized["score_observations"])


def test_reported_by_split_matches_the_source(normalized: dict) -> None:
    assert normalized["validation"]["reported_by_distribution"] == {
        "self_reported": 5410,
        "third_party": 134,
    }


def test_slugs_are_filename_safe_and_unique(normalized: dict) -> None:
    slugs = [record["slug"] for record in normalized["source_records"]]
    assert len(set(slugs)) == len(slugs)
    for slug in slugs:
        assert ":" not in slug
        assert "/" not in slug
        assert slug == slug.lower()
        assert slug.strip("-") == slug


def test_community_uuid_keys_survive_slugging(normalized: dict) -> None:
    """Colon-bearing ids are exactly what a naive filename scheme breaks on."""
    record = next(
        item
        for item in normalized["source_records"]
        if item["key"] == "llm-stats:community:07c9946d-dcf0-4977-a640-a6b1356b4f0b"
    )
    assert record["slug"] == "llm-stats-community-07c9946d-dcf0-4977-a640-a6b1356b4f0b"


def test_known_zero_score_benchmarks_are_kept_not_dropped(normalized: dict) -> None:
    """Counted, not dropped, is the whole point of the external key."""
    keys = {record["key"] for record in normalized["source_records"]}
    assert ZERO_OBSERVATION_KEYS <= keys
    assert set(normalized["validation"]["benchmarks_with_zero_observations"]) == (
        ZERO_OBSERVATION_KEYS
    )


def test_max_score_contradiction_is_recorded_as_fact(normalized: dict) -> None:
    contradicted = {
        row["key"] for row in normalized["score_series"] if row["max_score_contradicted"]
    }
    assert contradicted == CONTRADICTED_KEYS
    assert normalized["validation"]["max_score_contradicted_row_count"] == 5


def test_contradicted_values_are_not_rescaled(normalized: dict) -> None:
    """A declared max of 1.0 does not license rewriting an 8017.59 observation."""
    values = [
        row["value"]
        for row in normalized["score_observations"]
        if row["key"] == "llm-stats:vending-bench-2"
    ]
    assert max(values) == pytest.approx(8017.59)


def test_no_max_score_trustworthy_judgement_is_emitted(normalized: dict) -> None:
    """Mechanically checkable facts only; "obviously a placeholder" is an opinion."""
    for row in normalized["score_series"]:
        assert "max_score_trustworthy" not in row


def test_output_is_byte_identical_across_runs(normalized: dict, tmp_path: Path) -> None:
    first = write_llm_stats_catalog(normalized, tmp_path / "a")
    second = write_llm_stats_catalog(normalize_llm_stats_again(), tmp_path / "b")
    for name, path in first.items():
        assert path.read_bytes() == second[name].read_bytes()


def normalize_llm_stats_again() -> dict:
    snapshots = load_snapshots(DEFAULT_SNAPSHOTS_PATH)
    snapshot = next(
        item for item in snapshots["snapshots"] if item["id"] == LLM_STATS_SNAPSHOT_ID
    )
    return normalize_llm_stats(snapshot)


def test_slugify_rejects_a_key_with_nothing_usable() -> None:
    with pytest.raises(ExternalCatalogError):
        slugify(":::")


def write_registry(tmp_path: Path, rows: int) -> Path:
    """A minimal snapshot registry whose declared count can be made to drift."""
    directory = tmp_path / "files"
    directory.mkdir()
    csv_path = directory / "bench.csv"
    lines = ["benchmark_id,name"] + [f"b{index},Bench {index}" for index in range(rows)]
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    registry = tmp_path / "leaderboard_snapshots.yml"
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "snapshots": [
                    {
                        "id": "test",
                        "source": "Test",
                        "source_url": "https://example.invalid/",
                        "crawled_at": "2026-08-17T00:00:00+00:00",
                        "benchmark_file": "files/bench.csv",
                        "benchmark_count": 3,
                        "columns": {"benchmark_id": "benchmark_id", "benchmark_name": "name"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return registry


def test_loader_accepts_a_file_matching_its_declaration(tmp_path: Path) -> None:
    loaded = load_snapshots(write_registry(tmp_path, rows=3))
    assert len(loaded["snapshots"][0]["benchmark_rows"]) == 3


def test_loader_rejects_a_file_whose_row_count_drifted(tmp_path: Path) -> None:
    """A truncated copy would otherwise look identical to a complete snapshot."""
    with pytest.raises(LeaderboardSnapshotError, match="registry declares 3"):
        load_snapshots(write_registry(tmp_path, rows=2))


def test_opencompass_normalizes_and_cleans_licences() -> None:
    """NOASSERTION is the absence of an identification, not a licence."""
    from benchmark_radar.external_opencompass import normalize_opencompass

    result = normalize_opencompass()
    assert result["validation"]["source_record_count"] == 461
    for record in result["source_records"]:
        assert record["openness"]["status"] in {"open", "restricted", "unknown"}
        assert record["openness"]["code_license"] != "NOASSERTION"
        assert record["openness"]["data_license"] != "NOASSERTION"
        # A stringified list would make '["mit"]' and 'MIT' two licences.
        for field in ("code_license", "data_license"):
            value = record["openness"][field]
            assert value is None or not value.startswith("[")
    assert result["validation"]["license_file_present_unparsed"] == 32


def test_opencompass_publisher_is_labelled_as_the_hub_publisher() -> None:
    """publishOrg is who posted the card, often not who made the benchmark."""
    from benchmark_radar.external_opencompass import normalize_opencompass

    for record in normalize_opencompass()["source_records"]:
        if record["publisher"]:
            assert record["publisher"]["role"] == "hub_publisher"


def test_index_has_one_row_per_source_record(normalized: dict) -> None:
    """Merging two sources into one row is a claim identity.yml has to make."""
    from benchmark_radar.external_catalog import build_benchmark_index
    from benchmark_radar.external_opencompass import normalize_opencompass

    records = normalized["source_records"] + normalize_opencompass()["source_records"]
    index = build_benchmark_index(
        records, {row["key"]: row for row in normalized["score_series"]}
    )
    assert len(index) == 1148
    assert len({row["key"] for row in index}) == 1148
    assert len({row["slug"] for row in index}) == 1148
