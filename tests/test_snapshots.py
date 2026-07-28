import json
from datetime import UTC, datetime, timedelta

import pytest

from benchmark_radar.models import (
    AttentionObservation,
    ProducerHealth,
    RadarItem,
    RadarRun,
    SourceHealth,
)
from benchmark_radar.snapshots import (
    SnapshotError,
    load_snapshots,
    migrate_snapshot_history,
    rebuild_dashboard,
    snapshot_for_run,
    validate_snapshot,
    write_snapshot,
)


def radar_run(day: int = 27, *, title: str = "A New Evaluation Benchmark") -> RadarRun:
    generated = datetime(2026, 7, day, 12, 15, tzinfo=UTC)
    return RadarRun(
        generated_at=generated,
        since=generated - timedelta(hours=48),
        items=[
            RadarItem(
                source="arXiv",
                source_id=f"2607.{day:04d}",
                title=title,
                url=f"https://arxiv.org/abs/2607.{day:04d}",
                published_at=generated - timedelta(hours=3),
                summary="A fixture-backed benchmark release.",
                event_kind="released",
                authors=["Radar Author"],
                categories=["benchmark", "evaluation"],
                metrics={"citations": 2},
                evidence_score=2.5,
                relevance_score=2.9,
                recency_score=3.8,
                adoption_score=0.3,
                total_score=2.7,
                rationale=["Matched: benchmark", "Primary record: arXiv"],
            )
        ],
        health=[
            SourceHealth(source="arxiv", ok=True, item_count=1),
            SourceHealth(source="brave", ok=False, error="API key unavailable"),
        ],
        attention=[
            AttentionObservation(
                observation_id=f"producer:hacker-news:{day}",
                producer="fixture-producer",
                source="Hacker News",
                source_id=str(day),
                title="Public benchmark discussion",
                url=f"https://news.ycombinator.com/item?id={day}",
                published_at=generated - timedelta(hours=2),
                discovered_at=generated - timedelta(hours=1),
                observed_at=generated,
                categories=["benchmark"],
                metrics={"points": 4},
                rationale=["Attention only"],
                supporting_observations=[
                    {
                        "source": "Hacker News",
                        "source_id": f"{day}-supporting",
                        "url": f"https://news.ycombinator.com/item?id={day}-supporting",
                        "published_at": generated.isoformat(),
                        "metrics": {"points": 1},
                    }
                ],
            )
        ],
        attention_ingest_health=[
            SourceHealth(
                source="Fixture feed",
                kind="attention",
                ok=True,
                item_count=1,
            )
        ],
        producer_health=[
            ProducerHealth(
                producer="fixture-producer",
                source="Hacker News",
                ok=True,
                item_count=1,
            )
        ],
    )


def test_snapshot_has_version_and_public_evidence_fields():
    snapshot = snapshot_for_run(radar_run())

    validate_snapshot(snapshot)

    assert snapshot["schema_version"] == 2
    assert snapshot["date"] == "2026-07-27"
    assert snapshot["evidence_items"][0]["event_kind"] == "released"
    assert "raw" not in snapshot["evidence_items"][0]
    assert snapshot["attention"]["observations"][0]["quality_scored"] is False
    assert (
        snapshot["attention"]["observations"][0]["supporting_observations"][0]["source"]
        == "Hacker News"
    )


def test_same_utc_day_is_idempotent(tmp_path):
    first = radar_run(title="First run")
    second = radar_run(title="Replacement run")

    first_path = write_snapshot(first, tmp_path)
    second_path = write_snapshot(second, tmp_path)

    assert first_path == second_path
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert load_snapshots(tmp_path)[0]["evidence_items"][0]["title"] == "Replacement run"


def test_rebuild_is_deterministic(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    write_snapshot(radar_run(26), snapshot_dir)
    write_snapshot(radar_run(27), snapshot_dir)
    output = tmp_path / "radar.json"

    first = rebuild_dashboard(snapshot_dir, output)
    first_bytes = output.read_bytes()
    second = rebuild_dashboard(snapshot_dir, output)

    assert first == second
    assert first_bytes == output.read_bytes()
    assert first["facets"]["dates"] == ["2026-07-26", "2026-07-27"]
    assert first["days"][0]["category_counts"] == {"benchmark": 1, "evaluation": 1}
    assert first["days"][0]["evidence_count"] == 1
    assert first["days"][0]["attention"]["new_count"] == 1
    assert first["days"][0]["attention"]["active_count"] == 1


def test_thirty_snapshots_replay_into_one_deterministic_cumulative_entity(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    for day in range(1, 31):
        run = radar_run(day)
        run.items[0].source_id = "2607.0001"
        run.items[0].url = "https://arxiv.org/abs/2607.0001"
        write_snapshot(run, snapshot_dir)
    output = tmp_path / "radar.json"

    first = rebuild_dashboard(snapshot_dir, output)
    first_bytes = output.read_bytes()
    second = rebuild_dashboard(snapshot_dir, output)
    artifacts = [entity for entity in first["corpus"]["entities"] if entity["type"] == "artifact"]
    benchmark = next(
        topic for topic in first["corpus"]["aggregates"]["topics"] if topic["topic"] == "benchmark"
    )

    assert first == second
    assert first_bytes == output.read_bytes()
    assert first["snapshot_count"] == 30
    assert len(artifacts) == 1
    assert artifacts[0]["observation_count"] == 30
    assert len(artifacts[0]["seen_days"]) == 30
    assert benchmark["persistence_days"] == 30
    assert benchmark["velocity"] == 0
    assert first["corpus"]["aggregates"]["provenance"]["primary_source_rate"] >= 0.9


def test_dashboard_publishes_the_rubric_that_scored_its_records(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    run = radar_run(27)
    run.selection = {
        "minimum_score": 40.0,
        "report_limit": 30,
        "score_version": 2,
        "score_max": 100,
        "lookback_hours": 48,
    }
    write_snapshot(run, snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")

    published = data["rubric"]
    assert published["score_max"] == 100.0
    assert [component["key"] for component in published["components"]] == [
        "relevance",
        "evidence",
        "recency",
        "adoption",
    ]
    # The reader is looking at a filtered corpus, so the cutoff that filtered it
    # belongs with the rubric that scored it.
    assert published["minimum_score"] == 40.0
    assert published["limits"]


def test_dashboard_keeps_legacy_scores_on_their_original_rubric(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    run = radar_run(27)
    # The fixture models a snapshot written before score_version was persisted.
    run.items[0].score_version = 1
    run.items[0].score_max = 4
    write_snapshot(run, snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")
    published = data["days"][0]["evidence_items"][0]

    assert published["score_version"] == 1
    assert published["score_max"] == 4
    assert data["rubrics"]["1"]["score_max"] == 4
    assert data["rubrics"]["2"]["score_max"] == 100


def test_dashboard_without_snapshots_publishes_no_cutoff(tmp_path):
    data = rebuild_dashboard(tmp_path / "empty", tmp_path / "radar.json")

    assert "minimum_score" not in data["rubric"]
    assert data["rubric"]["components"]


def test_dashboard_reports_per_category_deltas_and_cumulative(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    write_snapshot(radar_run(26), snapshot_dir)
    write_snapshot(radar_run(27), snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")

    first, second = data["days"]
    assert first["category_trends"]["benchmark"]["count"] == 1
    # Nothing precedes the first scan, so no change is claimed.
    assert first["category_trends"]["benchmark"]["delta"] is None
    assert first["category_trends"]["benchmark"]["baseline"] is None
    # Day two matches day one, so the domain is flat but the total accumulates.
    assert second["category_trends"]["benchmark"]["delta"] == 0
    assert second["category_trends"]["benchmark"]["baseline"] == 1.0
    assert second["category_trends"]["benchmark"]["cumulative"] == 2
    assert second["cumulative_evidence_count"] == 2


def test_cumulative_counts_artifacts_once_across_overlapping_windows(tmp_path):
    # The scan window overlaps by design, so the same repository appears on
    # adjacent days. Summing daily counts would grow the total while nothing
    # new was actually discovered.
    snapshot_dir = tmp_path / "snapshots"
    for day in (26, 27):
        run = radar_run(day)
        # Same artifact identity on both days.
        run.items[0].source_id = "2607.0001"
        run.items[0].url = "https://arxiv.org/abs/2607.0001"
        write_snapshot(run, snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")

    second = data["days"][1]
    assert second["category_trends"]["benchmark"]["cumulative"] == 1
    assert second["cumulative_evidence_count"] == 1


def test_trends_do_not_compare_across_a_report_limit_change(tmp_path):
    # Raising the cap lifts every count at once. Reporting that as domain
    # momentum would present a collection-policy change as a change in field.
    snapshot_dir = tmp_path / "snapshots"
    narrow = radar_run(26)
    narrow.selection = {"report_limit": 30}
    wide = radar_run(27)
    wide.selection = {"report_limit": 300}
    write_snapshot(narrow, snapshot_dir)
    write_snapshot(wide, snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")

    after = data["days"][1]["category_trends"]["benchmark"]
    assert after["delta"] is None
    assert after["baseline"] is None
    assert after["comparable"] is False
    # Cumulative totals still accrue: they describe the corpus, not a rate.
    assert after["cumulative"] == 2


def test_trends_compare_snapshots_sharing_a_report_limit(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    for day in (26, 27):
        run = radar_run(day)
        run.selection = {"report_limit": 300}
        write_snapshot(run, snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")

    after = data["days"][1]["category_trends"]["benchmark"]
    assert after["delta"] == 0
    assert after["comparable"] is True


def test_trends_do_not_compare_when_connector_coverage_changes(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    first = radar_run(26)
    first.selection = {"report_limit": 300}
    second = radar_run(27)
    second.selection = {"report_limit": 300}
    second.health[1] = SourceHealth(source="brave", ok=True, item_count=1)
    write_snapshot(first, snapshot_dir)
    write_snapshot(second, snapshot_dir)

    data = rebuild_dashboard(snapshot_dir, tmp_path / "radar.json")

    before, after = data["days"]
    assert before["coverage_complete"] is False
    assert before["coverage_gaps"] == ["brave"]
    assert after["coverage_complete"] is True
    assert after["category_trends"]["benchmark"]["comparable"] is False


def test_selection_counts_round_trip_through_the_snapshot(tmp_path):
    run = radar_run(27)
    run.selection = {"fetched": 300, "published": 30, "minimum_score": 2.0}

    snapshot = snapshot_for_run(run)
    validate_snapshot(snapshot)

    write_snapshot(run, tmp_path / "snapshots")
    data = rebuild_dashboard(tmp_path / "snapshots", tmp_path / "radar.json")
    assert data["days"][-1]["selection"]["fetched"] == 300


def test_snapshots_without_selection_stay_valid():
    snapshot = snapshot_for_run(radar_run())
    snapshot.pop("selection")

    validate_snapshot(snapshot)


def test_validation_rejects_missing_item_fields():
    snapshot = snapshot_for_run(radar_run())
    del snapshot["evidence_items"][0]["event_kind"]

    with pytest.raises(SnapshotError, match="event_kind"):
        validate_snapshot(snapshot)


def test_validation_rejects_raw_source_payloads():
    snapshot = snapshot_for_run(radar_run())
    snapshot["evidence_items"][0]["raw"] = {"private": "source payload"}

    with pytest.raises(SnapshotError, match="raw source payloads"):
        validate_snapshot(snapshot)


def test_schema_one_snapshot_is_normalized_for_rebuild(tmp_path):
    current = snapshot_for_run(radar_run())
    legacy = {
        "schema_version": 1,
        "date": current["date"],
        "generated_at": current["generated_at"],
        "since": current["since"],
        "items": current["evidence_items"],
        "health": current["ingest_health"][:2],
    }
    path = tmp_path / "2026-07-27.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")

    normalized = load_snapshots(tmp_path)[0]

    assert normalized["schema_version"] == 2
    assert normalized["evidence_items"][0]["discovered_at"] == current["generated_at"]
    assert normalized["attention"] == {"observations": []}


def test_attention_can_never_be_marked_quality_scored():
    snapshot = snapshot_for_run(radar_run())
    snapshot["attention"]["observations"][0]["quality_scored"] = True

    with pytest.raises(SnapshotError, match="quality_scored false"):
        validate_snapshot(snapshot)


def test_supporting_attention_requires_valid_timestamp():
    snapshot = snapshot_for_run(radar_run())
    snapshot["attention"]["observations"][0]["supporting_observations"][0]["published_at"] = (
        "not-a-time"
    )

    with pytest.raises(SnapshotError, match="supporting observation 0 published_at"):
        validate_snapshot(snapshot)


def test_migrate_does_not_refetch_attention_for_schema_two(tmp_path, monkeypatch):
    write_snapshot(radar_run(), tmp_path)
    monkeypatch.setattr(
        "benchmark_radar.snapshots.fetch_attention_feeds",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected refetch")),
    )

    migrated = migrate_snapshot_history({}, tmp_path)

    assert migrated[0]["schema_version"] == 2
