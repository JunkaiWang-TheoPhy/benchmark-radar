"""Static per-benchmark pages: one crawlable URL per benchmark (issue #424).

The dashboard is one HTML document whose four views share a single path, so a
catalog of 1,100+ benchmarks exposes four indexable URLs to a search engine.
Each per-benchmark shard already answers the reader's questions about one
benchmark, but only as JSON consumed by JavaScript. This module renders that
same evidence as plain HTML, one page per slug, readable with JavaScript
disabled. It turns the catalog's data advantage into a search advantage: every
benchmark gets its own title, description, canonical URL, and structured data,
and the sitemap publishes all of them.

The pages derive from the shards exactly as the shards derive from the crawl
CSVs, so they are generated and gitignored, never committed. The build calls
this right after `normalize-external` writes the shards, and the sitemap build
scans the same shard directory for the URLs to list. A page never invents
values: missing fields are omitted from the HTML, never shown as a zero, an
empty string, or the literal word for a missing value. Scores stay partitioned
by the source that reported them, the same rule the shards enforce in JSON.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .feed import SITE_URL
from .site_shell import breadcrumb_schema, esc, render_page, webpage_schema

DEFAULT_SHARD_DIR = Path("site/data/benchmarks")
DEFAULT_PAGES_DIR = Path("site/benchmarks")

_DESCRIPTION_LIMIT = 155

_DIR_DESCRIPTION = (
    "Every benchmark in the Benchmark Radar catalog, each with its own page "
    "covering what it tests, who published it, and which scores are on record."
)


def _esc(value: str) -> str:
    return esc(value)


def _text(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _description(record: dict[str, Any]) -> str:
    """A human sentence for the page, never empty, at most one line.

    The shard's own description wins when it exists. Otherwise the fallback is
    assembled from fields the record actually carries, so two benchmarks with
    nothing but a name do not share identical copy.
    """
    raw = record.get("description") or {}
    own = raw.get("en")
    if isinstance(own, str) and own.strip():
        text = own.strip().replace("\n", " ")
    else:
        name = _text(record, "name") or "This benchmark"
        parts = [name]
        categories = record.get("categories") or []
        if categories:
            parts.append(f"covers {', '.join(str(c) for c in categories)}")
        source = _text(record, "source")
        if source:
            parts.append(f"with evidence collected daily by Benchmark Radar from {source}")
        else:
            parts.append("with evidence collected daily by Benchmark Radar")
        text = ", ".join(parts)
    if len(text) <= _DESCRIPTION_LIMIT:
        return text
    return text[:_DESCRIPTION_LIMIT].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def _canonical(slug: str) -> str:
    return f"{SITE_URL}/benchmarks/{slug}/"


def _facts(record: dict[str, Any], scores_by_source: dict[str, Any]) -> list[tuple[str, str]]:
    facts: list[tuple[str, str]] = []
    publisher = _text(record, "publisher")
    if publisher:
        facts.append(("Publisher", publisher))
    released = _text(record, "released")
    if released:
        facts.append(("Released", released))
    modality = _text(record, "modality")
    if modality:
        facts.append(("Modality", modality))
    categories = record.get("categories") or []
    if categories:
        facts.append(("Categories", ", ".join(str(c) for c in categories)))
    openness = record.get("openness") or {}
    status = openness.get("status")
    if isinstance(status, str) and status:
        facts.append(("Openness", status))
    source = _text(record, "source")
    if source:
        facts.append(("Source", source))
    score_count = sum(
        len(source_data.get("rows") or []) for source_data in scores_by_source.values()
    )
    facts.append(("Reported scores", str(score_count)))
    return facts


def _cell(*candidates: Any) -> str:
    for candidate in candidates:
        if candidate is not None and candidate != "":
            return _esc(str(candidate))
    return "—"


def _scores_sections(scores_by_source: dict[str, Any]) -> str:
    sections: list[str] = []
    for source in sorted(scores_by_source):
        rows = sorted(
            (scores_by_source[source].get("rows") or []),
            key=lambda row: (
                str(row.get("model_name") or "").lower(),
                str(row.get("reported_date") or ""),
            ),
        )
        body = "".join(
            "<tr>"
            f"<td>{_cell(row.get('model_name'), row.get('model_id'))}</td>"
            f"<td>{_cell(row.get('organization'))}</td>"
            f"<td>{_cell(row.get('raw_value'), row.get('value'))}</td>"
            f"<td>{_cell(row.get('reported_date'))}</td>"
            f'<td><a href="{_esc(str(row.get("source_url") or SITE_URL))}">evidence</a></td>'
            "</tr>"
            for row in rows
        )
        if not body:
            continue
        sections.append(
            '<section class="content-section">'
            f"<h2>{_esc(source)}</h2>"
            '<div class="table-wrap"><table class="content-table"><thead>'
            "<tr><th>Model</th><th>Organization</th>"
            "<th>Reported value</th><th>Reported</th><th>Evidence</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div></section>"
        )
    return "".join(sections)


def _page_html(slug: str, shard: dict[str, Any]) -> str:
    record = shard.get("record") or {}
    scores_by_source = shard.get("scores_by_source") or {}
    name = _text(record, "name") or slug
    description = _description(record)
    canonical = _canonical(slug)
    title = f"{name} · Benchmark Radar"
    facts = "".join(
        f"<dt>{_esc(label)}</dt><dd>{_esc(value)}</dd>"
        for label, value in _facts(record, scores_by_source)
    )
    scores = _scores_sections(scores_by_source)
    if scores:
        scores_html = (
            f'<section class="content-section"><h2>Reported scores</h2>{scores}</section>'
            '<p class="content-caveat">Scores are partitioned by the source that reported '
            "them and are never merged into a single cross-source ranking, because "
            "the sources measure different things and say so.</p>"
        )
    else:
        scores_html = (
            '<p class="content-caveat">No reported scores are on record for this benchmark yet.</p>'
        )
    interactive = f"{SITE_URL}/leaderboard/?lfrontier={slug}"
    body = f"""<header class="content-hero">
  <p class="eyebrow">Benchmark</p>
  <h1>{_esc(name)}</h1>
  <p class="content-lede">{_esc(description)}</p>
  <div class="content-actions">
    <a class="primary-link" href="{interactive}">Open the interactive view</a>
    <a class="secondary-link" href="{SITE_URL}/benchmarks/">Benchmark directory</a>
  </div>
</header>
<section class="content-panel"><dl class="content-facts">{facts}</dl></section>
{scores_html}"""
    page_schema = webpage_schema(
        title=title, description=description, canonical=canonical, languages=("en", "zh-Hans")
    )
    page_schema["about"] = {"@type": "Thing", "name": name, "description": description}
    return render_page(
        title=title,
        description=description,
        canonical=canonical,
        active="leaderboard",
        body=body,
        schemas=(
            page_schema,
            breadcrumb_schema(
                ("Benchmark Radar", f"{SITE_URL}/"),
                ("Benchmark directory", f"{SITE_URL}/benchmarks/"),
                (name, canonical),
                canonical=canonical,
            ),
        ),
    )


def _directory_html(entries: list[tuple[str, str]]) -> str:
    """Directory page: title, canonical, schema, and the full listing."""
    canonical = f"{SITE_URL}/benchmarks/"
    links = "".join(f'<li><a href="{_esc(url)}">{_esc(name)}</a></li>' for name, url in entries)
    count = f"{len(entries)} benchmarks"
    body = f"""<header class="content-hero">
  <p class="eyebrow">Benchmark catalog</p>
  <h1>Benchmark directory</h1>
  <p class="content-lede">Every benchmark in the catalog, each with its own page covering
    what it tests, who published it, and which scores are on record. The
    interactive dashboard is <a href="{SITE_URL}/leaderboard/">here</a>.</p>
  <p class="content-meta">{count}</p>
</header>
<section class="content-panel"><ul class="content-directory">{links}</ul></section>"""
    return render_page(
        title="Benchmark directory · Benchmark Radar",
        description=_DIR_DESCRIPTION,
        canonical=canonical,
        active="leaderboard",
        body=body,
        schemas=(
            webpage_schema(
                title="Benchmark directory · Benchmark Radar",
                description=_DIR_DESCRIPTION,
                canonical=canonical,
                languages=("en", "zh-Hans"),
            ),
            breadcrumb_schema(
                ("Benchmark Radar", f"{SITE_URL}/"),
                ("Benchmark directory", canonical),
                canonical=canonical,
            ),
        ),
    )


def _load_shard(path: Path) -> tuple[str, dict[str, Any]]:
    shard = json.loads(path.read_text(encoding="utf-8"))
    record = shard.get("record") or {}
    slug = record.get("slug")
    if (
        not isinstance(slug, str)
        or not slug
        or slug in {".", ".."}
        or any(ch in slug for ch in "/\\")
    ):
        raise ValueError(f"unsafe slug in {path.name}")
    return slug, shard


def benchmark_slugs(shard_dir: Path) -> list[str]:
    """Stable sorted slugs of every shard, for the sitemap."""
    if not shard_dir.is_dir():
        return []
    return sorted(path.stem for path in shard_dir.glob("*.json"))


def benchmark_page_urls(shard_dir: Path) -> list[str]:
    """Canonical benchmark page URLs in stable slug order."""
    return [_canonical(slug) for slug in benchmark_slugs(shard_dir)]


def write_benchmark_pages(
    shard_dir: Path = DEFAULT_SHARD_DIR,
    output_dir: Path = DEFAULT_PAGES_DIR,
) -> dict[str, Any]:
    """Render one static page per shard plus the directory page, atomically.

    Fails loudly when the shard directory is missing or empty: an empty build
    must never silently wipe the published benchmark pages.
    """
    if not shard_dir.is_dir():
        raise FileNotFoundError(
            f"{shard_dir} holds no benchmark shards; run `benchmark-radar normalize-external` first"
        )
    shard_paths = sorted(shard_dir.glob("*.json"))
    if not shard_paths:
        raise ValueError(f"{shard_dir} holds no benchmark shards; refusing to write empty pages")

    staging = output_dir.with_name(output_dir.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    entries: list[tuple[str, str]] = []
    for path in shard_paths:
        slug, shard = _load_shard(path)
        page_dir = staging / slug
        page_dir.mkdir(parents=True)
        (page_dir / "index.html").write_text(_page_html(slug, shard), encoding="utf-8")
        name = _text(shard.get("record") or {}, "name") or slug
        entries.append((name, _canonical(slug)))

    entries.sort(key=lambda item: (item[0].lower(), item[1]))
    (staging / "index.html").write_text(_directory_html(entries), encoding="utf-8")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    staging.rename(output_dir)
    return {"page_count": len(shard_paths), "output_dir": output_dir}
