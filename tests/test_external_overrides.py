"""Reviewed llm-stats identity must reach every generated catalog surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from benchmark_radar.external_catalog import (
    build_benchmark_index,
    normalize_snapshot,
    write_catalog,
)
from benchmark_radar.external_overrides import (
    DEFAULT_LLM_STATS_IDENTITY_OVERRIDES_PATH,
    IdentityOverrideError,
    apply_llm_stats_identity_overrides,
    load_llm_stats_identity_overrides,
    overridden_validation,
)
from benchmark_radar.leaderboard_snapshots import DEFAULT_SNAPSHOTS_PATH, load_snapshots

LLM_STATS_SNAPSHOT_ID = "llm_stats_2026-08-17"


@pytest.fixture(scope="module")
def normalized() -> dict:
    snapshots = load_snapshots(DEFAULT_SNAPSHOTS_PATH)
    snapshot = next(item for item in snapshots["snapshots"] if item["id"] == LLM_STATS_SNAPSHOT_ID)
    return normalize_snapshot(snapshot)


@pytest.fixture(scope="module")
def overrides(normalized: dict):
    return load_llm_stats_identity_overrides(
        normalized["source_records"], DEFAULT_LLM_STATS_IDENTITY_OVERRIDES_PATH
    )


@pytest.fixture(scope="module")
def enriched(normalized: dict, overrides) -> list[dict]:
    return apply_llm_stats_identity_overrides(normalized["source_records"], overrides)


def test_checked_in_overrides_cover_every_phase_a_outcome(overrides) -> None:
    assert overrides.validation == {
        "override_count": 57,
        "resolution_status_counts": {
            "needs_review": 2,
            "not_found": 9,
            "resolved": 46,
        },
        "repo_kind_counts": {
            "benchmark_source": 25,
            "harness_only": 3,
            "monorepo_subdir": 3,
            "not_found": 11,
            "shared_parent": 15,
        },
    }


def test_all_resolved_overrides_become_searchable_repository_artifacts(
    enriched: list[dict],
) -> None:
    index = build_benchmark_index(enriched)
    resolved = [row for row in index if row["repo_resolution_status"] == "resolved"]

    assert len(resolved) == 46
    assert all(row["has_repo"] for row in resolved)
    assert {row["repo_kind"] for row in resolved} == {
        "benchmark_source",
        "harness_only",
        "monorepo_subdir",
        "shared_parent",
    }


def test_repository_classification_is_structural_and_crawl_safe(enriched: list[dict]) -> None:
    by_id = {row["source_benchmark_id"]: row for row in enriched}

    assert by_id["mcp-atlas"]["repository"]["kind"] == "benchmark_source"
    assert by_id["aime-2025"]["repository"]["kind"] == "shared_parent"
    assert by_id["browsecomp"]["repository"]["kind"] == "harness_only"
    assert by_id["imo-answerbench"]["repository"] == {
        "url": "https://github.com/google-deepmind/superhuman",
        "full_name": "google-deepmind/superhuman",
        "kind": "monorepo_subdir",
        "subpath": "imobench",
        "resolution_status": "resolved",
    }

    crawlable = {
        benchmark_id
        for benchmark_id, row in by_id.items()
        if (row.get("repository") or {}).get("kind") == "benchmark_source"
    }
    assert "mcp-atlas" in crawlable
    assert "aime-2025" not in crawlable
    assert "browsecomp" not in crawlable
    assert "imo-answerbench" not in crawlable


def test_unresolved_rows_remain_visible_without_manufacturing_artifacts(
    enriched: list[dict],
) -> None:
    by_id = {row["source_benchmark_id"]: row for row in enriched}
    for benchmark_id in ("aime-2024", "include", "hmmt25", "t2-bench"):
        row = by_id[benchmark_id]
        assert row["repository"]["kind"] == "not_found"
        assert row["repository"]["url"] is None
        assert row["artifacts"] == []
        assert row["identity_override"]["candidate_matches"]


def test_enriched_source_records_are_the_records_written_to_disk(
    normalized: dict, overrides, enriched: list[dict], tmp_path: Path
) -> None:
    result = dict(normalized)
    result["source_records"] = enriched
    result["validation"] = overridden_validation(normalized["validation"], enriched, overrides)
    paths = write_catalog(result, tmp_path)
    rows = [
        json.loads(line)
        for line in paths["source_records"].read_text(encoding="utf-8").splitlines()
    ]
    by_id = {row["source_benchmark_id"]: row for row in rows}

    assert by_id["mcp-atlas"]["repository"]["full_name"] == "scaleapi/mcp-atlas"
    assert any(artifact["kind"] == "repo" for artifact in by_id["mcp-atlas"]["artifacts"])
    validation = json.loads(paths["validation"].read_text(encoding="utf-8"))
    assert validation["identity_overrides"]["override_count"] == 57
    assert validation["empty_provenance_fraction"] < 1.0


def _write_override(tmp_path: Path, row: dict, benchmark_id: str = "mcp-atlas") -> Path:
    path = tmp_path / "overrides.yml"
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "benchmarks": {benchmark_id: row}},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _valid_row() -> dict:
    return {
        "resolution_status": "resolved",
        "repo_kind": "benchmark_source",
        "repo_url": "https://github.com/scaleapi/mcp-atlas",
        "repo_full_name": "scaleapi/mcp-atlas",
        "repo_subpath": None,
        "paper_url": "https://arxiv.org/abs/2602.00933",
        "note": "The paper and repository identify the same benchmark.",
    }


def test_loader_rejects_repository_subpaths_hidden_in_repo_url(
    normalized: dict, tmp_path: Path
) -> None:
    row = _valid_row()
    row["repo_url"] += "/tree/main/tasks"
    path = _write_override(tmp_path, row)
    with pytest.raises(IdentityOverrideError, match="repository root"):
        load_llm_stats_identity_overrides(normalized["source_records"], path)


def test_loader_rejects_resolved_rows_without_two_url_evidence(
    normalized: dict, tmp_path: Path
) -> None:
    row = _valid_row()
    row.pop("paper_url")
    path = _write_override(tmp_path, row)
    with pytest.raises(IdentityOverrideError, match="two different URLs"):
        load_llm_stats_identity_overrides(normalized["source_records"], path)


def test_loader_rejects_monorepo_without_a_structured_subpath(
    normalized: dict, tmp_path: Path
) -> None:
    row = _valid_row()
    row["repo_kind"] = "monorepo_subdir"
    path = _write_override(tmp_path, row)
    with pytest.raises(IdentityOverrideError, match="requires repo_subpath"):
        load_llm_stats_identity_overrides(normalized["source_records"], path)


def test_loader_rejects_unresolved_rows_that_publish_a_repository(
    normalized: dict, tmp_path: Path
) -> None:
    row = _valid_row()
    row.update(
        {
            "resolution_status": "needs_review",
            "repo_kind": "not_found",
            "candidate_matches": [
                {"url": "https://github.com/scaleapi/mcp-atlas", "note": "Candidate only."}
            ],
        }
    )
    path = _write_override(tmp_path, row)
    with pytest.raises(IdentityOverrideError, match="cannot publish repository fields"):
        load_llm_stats_identity_overrides(normalized["source_records"], path)


def test_loader_rejects_an_override_for_an_unknown_source_id(
    normalized: dict, tmp_path: Path
) -> None:
    path = _write_override(tmp_path, _valid_row(), benchmark_id="does-not-exist")
    with pytest.raises(IdentityOverrideError, match="current llm-stats source record"):
        load_llm_stats_identity_overrides(normalized["source_records"], path)
