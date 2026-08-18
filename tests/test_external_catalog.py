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
    snapshot = next(item for item in snapshots["snapshots"] if item["id"] == LLM_STATS_SNAPSHOT_ID)
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
    snapshot = next(item for item in snapshots["snapshots"] if item["id"] == LLM_STATS_SNAPSHOT_ID)
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
    index = build_benchmark_index(records, {row["key"]: row for row in normalized["score_series"]})
    assert len(index) == 1148
    assert len({row["key"] for row in index}) == 1148
    assert len({row["slug"] for row in index}) == 1148


@pytest.fixture(scope="module")
def all_records(normalized: dict) -> list[dict]:
    from benchmark_radar.external_opencompass import normalize_opencompass

    return normalized["source_records"] + normalize_opencompass()["source_records"]


# Identity candidate generation


def test_candidates_only_promote_pairs_sharing_two_anchors(all_records: list[dict]) -> None:
    """A shared name is not an anchor; two independent anchors is the bar."""
    from benchmark_radar.external_identity import _anchors, build_identity_candidates

    candidates = build_identity_candidates(all_records)
    by_key = {record["key"]: record for record in all_records}
    for candidate in candidates["equivalent_candidates"]:
        left, right = candidate["members"]
        shared = _anchors(by_key[left]) & _anchors(by_key[right])
        assert len(shared) >= 2
        assert set(candidate["anchors"]) == shared


def test_name_only_block_is_cross_source_and_not_anchor_backed(
    all_records: list[dict],
) -> None:
    """The MMLU-Pro-twice case: same name across crawls, no shared anchor."""
    from benchmark_radar.external_identity import _anchors, build_identity_candidates

    candidates = build_identity_candidates(all_records)
    by_key = {record["key"]: record for record in all_records}
    names = {pair["name"] for pair in candidates["name_only"]}
    assert "MMLU-Pro" in names
    for pair in candidates["name_only"]:
        left, right = pair["members"]
        assert by_key[left]["source"] != by_key[right]["source"]
        assert len(_anchors(by_key[left]) & _anchors(by_key[right])) < 2


def test_llm_stats_records_have_no_anchors(all_records: list[dict]) -> None:
    """llm-stats carries no artifacts, so no llm-stats pair can ever auto-merge."""
    from benchmark_radar.external_identity import _anchors

    for record in all_records:
        if record["source"] == "llm_stats":
            assert _anchors(record) == set()


# Identity loader


def _write_identity(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "identity.yml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_identity_seed_loads_against_the_records(all_records: list[dict]) -> None:
    """The checked-in seed must resolve against the real records or the build lies."""
    from benchmark_radar.external_identity import DEFAULT_IDENTITY_PATH, load_identity

    identity = load_identity(all_records, DEFAULT_IDENTITY_PATH)
    # Every seed variant is cross-linked both ways as a sibling.
    assert identity.siblings_for("opencompass:517")  # RACE(Middle) -> RACE(High)
    assert identity.siblings_for("opencompass:516")  # and back


def test_loader_rejects_equivalent_group_with_one_anchor(
    all_records: list[dict], tmp_path: Path
) -> None:
    """One anchor is a candidate, not an equivalence. This is the enforcement point."""
    from benchmark_radar.external_identity import IdentityError, load_identity

    member = all_records[0]["key"]
    other = all_records[1]["key"]
    path = _write_identity(
        tmp_path,
        {
            "schema_version": 1,
            "equivalent": [{"group_id": "g", "members": [member, other], "anchors": ["arxiv:1"]}],
        },
    )
    with pytest.raises(IdentityError, match="two independent anchors"):
        load_identity(all_records, path)


def test_loader_rejects_member_that_is_not_a_record(
    all_records: list[dict], tmp_path: Path
) -> None:
    from benchmark_radar.external_identity import IdentityError, load_identity

    path = _write_identity(
        tmp_path,
        {
            "schema_version": 1,
            "equivalent": [
                {
                    "group_id": "g",
                    "members": ["llm-stats:does-not-exist", all_records[0]["key"]],
                    "anchors": ["arxiv:1", "gh:a/b"],
                }
            ],
        },
    )
    with pytest.raises(IdentityError, match="not a source record"):
        load_identity(all_records, path)


def test_loader_rejects_duplicate_group_id(all_records: list[dict], tmp_path: Path) -> None:
    from benchmark_radar.external_identity import IdentityError, load_identity

    a, b, c = (record["key"] for record in all_records[:3])
    group = {"members": [a, b], "anchors": ["arxiv:1", "gh:a/b"]}
    path = _write_identity(
        tmp_path,
        {
            "schema_version": 1,
            "equivalent": [
                {"group_id": "dup", **group},
                {"group_id": "dup", "members": [c], "anchors": ["arxiv:2", "gh:c/d"]},
            ],
        },
    )
    with pytest.raises(IdentityError, match="duplicate group_id"):
        load_identity(all_records, path)


def test_loader_rejects_key_in_two_equivalent_groups(
    all_records: list[dict], tmp_path: Path
) -> None:
    from benchmark_radar.external_identity import IdentityError, load_identity

    a, b, c = (record["key"] for record in all_records[:3])
    path = _write_identity(
        tmp_path,
        {
            "schema_version": 1,
            "equivalent": [
                {"group_id": "g1", "members": [a, b], "anchors": ["arxiv:1", "gh:a/b"]},
                {"group_id": "g2", "members": [a, c], "anchors": ["arxiv:2", "gh:c/d"]},
            ],
        },
    )
    with pytest.raises(IdentityError, match="two equivalent groups"):
        load_identity(all_records, path)


def test_loader_rejects_wrong_schema_version(all_records: list[dict], tmp_path: Path) -> None:
    from benchmark_radar.external_identity import IdentityError, load_identity

    path = _write_identity(tmp_path, {"schema_version": 99, "equivalent": []})
    with pytest.raises(IdentityError, match="schema_version"):
        load_identity(all_records, path)


def test_missing_identity_file_is_not_an_error(all_records: list[dict], tmp_path: Path) -> None:
    """The identity layer is the one piece the catalog can ship without."""
    from benchmark_radar.external_identity import load_identity

    identity = load_identity(all_records, tmp_path / "absent.yml")
    assert identity.siblings_for(all_records[0]["key"]) == []


# Shards


@pytest.fixture(scope="module")
def shard_inputs(normalized: dict, all_records: list[dict]) -> dict:
    from benchmark_radar.external_identity import DEFAULT_IDENTITY_PATH, load_identity

    return {
        "records": all_records,
        "identity": load_identity(all_records, DEFAULT_IDENTITY_PATH),
        "series": normalized["score_series"],
        "observations": normalized["score_observations"],
    }


def _build_all_shards(shard_inputs: dict, output_dir: Path) -> dict:
    from benchmark_radar.external_shards import write_shards

    return write_shards(
        shard_inputs["records"],
        identity=shard_inputs["identity"],
        series=shard_inputs["series"],
        observations=shard_inputs["observations"],
        output_dir=output_dir,
    )


def test_one_shard_per_source_record(shard_inputs: dict, tmp_path: Path) -> None:
    report = _build_all_shards(shard_inputs, tmp_path / "benchmarks")
    files = list((tmp_path / "benchmarks").glob("*.json"))
    assert report["shard_count"] == 1148
    assert len(files) == 1148


def test_scores_are_a_keyed_object_never_a_flat_array(shard_inputs: dict, tmp_path: Path) -> None:
    """A keyed object cannot be .sort()ed into a cross-source ranking."""
    import json

    _build_all_shards(shard_inputs, tmp_path / "benchmarks")
    for path in (tmp_path / "benchmarks").glob("*.json"):
        shard = json.loads(path.read_text(encoding="utf-8"))
        scores = shard["scores_by_source"]
        assert isinstance(scores, dict)
        for source, block in scores.items():
            # No `source` field lives on a row: the source is the key, so the
            # rows of two sources are never in one flattenable list.
            for row in block["rows"]:
                assert "source" not in row
            assert source == "llm_stats"


def test_llm_stats_shard_carries_its_scores(shard_inputs: dict, tmp_path: Path) -> None:
    import json

    _build_all_shards(shard_inputs, tmp_path / "benchmarks")
    shard = json.loads(
        (tmp_path / "benchmarks" / "llm-stats-gpqa.json").read_text(encoding="utf-8")
    )
    block = shard["scores_by_source"]["llm_stats"]
    assert len(block["rows"]) == 239
    assert block["series"]["display_scale"] is None


def test_opencompass_shard_has_empty_scores(shard_inputs: dict, tmp_path: Path) -> None:
    """OpenCompass supplies no observations, so absence renders as absence."""
    import json

    _build_all_shards(shard_inputs, tmp_path / "benchmarks")
    shard = json.loads(
        (tmp_path / "benchmarks" / "opencompass-498-mmlu.json").read_text(encoding="utf-8")
    )
    assert shard["scores_by_source"] == {}


def test_zero_score_llm_stats_record_still_gets_a_shard(shard_inputs: dict, tmp_path: Path) -> None:
    """Counted, not dropped: a benchmark with no scores is still addressable."""
    _build_all_shards(shard_inputs, tmp_path / "benchmarks")
    assert (tmp_path / "benchmarks" / "llm-stats-cvtg-2k.json").exists()


def test_variant_siblings_are_cross_linked_in_the_shard(shard_inputs: dict, tmp_path: Path) -> None:
    import json

    _build_all_shards(shard_inputs, tmp_path / "benchmarks")
    shard = json.loads(
        (tmp_path / "benchmarks" / "opencompass-517-race-middle.json").read_text(encoding="utf-8")
    )
    siblings = {sibling["key"] for sibling in shard["siblings"]}
    assert "opencompass:516" in siblings


def test_stale_shards_are_swapped_out(shard_inputs: dict, tmp_path: Path) -> None:
    """A removed benchmark must not leave a live URL serving last month's data."""
    output_dir = tmp_path / "benchmarks"
    _build_all_shards(shard_inputs, output_dir)
    stale = output_dir / "ghost-benchmark.json"
    stale.write_text("{}", encoding="utf-8")
    _build_all_shards(shard_inputs, output_dir)
    assert not stale.exists()


def test_shards_are_byte_identical_across_runs(shard_inputs: dict, tmp_path: Path) -> None:
    _build_all_shards(shard_inputs, tmp_path / "a")
    _build_all_shards(shard_inputs, tmp_path / "b")
    for path in (tmp_path / "a").glob("*.json"):
        assert path.read_bytes() == (tmp_path / "b" / path.name).read_bytes()
