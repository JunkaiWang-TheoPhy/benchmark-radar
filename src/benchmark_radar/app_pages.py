"""Serve the dashboard itself at ``/leaderboard/``, ``/trends/`` and ``/explore/``.

Every dashboard view used to live at a query string, and a query string is not a
page: crawlers that do not run JavaScript saw only the homepage, and the four
views competed with each other for one ranking signal. Giving each view a path
fixed that, but the first attempt built a second, thinner site at those paths,
so a reader arriving from search got a ten-row table where the dashboard has a
ranked chart, a score frontier, and a search over the whole catalog. Worse, both
documents claimed the same canonical, so the thin one won.

So these pages are the dashboard. ``site/index.html`` is the only design, and
this module writes copies of it that differ in four ways:

* the head block between the ``br:head-seo`` markers carries the view's own
  title, summary, social card text, and canonical URL;
* a ``WebPage`` and ``BreadcrumbList`` block lands at the ``br:page-jsonld``
  marker, so a result can show where the page sits;
* the named view starts visible and Today starts hidden;
* the view's own containers arrive holding real rows.

Every substitution asserts its anchor and raises when it is missing, so an edit
to ``site/index.html`` that moves an anchor fails the build instead of quietly
publishing a page that describes the homepage.

The seeded rows go into the containers ``assets/app.js`` renders into, because
that script calls ``replaceChildren`` and overwrites them on first paint. That
is the point: a crawler and a reader on a slow connection get the ranking, and
nobody sees it twice. It also sets the rule these seeds follow: a seed must be
what the renderer would produce from the same data, never a summary written for
crawlers. A page that shows a visitor something other than what it shows a
crawler is lying to one of them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .app_seeds import view_seeds
from .feed import SITE_URL
from .site_shell import breadcrumb_schema, esc, json_ld, webpage_schema

# Published in this order. "map" is the view key; its path is /explore/.
APP_VIEWS: tuple[str, ...] = ("leaderboard", "trends", "map")

HEAD_SEO_OPEN = "<!-- br:head-seo -->"
HEAD_SEO_CLOSE = "<!-- /br:head-seo -->"
PAGE_JSONLD = "<!-- br:page-jsonld -->"

# Breadcrumb names, matching the navigation labels a reader clicked to get here.
VIEW_LABELS = {
    "leaderboard": "Leaderboard",
    "trends": "Trends",
    "map": "Explore",
}

_VIEW_SEO_BLOCK = re.compile(r"const VIEW_SEO = \{\n(.*?)\n\};", re.DOTALL)
_VIEW_ENTRY = re.compile(r"^  (\w+): \{\n(.*?)^  \},$", re.DOTALL | re.MULTILINE)
_SEO_FIELD = re.compile(r'^\s*(\w+):\s*\n?\s*"((?:[^"\\]|\\.)*)",?$', re.MULTILINE)
_COLOR_TABLE = re.compile(r"const CATEGORY_COLORS = \{(.*?)\};", re.DOTALL)
_COLOR_ENTRY = re.compile(r'(\w+):\s*"(#[0-9a-fA-F]+)"')
_FALLBACK_COLORS = re.compile(r"const FALLBACK_COLORS = \[(.*?)\];", re.DOTALL)


class AppPageError(RuntimeError):
    """An anchor this module substitutes into no longer exists in the source."""


def _unescape_js(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def load_view_seo(app_js: Path) -> dict[str, dict[str, str]]:
    """Read each view's title, summary and canonical path out of assets/app.js.

    Parsed rather than restated in Python. The browser needs these strings at
    runtime to rewrite the head when a reader switches view without a page load,
    so app.js has to own them. A second copy here would drift silently, and the
    symptom would be a page whose crawled title and shared title disagree.
    """
    source = app_js.read_text(encoding="utf-8")
    block = _VIEW_SEO_BLOCK.search(source)
    if not block:
        raise AppPageError(f"VIEW_SEO block not found in {app_js}")
    views: dict[str, dict[str, str]] = {}
    for view, body in _VIEW_ENTRY.findall(block.group(1)):
        fields = {name: _unescape_js(value) for name, value in _SEO_FIELD.findall(body)}
        missing = sorted({"title", "description", "canonical"} - fields.keys())
        if missing:
            raise AppPageError(f"VIEW_SEO.{view} is missing {missing}")
        views[view] = fields
    absent = sorted(set(APP_VIEWS) - views.keys())
    if absent:
        raise AppPageError(f"VIEW_SEO is missing {absent}")
    return views


def load_category_colors(glyphs_js: Path) -> tuple[dict[str, str], list[str]]:
    """Read the domain swatch palette out of assets/glyphs.js, for the same reason."""
    source = glyphs_js.read_text(encoding="utf-8")
    table = _COLOR_TABLE.search(source)
    fallback = _FALLBACK_COLORS.search(source)
    if not table or not fallback:
        raise AppPageError(f"CATEGORY_COLORS or FALLBACK_COLORS not found in {glyphs_js}")
    colors = dict(_COLOR_ENTRY.findall(table.group(1)))
    fallbacks = re.findall(r'"(#[0-9a-fA-F]+)"', fallback.group(1))
    if not colors or not fallbacks:
        raise AppPageError(f"category palette in {glyphs_js} parsed empty")
    return colors, fallbacks


def _replace_once(document: str, old: str, new: str, *, what: str) -> str:
    found = document.count(old)
    if found != 1:
        raise AppPageError(f"expected exactly one {what} in site/index.html, found {found}")
    return document.replace(old, new, 1)


def _replace_between(document: str, open_marker: str, close_marker: str, body: str) -> str:
    start = document.find(open_marker)
    end = document.find(close_marker, start + 1)
    if start == -1 or end == -1:
        raise AppPageError(f"markers {open_marker} .. {close_marker} not found in site/index.html")
    return f"{document[: start + len(open_marker)]}\n{body}    {document[end:]}"


def _head_seo(seo: dict[str, str]) -> str:
    title = esc(seo["title"])
    description = esc(seo["description"])
    canonical = f"{SITE_URL}{seo['canonical']}"
    return f"""    <meta name="description" content="{description}">
    <title>{title}</title>
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{canonical}">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <link rel="canonical" href="{canonical}">
"""


def _page_jsonld(view: str, seo: dict[str, str]) -> str:
    canonical = f"{SITE_URL}{seo['canonical']}"
    blocks = (
        webpage_schema(
            title=seo["title"],
            description=seo["description"],
            canonical=canonical,
            languages=("en", "zh-Hans"),
        ),
        breadcrumb_schema(
            ("Benchmark Radar", f"{SITE_URL}/"),
            (VIEW_LABELS[view], canonical),
            canonical=canonical,
        ),
    )
    return "\n".join(
        f'    <script type="application/ld+json">{json_ld(block)}</script>' for block in blocks
    )


def _open_on(document: str, view: str) -> str:
    """Start on the named view instead of Today, leaving the other sections alone."""
    document = _replace_once(
        document,
        '<section class="view" id="today-view" aria-label="Today">',
        '<section class="view" id="today-view" aria-label="Today" hidden>',
        what="today view section",
    )
    opening = re.compile(rf'<section class="view" id="{view}-view"([^>]*) hidden>')
    if not opening.search(document):
        raise AppPageError(f"{view}-view section is not present and hidden in site/index.html")
    return opening.sub(rf'<section class="view" id="{view}-view"\1>', document, count=1)


def render_app_page(
    template: str,
    view: str,
    seo: dict[str, str],
    seeds: dict[str, str],
) -> str:
    """Build one published page out of the dashboard document."""
    document = _replace_between(template, HEAD_SEO_OPEN, HEAD_SEO_CLOSE, _head_seo(seo))
    document = _replace_once(
        document,
        PAGE_JSONLD,
        f"{PAGE_JSONLD}\n{_page_jsonld(view, seo)}",
        what="page JSON-LD marker",
    )
    document = _open_on(document, view)
    for anchor, replacement in seeds.items():
        document = _replace_once(document, anchor, replacement, what=f"{view} seed container")
    return document


def write_app_pages(
    dashboard: dict[str, Any],
    site_dir: Path,
) -> dict[str, Any]:
    """Publish the dashboard at each view's own path.

    A view with nothing to show is not published. ``/leaderboard/`` on a build
    without the curated registry would carry the leaderboard's title and
    canonical over whatever the runtime falls back to showing, and a URL that
    describes a page nobody can see is worse than a URL that does not exist yet.
    The returned paths are what the sitemap lists, so the two cannot disagree.
    """
    template = (site_dir / "index.html").read_text(encoding="utf-8")
    seo = load_view_seo(site_dir / "assets" / "app.js")
    palette = load_category_colors(site_dir / "assets" / "glyphs.js")
    seeds = view_seeds(dashboard, palette)
    written: list[Path] = []
    published: list[str] = []
    for view in APP_VIEWS:
        path = seo[view]["canonical"]
        output = site_dir / path.strip("/") / "index.html"
        if not seeds[view]:
            # A view that lost its data has to lose its page too. Leaving the
            # last build's copy on disk would keep serving a URL this build
            # dropped from the sitemap, under a canonical still claiming it.
            output.unlink(missing_ok=True)
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name("index.html.tmp")
        staging.write_text(
            render_app_page(template, view, seo[view], seeds[view]), encoding="utf-8"
        )
        staging.replace(output)
        written.append(output)
        published.append(path)
    return {"page_count": len(written), "outputs": written, "paths": published}
