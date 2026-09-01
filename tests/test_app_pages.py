"""The published view pages must be the dashboard, and must say what they are.

The bug these guard against is not a crash. It is a page that loads fine and
describes something else: a `/leaderboard/` carrying the homepage's title, or a
thin summary served under a canonical that points search traffic at it. Every
assertion below is about agreement between what a page claims and what it shows.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from benchmark_radar.app_pages import (
    APP_VIEWS,
    AppPageError,
    load_category_colors,
    load_view_seo,
    render_app_page,
    write_app_pages,
)
from benchmark_radar.feed import SITE_URL

SITE = Path(__file__).resolve().parents[1] / "site"


def _dashboard() -> dict:
    return {
        "model_card_leaderboard": {
            "measures": "How many curated model cards report each benchmark.",
            "entries": [
                {"rank": 1, "name": "Alpha & Reasoning", "card_count": 20},
                {"rank": 2, "name": "Beta Bench", "card_count": 10},
                {"rank": 3, "name": "Gamma", "card_count": 1},
                {"rank": 4, "name": "Unreported", "card_count": 0},
            ],
        },
        "days": [
            {
                "date": "2026-08-30",
                "category_trends": {
                    "benchmark": {
                        "count": 7,
                        "total_count": 9,
                        "delta": 3,
                        "baseline": 4.5,
                        "momentum": 0.5,
                        "cumulative": 1234,
                    },
                    "agentic": {
                        "count": 2,
                        "total_count": 2,
                        "delta": None,
                        "baseline": None,
                        "momentum": None,
                        "cumulative": 40,
                    },
                },
            }
        ],
        "corpus": {
            "aggregates": {
                "entity_types": {
                    "artifact": 4645,
                    "organization": 1775,
                    "person": 13907,
                    "source": 12,
                    "topic": 5,
                }
            }
        },
    }


def _write(tmp_path: Path, dashboard: dict) -> dict:
    (tmp_path / "assets").mkdir(parents=True, exist_ok=True)
    for name in ("app.js", "glyphs.js"):
        (tmp_path / "assets" / name).write_text(
            (SITE / "assets" / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "index.html").write_text(
        (SITE / "index.html").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return write_app_pages(dashboard, tmp_path)


def test_view_seo_is_read_from_the_script_the_browser_uses():
    seo = load_view_seo(SITE / "assets" / "app.js")
    assert {view: entry["canonical"] for view, entry in seo.items()} == {
        "today": "/",
        "leaderboard": "/leaderboard/",
        "trends": "/trends/",
        "map": "/explore/",
    }
    assert all(entry["title"] and entry["description"] for entry in seo.values())


def test_category_palette_is_read_from_the_script_the_browser_uses():
    colors, fallbacks = load_category_colors(SITE / "assets" / "glyphs.js")
    assert colors["benchmark"].startswith("#")
    assert fallbacks and all(color.startswith("#") for color in fallbacks)


def test_every_view_is_published_at_its_own_path(tmp_path):
    report = _write(tmp_path, _dashboard())
    assert report["paths"] == ["/leaderboard/", "/trends/", "/explore/"]
    for path in report["paths"]:
        assert (tmp_path / path.strip("/") / "index.html").exists()
    assert not list(tmp_path.glob("*/index.html.tmp"))


def test_each_page_declares_the_url_it_is_served_at(tmp_path):
    _write(tmp_path, _dashboard())
    seo = load_view_seo(SITE / "assets" / "app.js")
    for view in APP_VIEWS:
        path = seo[view]["canonical"]
        page = (tmp_path / path.strip("/") / "index.html").read_text(encoding="utf-8")
        canonical = f'<link rel="canonical" href="{SITE_URL}{path}">'
        assert page.count(canonical) == 1
        assert page.count("<title>") == 1
        assert f"<title>{seo[view]['title']}</title>" in page
        assert f'<meta property="og:url" content="{SITE_URL}{path}">' in page


def test_only_the_named_view_is_open(tmp_path):
    _write(tmp_path, _dashboard())
    for path, open_id in (
        ("leaderboard", "leaderboard-view"),
        ("trends", "trends-view"),
        ("explore", "map-view"),
    ):
        page = (tmp_path / path / "index.html").read_text(encoding="utf-8")
        sections = re.findall(r'<section class="view" id="([\w-]+)"([^>]*)>', page)
        assert sections, "no view sections found"
        visible = [name for name, attrs in sections if "hidden" not in attrs]
        assert visible == [open_id]


def test_exactly_one_heading_is_visible_per_page(tmp_path):
    """Four h1s live in the document, one per view, and three are inside hidden
    sections. A page with two visible h1s or none is a page whose outline lies."""
    _write(tmp_path, _dashboard())
    for path in ("leaderboard", "trends", "explore"):
        page = (tmp_path / path / "index.html").read_text(encoding="utf-8")
        open_section = re.search(
            r'<section class="view" id="[\w-]+"(?![^>]*hidden)[^>]*>(.*?)\n      </section>',
            page,
            re.DOTALL,
        )
        assert open_section, f"no open view section in /{path}/"
        assert len(re.findall(r"<h1[ >]", open_section.group(1))) == 1


def test_pages_carry_breadcrumb_and_webpage_schema(tmp_path):
    _write(tmp_path, _dashboard())
    page = (tmp_path / "leaderboard" / "index.html").read_text(encoding="utf-8")
    blocks = [
        json.loads(block)
        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', page, re.DOTALL
        )
    ]
    types = {block.get("@type") for block in blocks}
    assert {"WebPage", "BreadcrumbList"} <= types
    crumb = next(block for block in blocks if block["@type"] == "BreadcrumbList")
    assert [item["item"] for item in crumb["itemListElement"]] == [
        f"{SITE_URL}/",
        f"{SITE_URL}/leaderboard/",
    ]


def test_no_page_ships_a_second_url_for_itself(tmp_path):
    _write(tmp_path, _dashboard())
    for path in ("leaderboard", "trends", "explore"):
        page = (tmp_path / path / "index.html").read_text(encoding="utf-8")
        assert "?view=" not in page


def test_seeded_rows_match_what_the_renderer_would_draw(tmp_path):
    _write(tmp_path, _dashboard())
    page = (tmp_path / "leaderboard" / "index.html").read_text(encoding="utf-8")
    rows = re.findall(r'<li class="leaderboard-top-row">(.*?)</li>', page)
    # The zero-count entry is filtered out, exactly as renderLeaderboardTop does.
    assert len(rows) == 3
    assert "Alpha &amp; Reasoning" in rows[0]
    assert "20 model cards" in rows[0]
    assert "width:100.0%" in rows[0]
    assert "width:50.0%" in rows[1]
    # Singular noun at one, same as metricLabel.
    assert "1 model card<" in rows[2]
    assert "How many curated model cards report each benchmark." in page


def test_seeded_domain_cards_match_what_the_renderer_would_draw(tmp_path):
    _write(tmp_path, _dashboard())
    page = (tmp_path / "trends" / "index.html").read_text(encoding="utf-8")
    cards = re.findall(r'<article class="domain-card([^"]*)">(.*?)</article>', page)
    assert [state for state, _ in cards] == [" is-up", ""]
    benchmark, agentic = (body for _, body in cards)
    assert "<h3>benchmark</h3>" in benchmark
    assert "<dd>+3</dd>" in benchmark
    assert "<dd>4.50</dd>" in benchmark
    assert "<dd>+50%</dd>" in benchmark
    assert "<dd>1,234</dd>" in benchmark
    assert "<dd>2</dd>" in benchmark  # also updated, not counted above
    # A null delta claims no direction and no baseline.
    assert "<dd>not comparable</dd>" in agentic
    assert "<dd>not enough history</dd>" in agentic


def test_seeded_overview_matches_what_the_renderer_would_draw(tmp_path):
    _write(tmp_path, _dashboard())
    page = (tmp_path / "explore" / "index.html").read_text(encoding="utf-8")
    card = re.search(r'<article class="map-insight-card">(.*?)</article>', page)
    assert card
    assert "<h2>At a glance</h2>" in card.group(1)
    assert "<span>Authors</span><strong>13,907</strong>" in card.group(1)


def test_a_view_with_no_data_is_not_published(tmp_path):
    """A URL that describes a ranking nobody can see is worse than no URL."""
    dashboard = _dashboard()
    dashboard["model_card_leaderboard"] = {}
    report = _write(tmp_path, dashboard)
    assert report["paths"] == ["/trends/", "/explore/"]
    assert not (tmp_path / "leaderboard").exists()


def test_a_moved_anchor_fails_the_build_instead_of_shipping(tmp_path):
    seo = load_view_seo(SITE / "assets" / "app.js")
    document = (SITE / "index.html").read_text(encoding="utf-8")
    template = document.replace("<!-- br:page-jsonld -->", "")
    with pytest.raises(AppPageError, match="page JSON-LD marker"):
        render_app_page(template, "leaderboard", seo["leaderboard"], {})


def test_a_missing_seed_container_fails_the_build(tmp_path):
    seo = load_view_seo(SITE / "assets" / "app.js")
    template = (SITE / "index.html").read_text(encoding="utf-8")
    with pytest.raises(AppPageError, match="leaderboard seed container"):
        render_app_page(template, "leaderboard", seo["leaderboard"], {"<ol id='gone'></ol>": "x"})


def test_rebuilding_the_same_data_produces_the_same_bytes(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    _write(first, _dashboard())
    _write(second, _dashboard())
    for path in ("leaderboard", "trends", "explore"):
        assert (first / path / "index.html").read_bytes() == (
            second / path / "index.html"
        ).read_bytes()


def test_navigation_agrees_between_the_shell_and_the_dashboard():
    """site_shell.py hardcodes its own nav, which is how it drifted from the
    dashboard in the first place. Drift should fail here, not ship."""
    from benchmark_radar.site_shell import navigation

    shell_links = set(re.findall(r'href="([^"]+)"', navigation("leaderboard")))
    document = (SITE / "index.html").read_text(encoding="utf-8")
    nav_block = re.search(r'<nav class="view-nav".*?</nav>', document, re.DOTALL)
    assert nav_block
    page_links = {SITE_URL + link for link in re.findall(r'href="(/[^"]*)"', nav_block.group(0))}
    # Today is a button in the dashboard and a link in the article shell, so the
    # root is the one entry the two are allowed to disagree about.
    assert page_links == shell_links - {f"{SITE_URL}/"}


def test_a_failed_boot_keeps_the_seeded_rows_and_leads_with_the_error():
    """A data outage must not turn a published URL into an empty page.

    /leaderboard/ promises a ranking in its title, its canonical and the
    sitemap. Hiding every view on a fetch failure would leave a shell behind
    that promise: a broken page to a reader, a missing page to a crawler. The
    rows the page shipped with are still true, so they stay, and the banner
    moves above them so nobody reads them as fresh.
    """
    script = (SITE / "assets" / "app.js").read_text(encoding="utf-8")
    # The boot handler is the one that reveals the error state.
    catch = next(
        block
        for block in script.split("} catch (error) {")[1:]
        if 'byId("error-state")' in block.split("\n  }", 1)[0]
    ).split("\n  }", 1)[0]

    # A view survives only when it is the one being shown and it carries a seed.
    assert 'section.id === `${state.view}-view` && section.querySelector("[data-seed]")' in catch
    assert "section.hidden = !seeded;" in catch
    assert "banner.hidden = false;" in catch
    assert "if (survivor) survivor.before(banner);" in catch


def test_every_seeded_container_is_one_the_renderer_already_owns(tmp_path):
    """The seed has to land in the host the renderer writes to.

    Seeding anywhere else would leave a second copy on screen once the data
    loads, because the renderers replace their host's children rather than
    merging into them.
    """
    _write(tmp_path, _dashboard())
    script = (SITE / "assets" / "app.js").read_text(encoding="utf-8")

    seen = set()
    for path in ("leaderboard", "trends", "explore"):
        page = (tmp_path / path / "index.html").read_text(encoding="utf-8")
        ids = re.findall(r'id="([a-z-]+)"[^>]*\bdata-seed\b', page)
        assert ids, path
        seen.update(ids)
    for element_id in sorted(seen):
        assert f'byId("{element_id}")' in script or f'"{element_id}"' in script, element_id
