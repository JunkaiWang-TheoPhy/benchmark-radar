import json

import pytest

from benchmark_radar import kw_bench, kw_bench_store
from benchmark_radar.kw_bench_tracks import (
    MappingExtractor,
    NullExtractor,
    backfill,
    classification_layer,
    classify_tracks,
    derive_tracks,
)

CLASSIFIED_AT = "2026-08-06T00:00:00+00:00"


def item(**overrides):
    value = {
        "source": "arXiv",
        "source_id": "paper-1",
        "title": "A benchmark",
        "url": "https://arxiv.org/abs/2607.12345",
        "published_at": "2026-07-28T12:00:00+00:00",
        "updated_at": None,
        "event_kind": "released",
        "categories": ["benchmark"],
        "authors": [],
        "artifact_urls": [],
        "metrics": {},
        "total_score": 50,
    }
    value.update(overrides)
    return value


def snapshot(date, *items):
    return {"date": date, "evidence_items": list(items)}


# --- Track derivation ----------------------------------------------------


def test_repeated_sightings_collapse_to_one_track():
    """The core dedup property: thousands of observations, one canonical track."""
    snapshots = [snapshot(f"2026-07-{day:02d}", item()) for day in range(20, 30)]

    tracks = derive_tracks(snapshots)

    assert len(tracks) == 1
    assert tracks[0]["canonical_artifact_id"] == "artifact:arxiv:2607.12345"


def test_cross_source_sightings_of_one_artifact_collapse():
    tracks = derive_tracks(
        [
            snapshot(
                "2026-07-28",
                item(source="arXiv", url="https://arxiv.org/abs/2607.12345"),
                item(
                    source="GitHub",
                    source_id="repo-1",
                    url="https://github.com/org/bench",
                    artifact_urls=["https://arxiv.org/abs/2607.12345"],
                ),
            )
        ]
    )

    assert len(tracks) == 1


def test_dataset_only_records_are_not_scored_tracks():
    """A corpus release has no scoring procedure, so it has no capability frontier."""
    tracks = derive_tracks([snapshot("2026-07-28", item(categories=["dataset"]))])

    assert tracks == []


def test_evaluation_records_are_scored_tracks():
    tracks = derive_tracks([snapshot("2026-07-28", item(categories=["evaluation"]))])

    assert len(tracks) == 1


def test_a_later_update_does_not_demote_a_released_track():
    tracks = derive_tracks(
        [
            snapshot("2026-07-28", item(event_kind="released")),
            snapshot("2026-07-29", item(event_kind="updated")),
        ]
    )

    assert tracks[0]["event_kind"] == "released"


def test_derivation_is_deterministic():
    snapshots = [
        snapshot(
            "2026-07-28",
            item(url="https://arxiv.org/abs/2607.00002"),
            item(source_id="p2", url="https://arxiv.org/abs/2607.00001"),
        )
    ]

    assert derive_tracks(snapshots) == derive_tracks(snapshots)
    assert [track["canonical_artifact_id"] for track in derive_tracks(snapshots)] == [
        "artifact:arxiv:2607.00001",
        "artifact:arxiv:2607.00002",
    ]


# --- Backfill and caching ------------------------------------------------


def test_null_extractor_leaves_every_track_unclassified(tmp_path):
    store = tmp_path / "kw.jsonl"
    summary = backfill(
        [snapshot("2026-07-28", item())],
        store_path=store,
        classified_at=CLASSIFIED_AT,
    )

    assert summary["classified"] == 1
    records = kw_bench_store.read_records(store)
    assert records[0]["level"] == kw_bench.UNCLASSIFIED
    assert records[0]["missing_evidence"]


def test_rerunning_a_completed_backfill_classifies_nothing(tmp_path):
    """The acceptance criterion: unchanged artifacts produce no new work."""
    store = tmp_path / "kw.jsonl"
    snapshots = [snapshot("2026-07-28", item())]
    backfill(snapshots, store_path=store, classified_at=CLASSIFIED_AT)

    second = backfill(snapshots, store_path=store, classified_at=CLASSIFIED_AT)

    assert second["classified"] == 0
    assert second["reused_from_cache"] == 1
    assert len(kw_bench_store.read_records(store)) == 1


def test_changed_evidence_supersedes_without_rewriting_history(tmp_path):
    store = tmp_path / "kw.jsonl"
    snapshots = [snapshot("2026-07-28", item())]
    artifact = "artifact:arxiv:2607.12345"
    backfill(snapshots, store_path=store, classified_at=CLASSIFIED_AT)

    extractor = MappingExtractor(
        {
            artifact: {
                "scored_outcome": "The verifier checks the end state of the repository.",
                "agent_visible_target": "The goal is given to the agent.",
                "evaluator_knowledge": "The expected end state is recorded.",
                "verifier_modality": "executable",
                "verifier_procedure": "Tests are executed against the modified repository.",
            }
        }
    )
    backfill(
        snapshots,
        store_path=store,
        classified_at=CLASSIFIED_AT,
        extractor=extractor,
    )

    records = kw_bench_store.read_records(store)
    assert len(records) == 2
    assert records[0]["level"] == kw_bench.UNCLASSIFIED
    assert records[1]["level"] == "L2"
    assert records[1]["supersedes_evidence_hash"] == records[0]["evidence_hash"]
    live = kw_bench_store.current_records(store)
    assert live[(artifact, records[1]["track_id"])]["level"] == "L2"


def test_a_rubric_version_bump_invalidates_the_cache(tmp_path, monkeypatch):
    store = tmp_path / "kw.jsonl"
    snapshots = [snapshot("2026-07-28", item())]
    backfill(snapshots, store_path=store, classified_at=CLASSIFIED_AT)

    monkeypatch.setattr(kw_bench_store, "KW_BENCH_VERSION", "0.2")
    summary = backfill(snapshots, store_path=store, classified_at=CLASSIFIED_AT)

    assert summary["classified"] == 1


def test_changed_source_hashes_force_reclassification(tmp_path):
    """An edited README must re-extract even when the evidence text is unchanged."""
    store = tmp_path / "kw.jsonl"
    snapshots = [snapshot("2026-07-28", item())]
    artifact = "artifact:arxiv:2607.12345"
    fields = {"evidence": {}, "source_hashes": ["sha256:aaa"]}
    backfill(
        snapshots,
        store_path=store,
        classified_at=CLASSIFIED_AT,
        extractor=MappingExtractor({artifact: fields}),
    )

    summary = backfill(
        snapshots,
        store_path=store,
        classified_at=CLASSIFIED_AT,
        extractor=MappingExtractor({artifact: {**fields, "source_hashes": ["sha256:bbb"]}}),
    )

    assert summary["classified"] == 1


def test_an_interrupted_backfill_keeps_completed_batches(tmp_path):
    store = tmp_path / "kw.jsonl"
    snapshots = [
        snapshot(
            "2026-07-28",
            *[item(source_id=f"p{n}", url=f"https://arxiv.org/abs/2607.{n:05d}") for n in range(6)],
        )
    ]
    tracks = derive_tracks(snapshots)

    class Failing(NullExtractor):
        def __init__(self):
            self.calls = 0

        def extract(self, track):
            self.calls += 1
            if self.calls > 4:
                raise RuntimeError("rate limited")
            return {}, []

    with pytest.raises(RuntimeError):
        classify_tracks(
            tracks,
            store_path=store,
            classified_at=CLASSIFIED_AT,
            extractor=Failing(),
            batch_size=2,
        )

    # Two batches of two committed before the third batch raised.
    assert len(kw_bench_store.read_records(store)) == 4

    resumed = classify_tracks(tracks, store_path=store, classified_at=CLASSIFIED_AT, batch_size=2)
    assert resumed["classified"] == 2
    assert resumed["reused_from_cache"] == 4


def test_limit_bounds_a_backfill_run(tmp_path):
    store = tmp_path / "kw.jsonl"
    snapshots = [
        snapshot(
            "2026-07-28",
            *[item(source_id=f"p{n}", url=f"https://arxiv.org/abs/2607.{n:05d}") for n in range(5)],
        )
    ]

    summary = backfill(snapshots, store_path=store, classified_at=CLASSIFIED_AT, limit=2)

    assert summary["tracks_derived"] == 5
    assert summary["classified"] == 2


# --- Store mechanics -----------------------------------------------------


def test_blank_lines_do_not_break_a_partial_store(tmp_path):
    store = tmp_path / "kw.jsonl"
    store.write_text('{"canonical_artifact_id":"a","track_id":"t"}\n\n', encoding="utf-8")

    assert len(kw_bench_store.read_records(store)) == 1


def test_corrupt_json_is_reported_with_its_line(tmp_path):
    store = tmp_path / "kw.jsonl"
    store.write_text("{not json}\n", encoding="utf-8")

    with pytest.raises(kw_bench.KwBenchError, match="kw.jsonl:1"):
        kw_bench_store.read_records(store)


def test_missing_store_reads_as_empty(tmp_path):
    assert kw_bench_store.read_records(tmp_path / "absent.jsonl") == []


def test_rewrite_is_atomic_and_leaves_no_temp_files(tmp_path):
    store = tmp_path / "kw.jsonl"
    kw_bench_store.rewrite_records(store, [{"canonical_artifact_id": "a", "track_id": "t"}])

    assert len(kw_bench_store.read_records(store)) == 1
    assert list(tmp_path.glob(".*tmp")) == []


def test_zero_batch_size_is_rejected():
    with pytest.raises(kw_bench.KwBenchError):
        list(kw_bench_store.iter_batches([1, 2], 0))


# --- Dashboard layer -----------------------------------------------------


def test_classification_layer_is_marked_shadow(tmp_path):
    store = tmp_path / "kw.jsonl"
    backfill([snapshot("2026-07-28", item())], store_path=store, classified_at=CLASSIFIED_AT)

    layer = classification_layer(store)

    assert layer["shadow"] is True
    assert layer["chart_levels"] == list(kw_bench.CHART_LEVELS)
    assert layer["level_counts"][kw_bench.UNCLASSIFIED] == 1
    assert layer["coverage"]["classified_rate"] == 0.0


def test_classification_layer_is_json_serializable(tmp_path):
    store = tmp_path / "kw.jsonl"
    backfill([snapshot("2026-07-28", item())], store_path=store, classified_at=CLASSIFIED_AT)

    assert json.loads(json.dumps(classification_layer(store)))
