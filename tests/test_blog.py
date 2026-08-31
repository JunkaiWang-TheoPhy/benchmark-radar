import json
from pathlib import Path

import pytest

from benchmark_radar.blog import BlogSourceError, load_manual_posts, write_blog
from benchmark_radar.feed import SITE_URL


def _snapshot(day: str = "2026-08-30", *, briefing: bool = True, translated: bool = True) -> dict:
    value = {
        "date": day,
        "generated_at": f"{day}T10:10:24+00:00",
        "evidence_items": [
            {
                "title": "Alpha & Safety",
                "url": "https://example.test/alpha",
                "source": "arXiv",
                "categories": ["benchmark"],
            }
        ],
        "attention": {"observations": [{"source": "Hacker News"}]},
    }
    if briefing:
        value["briefing"] = {
            "bullets": ["Alpha tests independent agent logging. Why it matters: audits."],
            "citations": [
                {
                    "title": "Alpha source",
                    "url": "https://example.test/alpha",
                    "source": "arXiv",
                }
            ],
            "caveat": "Publisher-authored evidence; inspect the source.",
            "model": "gpt-test",
            "input": {"coverage": {"evidence_injected": 1, "corpus_evidence_records": 1}},
        }
        if translated:
            value["briefing"]["bullets_zh"] = ["Alpha 测试独立智能体日志。"]
            value["briefing"]["caveat_zh"] = "证据来自发布者；请检查原始来源。"
        value["questions"] = {
            "groups": [
                {
                    "title": "What arrived",
                    "answers": [
                        {
                            "question": "What changed?",
                            "signal": "Independent logs became an evaluation signal.",
                            "plain_english": "The system checks actions outside the model.",
                            "takeaway": "Keep an independent log.",
                            "counter_view": "One artifact is not field-wide evidence.",
                            "confidence": "medium",
                            "sufficient_evidence": True,
                            "signal_zh": "独立日志成为评估信号。" if translated else None,
                            "plain_chinese": "系统在模型之外检查操作。" if translated else None,
                            "takeaway_zh": "保留独立日志。" if translated else None,
                            "counter_view_zh": "单个项目不能代表整个领域。" if translated else None,
                            "cited_stats": [
                                {"label": "records reviewed", "value": 1, "unit": "count"}
                            ],
                            "cited_evidence": value["briefing"]["citations"],
                        }
                    ],
                }
            ]
        }
    return value


def _read(site_dir: Path, *parts: str) -> str:
    return (site_dir.joinpath(*parts) / "index.html").read_text(encoding="utf-8")


def _jsonld_blocks(page: str) -> list[dict]:
    return [
        json.loads(chunk.split(">", 1)[1].split("</script>", 1)[0])
        for chunk in page.split('type="application/ld+json"')[1:]
    ]


def test_daily_blog_is_server_delivered_bilingual_and_uses_radar_style(tmp_path):
    report = write_blog([_snapshot()], tmp_path)

    assert report["page_count"] == 3
    assert report["daily_count"] == 1
    page = _read(tmp_path, "blog", "2026-08-30")
    assert '<link rel="canonical" href="https://benchmark-radar.org/blog/2026-08-30/">' in page
    assert 'href="/assets/styles.css"' in page
    assert 'href="/assets/content.css"' in page
    assert "<style>" not in page
    assert "font-family:" not in page
    assert 'data-lang-content="en"' in page
    assert 'data-lang-content="zh" hidden' in page
    assert "Alpha 测试独立智能体日志。" in page
    assert "Briefing model: gpt-test; evidence supplied: 1 of 1." in page
    schema = _jsonld_blocks(page)[0]
    assert schema["@type"] == "BlogPosting"
    assert schema["citation"] == ["https://example.test/alpha"]
    assert schema["inLanguage"] == ["en", "zh-Hans"]


def test_snapshot_without_ai_briefing_gets_deterministic_evidence_fallback(tmp_path):
    snapshot = _snapshot(briefing=False)
    snapshot["evidence_items"][0]["url"] = "javascript:alert(1)"
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_blog([snapshot], first)
    write_blog([snapshot], second)

    assert (first / "blog" / "2026-08-30" / "index.html").read_bytes() == (
        second / "blog" / "2026-08-30" / "index.html"
    ).read_bytes()
    page = _read(first, "blog", "2026-08-30")
    assert "Alpha &amp; Safety" in page
    assert 'href="javascript:' not in page
    assert "deterministic snapshot summary" in page
    assert 'id="lang-toggle"' not in page


def _manual_source(source_dir: Path, *, draft: bool = False) -> Path:
    source_dir.mkdir(parents=True)
    path = source_dir / "read-adoption-rank.md"
    path.write_text(
        f"""---
title: How to read an adoption ranking
title_zh: 如何阅读采用率排名
description: Reporting frequency is useful, but it is not benchmark quality.
description_zh: 报告频率有用，但它不代表 benchmark 质量。
published: 2026-08-29
updated: 2026-08-30
author: Koutian Wu
tags: [model cards, interpretation]
featured: true
draft: {str(draft).lower()}
sources:
  - title: Benchmark Radar methodology
    url: https://benchmark-radar.org/#rubric
---
## Adoption is not quality

<script>alert(1)</script>

[Unsafe](javascript:alert(2))
""",
        encoding="utf-8",
    )
    (source_dir / "read-adoption-rank.zh.md").write_text(
        "## 采用率并不等于质量\n\n先检查证据。\n", encoding="utf-8"
    )
    return path


def test_reviewed_markdown_and_translation_share_one_safe_canonical_page(tmp_path):
    source_dir = tmp_path / "content"
    _manual_source(source_dir)

    report = write_blog([], tmp_path / "site", source_dir=source_dir)

    assert report["manual_count"] == 1
    assert report["manual_feed_entries"][0]["title"] == "How to read an adoption ranking"
    page = _read(tmp_path / "site", "blog", "read-adoption-rank")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)</script>" not in page
    assert 'href="javascript:' not in page
    assert "采用率并不等于质量" in page
    assert page.count('<link rel="canonical"') == 1
    schema = _jsonld_blocks(page)[0]
    assert schema["author"] == {"@type": "Person", "name": "Koutian Wu"}
    assert schema["datePublished"] == "2026-08-29"


def test_drafts_are_validated_but_not_published(tmp_path):
    source_dir = tmp_path / "content"
    _manual_source(source_dir, draft=True)

    posts = load_manual_posts(source_dir)
    report = write_blog([], tmp_path / "site", source_dir=source_dir)

    assert posts == []
    assert report["manual_count"] == 0
    assert not (tmp_path / "site" / "blog" / "read-adoption-rank").exists()


def test_manual_sources_fail_loudly_on_missing_gate_or_unsafe_slug(tmp_path):
    source_dir = tmp_path / "content"
    path = _manual_source(source_dir)
    path.write_text(path.read_text(encoding="utf-8").replace("draft: false\n", ""))
    with pytest.raises(BlogSourceError, match="draft must be an explicit boolean"):
        load_manual_posts(source_dir)

    path.rename(source_dir / "Unsafe Name.md")
    with pytest.raises(BlogSourceError, match="lowercase hyphenated slug"):
        load_manual_posts(source_dir)


def test_blog_report_exposes_complete_dated_sitemap_entries(tmp_path):
    report = write_blog([_snapshot()], tmp_path)

    assert report["sitemap_entries"] == [
        ("/blog/", "2026-08-30"),
        ("/blog/archive/", "2026-08-30"),
        ("/blog/2026-08-30/", "2026-08-30"),
    ]
    index = _read(tmp_path, "blog")
    archive = _read(tmp_path, "blog", "archive")
    assert f'href="{SITE_URL}/blog/2026-08-30/"' in index
    assert f'href="{SITE_URL}/blog/2026-08-30/"' in archive


def test_duplicate_snapshot_dates_cannot_overwrite_a_blog_post(tmp_path):
    with pytest.raises(BlogSourceError, match="duplicate blog slug '2026-08-30'"):
        write_blog([_snapshot(), _snapshot()], tmp_path)
