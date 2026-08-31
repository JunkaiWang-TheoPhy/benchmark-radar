"""Generate sitemap.xml for the published site (issues #236 and #424).

Each major search intent has a path-based static landing page. The dashboard's
query-string views remain interactive application states, but are not sitemap
entries: their canonical URLs consolidate onto the corresponding static page.
Filter permutations are deliberately left out.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .feed import SITE_URL

SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"

# One entry per dashboard view, in nav order. logos.html is excluded on
# purpose: it is a maintainer QA page carrying <meta name="robots"
# content="noindex">, so listing it would contradict the page itself.
INDEXABLE_VIEWS: tuple[tuple[str, str], ...] = (
    ("Today", "/"),
    ("Leaderboard", "/leaderboard/"),
    ("Trends", "/trends/"),
    ("Explore", "/explore/"),
)

BENCHMARK_DIRECTORY_PATH = "/benchmarks/"

ET.register_namespace("sm", SITEMAP_NAMESPACE)


def _lastmod_date(snapshots: list[dict[str, Any]]) -> str | None:
    """Date of the newest snapshot, or None when there is no history yet.

    Derived from the snapshots rather than the clock so two rebuilds over the
    same history produce byte-identical output; feed.xml's lastBuildDate makes
    the same choice.
    """
    if not snapshots:
        return None
    generated = max(
        datetime.fromisoformat(str(snapshot["generated_at"]).replace("Z", "+00:00"))
        for snapshot in snapshots
    )
    return generated.astimezone(UTC).date().isoformat()


def _q(tag: str) -> str:
    # Tags are written with the qualified name; register_namespace above makes
    # the serializer emit the readable sm: prefix instead of ns0.
    return f"{{{SITEMAP_NAMESPACE}}}{tag}"


def sitemap_tree(
    snapshots: list[dict[str, Any]],
    benchmark_slugs: Sequence[str] = (),
    extra_entries: Sequence[tuple[str, str | None]] = (),
) -> ET.ElementTree:
    """Build one stable urlset covering views, benchmarks, and published articles."""
    root = ET.Element(_q("urlset"))
    lastmod = _lastmod_date(snapshots)
    entries = [(path, lastmod) for _, path in INDEXABLE_VIEWS]
    entries.append((BENCHMARK_DIRECTORY_PATH, lastmod))
    entries.extend((f"/benchmarks/{slug}/", lastmod) for slug in benchmark_slugs)
    entries.extend(extra_entries)
    seen: set[str] = set()
    for path, entry_lastmod in entries:
        if path in seen:
            continue
        seen.add(path)
        url = ET.SubElement(root, _q("url"))
        ET.SubElement(url, _q("loc")).text = SITE_URL + path
        if entry_lastmod:
            ET.SubElement(url, _q("lastmod")).text = entry_lastmod
    return ET.ElementTree(root)


def write_sitemap(
    snapshots: list[dict[str, Any]],
    output: Path,
    benchmark_slugs: Sequence[str] = (),
    extra_entries: Sequence[tuple[str, str | None]] = (),
) -> Path:
    """Write a deterministic UTF-8 sitemap beside the published data."""
    output.parent.mkdir(parents=True, exist_ok=True)
    tree = sitemap_tree(snapshots, benchmark_slugs, extra_entries)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return output
