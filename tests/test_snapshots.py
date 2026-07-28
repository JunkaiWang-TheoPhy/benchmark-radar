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
