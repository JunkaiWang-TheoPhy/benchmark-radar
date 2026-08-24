#!/usr/bin/env python3
"""Generate repository-owned light and dark star-history SVGs."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query StarHistory($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    stargazers(first: 100, after: $cursor, orderBy: {field: STARRED_AT, direction: ASC}) {
      edges { starredAt }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


def fetch_star_dates(repo: str, token: str) -> list[date]:
    """Read every stargazer timestamp through the repository's own token."""
    owner, name = repo.split("/", 1)
    cursor: str | None = None
    dates: list[date] = []

    while True:
        body = json.dumps(
            {
                "query": QUERY,
                "variables": {"owner": owner, "name": name, "cursor": cursor},
            }
        ).encode()
        request = Request(
            GRAPHQL_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "benchmark-radar-star-history",
            },
        )
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub endpoint
            payload = json.load(response)
        if errors := payload.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error: {errors[0]['message']}")

        connection = payload["data"]["repository"]["stargazers"]
        dates.extend(
            datetime.fromisoformat(edge["starredAt"].replace("Z", "+00:00")).date()
            for edge in connection["edges"]
        )
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            return dates
        cursor = page["endCursor"]


def cumulative_points(star_dates: list[date]) -> list[tuple[date, int]]:
    """Collapse individual stars into a cumulative daily series."""
    counts = Counter(star_dates)
    total = 0
    points = []
    for day in sorted(counts):
        total += counts[day]
        points.append((day, total))
    return points


def _ticks(start: date, end: date, count: int = 5) -> list[date]:
    span = (end - start).days
    if span == 0:
        return [start]
    return [start + timedelta(days=round(span * index / (count - 1))) for index in range(count)]


def render_svg(repo: str, points: list[tuple[date, int]], *, dark: bool) -> str:
    """Render a dependency-free, theme-specific SVG chart."""
    width, height = 800, 480
    left, right, top, bottom = 72, 28, 72, 62
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = {
        "background": "#0d1117" if dark else "#ffffff",
        "text": "#e6edf3" if dark else "#1f2328",
        "muted": "#8b949e" if dark else "#656d76",
        "grid": "#30363d" if dark else "#d8dee4",
        "line": "#58a6ff" if dark else "#0969da",
        "area": "#1f6feb" if dark else "#54aeff",
    }

    if not points:
        message = '<text x="400" y="245" text-anchor="middle" font-size="20">No stars yet</text>'
        plot = message
        subtitle = "0 stars"
    else:
        first_day, last_day = points[0][0], points[-1][0]
        max_stars = points[-1][1]
        span = max((last_day - first_day).days, 1)

        def x(day: date) -> float:
            return left + (day - first_day).days / span * plot_width

        def y(stars: int) -> float:
            return top + plot_height - stars / max_stars * plot_height

        coordinates = [(x(day), y(stars)) for day, stars in points]
        if first_day == last_day:
            coordinates = [(left, y(max_stars)), (left + plot_width, y(max_stars))]
        line_path = " ".join(
            f"{'M' if index == 0 else 'L'} {px:.1f} {py:.1f}"
            for index, (px, py) in enumerate(coordinates)
        )
        area_path = (
            f"M {coordinates[0][0]:.1f} {top + plot_height:.1f} "
            + " ".join(f"L {px:.1f} {py:.1f}" for px, py in coordinates)
            + f" L {coordinates[-1][0]:.1f} {top + plot_height:.1f} Z"
        )

        y_step = max(1, math.ceil(max_stars / 4))
        y_values = sorted({0, max_stars, *(min(max_stars, y_step * i) for i in range(1, 4))})
        grid = []
        for value in y_values:
            py = y(value)
            grid.append(
                f'<line x1="{left}" y1="{py:.1f}" x2="{left + plot_width}" y2="{py:.1f}" />'
            )
            grid.append(f'<text x="{left - 12}" y="{py + 5:.1f}" text-anchor="end">{value}</text>')
        date_ticks = _ticks(first_day, last_day)
        for index, day in enumerate(date_ticks):
            px = x(day)
            anchor = "start" if index == 0 else "end" if index == len(date_ticks) - 1 else "middle"
            grid.append(
                f'<text x="{px:.1f}" y="{height - 28}" text-anchor="{anchor}">{day:%Y-%m-%d}</text>'
            )

        plot = (
            f'<g class="grid">{"".join(grid)}</g>'
            f'<path d="{area_path}" fill="{colors["area"]}" opacity="0.18" />'
            f'<path d="{line_path}" fill="none" stroke="{colors["line"]}" stroke-width="3" '
            'stroke-linecap="round" stroke-linejoin="round" />'
            f'<circle cx="{coordinates[-1][0]:.1f}" cy="{coordinates[-1][1]:.1f}" '
            f'r="5" fill="{colors["line"]}" />'
        )
        subtitle = f"{max_stars:,} stars · {first_day:%Y-%m-%d} – {last_day:%Y-%m-%d}"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
  role="img" aria-labelledby="title description">
  <title id="title">{escape(repo)} star history</title>
  <desc id="description">{escape(subtitle)}</desc>
  <rect width="{width}" height="{height}" rx="12" fill="{colors["background"]}" />
  <style>
    text {{
      fill: {colors["text"]};
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .grid line {{ stroke: {colors["grid"]}; stroke-width: 1; }}
    .grid text {{ fill: {colors["muted"]}; font-size: 12px; }}
  </style>
  <text x="{left}" y="34" font-size="22" font-weight="600">{escape(repo)} Star History</text>
  <text x="{left}" y="56" font-size="13" fill="{colors["muted"]}">{escape(subtitle)}</text>
  {plot}
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="GitHub repository as owner/name")
    parser.add_argument("--token", required=True, help="GitHub token that can read stargazers")
    parser.add_argument("--output-dir", type=Path, default=Path("assets"))
    args = parser.parse_args()

    points = cumulative_points(fetch_star_dates(args.repo, args.token))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "star-history.svg").write_text(
        render_svg(args.repo, points, dark=False), encoding="utf-8"
    )
    (args.output_dir / "star-history-dark.svg").write_text(
        render_svg(args.repo, points, dark=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
