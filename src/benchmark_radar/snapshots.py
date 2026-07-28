from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .attention import fetch_attention_feeds
from .models import RadarRun

SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, SCHEMA_VERSION}


class SnapshotError(ValueError):
    """Raised when persisted public data does not match the supported schema."""


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def snapshot_for_run(run: RadarRun) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "date": run.generated_at.astimezone(UTC).date().isoformat(),
        "generated_at": _iso_utc(run.generated_at),
        "since": _iso_utc(run.since),
        "evidence_items": [item.to_dict() for item in run.items],
        "attention": {
            "observations": [observation.to_dict() for observation in run.attention],
        },
        "ingest_health": [
            health.to_dict() for health in [*run.health, *run.attention_ingest_health]
        ],
        "producer_health": [health.to_dict() for health in run.producer_health],
        "discovery_state": run.discovery_state,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_time(value: Any, *, source: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as error:
        raise SnapshotError(f"{source}: invalid {field}") from error


def _validate_evidence_items(items: Any, *, source: str) -> None:
    if not isinstance(items, list):
        raise SnapshotError(f"{source}: evidence_items must be an array")
    item_fields = {
        "source",
        "source_id",
        "title",
        "url",
        "published_at",
        "event_kind",
        "categories",
        "metrics",
        "evidence_score",
        "relevance_score",
        "recency_score",
        "adoption_score",
        "total_score",
        "rationale",
    }
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SnapshotError(f"{source}: evidence item {index} must be an object")
        if "raw" in item:
            raise SnapshotError(
                f"{source}: evidence item {index} must not expose raw source payloads"
            )
        item_missing = sorted(item_fields - item.keys())
        if item_missing:
            raise SnapshotError(
                f"{source}: evidence item {index} missing fields: {', '.join(item_missing)}"
            )
        if not str(item["url"]).startswith(("https://", "http://")):
            raise SnapshotError(f"{source}: evidence item {index} URL must be HTTP(S)")
        _validate_time(
            item["published_at"],
            source=source,
            field=f"evidence item {index} published_at",
        )
        for field in ("updated_at", "discovered_at"):
            if item.get(field):
                _validate_time(
                    item[field],
                    source=source,
                    field=f"evidence item {index} {field}",
                )


def _validate_health(values: Any, *, source: str, field: str) -> None:
    if not isinstance(values, list):
        raise SnapshotError(f"{source}: {field} must be an array")
    for index, health in enumerate(values):
        if (
            not isinstance(health, dict)
            or not {
                "source",
                "ok",
                "item_count",
            }
            <= health.keys()
        ):
            raise SnapshotError(f"{source}: {field} {index} is invalid")


def _validate_attention(attention: Any, *, source: str) -> None:
    if not isinstance(attention, dict) or not isinstance(attention.get("observations"), list):
        raise SnapshotError(f"{source}: attention.observations must be an array")
    required = {
        "observation_id",
        "producer",
        "source",
        "source_id",
        "title",
        "url",
        "published_at",
        "discovered_at",
        "observed_at",
        "event_kind",
        "categories",
        "metrics",
        "rationale",
        "quality_scored",
    }
    for index, observation in enumerate(attention["observations"]):
        if not isinstance(observation, dict):
            raise SnapshotError(f"{source}: attention observation {index} must be an object")
        missing = sorted(required - observation.keys())
        if missing:
            raise SnapshotError(
                f"{source}: attention observation {index} missing fields: {', '.join(missing)}"
            )
        if observation["quality_scored"] is not False:
            raise SnapshotError(
                f"{source}: attention observation {index} must set quality_scored false"
            )
        if not str(observation["url"]).startswith(("https://", "http://")):
            raise SnapshotError(f"{source}: attention observation {index} URL must be HTTP(S)")
        for field in ("published_at", "discovered_at", "observed_at"):
            _validate_time(
                observation[field],
                source=source,
                field=f"attention observation {index} {field}",
            )
        for supporting_index, supporting in enumerate(
            observation.get("supporting_observations") or []
        ):
            if (
                not isinstance(supporting, dict)
                or not {
                    "source",
                    "source_id",
                    "url",
                    "published_at",
                    "metrics",
                }
                <= supporting.keys()
            ):
                raise SnapshotError(
                    f"{source}: attention observation {index} supporting observation "
                    f"{supporting_index} is invalid"
                )
            if not str(supporting["url"]).startswith(("https://", "http://")):
                raise SnapshotError(
                    f"{source}: attention observation {index} supporting observation "
                    f"{supporting_index} URL must be HTTP(S)"
                )
            _validate_time(
                supporting["published_at"],
                source=source,
                field=(
                    f"attention observation {index} supporting observation "
                    f"{supporting_index} published_at"
                ),
            )


def validate_snapshot(snapshot: dict[str, Any], *, source: str = "snapshot") -> None:
    version = snapshot.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SnapshotError(f"{source}: unsupported schema_version {version!r}")
    if version == 1:
        required = {"schema_version", "date", "generated_at", "since", "items", "health"}
    else:
        required = {
            "schema_version",
            "date",
            "generated_at",
            "since",
            "evidence_items",
            "attention",
            "ingest_health",
            "producer_health",
            "discovery_state",
        }
    missing = sorted(required - snapshot.keys())
    if missing:
        raise SnapshotError(f"{source}: missing fields: {', '.join(missing)}")
    generated = _validate_time(snapshot["generated_at"], source=source, field="generated_at")
    since = _validate_time(snapshot["since"], source=source, field="since")
    expected_date = generated.date().isoformat()
    if snapshot["date"] != expected_date:
        raise SnapshotError(
            f"{source}: date {snapshot['date']!r} does not match generated_at UTC date"
        )
    if since > generated:
        raise SnapshotError(f"{source}: since must not be after generated_at")
    if version == 1:
        _validate_evidence_items(snapshot["items"], source=source)
        _validate_health(snapshot["health"], source=source, field="health")
        return
    _validate_evidence_items(snapshot["evidence_items"], source=source)
    _validate_attention(snapshot["attention"], source=source)
    _validate_health(snapshot["ingest_health"], source=source, field="ingest_health")
    _validate_health(snapshot["producer_health"], source=source, field="producer_health")
    if not isinstance(snapshot["discovery_state"], dict):
        raise SnapshotError(f"{source}: discovery_state must be an object")


def normalize_snapshot(snapshot: dict[str, Any], *, source: str = "snapshot") -> dict[str, Any]:
    validate_snapshot(snapshot, source=source)
    if snapshot["schema_version"] == SCHEMA_VERSION:
        return deepcopy(snapshot)
    evidence_items = []
    discovery_state: dict[str, Any] = {}
    for item in snapshot["items"]:
        normalized_item = {
            **item,
            "updated_at": item.get("updated_at"),
            "discovered_at": item.get("discovered_at") or snapshot["generated_at"],
        }
        evidence_items.append(normalized_item)
        if item["source"] == "arXiv":
            discovery_state.setdefault("arxiv", {})[item["source_id"]] = {
                "discovered_at": normalized_item["discovered_at"],
                "last_activity_at": item.get("updated_at") or item["published_at"],
            }
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "date": snapshot["date"],
        "generated_at": snapshot["generated_at"],
        "since": snapshot["since"],
        "evidence_items": evidence_items,
        "attention": {"observations": []},
        "ingest_health": [
            {**health, "kind": health.get("kind") or "evidence"} for health in snapshot["health"]
        ],
        "producer_health": [],
        "discovery_state": discovery_state,
    }
    validate_snapshot(normalized, source=source)
    return normalized


def write_snapshot(run: RadarRun, snapshot_dir: Path) -> Path:
    snapshot = snapshot_for_run(run)
    validate_snapshot(snapshot)
    path = snapshot_dir / f"{snapshot['date']}.json"
    _write_json(path, snapshot)
    return path


def load_snapshots(snapshot_dir: Path) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for path in sorted(snapshot_dir.glob("*.json")):
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SnapshotError(f"{path}: invalid JSON: {error}") from error
        snapshots.append(normalize_snapshot(snapshot, source=str(path)))
    snapshots.sort(key=lambda value: (value["date"], value["generated_at"]))
    return snapshots


def dashboard_data(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    days: list[dict[str, Any]] = []
    categories: set[str] = set()
    sources: set[str] = set()
    event_kinds: set[str] = set()
    for snapshot in snapshots:
        evidence_items = snapshot["evidence_items"]
        observations = snapshot["attention"]["observations"]
        category_counts = Counter(
            category for item in evidence_items for category in item["categories"]
        )
        source_counts = Counter(item["source"] for item in evidence_items)
        event_counts = Counter(item["event_kind"] for item in evidence_items)
        attention_source_counts = Counter(item["source"] for item in observations)
        attention_event_counts = Counter(item["event_kind"] for item in observations)
        attention_new_count = sum(
            str(item["observed_at"]).startswith(snapshot["date"]) for item in observations
        )
        categories.update(category_counts)
        categories.update(
            category for item in observations for category in item.get("categories") or []
        )
        sources.update(source_counts)
        sources.update(attention_source_counts)
        event_kinds.update(event_counts)
        event_kinds.update(attention_event_counts)
        days.append(
            {
                "date": snapshot["date"],
                "generated_at": snapshot["generated_at"],
                "since": snapshot["since"],
                "item_count": len(evidence_items),
                "evidence_count": len(evidence_items),
                "category_counts": dict(sorted(category_counts.items())),
                "source_counts": dict(sorted(source_counts.items())),
                "event_kind_counts": dict(sorted(event_counts.items())),
                "evidence_items": evidence_items,
                "attention": {
                    "observations": observations,
                    "active_count": len(observations),
                    "new_count": attention_new_count,
                    "source_counts": dict(sorted(attention_source_counts.items())),
                    "event_kind_counts": dict(sorted(attention_event_counts.items())),
                },
                "ingest_health": snapshot["ingest_health"],
                "producer_health": snapshot["producer_health"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "latest_date": days[-1]["date"] if days else None,
        "snapshot_count": len(days),
        "generated_at": days[-1]["generated_at"] if days else None,
        "facets": {
            "dates": [day["date"] for day in days],
            "categories": sorted(categories),
            "sources": sorted(sources),
            "event_kinds": sorted(event_kinds),
            "kinds": ["evidence", "attention"],
        },
        "days": days,
    }


def rebuild_dashboard(snapshot_dir: Path, output: Path) -> dict[str, Any]:
    value = dashboard_data(load_snapshots(snapshot_dir))
    _write_json(output, value)
    return value


def migrate_snapshot_history(config: dict[str, Any], snapshot_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(snapshot_dir.glob("*.json"))
    snapshots: list[dict[str, Any]] = []
    versions: list[int] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        versions.append(int(raw.get("schema_version") or 0))
        snapshots.append(normalize_snapshot(raw, source=str(path)))
    if snapshots and versions[-1] == 1:
        latest = snapshots[-1]
        observed_at = _validate_time(
            latest["generated_at"],
            source=str(paths[-1]),
            field="generated_at",
        )
        previous_attention = latest["discovery_state"].get("attention") or {}
        observations, ingest_health, producer_health, attention_state = fetch_attention_feeds(
            config.get("attention") or {},
            observed_at=observed_at,
            previous_state=previous_attention,
        )
        latest["attention"] = {
            "observations": [observation.to_dict() for observation in observations]
        }
        latest["ingest_health"] = [
            health for health in latest["ingest_health"] if health.get("kind") != "attention"
        ] + [health.to_dict() for health in ingest_health]
        latest["producer_health"] = [health.to_dict() for health in producer_health]
        latest["discovery_state"]["attention"] = attention_state
    for path, snapshot in zip(paths, snapshots, strict=True):
        validate_snapshot(snapshot, source=str(path))
        _write_json(path, snapshot)
    return snapshots
