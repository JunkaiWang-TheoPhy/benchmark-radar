from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from .http import get_json
from .models import AttentionObservation, ProducerHealth, SourceHealth


def _date(value: str | None, *, fallback: datetime) -> datetime:
    if not value:
        return fallback
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _http_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _supporting_observations(
    values: Any,
    *,
    default_source: str,
) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    supporting: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        url = _http_url(value.get("url"))
        source_id = str(value.get("source_id") or "").strip()
        published_at = value.get("published_at")
        if not url or not source_id or not published_at:
            continue
        supporting.append(
            {
                "source": str(value.get("source") or default_source),
                "source_id": source_id,
                "url": url,
                "published_at": str(published_at),
                "metrics": {
                    str(key): float(metric)
                    for key, metric in (value.get("metrics") or {}).items()
                    if isinstance(metric, int | float) and metric >= 0
                },
                **(
                    {"primary_artifact_url": primary}
                    if (primary := _http_url(value.get("primary_artifact_url")))
                    else {}
                ),
            }
        )
    return supporting


def fetch_attention_feeds(
    config: dict[str, Any],
    *,
    observed_at: datetime,
    previous_state: dict[str, Any] | None = None,
) -> tuple[
    list[AttentionObservation],
    list[SourceHealth],
    list[ProducerHealth],
    dict[str, Any],
]:
    observations: dict[str, AttentionObservation] = {}
    ingest_health: list[SourceHealth] = []
    producer_health: list[ProducerHealth] = []
    state = dict(previous_state or {})

    for feed_config in config.get("feeds", []):
        if not feed_config.get("enabled", True):
            continue
        name = str(feed_config.get("name") or feed_config.get("url") or "attention feed")
        url = _http_url(feed_config.get("url"))
        if not url:
            ingest_health.append(
                SourceHealth(
                    source=name,
                    kind="attention",
                    ok=False,
                    error="Feed URL must be HTTP(S)",
                )
            )
            continue
        try:
            payload = get_json(url)
            if payload.get("schema_version") != 1 or not isinstance(
                payload.get("observations"), list
            ):
                raise ValueError("unsupported public observation feed schema")
            producer = str(payload.get("producer") or name)
            accepted = 0
            for raw in payload["observations"]:
                if not isinstance(raw, dict):
                    continue
                raw_id = str(raw.get("id") or "").strip()
                source = str(raw.get("source") or producer).strip()
                source_id = str(raw.get("source_id") or "").strip()
                title = str(raw.get("title") or "").strip()
                record_url = _http_url(raw.get("url"))
                if not raw_id or not source_id or not title or not record_url:
                    continue
                observation_id = f"{producer}:{raw_id}"
                previous = state.get(observation_id) or {}
                first_observed = _date(previous.get("observed_at"), fallback=observed_at)
                published = _date(raw.get("published_at"), fallback=observed_at)
                discovered = _date(raw.get("discovered_at"), fallback=observed_at)
                observation = AttentionObservation(
                    observation_id=observation_id,
                    producer=producer,
                    source=source,
                    source_id=source_id,
                    title=title,
                    url=record_url,
                    published_at=published,
                    discovered_at=discovered,
                    observed_at=first_observed,
                    summary=str(raw.get("summary") or ""),
                    event_kind=str(raw.get("event_kind") or "discussed"),
                    authors=[str(author) for author in raw.get("authors") or []],
                    primary_artifact_url=_http_url(raw.get("primary_artifact_url")),
                    metrics={
                        str(key): float(value)
                        for key, value in (raw.get("metrics") or {}).items()
                        if isinstance(value, int | float) and value >= 0
                    },
                    categories=sorted(
                        {str(category) for category in raw.get("categories") or [] if category}
                    ),
                    rationale=[str(reason) for reason in raw.get("rationale") or []],
                    supporting_observations=_supporting_observations(
                        raw.get("supporting_observations"),
                        default_source=source,
                    ),
                )
                observations[observation_id] = observation
                state[observation_id] = {
                    "observed_at": first_observed.astimezone(UTC).isoformat(),
                    "last_seen_at": observed_at.astimezone(UTC).isoformat(),
                }
                accepted += 1
            ingest_health.append(
                SourceHealth(source=name, kind="attention", ok=True, item_count=accepted)
            )
            for raw_health in payload.get("health") or []:
                if not isinstance(raw_health, dict):
                    continue
                producer_health.append(
                    ProducerHealth(
                        producer=producer,
                        source=str(raw_health.get("source") or producer),
                        ok=bool(raw_health.get("ok")),
                        item_count=int(raw_health.get("item_count") or 0),
                        error=(
                            str(raw_health["error"])
                            if raw_health.get("error") is not None
                            else None
                        ),
                    )
                )
        except Exception as error:
            ingest_health.append(
                SourceHealth(
                    source=name,
                    kind="attention",
                    ok=False,
                    error=f"{type(error).__name__}: {error}",
                )
            )

    ordered = sorted(
        observations.values(),
        key=lambda item: (item.observed_at, item.published_at, item.observation_id),
        reverse=True,
    )
    return ordered, ingest_health, producer_health, state
