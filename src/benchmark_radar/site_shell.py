"""Shared Benchmark Radar shell for static, server-delivered pages."""

from __future__ import annotations

import html
import json
from collections.abc import Iterable
from typing import Any

from .feed import SITE_URL


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def json_ld(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


def breadcrumb_schema(*items: tuple[str, str], canonical: str) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "@id": f"{canonical}#breadcrumb",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": url,
            }
            for position, (name, url) in enumerate(items, start=1)
        ],
    }


def webpage_schema(
    *, title: str, description: str, canonical: str, languages: Iterable[str] = ("en",)
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical,
        "name": title,
        "url": canonical,
        "description": description,
        "inLanguage": list(languages),
        "isPartOf": {"@id": f"{SITE_URL}/#website"},
    }


def _brand() -> str:
    return f"""<a class="brand" href="{SITE_URL}/" aria-label="Benchmark Radar home">
  <span class="brand-mark" aria-hidden="true"><span></span></span>
  <strong>Benchmark Radar</strong>
</a>"""


def _rss_icon() -> str:
    return """<svg viewBox="0 0 24 24" aria-hidden="true">
  <circle cx="5" cy="19" r="2"></circle>
  <path d="M4 11a9 9 0 0 1 9 9"></path>
  <path d="M4 4a16 16 0 0 1 16 16"></path>
</svg>"""


def _github_icon() -> str:
    return """<svg class="brand-icon github-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M12 2.5a9.5 9.5 0 0 0-3 18.52c.48.09.65-.21.65-.46v-1.67
    c-2.67.58-3.23-1.13-3.23-1.13-.44-1.12-1.07-1.42-1.07-1.42-.87-.6.07-.59.07-.59
    .96.07 1.47.99 1.47.99.86 1.47 2.25 1.05 2.8.8.09-.62.34-1.05.61-1.29
    -2.13-.24-4.37-1.07-4.37-4.75 0-1.05.38-1.91.99-2.58-.1-.24-.43-1.22.09-2.54
    0 0 .81-.26 2.63.98A9.16 9.16 0 0 1 12 7.96c.82 0 1.65.11 2.42.33
    1.82-1.24 2.63-.98 2.63-.98.52 1.32.19 2.3.09 2.54.61.67.99 1.53.99 2.58
    0 3.69-2.25 4.5-4.39 4.74.35.3.65.88.65 1.78v2.63c0 .25.17.55.66.46
    A9.5 9.5 0 0 0 12 2.5Z"></path>
</svg>"""


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
  <a class="repo-badge feed-badge" href="/feed.xml"
     aria-label="Subscribe to Benchmark Radar via RSS">{_rss_icon()}
    <span class="repo-badge-label">RSS</span></a>
  {toggle}
  <a class="repo-badge" href="https://github.com/ktwu01/benchmark-radar"
     aria-label="Open Benchmark Radar on GitHub">{_github_icon()}
    <span class="repo-badge-label">GitHub</span></a>
</div>
</header>"""


def navigation(active: str) -> str:
    links = (
        ("today", "/", "Today"),
        ("leaderboard", "/leaderboard/", "Leaderboard"),
        ("trends", "/trends/", "Trends"),
        ("explore", "/explore/", "Explore"),
        ("blog", "/blog/", "Blog"),
    )
    rendered = []
    for key, path, label in links:
        current = ' class="nav-active" aria-current="page"' if key == active else ""
        rendered.append(f'<a href="{SITE_URL}{path}"{current}>{label}</a>')
    return '<nav class="view-nav" aria-label="Site sections">' + "".join(rendered) + "</nav>"


def render_page(
    *,
    title: str,
    description: str,
    canonical: str,
    active: str,
    body: str,
    schemas: Iterable[dict[str, Any]] = (),
    og_type: str = "website",
    translated: bool = False,
) -> str:
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
<link rel="alternate" type="application/rss+xml" title="Benchmark Radar RSS"
      href="/feed.xml">
<link rel="stylesheet" href="/assets/styles.css">
<link rel="stylesheet" href="/assets/content.css">
{schema_blocks}
<script src="/assets/content.js" defer></script>
</head>
<body class="content-page">
<a class="skip-link" href="#main-content">Skip to content</a>
{header(translated=translated)}
{navigation(active)}
<main id="main-content" tabindex="-1"><div class="content-view">{body}</div></main>
<footer class="content-footer">
  <strong>Benchmark Radar</strong>
  <span>Evidence first. Every claim should lead back to its source.</span>
</footer>
</body>
</html>
"""
