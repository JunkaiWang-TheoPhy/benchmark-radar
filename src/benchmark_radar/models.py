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

    @property
    def canonical_key(self) -> str:
        return f"{self.source}:{self.source_id}".lower()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["published_at"] = self.published_at.astimezone(UTC).isoformat()
        value.pop("raw", None)
        return value


@dataclass(slots=True)
class SourceHealth:
    source: str
    ok: bool
    item_count: int = 0
    error: str | None = None


@dataclass(slots=True)
class RadarRun:
    generated_at: datetime
    since: datetime
    items: list[RadarItem]
    health: list[SourceHealth]
