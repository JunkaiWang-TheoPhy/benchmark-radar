from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import rubric
from .attention import fetch_attention_feeds
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
    for item in sorted(
        items,
        key=lambda value: value.updated_at or value.published_at,
        reverse=True,
    ):
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
    *,
    lookback_hours: float = rubric.DEFAULT_LOOKBACK_HOURS,
) -> RadarItem:
    now = now or datetime.now(UTC)
    # Only match against text a human actually wrote about the artifact. If a
    # fetcher ever reintroduces a generated summary, the words in it must not
    # earn relevance -- otherwise the pipeline scores itself on its own prose.
    haystack = f"{item.title} {item.summary}".lower()
    categories = []
    matched_terms: list[str] = []
    for category, terms in taxonomy.items():
        matches = [term for term in terms if term.lower() in haystack]
        if matches:
            categories.append(category)
            matched_terms.extend(matches[:2])
    item.categories = categories
    relevance = min(
        rubric.SCORE_MAX,
        rubric.RELEVANCE_PER_CATEGORY * len(categories)
        + rubric.RELEVANCE_PER_TERM * len(matched_terms),
    )
    deductions = [
        signal
        for signal in rubric.LOW_VALUE_SIGNALS
        if re.search(str(signal["pattern"]), haystack, flags=re.IGNORECASE)
    ]
    deduction = min(
        rubric.MAX_LOW_VALUE_DEDUCTION,
        sum(float(signal["deduction"]) for signal in deductions),
    )
    item.relevance_score = max(0.0, relevance - deduction)
    item.suppression_reasons = [
        str(signal["label"]) for signal in deductions if signal["action"] == "suppress"
    ]

    evidence = rubric.EVIDENCE_BASE
    if item.source in rubric.EVIDENCE_PRIMARY_SOURCES:
        evidence += rubric.EVIDENCE_PRIMARY_CREDIT
    if item.source in rubric.EVIDENCE_ARTIFACT_SOURCES:
        evidence += rubric.EVIDENCE_ARTIFACT_CREDIT
    if item.authors:
        evidence += rubric.EVIDENCE_AUTHORSHIP_CREDIT
    if item.artifact_urls:
        evidence += rubric.EVIDENCE_CROSS_LINK_CREDIT
    item.evidence_score = min(evidence, rubric.SCORE_MAX)

    activity_at = item.updated_at or item.published_at
    age_hours = max(0.0, (now - activity_at).total_seconds() / 3600)
    if lookback_hours <= 0:
        raise ValueError("lookback_hours must be positive")
    item.recency_score = max(
        0.0,
        rubric.SCORE_MAX * (1.0 - age_hours / lookback_hours),
    )

    adoption = max(
        (
            rubric.SCORE_MAX
            * math.log10(1 + max(0.0, float(item.metrics.get(metric, 0))))
            / math.log10(1 + saturation)
            for metric, saturation in rubric.ADOPTION_METRIC_SATURATION.items()
            if item.metrics.get(metric, 0)
        ),
        default=0.0,
    )
    item.adoption_score = min(adoption, rubric.SCORE_MAX)
    item.total_score = round(
        sum(
            weight * getattr(item, f"{component}_score")
            for component, weight in rubric.WEIGHTS.items()
        ),
        2,
    )
    item.score_version = rubric.SCORING_VERSION
    item.score_max = rubric.SCORE_MAX
    item.rationale = [
        reason
        for reason in item.rationale
        if not reason.startswith(("Matched:", "Demoted:", "Primary record:"))
    ]
    if matched_terms:
        item.rationale.append(f"Matched: {', '.join(sorted(set(matched_terms)))}")
    for signal in deductions:
        item.rationale.append(
            f"Demoted: {signal['label']} (-{float(signal['deduction']):g} relevance)"
        )
    item.rationale.append(f"Primary record: {item.source}")
    return item


def apply_watchlist(
    items: list[RadarItem],
    watchlist: list[dict[str, Any]],
) -> list[RadarItem]:
    """Tag records naming an artifact the reader always wants to see.

    Only the title and source id are matched. A watchlisted name mentioned in
    passing inside an abstract describes related work, not a release of that
    artifact, so including the summary pinned unrelated papers to the top.
    Matching is on word boundaries for the same reason: a bare substring made
    "long horizon" swallow every agent paper that used the phrase.

    This marks and routes the record only; it never edits a score, so the
    published ranking stays explainable.
    """
    if not watchlist:
        return items
    for item in items:
        haystack = f"{item.title} {item.source_id}".casefold()
        for entry in watchlist:
            name = str(entry.get("name") or "").strip()
            aliases = [str(alias).casefold() for alias in entry.get("aliases") or []]
            terms = [alias for alias in [*aliases, name.casefold()] if alias]
            # Hyphens, spaces and underscores are interchangeable separators
            # so "mle-bench", "mle bench" and "mle_bench" all match one alias.
            patterns = [
                r"(?<![0-9a-z])"
                + r"[\s_-]*".join(re.escape(part) for part in re.split(r"[\s_-]+", term) if part)
                + r"(?![0-9a-z])"
                for term in terms
            ]
            if any(re.search(pattern, haystack) for pattern in patterns):
                item.watchlist = name or terms[0]
                item.watchlist_note = str(entry.get("note") or "").strip()
                item.rationale.append(f"Watchlist: {item.watchlist}")
                break
    return items


BOILERPLATE_THRESHOLD = 3


def assert_no_boilerplate_summaries(items: list[RadarItem]) -> None:
    """Fail the run when a fetcher emits one summary for many different records.

    A summary repeated across unrelated artifacts is templated text, not a
    description. It misleads the reader and, because `score_item` reads
    `summary`, it also inflates relevance for every record from that source.
    This is a hard error rather than a warning: a silently boilerplated report
    looks successful, which is how the defect survived unnoticed before.
    """
    counts = Counter(item.summary.strip().lower() for item in items if item.summary.strip())
    repeated = {text: n for text, n in counts.items() if n >= BOILERPLATE_THRESHOLD}
    if repeated:
        worst = max(repeated.items(), key=lambda pair: pair[1])
        raise RuntimeError(
            f"Refusing to publish templated descriptions: {worst[1]} records share the "
            f"summary {worst[0]!r}. Derive summaries from source metadata (see describe.py) "
            "and leave them empty when the source publishes none."
        )


def _date(value: str | None, *, fallback: datetime) -> datetime:
    if not value:
        return fallback
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _apply_arxiv_discovery_state(
    fetched: list[RadarItem],
    *,
    now: datetime,
    state: dict[str, Any],
) -> list[RadarItem]:
    arxiv_state = state.setdefault("arxiv", {})
    changed: list[RadarItem] = []
    for item in fetched:
        previous = arxiv_state.get(item.source_id) or {}
        activity_at = item.updated_at or item.published_at
        item.discovered_at = _date(previous.get("discovered_at"), fallback=now)
        previous_activity = _date(
            previous.get("last_activity_at"),
            fallback=datetime.min.replace(tzinfo=UTC),
        )
        if not previous or activity_at > previous_activity:
            changed.append(item)
        arxiv_state[item.source_id] = {
            "discovered_at": item.discovered_at.astimezone(UTC).isoformat(),
            "last_activity_at": activity_at.astimezone(UTC).isoformat(),
        }
    return changed


def run_pipeline(
    config: dict[str, Any],
    now: datetime | None = None,
    *,
    previous_snapshot: dict[str, Any] | None = None,
) -> RadarRun:
    now = now or datetime.now(UTC)
    settings = config["radar"]
    since = now - timedelta(hours=int(settings["lookback_hours"]))
    limit = int(settings["max_items_per_source"])
    items: list[RadarItem] = []
    health: list[SourceHealth] = []
    # Counted before arXiv overlap suppression, so this always agrees with the
    # per-source health table rather than silently excluding repeat records.
    fetched_count = 0
    suppressed_count = 0
    discovery_state = deepcopy((previous_snapshot or {}).get("discovery_state") or {})
    for source_name, source_config in config["sources"].items():
        if not source_config.get("enabled", True):
            continue
        fetcher = SOURCE_FETCHERS[source_name]
        try:
            fetched = fetcher(source_config, since, limit)
            fetched_count += len(fetched)
            health.append(SourceHealth(source=source_name, ok=True, item_count=len(fetched)))
            if source_name == "arxiv":
                changed = _apply_arxiv_discovery_state(
                    fetched,
                    now=now,
                    state=discovery_state,
                )
                suppressed_count += len(fetched) - len(changed)
                items.extend(changed)
            else:
                for item in fetched:
                    item.discovered_at = now
                items.extend(fetched)
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
    required_health = {source.source: source for source in health if source.source in required}
    unavailable_required = []
    for source in sorted(required):
        source_health = required_health.get(source)
        if source_health is None:
            unavailable_required.append(f"{source} was not checked")
        elif not source_health.ok:
            unavailable_required.append(
                f"{source} failed" + (f" ({source_health.error})" if source_health.error else "")
            )
        elif source_health.item_count == 0:
            unavailable_required.append(f"{source} returned no records")
    if unavailable_required:
        raise RuntimeError(
            "Required discovery sources failed or returned no records: "
            + ", ".join(unavailable_required)
        )
    unique = deduplicate(items)
    scored = apply_watchlist(
        [
            score_item(
                item,
                config["taxonomy"],
                now,
                lookback_hours=float(settings["lookback_hours"]),
            )
            for item in unique
        ],
        config.get("watchlist") or [],
    )
    selected = [
        item
        for item in scored
        # A watchlist hit is published even when the generic score or taxonomy
        # would have dropped it: the reader asked for these by name.
        if item.watchlist
        or (
            not item.suppression_reasons
            and item.total_score >= float(settings["minimum_score"])
            and item.categories
        )
    ]
    selected.sort(
        key=lambda item: (bool(item.watchlist), item.total_score, item.published_at),
        reverse=True,
    )
    published = selected[: int(settings["report_limit"])]
    assert_no_boilerplate_summaries(published)
    # The dashboard previously showed "228 found" beside 8 published records
    # with nothing to explain the gap. Persist each stage so the drop-off is
    # auditable rather than looking like lost data.
    selection = {
        "fetched": fetched_count,
        # arXiv records already seen in a previous run, dropped before dedupe.
        "suppressed_as_seen": suppressed_count,
        "deduplicated": len(unique),
        "scored": len(scored),
        "qualified": len(selected),
        # Qualified purely by a watchlist match, so the threshold wording in
        # the report stays true for the records that did clear the bar.
        "watchlisted": sum(
            1
            for item in selected
            if item.watchlist
            and not (
                not item.suppression_reasons
                and item.total_score >= float(settings["minimum_score"])
                and item.categories
            )
        ),
        "suppressed_low_value": sum(
            1 for item in scored if item.suppression_reasons and not item.watchlist
        ),
        "published": len(published),
        "minimum_score": float(settings["minimum_score"]),
        "report_limit": int(settings["report_limit"]),
        "lookback_hours": float(settings["lookback_hours"]),
        "score_version": rubric.SCORING_VERSION,
        "score_max": rubric.SCORE_MAX,
    }
    attention, attention_health, producer_health, attention_state = fetch_attention_feeds(
        config.get("attention") or {},
        observed_at=now,
        previous_state=((previous_snapshot or {}).get("discovery_state") or {}).get("attention")
        or {},
    )
    return RadarRun(
        generated_at=now,
        since=since,
        items=published,
        health=health,
        attention=attention,
        attention_ingest_health=attention_health,
        producer_health=producer_health,
        selection=selection,
        discovery_state={
            **discovery_state,
            "attention": attention_state,
        },
    )
