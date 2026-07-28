from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class RadarItem:
    source: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    updated_at: datetime | None = None
    discovered_at: datetime | None = None
    summary: str = ""
    event_kind: str = "discovered"
    authors: list[str] = field(default_factory=list)
    artifact_urls: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    categories: list[str] = field(default_factory=list)
    evidence_score: float = 0.0
    relevance_score: float = 0.0
    recency_score: float = 0.0
    adoption_score: float = 0.0
    total_score: float = 0.0
    rationale: list[str] = field(default_factory=list)
    # Set when the record matches a named artifact on the configured
    # watchlist. Routing metadata only: it never alters a score.
    watchlist: str | None = None
    watchlist_note: str = ""

    @property
    def canonical_key(self) -> str:
        return f"{self.source}:{self.source_id}".lower()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["published_at"] = self.published_at.astimezone(UTC).isoformat()
        value["updated_at"] = (
            self.updated_at.astimezone(UTC).isoformat() if self.updated_at else None
        )
        value["discovered_at"] = (
            self.discovered_at.astimezone(UTC).isoformat() if self.discovered_at else None
        )
        value.pop("raw", None)
        return value


@dataclass(slots=True)
class SourceHealth:
    source: str
    ok: bool
    item_count: int = 0
    error: str | None = None
    kind: str = "evidence"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProducerHealth:
    producer: str
    source: str
    ok: bool
    item_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AttentionObservation:
    observation_id: str
    producer: str
    source: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    discovered_at: datetime
    observed_at: datetime
    summary: str = ""
    event_kind: str = "discussed"
    authors: list[str] = field(default_factory=list)
    primary_artifact_url: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    supporting_observations: list[dict[str, Any]] = field(default_factory=list)
    quality_scored: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("published_at", "discovered_at", "observed_at"):
            value[key] = getattr(self, key).astimezone(UTC).isoformat()
        return value


@dataclass(slots=True)
class RadarRun:
    generated_at: datetime
    since: datetime
    items: list[RadarItem]
    health: list[SourceHealth]
    attention: list[AttentionObservation] = field(default_factory=list)
    attention_ingest_health: list[SourceHealth] = field(default_factory=list)
    producer_health: list[ProducerHealth] = field(default_factory=list)
    discovery_state: dict[str, Any] = field(default_factory=dict)
    # Per-stage record counts (fetched → deduplicated → scored → qualified →
    # published) so the gap between "228 found" and what ships is visible.
    selection: dict[str, Any] = field(default_factory=dict)
