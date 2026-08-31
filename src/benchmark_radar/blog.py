"""Build the evidence blog from validated snapshots and reviewed Markdown."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from markdown_it import MarkdownIt

from .feed import SITE_URL
from .site_shell import breadcrumb_schema, esc, render_page, webpage_schema

DEFAULT_BLOG_SOURCE_DIR = Path("content/blog")
BLOG_PATH = "/blog/"
BLOG_ARCHIVE_PATH = "/blog/archive/"
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_DATE_SLUG = re.compile(r"\d{4}-\d{2}-\d{2}")
_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")
_LATEST_POST_LIMIT = 30


class BlogSourceError(ValueError):
    """A reviewed blog source cannot be published safely."""


@dataclass(frozen=True)
class BlogPost:
    slug: str
    title: str
    description: str
    published: str
    updated: str
    author: str
    tags: tuple[str, ...]
    sources: tuple[tuple[str, str], ...]
    body_en: str
    body_zh: str | None
    title_zh: str | None
    description_zh: str | None
    kind: str
    featured: bool = False

    @property
    def path(self) -> str:
        return f"{BLOG_PATH}{self.slug}/"

    @property
    def canonical(self) -> str:
        return SITE_URL + self.path

    def feed_entry(self) -> dict[str, str]:
        return {
            "title": self.title,
            "link": self.canonical,
            "published": self.published,
            "updated": self.updated,
            "description": self.description,
        }


def _plain_date(value: Any, *, field: str, source: Path) -> str:
    if isinstance(value, datetime):
        rendered = value.date().isoformat()
    elif isinstance(value, date):
        rendered = value.isoformat()
    else:
        rendered = str(value or "").strip()
    try:
        date.fromisoformat(rendered)
    except ValueError as error:
        raise BlogSourceError(f"{source}: {field} must be an ISO date") from error
    return rendered


def _required_text(metadata: dict[str, Any], field: str, source: Path) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BlogSourceError(f"{source}: {field} must be a non-empty string")
    return value.strip()


def _safe_url(value: Any, *, source: Path | None = None) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        location = f"{source}: " if source else ""
        raise BlogSourceError(f"{location}source URLs must use http or https")
    return url


def _optional_safe_url(value: Any) -> str | None:
    try:
        return _safe_url(value)
    except BlogSourceError:
        return None


def _front_matter(path: Path) -> tuple[dict[str, Any], str]:
    source = path.read_text(encoding="utf-8")
    if not source.startswith("---\n"):
        raise BlogSourceError(f"{path}: missing YAML front matter")
    marker = source.find("\n---\n", 4)
    if marker < 0:
        raise BlogSourceError(f"{path}: front matter is not closed")
    payload = yaml.safe_load(source[4:marker])
    if not isinstance(payload, dict):
        raise BlogSourceError(f"{path}: front matter must be an object")
    body = source[marker + 5 :].strip()
    if not body:
        raise BlogSourceError(f"{path}: article body is empty")
    return payload, body


def load_manual_posts(source_dir: Path = DEFAULT_BLOG_SOURCE_DIR) -> list[BlogPost]:
    """Load reviewed English Markdown and its optional Chinese companion."""
    if not source_dir.exists():
        return []
    posts: list[BlogPost] = []
    seen: set[str] = set()
    for path in sorted(source_dir.glob("*.md")):
        if path.name == "README.md" or path.name.endswith(".zh.md"):
            continue
        slug = path.stem
        if not _SLUG.fullmatch(slug) or _DATE_SLUG.fullmatch(slug):
            raise BlogSourceError(
                f"{path}: filename must be a lowercase hyphenated slug and cannot be a date"
            )
        if slug in seen:
            raise BlogSourceError(f"{path}: duplicate blog slug {slug!r}")
        seen.add(slug)
        metadata, markdown = _front_matter(path)
        if "draft" not in metadata or not isinstance(metadata["draft"], bool):
            raise BlogSourceError(f"{path}: draft must be an explicit boolean")
        tags = metadata.get("tags")
        if (
            not isinstance(tags, list)
            or not tags
            or not all(isinstance(tag, str) and tag.strip() for tag in tags)
        ):
            raise BlogSourceError(f"{path}: tags must be a non-empty string array")
        raw_sources = metadata.get("sources")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise BlogSourceError(f"{path}: sources must contain at least one citation")
        sources: list[tuple[str, str]] = []
        for citation in raw_sources:
            if not isinstance(citation, dict):
                raise BlogSourceError(f"{path}: each source must contain title and url")
            sources.append(
                (
                    _required_text(citation, "title", path),
                    _safe_url(citation.get("url"), source=path),
                )
            )
        published = _plain_date(metadata.get("published"), field="published", source=path)
        updated = _plain_date(metadata.get("updated", published), field="updated", source=path)
        zh_path = path.with_name(f"{slug}.zh.md")
        body_zh = None
        title_zh = None
        description_zh = None
        if zh_path.exists():
            zh_markdown = zh_path.read_text(encoding="utf-8").strip()
            if not zh_markdown:
                raise BlogSourceError(f"{zh_path}: translated article body is empty")
            title_zh = _required_text(metadata, "title_zh", path)
            description_zh = _required_text(metadata, "description_zh", path)
            body_zh = _MARKDOWN.render(zh_markdown)
        post = BlogPost(
            slug=slug,
            title=_required_text(metadata, "title", path),
            description=_required_text(metadata, "description", path),
            published=published,
            updated=updated,
            author=_required_text(metadata, "author", path),
            tags=tuple(str(tag).strip() for tag in tags if str(tag).strip()),
            sources=tuple(sources),
            body_en=_MARKDOWN.render(markdown),
            body_zh=body_zh,
            title_zh=title_zh,
            description_zh=description_zh,
            kind="Analysis",
            featured=bool(metadata.get("featured", False)),
        )
        if not metadata["draft"]:
            posts.append(post)
    return posts


def _summary_description(snapshot: dict[str, Any]) -> str:
    briefing = snapshot.get("briefing") or {}
    bullets = briefing.get("bullets") or []
    if bullets:
        text = str(bullets[0]).split(" Why it matters:", 1)[0].strip()
        if len(text) > 155:
            text = text[:155].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        return text
    evidence = snapshot.get("evidence_items") or []
    source_count = len({str(item.get("source") or "") for item in evidence if item.get("source")})
    return (
        f"Benchmark Radar collected {len(evidence)} evidence observations from "
        f"{source_count} sources on {snapshot.get('date')}."
    )


def _summary_description_zh(snapshot: dict[str, Any]) -> str | None:
    bullets = (snapshot.get("briefing") or {}).get("bullets_zh") or []
    if not bullets:
        return None
    text = str(bullets[0]).split(" Why it matters:", 1)[0].strip()
    return text[:155].rstrip("，。；：") + ("…" if len(text) > 155 else "")


def _daily_sources(snapshot: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    citations: list[tuple[str, str]] = []
    seen: set[str] = set()
    groups = [snapshot.get("briefing") or {}]
    groups.extend(
        answer
        for group in (snapshot.get("questions") or {}).get("groups") or []
        for answer in group.get("answers") or []
    )
    for group in groups:
        for citation in group.get("citations") or group.get("cited_evidence") or []:
            try:
                url = _safe_url(citation.get("url"))
            except BlogSourceError:
                continue
            if url in seen:
                continue
            seen.add(url)
            title = str(citation.get("title") or citation.get("source") or url).strip()
            citations.append((title, url))
    if citations:
        return tuple(citations)
    for item in snapshot.get("evidence_items") or []:
        try:
            url = _safe_url(item.get("url"))
        except BlogSourceError:
            continue
        if url in seen:
            continue
        seen.add(url)
        citations.append((str(item.get("title") or item.get("source") or url), url))
        if len(citations) == 20:
            break
    return tuple(citations)


def _stats(snapshot: dict[str, Any]) -> str:
    evidence = snapshot.get("evidence_items") or []
    raw_attention = snapshot.get("attention") or []
    attention = (
        raw_attention.get("observations") or []
        if isinstance(raw_attention, dict)
        else raw_attention
    )
    sources = {str(item.get("source") or "") for item in evidence if item.get("source")}
    return "".join(
        (
            f'<div class="content-stat"><strong>{len(evidence):,}</strong>'
            "<span>evidence observations</span></div>",
            f'<div class="content-stat"><strong>{len(sources):,}</strong>'
            "<span>sources represented</span></div>",
            f'<div class="content-stat"><strong>{len(attention):,}</strong>'
            "<span>public-attention signals</span></div>",
        )
    )


def _briefing(snapshot: dict[str, Any], language: str) -> str:
    briefing = snapshot.get("briefing") or {}
    key = "bullets_zh" if language == "zh" else "bullets"
    bullets = briefing.get(key) or (briefing.get("bullets") if language == "zh" else []) or []
    if bullets:
        items = "".join(f'<li class="content-card">{esc(bullet)}</li>' for bullet in bullets)
    else:
        evidence = snapshot.get("evidence_items") or []
        top = evidence[:10]
        rendered: list[str] = []
        for item in top:
            title = esc(item.get("title") or "Untitled")
            url = _optional_safe_url(item.get("url"))
            heading = f'<a href="{esc(url)}">{title}</a>' if url else title
            rendered.append(
                '<li class="content-card">'
                f"{heading}<p>{esc(item.get('source') or 'Unknown source')}</p></li>"
            )
        items = "".join(rendered)
        if not items:
            items = '<li class="content-card">No evidence observations were recorded.</li>'
    heading = "今日简报" if language == "zh" else "Daily briefing"
    return f"""<section class="content-section">
  <div class="content-section-heading"><h2>{heading}</h2></div>
  <ol class="content-index">{items}</ol>
</section>"""


def _stat_line(stat: dict[str, Any]) -> str:
    value = stat.get("value")
    rendered = f"{value:,}" if isinstance(value, (int, float)) else str(value or "—")
    unit = str(stat.get("unit") or "").strip()
    suffix = f" {esc(unit)}" if unit and unit != "count" else ""
    return (
        f"{esc(stat.get('label') or stat.get('id') or 'Statistic')}: "
        f"<strong>{esc(rendered)}{suffix}</strong>"
    )


def _questions(snapshot: dict[str, Any], language: str) -> str:
    questions = snapshot.get("questions") or {}
    groups = questions.get("groups") or []
    if not groups:
        return ""
    parts: list[str] = []
    for group in groups:
        answers: list[str] = []
        for answer in group.get("answers") or []:
            question = answer.get("question_zh") if language == "zh" else answer.get("question")
            question = question or answer.get("question") or "Question"
            signal = answer.get("signal_zh") if language == "zh" else answer.get("signal")
            plain = answer.get("plain_chinese") if language == "zh" else answer.get("plain_english")
            takeaway = answer.get("takeaway_zh") if language == "zh" else answer.get("takeaway")
            counter = (
                answer.get("counter_view_zh") if language == "zh" else answer.get("counter_view")
            )
            confidence = str(answer.get("confidence") or "unrated")
            sufficient = bool(answer.get("sufficient_evidence", True))
            stats = "".join(
                f"<li>{_stat_line(stat)}</li>" for stat in answer.get("cited_stats") or []
            )
            stats_html = f'<ul class="content-list">{stats}</ul>' if stats else ""
            status = "证据不足" if language == "zh" else "Insufficient evidence"
            status_html = f'<span class="content-chip">{status}</span>' if not sufficient else ""
            takeaway_label = "结论" if language == "zh" else "Takeaway"
            counter_label = "另一种解读" if language == "zh" else "Counter-view"
            answers.append(
                '<article class="content-panel">'
                f"<h3>{esc(question)}</h3>"
                '<div class="content-tags"><span class="content-chip">'
                f"{esc(confidence)} confidence</span>"
                f"{status_html}</div>"
                f"<p>{esc(signal or '')}</p><p>{esc(plain or '')}</p>{stats_html}"
                f"<p><strong>{takeaway_label}:</strong> {esc(takeaway or '')}</p>"
                '<p class="content-caveat">'
                f"<strong>{counter_label}:</strong> {esc(counter or '')}</p>"
                "</article>"
            )
        if answers:
            group_title = esc(group.get("title") or "Questions")
            parts.append(
                '<section class="content-section">'
                f'<div class="content-section-heading"><h2>{group_title}</h2></div>'
                + "".join(answers)
                + "</section>"
            )
    return "".join(parts)


def _provenance(snapshot: dict[str, Any], language: str) -> str:
    briefing = snapshot.get("briefing") or {}
    caveat_key = "caveat_zh" if language == "zh" else "caveat"
    caveat = briefing.get(caveat_key) or briefing.get("caveat") or ""
    model = str(briefing.get("model") or "deterministic snapshot summary")
    coverage = (briefing.get("input") or {}).get("coverage") or {}
    injected = int(coverage.get("evidence_injected") or 0)
    total = int(
        coverage.get("corpus_evidence_records") or len(snapshot.get("evidence_items") or [])
    )
    if language == "zh":
        disclosure = (
            f"内容来自已验证的每日快照。简报模型：{model}；输入证据 {injected}/{total} 条。"
        )
        heading = "来源与限制"
    else:
        disclosure = (
            "Built from the validated daily snapshot. "
            f"Briefing model: {model}; evidence supplied: {injected:,} of {total:,}."
        )
        heading = "Provenance and limits"
    return f"""<section class="content-section content-panel">
  <h2>{heading}</h2><p>{esc(disclosure)}</p>
  <p class="content-caveat">{esc(caveat)}</p>
</section>"""


def _daily_post(snapshot: dict[str, Any]) -> BlogPost:
    day = str(snapshot["date"])
    briefing = snapshot.get("briefing") or {}
    translated = bool(briefing.get("bullets_zh")) or any(
        answer.get("signal_zh") or answer.get("plain_chinese")
        for group in (snapshot.get("questions") or {}).get("groups") or []
        for answer in group.get("answers") or []
    )
    body_en = _briefing(snapshot, "en") + _questions(snapshot, "en") + _provenance(snapshot, "en")
    body_zh = None
    if translated:
        body_zh = (
            _briefing(snapshot, "zh") + _questions(snapshot, "zh") + _provenance(snapshot, "zh")
        )
    generated = str(snapshot.get("generated_at") or day)
    updated = generated[:10] if len(generated) >= 10 else day
    return BlogPost(
        slug=day,
        title=f"Daily AI benchmark brief — {day}",
        description=_summary_description(snapshot),
        published=day,
        updated=updated,
        author="Benchmark Radar",
        tags=("daily brief", "AI benchmarks", "evaluation"),
        sources=_daily_sources(snapshot),
        body_en=body_en,
        body_zh=body_zh,
        title_zh=f"AI Benchmark 每日简报 — {day}" if translated else None,
        description_zh=_summary_description_zh(snapshot),
        kind="Daily brief",
    )


def _source_list(post: BlogPost, language: str) -> str:
    if not post.sources:
        return ""
    heading = "证据来源" if language == "zh" else "Evidence sources"
    links = "".join(
        f'<li><a href="{esc(url)}">{esc(title)}</a></li>' for title, url in post.sources
    )
    return f"""<section class="content-section">
  <div class="content-section-heading"><h2>{heading}</h2></div>
  <ol class="content-evidence">{links}</ol>
</section>"""


def _post_html(post: BlogPost, snapshot: dict[str, Any] | None = None) -> str:
    tags = "".join(f'<span class="content-chip">{esc(tag)}</span>' for tag in post.tags)
    stats = _stats(snapshot) if snapshot is not None else ""

    def language_body(language: str, content: str, *, hidden: bool) -> str:
        title = post.title_zh if language == "zh" and post.title_zh else post.title
        description = (
            post.description_zh if language == "zh" and post.description_zh else post.description
        )
        hidden_attr = " hidden" if hidden else ""
        return f"""<div data-lang-content="{language}"{hidden_attr}>
<header class="content-hero">
  <p class="eyebrow">{esc(post.kind)}</p>
  <h1>{esc(title)}</h1>
  <p class="content-lede">{esc(description)}</p>
  <p class="content-meta">{esc(post.published)} · {esc(post.author)}</p>
  <div class="content-tags">{tags}</div>
</header>
{f'<div class="content-stats">{stats}</div>' if stats else ""}
<div class="content-prose">{content}</div>
{_source_list(post, language)}
</div>"""

    body = language_body("en", post.body_en, hidden=False)
    if post.body_zh:
        body += language_body("zh", post.body_zh, hidden=True)
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "@id": post.canonical,
        "headline": post.title,
        "description": post.description,
        "url": post.canonical,
        "mainEntityOfPage": post.canonical,
        "datePublished": post.published,
        "dateModified": post.updated,
        "inLanguage": ["en", "zh-Hans"] if post.body_zh else "en",
        "author": {
            "@type": "Organization" if post.author == "Benchmark Radar" else "Person",
            "name": post.author,
        },
        "publisher": {"@id": f"{SITE_URL}/#organization"},
        "citation": [url for _, url in post.sources],
        "keywords": list(post.tags),
    }
    return render_page(
        title=f"{post.title} | Benchmark Radar",
        description=post.description,
        canonical=post.canonical,
        active="blog",
        body=body,
        schemas=(
            schema,
            breadcrumb_schema(
                ("Benchmark Radar", f"{SITE_URL}/"),
                ("Blog", f"{SITE_URL}{BLOG_PATH}"),
                (post.title, post.canonical),
                canonical=post.canonical,
            ),
        ),
        og_type="article",
        translated=post.body_zh is not None,
    )


def _post_card(post: BlogPost) -> str:
    return f"""<li><article class="content-card">
  <div><span class="content-chip">{esc(post.kind)}</span>
  <h2><a href="{esc(post.canonical)}">{esc(post.title)}</a></h2></div>
  <time class="content-meta" datetime="{esc(post.published)}">{esc(post.published)}</time>
  <p>{esc(post.description)}</p>
</article></li>"""


def _index_html(posts: list[BlogPost], *, archive: bool) -> str:
    canonical_path = BLOG_ARCHIVE_PATH if archive else BLOG_PATH
    canonical = SITE_URL + canonical_path
    shown = posts if archive else posts[:_LATEST_POST_LIMIT]
    if shown:
        cards = "".join(_post_card(post) for post in shown)
    else:
        cards = '<li class="content-panel">No posts are available yet.</li>'
    if archive:
        title = "Blog archive · Benchmark Radar"
        heading = "Every evidence brief and analysis"
        description = "A complete archive of Benchmark Radar daily briefs and reviewed analysis."
        action = f'<a class="secondary-link" href="{SITE_URL}{BLOG_PATH}">Latest posts</a>'
    else:
        title = "AI benchmark evidence blog | Benchmark Radar"
        heading = "What changed in AI evaluation—and why it matters"
        description = (
            "Daily evidence briefs and reviewed analysis about AI benchmarks, evaluation methods, "
            "reported scores, and the limits behind each claim."
        )
        action = f'<a class="secondary-link" href="{SITE_URL}{BLOG_ARCHIVE_PATH}">Full archive</a>'
    body = f"""<header class="content-hero">
  <p class="eyebrow">Evidence blog</p><h1>{heading}</h1>
  <p class="content-lede">{description}</p>
  <div class="content-actions">{action}</div>
</header>
<ol class="content-index">{cards}</ol>"""
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": index, "url": post.canonical}
            for index, post in enumerate(shown, start=1)
        ],
    }
    return render_page(
        title=title,
        description=description,
        canonical=canonical,
        active="blog",
        body=body,
        schemas=(
            webpage_schema(title=title, description=description, canonical=canonical),
            item_list,
            breadcrumb_schema(
                ("Benchmark Radar", f"{SITE_URL}/"),
                (("Blog archive" if archive else "Blog"), canonical),
                canonical=canonical,
            ),
        ),
    )


def write_blog(
    snapshots: list[dict[str, Any]],
    site_dir: Path,
    *,
    source_dir: Path = DEFAULT_BLOG_SOURCE_DIR,
) -> dict[str, Any]:
    """Write the blog atomically from source snapshots and reviewed Markdown."""
    manual = load_manual_posts(source_dir)
    daily = [_daily_post(snapshot) for snapshot in snapshots]
    posts = manual + daily
    slugs: set[str] = set()
    for post in posts:
        if post.slug in slugs:
            raise BlogSourceError(f"duplicate blog slug {post.slug!r}")
        slugs.add(post.slug)
    posts.sort(key=lambda post: (post.published, post.featured, post.slug), reverse=True)
    snapshot_by_day = {str(snapshot["date"]): snapshot for snapshot in snapshots}

    output_dir = site_dir / "blog"
    staging = site_dir / "blog.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    (staging / "index.html").write_text(_index_html(posts, archive=False), encoding="utf-8")
    archive_dir = staging / "archive"
    archive_dir.mkdir()
    (archive_dir / "index.html").write_text(_index_html(posts, archive=True), encoding="utf-8")
    for post in posts:
        page_dir = staging / post.slug
        page_dir.mkdir()
        (page_dir / "index.html").write_text(
            _post_html(post, snapshot_by_day.get(post.slug)), encoding="utf-8"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    staging.rename(output_dir)

    latest = max((post.updated for post in posts), default=None)
    sitemap_entries: list[tuple[str, str | None]] = [
        (BLOG_PATH, latest),
        (BLOG_ARCHIVE_PATH, latest),
    ]
    sitemap_entries.extend((post.path, post.updated) for post in posts)
    return {
        "page_count": len(posts) + 2,
        "post_count": len(posts),
        "daily_count": len(daily),
        "manual_count": len(manual),
        "sitemap_entries": sitemap_entries,
        "manual_feed_entries": [post.feed_entry() for post in manual],
        "output_dir": output_dir,
    }
