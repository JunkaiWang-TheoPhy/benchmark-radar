"""Generate the figures embedded in the AI benchmark landscape report."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1400
BACKGROUND = "#FAFAFA"
INK = "#1B2A4A"
TEAL = "#2A7F8E"
CORAL = "#E0604E"
GOLD = "#D4A843"
SLATE = "#6B7B8D"
LIGHT = "#DDE3E8"
PALE = "#EEF2F4"
GREEN = "#5D7A5D"
RED = "#8B3A3A"
SOURCE_COLORS = {"arXiv": INK, "Hugging Face": TEAL, "GitHub": GOLD}

THEME_PATTERNS = {
    "Software & computer use": re.compile(
        r"\b(?:code|coding|software|web|browser|gui|computer|office|database|terminal|"
        r"devops|repository|repositories|repo|swe)\b"
    ),
    "Tool use & planning": re.compile(
        r"\b(?:tool|tools|tooling|planning|plan|workflow|function[ -]?call|"
        r"function[ -]?calls|action|actions|reasoning)\b"
    ),
    "Memory & long horizon": re.compile(
        r"\b(?:memory|context|long[ -]?horizon|long[ -]?term|persistent|trajectory|"
        r"trajectories)\b"
    ),
    "Domain & professional tasks": re.compile(
        r"\b(?:health|patient|patients|medical|finance|financial|legal|science|scientific|"
        r"aerial|bim|education|robot|robots|robotic|robotics)\b"
    ),
    "Security & safety": re.compile(
        r"\b(?:security|secure|securing|attack|attacks|pentest|pentesting|vulnerability|"
        r"vulnerabilities|vulnerable|red[ -]?team|red[ -]?teaming|poison|poisoning|"
        r"privacy|stealth|stealthy|risk|risks|safe|safety|unsafe)\b"
    ),
    "Multi-agent coordination": re.compile(
        r"\b(?:multi[ -]?agent|multi[ -]?agents|orchestration|orchestrating|cooperation|"
        r"cooperative|collaboration|collaborative|team|teams|coordination)\b"
    ),
}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


LABEL = font(29)
LABEL_BOLD = font(29, bold=True)
VALUE = font(45, bold=True)
TILE_VALUE = font(68, bold=True)
SMALL = font(24)


def load_data(repo: Path, cutoff: date) -> tuple[list[dict], dict, dict]:
    snapshots = []
    artifacts: dict[tuple[str, str], dict] = {}
    for path in sorted((repo / "data" / "snapshots").glob("*.json")):
        if date.fromisoformat(path.stem) > cutoff:
            continue
        snapshot = json.loads(path.read_text())
        snapshots.append(snapshot)
        for item in snapshot["evidence_items"]:
            artifacts[(item["source"], item["source_id"])] = item
    config = yaml.safe_load((repo / "config.yml").read_text())
    return list(artifacts.values()), snapshots[-1], config


def canvas(height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, height), BACKGROUND)
    return image, ImageDraw.Draw(image)


def save(image: Image.Image, output: Path, name: str) -> None:
    directory = output / name
    directory.mkdir(parents=True, exist_ok=True)
    image.save(directory / "figure.png", optimize=True)


def draw_bar_chart(
    rows: list[tuple[str, int]],
    *,
    denominator: int | None = None,
    colors: list[str] | None = None,
    label_width: int = 430,
    height: int | None = None,
) -> Image.Image:
    row_height = 92
    top = 45
    bottom = 45
    height = height or top + bottom + row_height * len(rows)
    image, draw = canvas(height)
    bar_left = label_width
    bar_right = WIDTH - (260 if denominator else 155)
    bar_width = bar_right - bar_left
    maximum = denominator or max(value for _, value in rows) or 1
    for index, ((label, value), color) in enumerate(
        zip(rows, colors or [TEAL] * len(rows), strict=True)
    ):
        y = top + index * row_height
        draw.text((35, y + 13), label, fill=INK, font=LABEL)
        draw.rounded_rectangle((bar_left, y + 18, bar_right, y + 56), radius=19, fill=PALE)
        filled = max(3, int(bar_width * value / maximum))
        draw.rounded_rectangle((bar_left, y + 18, bar_left + filled, y + 56), radius=19, fill=color)
        suffix = f"  {value / denominator:.1%}" if denominator else ""
        draw.text((bar_right + 25, y + 11), f"{value:,}{suffix}", fill=INK, font=LABEL_BOLD)
    return image


def figure_overview(artifacts: list[dict], config: dict) -> Image.Image:
    category_counts = Counter(
        category for item in artifacts for category in item.get("categories", [])
    )
    tiles = [
        ("Observed artifacts", len(artifacts), INK),
        ("Benchmark-tagged", category_counts["benchmark"], TEAL),
        ("Agentic-evaluation", category_counts["agentic"], CORAL),
        ("Operational tags", len(config["taxonomy"]), GOLD),
    ]
    source_counts = Counter(item["source"] for item in artifacts)
    image, draw = canvas(510)
    margin = 35
    gap = 20
    tile_width = (WIDTH - margin * 2 - gap * 3) // 4
    for index, (label, value, color) in enumerate(tiles):
        left = margin + index * (tile_width + gap)
        draw.rounded_rectangle((left, 35, left + tile_width, 250), radius=24, fill="#FFFFFF")
        draw.rectangle((left, 35, left + 9, 250), fill=color)
        draw.text((left + 28, 75), f"{value:,}", fill=color, font=TILE_VALUE)
        draw.text((left + 28, 170), label, fill=INK, font=SMALL)

    bar_left, bar_top, bar_right, bar_bottom = 35, 325, WIDTH - 35, 385
    cursor = bar_left
    for source, count in source_counts.most_common():
        segment = round((bar_right - bar_left) * count / len(artifacts))
        draw.rectangle(
            (cursor, bar_top, cursor + segment, bar_bottom),
            fill=SOURCE_COLORS.get(source, SLATE),
        )
        cursor += segment
    legend_x = 35
    for source, count in source_counts.most_common():
        color = SOURCE_COLORS.get(source, SLATE)
        draw.rounded_rectangle((legend_x, 430, legend_x + 22, 452), radius=5, fill=color)
        text = f"{source}  {count:,} ({count / len(artifacts):.1%})"
        draw.text((legend_x + 34, 422), text, fill=INK, font=SMALL)
        legend_x += int(draw.textlength(text, font=SMALL)) + 90
    return image


def figure_categories(artifacts: list[dict], config: dict) -> Image.Image:
    counts = Counter(category for item in artifacts for category in item["categories"])
    rows = [
        (category.replace("_", " ").title(), counts[category]) for category in config["taxonomy"]
    ]
    rows.sort(key=lambda row: row[1], reverse=True)
    palette = {"Agentic": CORAL, "Data Quality": GOLD}
    colors = [palette.get(label, TEAL) for label, _ in rows]
    return draw_bar_chart(rows, denominator=len(artifacts), colors=colors)


def figure_agentic_sources(artifacts: list[dict]) -> Image.Image:
    agentic = [item for item in artifacts if "agentic" in item["categories"]]
    counts = Counter(item["source"] for item in agentic)
    rows = counts.most_common()
    return draw_bar_chart(
        rows,
        denominator=len(agentic),
        colors=[SOURCE_COLORS.get(source, SLATE) for source, _ in rows],
        label_width=340,
    )


def figure_agentic_themes(artifacts: list[dict]) -> Image.Image:
    agentic = [item for item in artifacts if "agentic" in item["categories"]]
    rows = []
    for label, pattern in THEME_PATTERNS.items():
        count = sum(
            bool(pattern.search(f"{item['title']} {item['summary']}".lower())) for item in agentic
        )
        rows.append((label, count))
    rows.sort(key=lambda row: row[1], reverse=True)
    return draw_bar_chart(
        rows,
        denominator=len(agentic),
        colors=[CORAL] * len(rows),
        label_width=470,
    )


def figure_connectors(latest: dict) -> Image.Image:
    display_names = {
        "github": "GitHub",
        "huggingface": "Hugging Face",
        "arxiv": "arXiv",
        "github_releases": "GitHub Releases",
        "openreview": "OpenReview",
        "semantic_scholar": "Semantic Scholar",
        "openalex": "OpenAlex",
        "brave": "Brave Search",
    }
    health = [row for row in latest["ingest_health"] if row["kind"] == "evidence"]
    health.sort(key=lambda row: row["item_count"], reverse=True)
    rows = [
        (
            display_names.get(row["source"], row["source"].replace("_", " ").title()),
            row["item_count"],
        )
        for row in health
    ]
    colors = [GREEN if row["item_count"] else GOLD if row["ok"] else RED for row in health]
    image = draw_bar_chart(rows, colors=colors, label_width=390, height=890)
    draw = ImageDraw.Draw(image)
    legend = [("Active", GREEN), ("Zero records", GOLD), ("Unavailable", RED)]
    x = 390
    for label, color in legend:
        draw.rounded_rectangle((x, 825, x + 22, 847), radius=5, fill=color)
        draw.text((x + 34, 817), label, fill=INK, font=SMALL)
        x += int(draw.textlength(label, font=SMALL)) + 100
    return image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--cutoff",
        type=date.fromisoformat,
        default=date(2026, 7, 31),
        help="last snapshot date to include (default: 2026-07-31)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/figures/ai-benchmark-landscape"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    artifacts, latest, config = load_data(repo, args.cutoff)
    figures = {
        "01_overview": figure_overview(artifacts, config),
        "02_categories": figure_categories(artifacts, config),
        "03_agentic_sources": figure_agentic_sources(artifacts),
        "04_agentic_themes": figure_agentic_themes(artifacts),
        "05_connectors": figure_connectors(latest),
    }
    for name, image in figures.items():
        save(image, output, name)
        print(output / name / "figure.png")


if __name__ == "__main__":
    main()
