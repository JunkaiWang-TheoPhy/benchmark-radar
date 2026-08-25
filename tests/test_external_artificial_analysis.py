"""Artificial Analysis normalization: the invariants the rest of the system relies on.

The committed snapshot is the fixture. These tests pin what the source actually
shipped on 2026-08-25, so a recrawl that quietly loses a metric component, drops
a model, or promotes an unproven canonical identity fails here rather than on
the published site.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark_radar.external_artificial_analysis import (
    ARTIFICIAL_ANALYSIS_SOURCE,
    DEFAULT_SNAPSHOT_DIR,
    normalize_artificial_analysis,
    write_artificial_analysis_catalog,
)
from benchmark_radar.external_catalog import ExternalCatalogError

pytestmark = pytest.mark.skipif(
    not (DEFAULT_SNAPSHOT_DIR / "artificial_analysis_manifest_2026-08-25.json").exists(),
    reason="Artificial Analysis snapshot is not present",
)


@pytest.fixture(scope="module")
def normalized() -> dict:
    return normalize_artificial_analysis()


def test_counts_match_the_shipped_manifest(normalized: dict) -> None:
    report = normalized["validation"]
    assert report["source_record_count"] == 24
    assert report["score_series_count"] == 24
    assert report["score_observation_count"] == 7050
    assert report["model_count"] == 618
    # 618 models were captured; 23 sit in the catalog without appearing on any
    # of the 24 leaderboards. That gap is a fact about the source, not a loss.
    assert report["scored_model_count"] == 595
    assert report["models_without_scores"] == 23


def test_every_observation_is_a_number(normalized: dict) -> None:
    assert normalized["validation"]["value_kind_distribution"] == {"number": 7050}


def test_observation_ids_are_unique_across_metric_components(normalized: dict) -> None:
    """GDPval publishes two numbers per model; they are two rows, not a clash."""
    observations = normalized["score_observations"]
    assert len({obs["obs_id"] for obs in observations}) == len(observations)
    assert normalized["validation"]["obs_id_unique"] is True


def test_both_gdpval_components_survive(normalized: dict) -> None:
    """The reason this source does not go through the flat snapshot registry."""
    series = next(
        item for item in normalized["score_series"] if item["key"].endswith(":gdpval-aa-v2")
    )
    components = {item["component"]: item for item in series["components"]}
    assert set(components) == {"raw_elo", "normalized_score"}
    assert components["raw_elo"]["observation_count"] == 213
    assert components["normalized_score"]["observation_count"] == 213
    assert series["observation_count"] == 426
    # The Elo scale is not a percentage and is never rescaled into one.
    assert components["raw_elo"]["unit"] == "Elo"
    assert components["raw_elo"]["observed_max"] > 100


def test_gdpval_is_the_only_multi_component_evaluation(normalized: dict) -> None:
    assert normalized["validation"]["multi_component_evaluations"] == [
        "artificial-analysis:gdpval-aa-v2"
    ]


def test_raw_values_are_kept_beside_normalized_ones(normalized: dict) -> None:
    """Normalization is an extra column, never a replacement for what was published."""
    for obs in normalized["score_observations"]:
        assert obs["raw_value"]
        assert obs["value"] is not None
        if obs["normalized_value_0_100"] is not None:
            assert obs["normalization_basis"]


def test_unnormalized_rows_stay_null(normalized: dict) -> None:
    """278 rows carry no source normalization; none is invented here."""
    missing = [
        obs for obs in normalized["score_observations"] if obs["normalized_value_0_100"] is None
    ]
    assert len(missing) == 278


def test_every_row_carries_the_source_protocol_group(normalized: dict) -> None:
    """This source ran the test and states its method version, unlike llm-stats."""
    assert normalized["validation"]["source_comparable_group_null_fraction"] == 0.0
    for obs in normalized["score_observations"]:
        assert obs["source_comparable_group"].startswith("artificial-analysis:")
        assert obs["measurement_owner"] == "Artificial Analysis"
        assert obs["reported_by"] == "third_party"


def test_the_curated_comparability_field_stays_null(normalized: dict) -> None:
    """The source's grouping of its own runs never becomes a licence to join a
    curated line. Two different claims, two different field names."""
    assert normalized["validation"]["comparable_group_null_fraction"] == 1.0
    for obs in normalized["score_observations"]:
        assert obs["comparable_group"] is None


def test_dates_are_labelled_as_model_releases_not_measurements(normalized: dict) -> None:
    """`evaluated_at` is empty on all 7,050 rows, so the label has to say so."""
    for obs in normalized["score_observations"]:
        assert obs["date_precision"] == "model_announcement"


def test_no_record_claims_provenance_the_source_does_not_publish(normalized: dict) -> None:
    for record in normalized["source_records"]:
        assert record["source"] == ARTIFICIAL_ANALYSIS_SOURCE
        assert record["publisher"] is None
        assert record["artifacts"] == []
        assert record["sizes"] == []
        assert record["openness"]["status"] == "unknown"


def test_keys_and_slugs_are_unique(normalized: dict) -> None:
    records = normalized["source_records"]
    assert len({record["key"] for record in records}) == len(records)
    assert len({record["slug"] for record in records}) == len(records)


def test_no_canonical_identity_is_asserted_yet(normalized: dict) -> None:
    """All 24 mappings ship as needs_review, so no adoption count can move."""
    identity = normalized["validation"]["identity_candidates"]
    assert identity["mapping_count"] == 24
    assert identity["resolved_canonical_count"] == 0
    assert identity["resolution_status_counts"] == {"needs_review": 24}


def test_a_canonical_claim_without_two_anchors_is_refused(tmp_path: Path) -> None:
    """The gate a later hand-promoted mapping has to pass."""
    import shutil

    import yaml

    snapshot = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot)
    identity_path = snapshot / "artificial_analysis_identity_candidates_2026-08-25.yml"
    document = yaml.safe_load(identity_path.read_text(encoding="utf-8"))
    document["mappings"][0]["canonical_benchmark_id"] = "gpqa"
    document["mappings"][0]["evidence"] = ["https://example.org/one-anchor"]
    identity_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ExternalCatalogError, match="anchors"):
        normalize_artificial_analysis(snapshot)


def test_a_truncated_scores_file_is_refused(tmp_path: Path) -> None:
    """A partial rerun must not publish as a complete snapshot."""
    import shutil

    snapshot = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot)
    scores = snapshot / "artificial_analysis_scores_2026-08-25.csv"
    lines = scores.read_text(encoding="utf-8").splitlines(keepends=True)
    scores.write_text("".join(lines[:-10]), encoding="utf-8")

    with pytest.raises(ExternalCatalogError, match="score_row_count"):
        normalize_artificial_analysis(snapshot)


def test_a_renamed_upstream_column_fails_loudly(tmp_path: Path) -> None:
    import shutil

    snapshot = tmp_path / "snapshot"
    shutil.copytree(DEFAULT_SNAPSHOT_DIR, snapshot)
    evaluations = snapshot / "artificial_analysis_evaluations_2026-08-25.csv"
    text = evaluations.read_text(encoding="utf-8")
    evaluations.write_text(text.replace('"metric"', '"metric_name"', 1), encoding="utf-8")

    with pytest.raises(ExternalCatalogError, match="missing columns"):
        normalize_artificial_analysis(snapshot)


def test_rebuild_is_byte_identical(normalized: dict, tmp_path: Path) -> None:
    """No build timestamp, sorted keys: an unchanged input shows an empty diff."""
    first = write_artificial_analysis_catalog(normalized, tmp_path / "first")
    second = write_artificial_analysis_catalog(normalize_artificial_analysis(), tmp_path / "second")
    for name, path in first.items():
        assert path.read_bytes() == second[name].read_bytes()


def test_shards_file_scores_under_this_source_not_llm_stats(
    normalized: dict, tmp_path: Path
) -> None:
    """Filing one source's rows under another's name would be the merge we forbid."""
    from benchmark_radar.external_identity import IdentityIndex
    from benchmark_radar.external_shards import write_shards

    write_shards(
        normalized["source_records"],
        identity=IdentityIndex(),
        series=normalized["score_series"],
        observations=normalized["score_observations"],
        output_dir=tmp_path / "benchmarks",
    )
    for path in (tmp_path / "benchmarks").glob("*.json"):
        shard = json.loads(path.read_text(encoding="utf-8"))
        assert set(shard["scores_by_source"]) == {ARTIFICIAL_ANALYSIS_SOURCE}
