from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import RadarItem, RadarRun, SourceHealth
from .sources import SOURCE_FETCHERS

TRACKING_PARAMETERS = {"ref", "source", "utm_campaign", "utm_content", "utm_medium", "utm_source"}


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in TRACKING_PARAMETERS]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalized_title(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def deduplicate(items: list[RadarItem]) -> list[RadarItem]:
    kept: dict[str, RadarItem] = {}
    for item in sorted(items, key=lambda value: value.published_at, reverse=True):
        title_key = normalized_title(item.title)
        if len(title_key) >= 24:
            key = hashlib.sha256(title_key.encode()).hexdigest()
        else:
            key = hashlib.sha256(canonical_url(item.url).encode()).hexdigest()
        existing = kept.get(key)
        if existing:
            if item.url not in existing.artifact_urls:
                existing.artifact_urls.append(item.url)
            existing.metrics.update(
                {
                    metric: max(value, existing.metrics.get(metric, 0))
                    for metric, value in item.metrics.items()
                }
            )
            existing.rationale.append(f"Also found via {item.source}")
        else:
            kept[key] = item
    return list(kept.values())


def score_item(
    item: RadarItem,
    taxonomy: dict[str, list[str]],
    now: datetime | None = None,
) -> RadarItem:
    now = now or datetime.now(UTC)
    haystack = f"{item.title} {item.summary}".lower()
    categories = []
    matched_terms: list[str] = []
    for category, terms in taxonomy.items():
        matches = [term for term in terms if term.lower() in haystack]
        if matches:
            categories.append(category)
            matched_terms.extend(matches[:2])
    item.categories = categories
    item.relevance_score = min(4.0, 1.25 * len(categories) + 0.2 * len(matched_terms))

    evidence = 0.5
    if item.source in {"arXiv", "OpenAlex"}:
        evidence += 1.5
    if item.source in {"GitHub", "Hugging Face"}:
        evidence += 1.0
    if item.authors:
        evidence += 0.5
    if item.artifact_urls:
        evidence += 0.5
    item.evidence_score = min(evidence, 4.0)

    age_hours = max(0.0, (now - item.published_at).total_seconds() / 3600)
    item.recency_score = max(0.0, 4.0 - age_hours / 24)

    adoption = (
        math.log10(1 + item.metrics.get("stars", 0)) * 0.8
        + math.log10(1 + item.metrics.get("downloads", 0)) * 0.6
        + math.log10(1 + item.metrics.get("likes", 0)) * 0.5
        + math.log10(1 + item.metrics.get("citations", 0)) * 0.7
    )
    item.adoption_score = min(adoption, 4.0)
    item.total_score = round(
        0.4 * item.relevance_score
        + 0.25 * item.evidence_score
        + 0.2 * item.recency_score
        + 0.15 * item.adoption_score,
        2,
    )
    if matched_terms:
        item.rationale.append(f"Matched: {', '.join(sorted(set(matched_terms)))}")
    item.rationale.append(f"Primary record: {item.source}")
    return item


def run_pipeline(config: dict[str, Any], now: datetime | None = None) -> RadarRun:
    now = now or datetime.now(UTC)
    settings = config["radar"]
    since = now - timedelta(hours=int(settings["lookback_hours"]))
    limit = int(settings["max_items_per_source"])
    items: list[RadarItem] = []
    health: list[SourceHealth] = []
    for source_name, source_config in config["sources"].items():
        if not source_config.get("enabled", True):
            continue
        fetcher = SOURCE_FETCHERS[source_name]
        try:
            fetched = fetcher(source_config, since, limit)
            items.extend(fetched)
            health.append(SourceHealth(source=source_name, ok=True, item_count=len(fetched)))
        except Exception as error:  # a partial report is preferable; health exposes the gap
            health.append(
                SourceHealth(
                    source=source_name,
                    ok=False,
                    error=f"{type(error).__name__}: {error}",
                )
            )
    required = {
        name
        for name, source_config in config["sources"].items()
        if source_config.get("enabled", True) and source_config.get("required", False)
    }
    healthy_required = {
        source.source for source in health if source.ok and source.source in required
    }
    if required and not healthy_required:
        raise RuntimeError(
            "All required discovery sources failed; refusing to render a normal daily report"
        )
    unique = deduplicate(items)
    scored = [score_item(item, config["taxonomy"], now) for item in unique]
    selected = [
        item
        for item in scored
        if item.total_score >= float(settings["minimum_score"]) and item.categories
    ]
    selected.sort(key=lambda item: (item.total_score, item.published_at), reverse=True)
    return RadarRun(
        generated_at=now,
        since=since,
        items=selected[: int(settings["report_limit"])],
        health=health,
    )
