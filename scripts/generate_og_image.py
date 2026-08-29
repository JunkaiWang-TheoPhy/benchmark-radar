"""Render the Open Graph saturation card for the repository and dashboard.

The share image uses the same score-frontier data as the site, not the model-card
adoption ranking, so a shared card shows reported scores over time and their
approach to a ceiling.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from benchmark_radar.benchmark_scores import DEFAULT_SCORES_PATH, build_score_progression

WIDTH = 1200
HEIGHT = 630
BACKGROUND = "#FAFAFA"
INK = "#1B2A4A"
TEAL = "#2A7F8E"
SLATE = "#6B7B8D"
LIGHT = "#DDE3E8"
COLORS = ("#2A7F8E", "#D26A3A", "#6D58A6", "#3D8B5D")

MARGIN = 64
TITLE_SIZE = 46
MIN_TITLE_PROBE_WIDTH = 150
CHART_BENCHMARKS = ("gpqa_diamond", "hle", "terminal_bench", "swe_bench_verified")


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/DejaVuSans-Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/DejaVuSans.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc"
        if bold
        else "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _assert_scalable_fonts() -> None:
    """Refuse to write a card whose text ignored the requested size."""
    probe = "Benchmark"
    title_width = font(TITLE_SIZE, bold=True).getbbox(probe)[2]
    if title_width < MIN_TITLE_PROBE_WIDTH:
        raise SystemExit(
            f'Fonts resolved to a face that ignores the requested size: "{probe}" '
            f"measured {title_width}px wide at {TITLE_SIZE}px, expected at least "
            f"{MIN_TITLE_PROBE_WIDTH}px. Install DejaVu fonts and re-run."
        )


def _short_name(name: str) -> str:
    return {
        "Gpqa Diamond": "GPQA",
        "Hle": "HLE",
        "Swe Bench Verified": "SWE-bench",
    }.get(name, name)


def _date_position(value: str, first: date, span: int, left: int, width: int) -> int:
    return left + round((date.fromisoformat(value) - first).days / span * width)


def render(progression: dict, output: Path) -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 12, HEIGHT], fill=TEAL)

    title = font(TITLE_SIZE, bold=True)
    subtitle = font(30)
    body = font(22)
    label = font(20, bold=True)
    legend = font(21)

    y = MARGIN - 12
    draw.text((MARGIN, y), "Benchmark Radar", font=title, fill=INK)
    y += 60
    draw.text((MARGIN, y), "Where benchmark scores start to plateau", font=subtitle, fill=TEAL)
    y += 55
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=LIGHT, width=2)

    records = [
        progression["benchmarks"][benchmark_id]
        for benchmark_id in CHART_BENCHMARKS
        if benchmark_id in progression.get("benchmarks", {})
    ]
    if not records:
        raise ValueError("score progression contains no configured chart benchmarks")
    first = min(date.fromisoformat(record["first_reported_at"]) for record in records)
    last = max(date.fromisoformat(record["last_reported_at"]) for record in records)
    span = max((last - first).days, 1)
    left, right, top, bottom = MARGIN + 48, WIDTH - MARGIN - 10, y + 52, y + 282
    plot_width, plot_height = right - left, bottom - top

    for value in (0, 25, 50, 75, 100):
        grid_y = bottom - round(value / 100 * plot_height)
        draw.line([(left, grid_y), (right, grid_y)], fill=LIGHT, width=1)
        draw.text((left - 14, grid_y), str(value), font=legend, fill=SLATE, anchor="ra")
    draw.text((left - 48, top - 25), "%", font=label, fill=SLATE)

    for index, record in enumerate(records):
        points = record["historical_best_frontier"]["points"]
        xy = []
        for point in points:
            x = _date_position(point["reported_at"], first, span, left, plot_width)
            value = max(0, min(100, float(point["value"])))
            xy.append((x, bottom - round(value / 100 * plot_height)))
        if len(xy) > 1:
            draw.line(xy, fill=COLORS[index], width=5, joint="curve")
        for x, point_y in xy:
            draw.ellipse([x - 5, point_y - 5, x + 5, point_y + 5], fill=COLORS[index])

        legend_x = MARGIN + index * 260
        draw.ellipse([legend_x, bottom + 30, legend_x + 12, bottom + 42], fill=COLORS[index])
        draw.text(
            (legend_x + 22, bottom + 24),
            _short_name(record["benchmark_id"].replace("_", " ").title()),
            font=legend,
            fill=INK,
        )

    draw.text((left, bottom + 70), first.strftime("%b %Y"), font=legend, fill=SLATE)
    draw.text((right, bottom + 70), last.strftime("%b %Y"), font=legend, fill=SLATE, anchor="ra")
    y = bottom + 112
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=LIGHT, width=2)
    y += 20
    draw.text(
        (MARGIN, y),
        f"{progression['observation_count']} cited scores across "
        f"{progression['benchmark_count']} benchmarks",
        font=body,
        fill=INK,
    )
    y += 30
    draw.text(
        (MARGIN, y),
        "Historical best frontier · reporting signal, not a quality leaderboard",
        font=body,
        fill=SLATE,
    )
    draw.text(
        (WIDTH - MARGIN, y + 2),
        "github.com/ktwu01/benchmark-radar",
        font=font(19),
        fill=TEAL,
        anchor="ra",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES_PATH)
    parser.add_argument("--output", type=Path, default=Path("site/assets/og-card.png"))
    args = parser.parse_args()
    _assert_scalable_fonts()
    path = render(build_score_progression(args.scores), args.output)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
