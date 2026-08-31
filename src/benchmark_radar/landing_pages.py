"""Static, decision-useful entry pages for the dashboard's three heavy views.

The interactive dashboard remains the best place to filter and inspect the
data.  These pages solve a different problem: a reader or crawler arriving at
``/leaderboard/``, ``/trends/``, or ``/explore/`` should receive the result,
meaning, and next action in the first HTML response.  They are generated from
the same rebuilt dashboard data as the app, so their claims cannot drift from
the published dataset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .feed import SITE_URL
from .site_shell import (
    breadcrumb_schema,
    esc,
    render_page,
    webpage_schema,
)

LANDING_PATHS = {
    "leaderboard": "/leaderboard/",
    "trends": "/trends/",
    "explore": "/explore/",
}


def _esc(value: Any) -> str:
    return esc(value)


def _count(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _stat(value: Any, label: str) -> str:
    return (
        f'<div class="content-stat"><strong>{_esc(value)}</strong><span>{_esc(label)}</span></div>'
    )


def _leaderboard_href(name: Any) -> str:
    query = urlencode({"view": "leaderboard", "lq": str(name or "")})
    return _esc(f"{SITE_URL}/?{query}")


def _page(
    *,
    slug: str,
    title: str,
    description: str,
    eyebrow: str,
    heading: str,
    lede: str,
    stats: str,
    body: str,
    interactive_query: str,
) -> str:
    canonical = f"{SITE_URL}{LANDING_PATHS[slug]}"
    interactive = f"{SITE_URL}/?{interactive_query}"
    page_body = f"""<header class="content-hero">
  <p class="eyebrow">{_esc(eyebrow)}</p>
  <h1>{_esc(heading)}</h1>
  <p class="content-lede">{_esc(lede)}</p>
  <div class="content-actions">
    <a class="primary-link" href="{interactive}">Open the interactive view</a>
    <a class="secondary-link" href="{SITE_URL}/benchmarks/">Browse benchmark pages</a>
  </div>
</header>
<div class="content-stats">{stats}</div>
{body}"""
    return render_page(
        title=title,
        description=description,
        canonical=canonical,
        active=slug,
        body=page_body,
        schemas=(
            webpage_schema(title=title, description=description, canonical=canonical),
            breadcrumb_schema(
                ("Benchmark Radar", f"{SITE_URL}/"),
                (heading, canonical),
                canonical=canonical,
            ),
        ),
    )


def _leaderboard_page(dashboard: dict[str, Any]) -> str:
    leaderboard = dashboard.get("model_card_leaderboard") or {}
    entries = list(leaderboard.get("entries") or [])[:10]
    rows = "".join(
        "<tr>"
        f'<td class="num">{_esc(entry.get("rank") or index)}</td>'
        f'<td><a href="{_leaderboard_href(entry.get("name"))}">'
        f"{_esc(entry.get('name') or 'Unnamed benchmark')}</a></td>"
        f'<td class="num">{_count(entry.get("card_count"))}</td>'
        f'<td class="num">{_count(entry.get("organization_count"))}</td>'
        "</tr>"
        for index, entry in enumerate(entries, start=1)
    )
    if not rows:
        rows = '<tr><td colspan="4">No reviewed model-card records are available yet.</td></tr>'
    body = f"""
<section class="content-section">
  <div class="content-section-heading"><h2>Most reported benchmarks</h2>
  <p class="section-note">Ranked by how many reviewed model and system cards
  report the benchmark.</p></div>
  <div class="table-wrap" role="region" aria-label="Most reported benchmarks" tabindex="0">
  <table class="content-table"><thead><tr><th class="num">Rank</th><th>Benchmark</th>
  <th class="num">Model cards</th><th class="num">Organizations</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
</section>
<section class="content-section content-panel">
  <h2>What this ranking means</h2>
  <p>This is an adoption ranking, not a claim that the first benchmark is the best one. Reporting
  frequency shows which tests make it into public model documentation and therefore shape how
  frontier systems are compared.</p>
  <p class="content-caveat">A familiar benchmark can be saturated, narrow, or reported
  under different protocols. Open a benchmark before comparing scores, and keep scores
  separated by source.</p>
</section>"""
    return _page(
        slug="leaderboard",
        title="Most reported AI benchmarks in model cards | Benchmark Radar",
        description=(
            "See which AI benchmarks appear most often in reviewed model and system cards, "
            "with adoption counts and the caveats needed to interpret them."
        ),
        eyebrow="Model-card adoption",
        heading="Which benchmarks do frontier labs actually report?",
        lede=(
            "A transparent adoption ranking built from reviewed model and system cards—not a "
            "single blended score and not a popularity poll."
        ),
        stats=(
            _stat(_count(leaderboard.get("model_card_count")), "reviewed model and system cards")
            + _stat(_count(leaderboard.get("benchmark_count")), "reported benchmarks")
            + _stat(_count(leaderboard.get("organization_count")), "reporting organizations")
        ),
        body=body,
        interactive_query="view=leaderboard",
    )


def _trends_page(dashboard: dict[str, Any]) -> str:
    days = list(dashboard.get("days") or [])
    recent = days[-14:]
    rows = "".join(
        "<tr>"
        f"<td>{_esc(day.get('date') or '')}</td>"
        f'<td class="num">{_count(day.get("evidence_count"))}</td>'
        f'<td class="num">{_count(len(day.get("source_counts") or {}))}</td>'
        "</tr>"
        for day in reversed(recent)
    )
    if not rows:
        rows = '<tr><td colspan="3">No daily snapshots are available yet.</td></tr>'
    corpus = dashboard.get("corpus") or {}
    body = f"""
<section class="content-section">
  <div class="content-section-heading"><h2>Recent discovery volume</h2>
  <p class="section-note">The latest 14 collected days, delivered in HTML without
  loading the full history.</p></div>
  <div class="table-wrap" role="region" aria-label="Recent discovery volume" tabindex="0">
  <table class="content-table"><thead><tr><th>Date</th><th class="num">Evidence records</th>
  <th class="num">Sources represented</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>
<section class="content-section content-panel">
  <h2>How to read the trend</h2>
  <p>Rising volume means the radar found more public benchmark evidence. It can reflect new
  releases, updates, or broader attention; it does not prove that benchmark quality improved.</p>
  <p class="content-caveat">Categories overlap and collection coverage varies. Use the
  interactive ledger to inspect the underlying day and source before drawing a causal
  conclusion.</p>
</section>"""
    return _page(
        slug="trends",
        title="AI benchmark discovery trends over time | Benchmark Radar",
        description=(
            "Track daily AI benchmark evidence volume over time, then inspect the dates and "
            "sources behind each change instead of treating discovery counts as quality."
        ),
        eyebrow="Evidence over time",
        heading="Is benchmark activity accelerating—or just getting louder?",
        lede=(
            "Daily discovery volume with the caveat that matters: more records means more public "
            "evidence was found, not that evaluation science got better."
        ),
        stats=(
            _stat(_count(corpus.get("observation_count")), "evidence observations collected")
            + _stat(_count(dashboard.get("snapshot_count")), "daily snapshots")
            + _stat(dashboard.get("latest_date") or "—", "latest collected day")
        ),
        body=body,
        interactive_query="view=trends",
    )


def _explore_page(dashboard: dict[str, Any], benchmark_count: int) -> str:
    corpus = dashboard.get("corpus") or {}
    body = f"""
<section class="content-section">
  <h2>Choose the shortest path to an answer</h2>
  <div class="content-grid">
    <article class="content-card"><h3>Find one benchmark</h3>
      <p>Use the static directory for a fast, shareable page with provenance
      and reported scores.</p>
      <a href="{SITE_URL}/benchmarks/">Open the directory</a></article>
    <article class="content-card"><h3>Follow a connection</h3>
      <p>Use the interactive map to move among benchmarks, organizations, sources, and topics.</p>
      <a href="{SITE_URL}/?view=map">Open the relationship map</a></article>
    <article class="content-card"><h3>Analyze the corpus</h3>
      <p>Download the public JSON when the question needs reproducible analysis
      rather than browsing.</p>
      <a href="{SITE_URL}/data/radar.json">Download the dataset</a></article>
  </div>
</section>
<section class="content-section content-panel">
  <h2>What the map can—and cannot—show</h2>
  <p>Connections come from collected evidence: shared organizations, people, sources, artifacts,
  and topics. They help a reader find context and adjacent work.</p>
  <p class="content-caveat">A connection is not an endorsement, citation, or proof of
  influence. Open the linked evidence before interpreting why two entities appear together.</p>
</section>"""
    return _page(
        slug="explore",
        title="Explore the AI benchmark landscape | Benchmark Radar",
        description=(
            "Explore AI benchmarks through static benchmark pages, an evidence relationship map, "
            "and the downloadable Benchmark Radar dataset."
        ),
        eyebrow="Benchmark landscape",
        heading="Find the benchmark, evidence, or connection you need.",
        lede=(
            "Start with a searchable benchmark page, follow relationships in the map, or download "
            "the corpus for your own analysis."
        ),
        stats=(
            _stat(_count(benchmark_count), "external catalog benchmark pages")
            + _stat(_count(corpus.get("entity_count")), "evidence graph entities")
            + _stat(_count(corpus.get("edge_count")), "evidence-backed connections")
        ),
        body=body,
        interactive_query="view=map",
    )


def write_landing_pages(
    dashboard: dict[str, Any],
    site_dir: Path,
    *,
    benchmark_count: int = 0,
) -> dict[str, Any]:
    """Write all three static view pages using atomic file replacement."""
    pages = {
        "leaderboard": _leaderboard_page(dashboard),
        "trends": _trends_page(dashboard),
        "explore": _explore_page(dashboard, benchmark_count),
    }
    written: list[Path] = []
    for slug, content in pages.items():
        output = site_dir / slug / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_suffix(".html.tmp")
        staging.write_text(content, encoding="utf-8")
        staging.replace(output)
        written.append(output)
    return {"page_count": len(written), "outputs": written}
