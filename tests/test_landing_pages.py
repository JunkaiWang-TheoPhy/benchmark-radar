import json
from pathlib import Path

from benchmark_radar.feed import SITE_URL
from benchmark_radar.landing_pages import LANDING_PATHS, write_landing_pages


def _dashboard() -> dict:
    return {
        "latest_date": "2026-08-29",
        "snapshot_count": 2,
        "model_card_leaderboard": {
            "model_card_count": 12,
            "benchmark_count": 2,
            "organization_count": 3,
            "entries": [
                {
                    "rank": 1,
                    "name": "Alpha & Reasoning",
                    "card_count": 8,
                    "organization_count": 3,
                },
                {
                    "rank": 2,
                    "name": "Beta Bench",
                    "card_count": 4,
                    "organization_count": 2,
                },
            ],
        },
        "corpus": {
            "observation_count": 42,
            "entity_count": 30,
            "edge_count": 24,
        },
        "days": [
            {
                "date": "2026-08-28",
                "evidence_count": 6,
                "source_counts": {"GitHub": 4, "arXiv": 2},
            },
            {
                "date": "2026-08-29",
                "evidence_count": 9,
                "source_counts": {"GitHub": 6, "arXiv": 3},
            },
        ],
    }


def _read(site_dir: Path, slug: str) -> str:
    return (site_dir / slug / "index.html").read_text(encoding="utf-8")


def _jsonld_blocks(page: str) -> list[dict]:
    return [
        json.loads(chunk.split(">", 1)[1].split("</script>", 1)[0])
        for chunk in page.split('type="application/ld+json"')[1:]
    ]


def test_writes_three_static_content_rich_pages(tmp_path):
    report = write_landing_pages(_dashboard(), tmp_path, benchmark_count=1173)

    assert report["page_count"] == 3
    for slug in LANDING_PATHS:
        page = _read(tmp_path, slug)
        assert f'<link rel="canonical" href="{SITE_URL}{LANDING_PATHS[slug]}">' in page
        assert '<meta name="robots" content="index,follow,max-image-preview:large">' in page
        assert "Open the interactive view" in page
        assert "Browse benchmark pages" in page
        assert 'class="masthead"' in page
        assert 'href="/assets/styles.css"' in page
        assert 'href="/assets/content.css"' in page
        assert "<style>" not in page
        assert "font-family:" not in page


def test_each_page_has_unique_server_delivered_metadata(tmp_path):
    write_landing_pages(_dashboard(), tmp_path, benchmark_count=1173)
    pages = [_read(tmp_path, slug) for slug in LANDING_PATHS]
    titles = [page.split("<title>", 1)[1].split("</title>", 1)[0] for page in pages]
    descriptions = [
        page.split('<meta name="description" content="', 1)[1].split('">', 1)[0] for page in pages
    ]
    assert len(set(titles)) == 3
    assert len(set(descriptions)) == 3


def test_leaderboard_page_shows_result_and_interpretation(tmp_path):
    write_landing_pages(_dashboard(), tmp_path)
    page = _read(tmp_path, "leaderboard")

    assert "Which benchmarks do frontier labs actually report?" in page
    assert "Alpha &amp; Reasoning" in page
    assert "adoption ranking, not a claim" in page
    assert "view=leaderboard&amp;lq=Alpha+%26+Reasoning" in page


def test_trends_page_contains_small_recent_summary_not_dashboard_json(tmp_path):
    write_landing_pages(_dashboard(), tmp_path)
    page = _read(tmp_path, "trends")

    assert "2026-08-29" in page and "2026-08-28" in page
    assert "Daily discovery volume" in page
    assert "data/radar.json" not in page


def test_explore_page_distinguishes_catalog_graph_and_download(tmp_path):
    write_landing_pages(_dashboard(), tmp_path, benchmark_count=1173)
    page = _read(tmp_path, "explore")

    assert "1,173" in page
    assert "evidence graph entities" in page
    assert f'href="{SITE_URL}/benchmarks/"' in page
    assert f'href="{SITE_URL}/?view=map"' in page
    assert f'href="{SITE_URL}/data/radar.json"' in page


def test_jsonld_matches_visible_canonical_and_breadcrumb(tmp_path):
    write_landing_pages(_dashboard(), tmp_path)
    page = _read(tmp_path, "leaderboard")
    blocks = _jsonld_blocks(page)

    assert [block["@type"] for block in blocks] == ["WebPage", "BreadcrumbList"]
    assert blocks[0]["url"] == f"{SITE_URL}/leaderboard/"
    assert blocks[1]["itemListElement"][-1]["item"] == f"{SITE_URL}/leaderboard/"


def test_output_is_deterministic_and_escapes_dynamic_values(tmp_path):
    dashboard = _dashboard()
    dashboard["model_card_leaderboard"]["entries"][0]["name"] = "<script>alert(1)</script>"
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_landing_pages(dashboard, first)
    write_landing_pages(dashboard, second)

    for slug in LANDING_PATHS:
        assert (first / slug / "index.html").read_bytes() == (
            second / slug / "index.html"
        ).read_bytes()
    page = _read(first, "leaderboard")
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
