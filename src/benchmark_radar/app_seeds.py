"""Build the HTML each dashboard view ships in its first response.

``app_pages`` writes copies of ``site/index.html`` at ``/leaderboard/``,
``/trends/`` and ``/explore/``. The seeds here are what those copies carry
inside the containers ``assets/app.js`` renders into.

One rule governs all of them: a seed is what the renderer would produce from the
same data, in the same markup, no more and no less. A summary written for
crawlers would show them a page no reader sees. Leaving out a card the renderer
always draws does the same thing in the other direction: the crawler gets a
thinner page than the reader, under a canonical that claims otherwise. Every
seed below names the function in ``assets/app.js`` it mirrors, so a change on
one side has an obvious counterpart on the other.
"""

from __future__ import annotations

from typing import Any

from .site_shell import esc


def _num(value: Any) -> str:
    """Match Number.toLocaleString() for the en locale these seeds are written in."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _metric_label(value: Any, singular: str, plural: str | None = None) -> str:
    count = int(value or 0)
    noun = singular if count == 1 else (plural or f"{singular}s")
    return f"{count:,} {noun}"


def _collate(name: str) -> tuple[str, str]:
    """Order names the way String.prototype.localeCompare does for en.

    The renderers break count ties on the name, and the browser compares
    case-insensitively first: "arXiv" lands before "OpenAI" there and after it
    under Python's codepoint sort. Without this the two lists would disagree for
    the same data, which is exactly what a seed must never do.
    """
    return (name.casefold(), name)


# --- Leaderboard --------------------------------------------------------------

LEADERBOARD_TOP_LIMIT = 5

# The sentence renderLeaderboardTop joins onto board.measures inside the (i)
# beside the ranking. It is the caveat that keeps an adoption count from being
# read as a quality score, so a page that ships the ranking ships it too.
LEADERBOARD_TOP_NOTE = (
    "A report counts once per test, even if it lists that test several times. "
    "Some reports publish their results as a picture rather than text, and we "
    "read those with software that can misread a digit, so the list at the "
    "bottom of this page links every count back to the report it came from."
)


def _info_disclosure(text: str) -> str:
    """The markup infoDisclosure emits."""
    return (
        '<details class="info-disclosure">'
        '<summary class="info-disclosure-toggle" aria-label="What does this source record?">'
        "i</summary>"
        f'<p class="info-disclosure-body">{esc(text)}</p>'
        "</details>"
    )


def _leaderboard_seed(dashboard: dict[str, Any]) -> dict[str, str]:
    """The top rows, the measures note and the caveat renderLeaderboardTop emits."""
    board = dashboard.get("model_card_leaderboard") or {}
    ranked = [entry for entry in (board.get("entries") or []) if (entry.get("card_count") or 0) > 0]
    entries = ranked[:LEADERBOARD_TOP_LIMIT]
    if not entries:
        return {}
    # Scaled against the top row on screen rather than the top row overall,
    # because that is what the renderer scales against.
    top = max(int(entry["card_count"]) for entry in entries)
    rows = "".join(
        '<li class="leaderboard-top-row">'
        f'<span class="leaderboard-top-rank">{esc(str(entry.get("rank", "")).zfill(2))}</span>'
        f'<span class="leaderboard-top-name">{esc(entry.get("name") or "")}</span>'
        '<span class="leaderboard-top-bar">'
        '<span class="leaderboard-top-bar-fill" '
        f'style="width:{int(entry["card_count"]) / top * 100:.1f}%"></span>'
        "</span>"
        '<span class="leaderboard-top-count">'
        f"{esc(_metric_label(entry.get('card_count'), 'model card'))}</span>"
        "</li>"
        for entry in entries
    )
    measures = board.get("measures")
    note = " ".join(part for part in (measures, LEADERBOARD_TOP_NOTE) if part)
    seed = {
        '<ol class="leaderboard-top-list" id="leaderboard-top-list"></ol>': (
            f'<ol class="leaderboard-top-list" id="leaderboard-top-list" data-seed>{rows}</ol>'
        ),
        '<span id="leaderboard-top-info"></span>': (
            f'<span id="leaderboard-top-info" data-seed>{_info_disclosure(note)}</span>'
        ),
    }
    if measures:
        seed['<p class="leaderboard-deck visually-hidden" id="leaderboard-measures"></p>'] = (
            '<p class="leaderboard-deck visually-hidden" id="leaderboard-measures" data-seed>'
            f"{esc(measures)}</p>"
        )
    return seed


# --- Trends -------------------------------------------------------------------

# Intl.DateTimeFormat("en", {dateStyle: "medium"}) abbreviations. Spelled out
# rather than taken from strftime, whose %b follows the machine's LC_TIME and
# would make the published page depend on the runner's locale.
_MEDIUM_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _medium_date(value: str) -> str:
    """Match formatDate(value, {dateStyle: "medium"}) for the en locale."""
    try:
        year, month, day = (int(part) for part in value.split("-")[:3])
        return f"{_MEDIUM_MONTHS[month - 1]} {day}, {year}"
    except (AttributeError, IndexError, ValueError):
        return "Unknown"


def _domain_rows(trend: dict[str, Any]) -> list[tuple[str, str]]:
    """The stat rows domainCard builds, in its order and with its wording."""
    delta = trend.get("delta")
    if delta is None:
        change = "not comparable"
    else:
        change = "no change" if not int(delta) else f"{int(delta):+d}"
    baseline = trend.get("baseline")
    rows: list[tuple[str, str]] = [
        ("vs previous scan", change),
        (
            "recent daily average",
            "not enough history" if baseline is None else f"{float(baseline):.2f}",
        ),
    ]
    momentum = trend.get("momentum")
    if momentum is not None:
        percent = round(float(momentum) * 100)
        rows.append(("vs its average", f"{'+' if percent > 0 else ''}{percent}%"))
    rows.append(("cumulative", _num(trend.get("cumulative"))))
    updated_only = max(0, int(trend.get("total_count") or 0) - int(trend.get("count") or 0))
    if updated_only:
        rows.append(("also updated (not counted above)", _num(updated_only)))
    return rows


def _trends_seed(
    dashboard: dict[str, Any], palette: tuple[dict[str, str], list[str]]
) -> dict[str, str]:
    """The latest day's domain cards and its date, as renderDomainMetrics writes them."""
    days = dashboard.get("days") or []
    if not days:
        return {}
    day = days[-1]
    trends = day.get("category_trends") or {}
    entries = sorted(trends.items(), key=lambda item: (-int(item[1].get("count") or 0), item[0]))
    if not entries:
        return {}
    colors, fallbacks = palette
    cards = []
    for index, (category, trend) in enumerate(entries):
        delta = trend.get("delta")
        direction = ""
        if delta is not None:
            direction = " is-up" if int(delta) > 0 else (" is-down" if int(delta) < 0 else "")
        swatch = colors.get(category, fallbacks[index % len(fallbacks)])
        stats = "".join(
            f"<dt>{esc(label)}</dt><dd>{esc(value)}</dd>" for label, value in _domain_rows(trend)
        )
        cards.append(
            f'<article class="domain-card{direction}">'
            '<div class="domain-head">'
            f'<span class="legend-swatch" style="--swatch: {esc(swatch)};"></span>'
            f"<h3>{esc(category.replace('_', ' '))}</h3>"
            "</div>"
            '<p class="domain-count" '
            'title="New releases only. Re-announced updates are tracked separately.">'
            f"{esc(int(trend.get('count') or 0))}</p>"
            f'<dl class="domain-stats">{stats}</dl>'
            "</article>"
        )
    return {
        '<div class="domain-grid" id="domain-grid" aria-labelledby="domain-heading"></div>': (
            '<div class="domain-grid" id="domain-grid" aria-labelledby="domain-heading" data-seed>'
            f"{''.join(cards)}</div>"
        ),
        # The cards count one scan, so the heading beside them has to say which.
        '<span id="domain-date"></span>': (
            f'<span id="domain-date" data-seed>{esc(_medium_date(day.get("date")))}</span>'
        ),
    }


# --- Explore ------------------------------------------------------------------

# The five entity kinds renderMapInsights counts, with its labels.
MAP_COVERAGE_ROWS = (
    ("Items", "artifact"),
    ("Organizations", "organization"),
    ("Authors", "person"),
    ("Sources", "source"),
    ("Topics", "topic"),
)

# renderMapInsights spells out the topic keys a reader would not recognize and
# falls back to the key with its underscores opened up.
MAP_TOPIC_LABELS = {
    "agentic": "AI agents",
    "benchmark": "benchmarks",
    "dataset": "datasets",
    "evaluation": "evaluations",
    "data_quality": "data quality",
}


def _ranked_counts(values: Any, limit: int = 6) -> list[tuple[str, int]]:
    """The rankedCounts helper: highest count first, ties broken on the name."""
    items = (values or {}).items() if isinstance(values, dict) else ()
    ranked = sorted(items, key=lambda item: (-int(item[1] or 0), _collate(str(item[0]))))
    return [(str(name), int(count or 0)) for name, count in ranked[:limit]]


def _map_insight_card(title: str, entries: list[tuple[str, str]], empty_text: str) -> str:
    """The markup mapInsightCard emits for rows that carry no drill-in detail."""
    if entries:
        body = "".join(
            f"<li><span>{esc(label)}</span><strong>{esc(value)}</strong></li>"
            for label, value in entries
        )
        body = f"<ul>{body}</ul>"
    else:
        body = f"<p>{esc(empty_text)}</p>"
    return f'<article class="map-insight-card"><h2>{esc(title)}</h2>{body}</article>'


def _map_seed(dashboard: dict[str, Any]) -> dict[str, str]:
    """The four cards renderMapInsights builds, in its order.

    All four, not just the coverage counts: the renderer always draws the topic,
    source and organization rankings, so a page that shipped one card would give
    a crawler a quarter of what a reader sees.
    """
    aggregates = (dashboard.get("corpus") or {}).get("aggregates") or {}
    entity_types = aggregates.get("entity_types") or {}
    topics = aggregates.get("topics") or []
    sources = aggregates.get("sources") or {}
    organizations = aggregates.get("organizations") or {}
    if not (entity_types or topics or sources or organizations):
        return {}

    coverage = [(label, _num(entity_types.get(key))) for label, key in MAP_COVERAGE_ROWS]
    ranked_topics = sorted(
        topics,
        key=lambda topic: (
            -int(topic.get("entity_count") or 0),
            _collate(str(topic.get("topic"))),
        ),
    )
    topic_rows = []
    for topic in ranked_topics:
        key = str(topic.get("topic"))
        topic_rows.append(
            (
                MAP_TOPIC_LABELS.get(key, key.replace("_", " ")),
                f"{_num(topic.get('entity_count'))} items"
                f" · {_metric_label(topic.get('source_breadth'), 'source')}",
            )
        )
    source_rows = [(name, f"{_num(count)} times found") for name, count in _ranked_counts(sources)]
    organization_rows = [
        (name, f"{_num(count)} times found") for name, count in _ranked_counts(organizations)
    ]

    cards = "".join(
        (
            _map_insight_card("At a glance", coverage, "Nothing found yet."),
            _map_insight_card("What it is about", topic_rows, "No topics yet."),
            _map_insight_card("Where we found it", source_rows, "No sources yet."),
            _map_insight_card("Who appears most", organization_rows, "No organizations yet."),
        )
    )
    return {
        '<div class="map-insights" id="map-insights" aria-label="Overview"></div>': (
            '<div class="map-insights" id="map-insights" aria-label="Overview" data-seed>'
            f"{cards}</div>"
        )
    }


def view_seeds(
    dashboard: dict[str, Any], palette: tuple[dict[str, str], list[str]]
) -> dict[str, dict[str, str]]:
    """Every view's seed, keyed by view. An empty dict means nothing to publish."""
    return {
        "leaderboard": _leaderboard_seed(dashboard),
        "trends": _trends_seed(dashboard, palette),
        "map": _map_seed(dashboard),
    }
