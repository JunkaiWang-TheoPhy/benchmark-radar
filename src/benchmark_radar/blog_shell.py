"""Page chrome and the post record for the daily brief blog.

Blog pages are not the dashboard. The dashboard is one JavaScript application
whose views are published at their own paths by ``app_pages.py``; a brief is a
document that has to be readable with no script at all, because the whole point
of writing one per collection day is that a search engine and a reader arriving
cold can both see what changed that day. So these pages carry their own
skeleton and link the dashboard stylesheet for its design tokens rather than
reusing ``site/index.html``.

Nothing here writes files. It owns the record a brief is built into and the
markup that wraps it, so ``blog_content.py`` can turn snapshots into posts and
``blog.py`` can decide which pages exist without either of them restating the
masthead.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .feed import SITE_URL
from .site_shell import esc, json_ld

BLOG_PATH = "/blog/"
BLOG_ARCHIVE_PATH = "/blog/archive/"
BLOG_FEED_PATH = "/blog/feed.xml"


@dataclass(frozen=True)
class BlogPost:
    """One published brief, with its body already rendered.

    ``body_zh`` is None when the snapshot carries no stored translation. That
    absence is what suppresses the language toggle: a toggle that switches to a
    page identical to the one already shown is a broken control, and machine
    translating here would publish text nobody reviewed.
    """

    slug: str
    title: str
    description: str
    published: str
    updated: str
    kind: str
    tags: tuple[str, ...]
    sources: tuple[tuple[str, str, str], ...]
    body_en: str
    body_zh: str | None
    title_zh: str | None
    description_zh: str | None

    @property
    def path(self) -> str:
        return f"{BLOG_PATH}{self.slug}/"

    @property
    def canonical(self) -> str:
        return SITE_URL + self.path

    @property
    def translated(self) -> bool:
        return self.body_zh is not None


def _brand() -> str:
    # Root-relative, like the dashboard's own menubar. A canonical absolute URL
    # belongs in the SEO tags, not in a nav anchor: absolute links here eject a
    # local preview (or any non-canonical mirror) to the production domain.
    return """<a class="brand" href="/" aria-label="Benchmark Radar home">
  <span class="brand-mark" aria-hidden="true"><span></span></span>
  <strong>Benchmark Radar</strong>
</a>"""


_RSS_ICON = """<svg viewBox="0 0 24 24" aria-hidden="true">
  <circle cx="5" cy="19" r="2"></circle>
  <path d="M4 11a9 9 0 0 1 9 9"></path>
  <path d="M4 4a16 16 0 0 1 16 16"></path>
</svg>"""

_GITHUB_ICON = """<svg class="brand-icon github-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M12 2.5a9.5 9.5 0 0 0-3 18.52c.48.09.65-.21.65-.46v-1.67
    c-2.67.58-3.23-1.13-3.23-1.13-.44-1.12-1.07-1.42-1.07-1.42-.87-.6.07-.59.07-.59
    .96.07 1.47.99 1.47.99.86 1.47 2.25 1.05 2.8.8.09-.62.34-1.05.61-1.29
    -2.13-.24-4.37-1.07-4.37-4.75 0-1.05.38-1.91.99-2.58-.1-.24-.43-1.22.09-2.54
    0 0 .81-.26 2.63.98A9.16 9.16 0 0 1 12 7.96c.82 0 1.65.11 2.42.33
    1.82-1.24 2.63-.98 2.63-.98.52 1.32.19 2.3.09 2.54.61.67.99 1.53.99 2.58
    0 3.69-2.25 4.5-4.39 4.74.35.3.65.88.65 1.78v2.63c0 .25.17.55.66.46
    A9.5 9.5 0 0 0 12 2.5Z"></path>
</svg>"""

# Every dashboard route plus the blog, so a reader who landed on a brief from
# search can reach the rest of the site. The dashboard's own menubar is a
# separate list in site/index.html and stays the source of truth for it.
_NAV_LINKS: tuple[tuple[str, str, str], ...] = (
    ("today", "/", "Today"),
    ("leaderboard", "/leaderboard/", "Leaderboard"),
    ("trends", "/trends/", "Trends"),
    ("explore", "/explore/", "Explore"),
    ("blog", BLOG_PATH, "Blog"),
)


def header(*, translated: bool) -> str:
    toggle = (
        '<button type="button" class="repo-badge" id="lang-toggle" aria-pressed="false" '
        'aria-label="Switch to Chinese (中文)" data-next-language="zh">'
        '<span class="repo-badge-glyph" id="lang-toggle-label">中</span></button>'
        if translated
        else ""
    )
    return f"""<header class="masthead">
{_brand()}
<div class="masthead-end" aria-label="Site utilities">
  <a class="repo-badge feed-badge" href="{BLOG_FEED_PATH}"
     aria-label="Subscribe to the daily brief via RSS">{_RSS_ICON}
    <span class="repo-badge-label">RSS</span></a>
  {toggle}
  <a class="repo-badge" href="https://github.com/ktwu01/benchmark-radar"
     aria-label="Open Benchmark Radar on GitHub">{_GITHUB_ICON}
    <span class="repo-badge-label">GitHub</span></a>
</div>
</header>"""


def navigation(active: str) -> str:
    # Root-relative for the same reason as the brand link above: these stay on
    # whatever host serves the page. Sitemap locs, canonical, and og:url keep
    # the absolute SITE_URL because those are semantically absolute by spec.
    rendered = []
    for key, path, label in _NAV_LINKS:
        current = ' class="nav-active" aria-current="page"' if key == active else ""
        rendered.append(f'<a href="{path}"{current}>{label}</a>')
    return '<nav class="view-nav" aria-label="Site sections">' + "".join(rendered) + "</nav>"


def render_page(
    *,
    title: str,
    description: str,
    canonical: str,
    body: str,
    schemas: Iterable[dict[str, Any]] = (),
    og_type: str = "website",
    translated: bool = False,
) -> str:
    """Wrap one rendered body in the blog skeleton."""
    schema_blocks = "".join(
        f'<script type="application/ld+json">{json_ld(payload)}</script>' for payload in schemas
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<title>{esc(title)}</title>
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="{esc(og_type)}">
<meta property="og:site_name" content="Benchmark Radar">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{SITE_URL}/assets/og-card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{SITE_URL}/assets/og-card.png">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Benchmark Radar daily brief"
      href="{BLOG_FEED_PATH}">
<link rel="stylesheet" href="/assets/styles.css">
<link rel="stylesheet" href="/assets/blog.css">
{schema_blocks}
<script src="/assets/blog.js" defer></script>
</head>
<body class="blog-page">
<a class="skip-link" href="#main-content">Skip to content</a>
{header(translated=translated)}
{navigation("blog")}
<main id="main-content" tabindex="-1"><div class="blog-view">{body}</div></main>
<footer class="blog-footer">
  <strong>Benchmark Radar</strong>
  <span>Evidence first. Every claim should lead back to its source.</span>
</footer>
</body>
</html>
"""
